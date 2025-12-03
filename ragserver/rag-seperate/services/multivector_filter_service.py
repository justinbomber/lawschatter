import os
import re
import logging
from typing import List, Dict, Any, Set
from qdrant_client import models
from infrastructure.tokenizer import JiebaLawTokenizer
from domain.interfaces import IFilterService, IQdrantClient, ILLMExtractionService, Message
from config.settings import Settings


logger = logging.getLogger(__name__)


class MultivectorFilterService(IFilterService):
    def __init__(self, settings: Settings, llm_extraction_service: ILLMExtractionService):
        self.settings = settings
        self.llm_extraction_service = llm_extraction_service
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        dict_path = os.path.join(parent_dir, "dict.txt.big")
        self.tokenizer = JiebaLawTokenizer(
            dict_path=dict_path,
            cut_all=False,
            doc_hmm=False,
            query_hmm=True,
        )
    
    async def extract_filter_conditions(self, user_question: str, history_messages: List[Message] = None) -> List[Dict[str, Any]]:
        structured_output = await self.llm_extraction_service.extract_structured_filter(user_question, history_messages)
        
        if "defendants" in structured_output and isinstance(structured_output["defendants"], list):
            if len(structured_output["defendants"]) > 0:
                structured_output["defendants"] = [structured_output["defendants"][0]]
        
        output_lst = []
        summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval", "case_fact_summary"]
        _metadata = structured_output.copy()
        tmp_summary = {}
        
        negated_fields_value = _metadata.get("negated_fields")
        if "negated_fields" in _metadata:
            del _metadata["negated_fields"]
        
        for field in summary_fields:
            if field in structured_output and structured_output[field]:
                tmp_summary[field] = _metadata[field]
                del _metadata[field]
        
        for summary_type in tmp_summary:
            tmp_metadata = _metadata.copy()
            tmp_metadata[summary_type] = tmp_summary[summary_type]
            tmp_metadata["summary_type"] = [summary_type]
            if negated_fields_value:
                tmp_metadata["negated_fields"] = negated_fields_value.copy()
            output_lst.append(tmp_metadata)
        
        if not output_lst and _metadata:
            logger.info("沒有 summary_fields，但有基礎過濾條件，將其加入結果列表")
            if negated_fields_value:
                _metadata["negated_fields"] = negated_fields_value.copy()
            output_lst.append(_metadata)
                
        return output_lst
    
    def to_qdrant_filter(self, filter_dict: dict) -> tuple[models.Filter, int]:
        must_conditions = []
        must_not_conditions = []
        summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval"]
        for field in filter_dict.get("negated_fields", []):
            if field in summary_fields:
                filter_dict["negated_fields"].remove(field)
        negated_fields = set(filter_dict.get("negated_fields", []))
        limit = filter_dict.get("limit", 3)
        
        for key in ["jid_full", "jyear", "jcase", "jno", "jdate", "summary_type"]:
            value = filter_dict.get(key)
            
            if key == "summary_type" and value is not None:
                list_conditions = []
                for item in value:
                    if item == "defendants_role":
                        item = "role"
                    list_conditions.append(
                        models.FieldCondition(
                            key=f"summary_type",
                            match=models.MatchPhrase(phrase=item)
                        )
                    )
                if list_conditions:
                    if len(list_conditions) == 1:
                        must_conditions.append(list_conditions[0])
                    else:
                        must_conditions.append(models.Filter(should=list_conditions))
            
            elif key == "jid_full" and value is not None:
                # 使用分詞器處理 jid_full
                tokens = [
                    t.strip() for t in self.tokenizer.run_query(value)
                    if t.strip()
                ]
                # 為每個分詞結果創建 MatchPhrase 條件
                for token in tokens:
                    condition = models.FieldCondition(
                        key=f"{key}",
                        match=models.MatchPhrase(phrase=token)
                    )
                    must_conditions.append(condition)
            elif key == "jyear" and value is not None:
                if isinstance(value, int):
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
            elif key == "jdate" and value is not None:
                if isinstance(value, int):
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
            elif value is not None:
                if isinstance(value, str):
                    if value != "":
                        must_conditions.append(
                            models.FieldCondition(
                                key=f"{key}",
                                match=models.MatchValue(value=value)
                            )
                        )
                elif isinstance(value, bool):
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
        
        cm = filter_dict.get("case_metadata")
        if cm:
            for key in ["first_instance", "second_instance", "third_instance", "case_type", "jtitle_type"]:
                value = cm.get(key)
                if value is not None:
                    field_path = f"case_metadata.{key}"
                    is_negated = field_path in negated_fields
                    condition = None
                    
                    if isinstance(value, str):
                        if value != "":
                            condition = models.FieldCondition(
                                key=f"case_metadata.{key}",
                                match=models.MatchValue(value=value)
                            )
                    elif isinstance(value, bool):
                        condition = models.FieldCondition(
                            key=f"case_metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                    
                    if condition:
                        if is_negated:
                            must_not_conditions.append(condition)
                        else:
                            must_conditions.append(condition)
        
        defendants_list = filter_dict.get("defendants") or []
        if isinstance(defendants_list, list):
            for d in defendants_list:
                defendant_fields = [
                    # 基本信息
                    "defendant_name",
                    # 辯護人相關
                    "has_defense_attorney", "defense_attorney_name",
                    # 起訴法條變更
                    "indictment_changed", "original_indictment_articles", "changed_indictment_articles",
                    # 新舊法問題
                    "has_new_old_law_issue", "new_old_law_disputed_article",
                    # 自白與陳述
                    "has_contradictory_statements", "confession_status",
                    # 判決結果
                    "is_full_acquittal", "is_acquittal_due_to_insufficient_evidence", "is_other_verdict", "is_conviction",
                    # 罪名與法條
                    "crime_list", "violated_law_articles",
                    # 刑罰
                    "is_fixed_term_imprisonment", "fixed_term_years", "fixed_term_months",
                    "is_life_imprisonment", "is_death_penalty", "is_detention", "detention_days",
                    # 罰金
                    "has_concurrent_fine", "fine_amount", "may_convert_to_fine",
                    # 緩刑
                    "has_probation", "probation_period",
                    # 減刑
                    "has_mitigation_articles", "mitigation_articles",
                    # 和解
                    "has_settlement", "settlement_amount", "is_settlement_fulfilled", "is_settlement_installment",
                    # 證人
                    "has_witnesses", "witness_testified_in_investigation", "witness_testified_in_trial",
                    # 扣押沒收
                    "has_seized_items", "seized_items", "has_confiscated_items", "confiscated_items",
                    # 接續犯
                    "is_continuous_offense",
                    # 審級
                    "is_first_instance", "is_second_instance", "is_third_instance", "has_previous_instance",
                    # 上訴相關
                    "is_reversed_and_remanded", "is_sentence_reduced", "is_sentence_increased",
                    "is_law_article_changed_from_previous", "changed_law_articles",
                    "previous_instance_confession_status", "current_instance_confession_status",
                    "has_inconsistent_statements_with_previous", "statement_difference_description"
                ]
                
                for key in defendant_fields:
                    value = d.get(key)
                    if value is None:
                        continue
                    
                    field_path = f"defendants.{key}"
                    is_negated = field_path in negated_fields
                    condition = None
                    
                    # 處理列表類型字段
                    if key in ["crime_list", "violated_law_articles", "original_indictment_articles", 
                               "changed_indictment_articles", "seized_items", "confiscated_items", 
                               "changed_law_articles", "new_old_law_disputed_article", "mitigation_articles"] and value:
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, str):
                                    cleaned_item = re.sub(r'[（(][^）)]*[）)]', '', item)
                                    
                                    # 對 crime_list 使用分詞器拆分成關鍵字
                                    if key:
                                        tokens = [
                                            t.strip() for t in self.tokenizer.run_query(cleaned_item)
                                            if t.strip() and not any(char in t for char in ['罪', '法', '條'])
                                        ]
                                        # 為每個分詞結果創建條件
                                        for token in tokens:
                                            condition = models.FieldCondition(
                                                key=f"defendants[].{key}",
                                                match=models.MatchPhrase(phrase=token)
                                            )
                                            if is_negated:
                                                must_not_conditions.append(condition)
                                            else:
                                                must_conditions.append(condition)
                                    else:
                                        # 其他列表類型字段維持原本邏輯
                                        condition = models.FieldCondition(
                                            key=f"defendants[].{key}",
                                            match=models.MatchPhrase(phrase=cleaned_item)
                                        )
                                        if condition:
                                            if is_negated:
                                                must_not_conditions.append(condition)
                                            else:
                                                must_conditions.append(condition)
                    else:
                        # 處理其他字段（字符串、布林值、整數）
                        if isinstance(value, str):
                            if value != "":
                                condition = models.FieldCondition(
                                    key=f"defendants[].{key}",
                                    match=models.MatchValue(value=value)
                                )
                        elif isinstance(value, (bool, int)):
                            condition = models.FieldCondition(
                                key=f"defendants[].{key}",
                                match=models.MatchValue(value=value)
                            )
                    
                    if condition:
                        if is_negated:
                            must_not_conditions.append(condition)
                        else:
                            must_conditions.append(condition)
        
        if must_conditions or must_not_conditions:
            return models.Filter(must=must_conditions, must_not=must_not_conditions), limit
        return models.Filter(), limit
    
    def format_jid_full(self, jid_full: str) -> str:
        if not jid_full:
            return jid_full
            
        result = []
        for i, char in enumerate(jid_full):
            if char.isdigit():
                if i > 0 and not jid_full[i-1].isdigit() and jid_full[i-1] != ' ':
                    result.append(' ')
            result.append(char)
        
        return ''.join(result)
    
    async def retrieve_results_by_jids(
        self,
        qdrant_client: IQdrantClient,
        collection: str,
        limit: int,
        aggregated_jids: Set[str]
    ) -> List[Dict[str, Any]]:
        final_results = []
        logger.info(f"retrieve_results_by_jids 接收到 {len(aggregated_jids)} 個 jid")
        logger.info(f"jid 列表: {list(aggregated_jids)}")
        
        for jid in list(aggregated_jids):
        # for jid in list(aggregated_jids)[:limit]:
            logger.info(f"正在檢索 jid: {jid}")
            scroll_results, _ = await qdrant_client.scroll(
                collection_name=collection,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="jid", match=models.MatchValue(value=jid))]
                ),
                # limit=50,
                with_payload=True,
                with_vectors=False
            )
            logger.info(f"  從 Qdrant 取回 {len(scroll_results or [])} 條記錄")
            
            for idx, record in enumerate(scroll_results or []):
                record_jid = record.payload.get('jid', 'unknown')
                record_jid_full = record.payload.get('jid_full', 'unknown')
                if idx == 0:
                    logger.info(f"    第一條記錄 - jid: {record_jid}, jid_full: {record_jid_full}")
                final_results.append({
                    "id": record.id,
                    "score": None,
                    "payload": record.payload
                })
        
        logger.info(f"retrieve_results_by_jids 總共返回 {len(final_results)} 條記錄")
        return final_results

