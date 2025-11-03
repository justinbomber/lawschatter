import os
import logging
from typing import List, Dict, Any, Set
from openai import AsyncOpenAI
from qdrant_client import models
from entities.filters import Filter
from infrastructure.tokenizer import JiebaLawTokenizer
from domain.interfaces import IFilterService, IQdrantClient
from config.settings import Settings


logger = logging.getLogger(__name__)


class FilterService(IFilterService):
    def __init__(self, settings: Settings):
        self.client = AsyncOpenAI(api_key=settings.openai.api_key)
        self.settings = settings
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        dict_path = os.path.join(parent_dir, "dict.txt.big")
        self.tokenizer = JiebaLawTokenizer(
            dict_path=dict_path,
            cut_all=False,
            doc_hmm=False,
            query_hmm=True,
        )
    
    async def extract_filter_conditions(self, user_question: str) -> List[Dict[str, Any]]:
        system_prompt = """
你是法律判決查詢的過濾條件抽取助理。請根據使用者的問題，抽取出過濾條件並輸出 JSON。

輸出結構(JSON schema)：

case_metadata: 案件元資料
first_instance: 是否為地方法院判決
second_instance: 是否為高等法院判決
third_instance: 是否為最高法院判決
case_type: 案件類型（刑法/民法/行政法）
jtitle_type: 案件標題類型（詐欺/毒品/竊盜/侵占/妨害性自主/傷害/公共危險/槍砲彈藥刀械/偽造文書/其他刑事/債務給付類/侵權行為／損害賠償類/婚姻家庭類/物權類/公司／商事類/勞資爭議類/保險類/其他民事）
defendants: 被告相關資訊（數組格式，每個元素為一位被告的條件物件）
可包含但不限於：confession_status, has_probation, defendants_role, A_fact, B_claim, C_court_finding, D_court_reason, E_legal_eval
角色詞彙正規化與展開規則（重要）：

將使用者輸入中任何俗稱、簡稱或行話角色（例如：車手、水房、把風/望風、車手頭、主嫌、掮客、白手套等）改寫為判決常見的中性法律描述，著重「具體職責與行為」而非標籤。
展開的 defendants_role 應以行為描述為主，使用動詞與客觀職能，不加入未被使用者明示的細節（如具體時間/地點/金額/次數）。
可在展開描述後，以（俗稱：…）附註原俗稱以利檢索，但不得只寫俗稱。
範例（僅示意表述風格，不要求逐字相同）：
車手 → 「提供（或保管、使用）金融帳戶、提款卡及密碼，負責收受詐得款項並提領或轉交之成員，屬於金流收受與提領的人頭帳戶供應／操作角色（俗稱：車手）」。
把風/望風 → 「於犯案過程中負責警戒、通風報信、監看周遭動態以協助犯罪順利實施之成員（俗稱：把風/望風）」。
水房/金流中介 → 「集中管理、分拆或匯兌詐得款項，指示或分配資金流向之成員（俗稱：水房）」。
若使用者未提供任何角色資訊，則不要新增或推測 defendants_role。
輸出要求：

僅輸出實際存在於使用者問題中的過濾條件；不得推測或添加不存在的條件或預設值。
數組字段使用列表格式，如 ["詐欺", "洗錢"]；布林值用 true/false；字串需加引號。
僅在問題有明示時，才填寫對應欄位；未提到者不要輸出。
在 defendants 物件中，"defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval" 至少填入一個欄位（可一至多個）。
若使用者問題含「未認罪」「否認犯行」「緩刑」等，對應填入 confession_status、has_probation 或 E_legal_eval（僅限問題明示者）。
僅輸出 JSON，無多餘文字或解釋。
"""
# - "defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval"一定至少要選一個填入，也可以一至多個填入。且填入的內容需要詳細描述，每個名詞
        response = await self.client.responses.parse(
            # model=self.settings.openai.model,
            model="gpt-5",
            input=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": user_question}
            ],
            text_format=Filter,
            timeout=120
            # reasoning_effort="high"
        )
        result = response.output_parsed
        structured_output = result.model_dump(exclude_none=True, exclude_unset=True)
        logger.info(f"結構化輸出: {structured_output}")
        
        output_lst = []
        summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval", "case_fact_summary"]
        _metadata = structured_output
        tmp_summary = {}
        
        for field in summary_fields:
            if field in structured_output and structured_output[field]:
                tmp_summary[field] = _metadata[field]
                del _metadata[field]
        
        for summary_type in tmp_summary:
            tmp_metadata = _metadata.copy()
            tmp_metadata[summary_type] = tmp_summary[summary_type]
            tmp_metadata["summary_type"] = [summary_type]
            output_lst.append(tmp_metadata)
                
        return output_lst
    
    def to_qdrant_filter(self, filter_dict: dict) -> models.Filter:
        must_conditions = []
        
        for key in ["jid_full", "jyear", "jcase", "jno", "jdate", "summary_type"]:
            value = filter_dict.get(key)
            
            if key == "summary_type" and value is not None:
                list_conditions = []
                for item in value:
                    if item == "defendants_role":
                        item = "role"
                    list_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.summary_type",
                            match=models.MatchPhrase(phrase=item)
                        )
                    )
                if list_conditions:
                    if len(list_conditions) == 1:
                        must_conditions.append(list_conditions[0])
                    else:
                        must_conditions.append(models.Filter(should=list_conditions))
            
            elif key == "jid_full" and value is not None:
                pass
            elif key == "jyear" and value is not None:
                if isinstance(value, int):
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
            elif key == "jdate" and value is not None:
                if isinstance(value, int):
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
            elif value is not None:
                if isinstance(value, (str, bool)):
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
        
        cm = filter_dict.get("case_metadata")
        if cm:
            for key in ["first_instance", "second_instance", "third_instance", "case_type", "jtitle_type"]:
                value = cm.get(key)
                if value is not None:
                    if isinstance(value, (str, bool)):
                        must_conditions.append(
                            models.FieldCondition(
                                key=f"metadata.case_metadata.{key}",
                                match=models.MatchValue(value=value)
                            )
                        )
        
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
                    
                    # 處理列表類型字段
                    # "crime_list",
                    if key in [ "violated_law_articles", "original_indictment_articles", 
                               "changed_indictment_articles", "seized_items", "confiscated_items", 
                               "changed_law_articles"]:
                        if isinstance(value, list) and value:
                            must_conditions.append(
                                models.FieldCondition(
                                    key=f"metadata.defendants[].{key}",
                                    match=models.MatchAny(any=value)
                                )
                            )
                    else:
                        # 處理其他字段（字符串、布林值、整數）
                        if isinstance(value, (str, bool, int)):
                            must_conditions.append(
                                models.FieldCondition(
                                    key=f"metadata.defendants[].{key}",
                                    match=models.MatchValue(value=value)
                                )
                            )
        
        return models.Filter(must=must_conditions) if must_conditions else models.Filter()
    
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
        for jid in list(aggregated_jids)[:limit]:
            scroll_results, _ = await qdrant_client.scroll(
                collection_name=collection,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="metadata.jid", match=models.MatchValue(value=jid))]
                ),
                limit=50,
                with_payload=True,
                with_vectors=False
            )
            for record in scroll_results or []:
                final_results.append({
                    "id": record.id,
                    "score": None,
                    "payload": record.payload
                })
        
        return final_results

