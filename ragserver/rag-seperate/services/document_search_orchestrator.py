import logging
import json
from typing import Dict, Any, List, Set
from sentence_transformers import SentenceTransformer, util
import re
from domain.interfaces import IDocumentSearchOrchestrator, ISearchService, IFilterService, IQdrantClient
from services.search_service import SearchConfig
from config.settings import Settings

logger = logging.getLogger(__name__)


class DocumentSearchOrchestrator(IDocumentSearchOrchestrator):
    def __init__(
        self,
        qdrant_client: IQdrantClient,
        search_service: ISearchService,
        filter_service: IFilterService,
        settings: Settings
    ):
        self.qdrant_client = qdrant_client
        self.search_service = search_service
        self.filter_service = filter_service
        self.settings = settings
        self.semantic_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
    
    def _extract_negative_conditions(self, query_text: str) -> List[str]:
        negative_indicators = [
            r'沒有',
            r'未',
            r'無',
            r'不曾',
            r'從未',
            r'並未',
            r'未曾',
            r'不',
            r'否認',
            r'拒絕'
        ]
        
        negative_conditions = []
        
        for neg_word in negative_indicators:
            pattern = rf'{neg_word}([^，。！？；\s]{{2,20}})'
            matches = re.finditer(pattern, query_text)
            
            for match in matches:
                captured_content = match.group(1)
                if len(captured_content) >= 2:
                    positive_statement = f"有{captured_content}"
                    negative_conditions.append(positive_statement)
                    logger.info(f"檢測到負面條件: '{neg_word}{captured_content}' -> 正面陳述: '{positive_statement}'")
        
        return negative_conditions
    
    async def orchestrate_search(
        self,
        collection: str,
        query_text: str,
        mode: str,
        limit: int,
        logic: str = "AND"
    ) -> List[Dict[str, Any]]:
        structured_filter_lst = await self.filter_service.extract_filter_conditions(query_text)
        """
        structured_filter_lst = [
  {
    "defendants": [
      {
        "has_new_old_law_issue": True,
        "new_old_law_disputed_article": "洗錢防制法",
        "has_previous_instance": True,
        "is_reversed_and_remanded": True,
        "is_sentence_reduced": True,
        "is_law_article_changed_from_previous": True,
        "changed_law_articles": [
          "洗錢防制法"
        ]
      }
    ],
    "case_metadata": {
      "second_instance": True,
      "case_type": "刑法"
    },
    "B_claim": "二審主張依詐欺犯罪危害防制條例第47條請求減輕其刑",
    "summary_type": [
      "B_claim"
    ]
  },
  {
    "defendants": [
      {
        "has_new_old_law_issue": True,
        "new_old_law_disputed_article": "洗錢防制法",
        "has_previous_instance": True,
        "is_reversed_and_remanded": True,
        "is_sentence_reduced": True,
        "is_law_article_changed_from_previous": True,
        "changed_law_articles": [
          "洗錢防制法"
        ]
      }
    ],
    "case_metadata": {
      "second_instance": True,
      "case_type": "刑法"
    },
    "E_legal_eval": "二審就洗錢防制法部分適用舊法（從舊從輕），撤銷原判決並改判減輕刑度",
    "summary_type": [
      "E_legal_eval"
    ]
  }
]
        """
        logger.info("=" * 50)
        logger.info(f"過濾條件:\n{json.dumps(structured_filter_lst, ensure_ascii=False, indent=2)}")
        logger.info("=" * 50)
        
        summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval"]
        
        logic = logic.upper()
        if logic not in ["AND", "OR"]:
            logic = "AND"
        
        top_k = 15
        
        condition_jid_sets: List[Set[str]] = []
        jid_score_map: Dict[str, float] = {}
        
        for structured_filter in structured_filter_lst:
            qdrant_filter = self.filter_service.to_qdrant_filter(structured_filter)
            structured_filter_highlight = structured_filter.copy()
            structured_filter_highlight["summary_type"] = "case_highlights"
            qdrant_filter_highlight = self.filter_service.to_qdrant_filter(structured_filter_highlight)
            structured_filter_case_fact_summary = structured_filter.copy()
            structured_filter_case_fact_summary["summary_type"] = "case_fact_summary"
            qdrant_filter_case_fact_summary = self.filter_service.to_qdrant_filter(structured_filter_case_fact_summary)
            qdrant_filter_dict = qdrant_filter.model_dump(exclude_none=True) if qdrant_filter else None
            qdrant_filter_lst = [qdrant_filter]
            
            logger.info("=" * 50)
            logger.info(f"Qdrant 過濾條件:\n{json.dumps(qdrant_filter_dict, ensure_ascii=False, indent=2)}")
            logger.info("=" * 50)
            logger.info(f"搜尋請求: collection={collection}, query='{query_text}', mode={mode}, logic={logic}")
            logger.info("=" * 50)

            reconstructed_query = ""
            field_type = None
            for field in summary_fields:
                if field in structured_filter and structured_filter[field]:
                    extracted_value = structured_filter[field]
                    if len(extracted_value) < 10:
                        reconstructed_query = query_text
                        logger.info(f"欄位 '{field}' 值過短 ('{extracted_value}')，使用原始查詢進行語義搜尋")
                    else:
                        reconstructed_query = extracted_value
                    field_type = field
                    break

            # 負面條件過濾
            negative_conditions = self._extract_negative_conditions(reconstructed_query)
            negative_embeddings = None
            similarity_threshold = 0.7
            if negative_conditions:
                logger.info(f"啟用通用負面條件過濾，共 {len(negative_conditions)} 個條件")
                logger.info(f"負面條件列表: {negative_conditions}")
                negative_embeddings = self.semantic_model.encode(negative_conditions, convert_to_tensor=True)
            else:
                logger.info("未檢測到負面條件，跳過語義過濾")
            
            for qdrant_filter_sub in qdrant_filter_lst:
                config = SearchConfig(
                    collection=collection,
                    query_text=reconstructed_query,
                    mode=mode,
                    filter=qdrant_filter_sub,
                    limit=top_k,
                    score_threshold=0.95
                )
                
                response = await self.search_service.search(self.qdrant_client, config)
                results = self.search_service.flatten_points(response)
                
                if negative_embeddings is not None:
                    logger.info(f"對當前條件的 {len(results)} 個結果進行負面條件過濾...")
                    filtered_results = []
                    for result in results:
                        page_content = result.get('payload', {}).get('page_content', '')
                        jid = result.get('payload', {}).get('metadata', {}).get('jid')
                        
                        content_embedding = self.semantic_model.encode(page_content, convert_to_tensor=True)
                        similarities = util.cos_sim(negative_embeddings, content_embedding)
                        max_similarity = similarities.max().item()
                        
                        if max_similarity < similarity_threshold:
                            filtered_results.append(result)
                            logger.info(f"✓ 保留 jid={jid}, 相似度={max_similarity:.3f}")
                        else:
                            logger.info(f"✗ 排除 jid={jid}, 相似度={max_similarity:.3f} (包含被否定內容)")
                    
                    results = filtered_results
                    logger.info(f"負面條件過濾後剩餘 {len(results)} 個結果")
                
                condition_jids = set()
                print("=" * 50)
                for result in results:
                    jid = result.get('payload').get('metadata').get('jid')
                    score = result.get('score', 0)
                    print(f"-----> score: {score}, jid: {jid}")
                    
                    condition_jids.add(jid)
                    
                    if jid in jid_score_map:
                        jid_score_map[jid] += score
                    else:
                        jid_score_map[jid] = score
                
                print("=" * 50)
                condition_jid_sets.append(condition_jids)
            
            logger.info(f"條件 '{field_type or 'general'}' 結果: {len(condition_jids)} 個 jid")
        
        if not condition_jid_sets:
            aggregated_jids_by_logic = set()
        elif logic == "AND":
            aggregated_jids_by_logic = set.intersection(*condition_jid_sets) if condition_jid_sets else set()
        elif logic == "OR":
            aggregated_jids_by_logic = set.union(*condition_jid_sets) if condition_jid_sets else set()
        
        logger.info(f"邏輯聚合 ({logic}) 後的 jid: {len(aggregated_jids_by_logic)} 個")
        
        filtered_jid_scores = {jid: jid_score_map[jid] for jid in aggregated_jids_by_logic if jid in jid_score_map}
        sorted_jids = sorted(filtered_jid_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        aggregated_jids = {jid for jid, _ in sorted_jids}
        
        logger.info(f"按累加分數排序後的前三名:")
        for jid, total_score in sorted_jids:
            logger.info(f"  jid: {jid}, 累加分數: {total_score}")
        
        detailed_results = await self.filter_service.retrieve_results_by_jids(
            qdrant_client=self.qdrant_client,
            collection=collection,
            limit=limit,
            aggregated_jids=aggregated_jids
        )
        
        simplified_results = []
        for result in detailed_results:
            payload = result.get('payload', {})
            metadata = payload.get('metadata', {})
            simplified_results.append({
                "page_content": payload.get('page_content'),
                "jid": metadata.get('jid')
            })

        logger.info(f"最終搜尋結果: 總共 {len(simplified_results)} 個結果")
        if len(simplified_results) > 0:
            for result in simplified_results:
                logger.info(f"---> 最終結果: {result.get('jid')}")
        else:
            logger.info(f"---> 最終結果: 沒有結果")
        
        return simplified_results

