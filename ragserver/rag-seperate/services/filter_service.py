import os
import re
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
# 車手 → 「提供（或保管、使用）金融帳戶、提款卡及密碼，負責收受詐得款項並提領或轉交之成員，屬於金流收受與提領的人頭帳戶供應／操作角色（俗稱：車手）」。
        system_prompt = """
你是法律判決查詢的過濾條件抽取助理。根據使用者問題，抽取出過濾條件並輸出 JSON。

輸出結構：
- 可包含：confession_status, has_probation, defendants_role, A_fact, B_claim, C_court_finding, D_court_reason, E_legal_eval。
- negated_fields：否定欄位列表。

角色正規化規則：
- 俗稱/行話角色（如車手、水房、把風、主嫌、掮客、白手套）改寫為中性法律描述，著重具體職責與行為（用動詞、客觀職能，不加未明示細節）。
- 描述後可附註（俗稱：…），但不得只用俗稱。
- 範例：
  - 把風 → 「於犯案過程中負責警戒、通風報信、監看周遭動態以協助犯罪順利實施之成員（俗稱：把風）」。
  - 水房 → 「集中管理、分拆或匯兌詐得款項，指示或分配資金流向之成員（俗稱：水房）」。
- 無角色資訊時，不新增 defendants_role。

輸出要求：
- 僅輸出問題中明示條件；不推測/添加/預設。
- 未明示欄位不填。
- 分類類別：defendants_role, A_fact, B_claim, C_court_finding, D_court_reason, E_legal_eval（defendants 物件中至少填一至多個；已量化 metadata 不重複填類別；全量化時仍選類別填入）。
- 分類類別：defendants_role, A_fact, B_claim, C_court_finding, D_court_reason, E_legal_eval（defendants 物件中至少填一至多個；已量化 metadata 不重複填類別；全量化時仍選類別填入）。
- 分類類別：defendants_role, A_fact, B_claim, C_court_finding, D_court_reason, E_legal_eval（defendants 物件中至少填一至多個；已量化 metadata 不重複填類別；全量化時仍選類別填入）。
- 分類類別：defendants_role, A_fact, B_claim, C_court_finding, D_court_reason, E_legal_eval（defendants 物件中至少填一至多個；已量化 metadata 不重複填類別；全量化時仍選類別填入）。
- 分類類別：defendants_role, A_fact, B_claim, C_court_finding, D_court_reason, E_legal_eval（defendants 物件中至少填一至多個；已量化 metadata 不重複填類別；全量化時仍選類別填入）。
- 所有條件須放入 metadata 或類別；不漏掉任何條件。
- 「未認罪」「否認犯行」「緩刑」等明示時，填 confession_status、has_probation 或 E_legal_eval。

否定語義規則：
- 遇否定詞（如沒有、不是、未、非、無、不具、排除）：
  1. 識別修飾欄位。
  2. 填 negated_fields：欄位路徑列表（qdrant 'must_not'）。
  3. 路徑格式：一般 "jyear"；case_metadata "case_metadata.first_instance"；defendants "defendants.has_probation"。
  4. 同時填該欄位值。
- 範例：
  - "沒有辯護人" → defendants.has_defense_attorney = true；negated_fields: ["defendants.has_defense_attorney"]。
  - "不是一審" → case_metadata.first_instance = true；negated_fields: ["case_metadata.first_instance"]。
  - "未緩刑" → defendants.has_probation = true；negated_fields: ["defendants.has_probation"]。
  - "不是完全認罪" → defendants.confession_status = "完全認罪"；negated_fields: ["defendants.confession_status"]。

僅輸出 JSON，無多餘文字。
"""
# - "defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval"一定至少要選一個填入，也可以一至多個填入。且填入的內容需要詳細描述，每個名詞
        response = await self.client.responses.parse(
            # model=self.settings.openai.model,
            model="o3",
            input=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": user_question}
            ],
            text_format=Filter,
            timeout=120,
            reasoning={"effort": "high"}
        )
        result = response.output_parsed
        structured_output = result.model_dump(exclude_none=True, exclude_unset=True)
        logger.info(f"結構化輸出: {structured_output}")
        
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
                tmp_metadata["negated_fields"] = negated_fields_value
            output_lst.append(tmp_metadata)
                
        return output_lst
    
    def to_qdrant_filter(self, filter_dict: dict) -> models.Filter:
        must_conditions = []
        must_not_conditions = []
        negated_fields = set(filter_dict.get("negated_fields", []))
        
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
                if isinstance(value, str):
                    if value != "":
                        must_conditions.append(
                            models.FieldCondition(
                                key=f"metadata.{key}",
                                match=models.MatchValue(value=value)
                            )
                        )
                elif isinstance(value, bool):
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
                    field_path = f"case_metadata.{key}"
                    is_negated = field_path in negated_fields
                    condition = None
                    
                    if isinstance(value, str):
                        if value != "":
                            condition = models.FieldCondition(
                                key=f"metadata.case_metadata.{key}",
                                match=models.MatchValue(value=value)
                            )
                    elif isinstance(value, bool):
                        condition = models.FieldCondition(
                            key=f"metadata.case_metadata.{key}",
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
                    # "crime_list",
                    if key in [ "violated_law_articles", "original_indictment_articles", 
                               "changed_indictment_articles", "seized_items", "confiscated_items", 
                               "changed_law_articles", "new_old_law_disputed_article", "mitigation_articles"] and value:
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, str):
                                    cleaned_item = re.sub(r'[（(][^）)]*[）)]', '', item)
                                    condition = models.FieldCondition(
                                        key=f"metadata.defendants[].{key}",
                                        match=models.MatchPhrase(phrase=cleaned_item)
                                    )
                            if condition:
                                must_conditions.append(condition)
                    elif key in ["crime_list"]:
                        pass
                    else:
                        # 處理其他字段（字符串、布林值、整數）
                        if isinstance(value, str):
                            if value != "":
                                condition = models.FieldCondition(
                                    key=f"metadata.defendants[].{key}",
                                    match=models.MatchValue(value=value)
                                )
                        elif isinstance(value, (bool, int)):
                            condition = models.FieldCondition(
                                key=f"metadata.defendants[].{key}",
                                match=models.MatchValue(value=value)
                            )
                    
                    if condition:
                        if is_negated:
                            must_not_conditions.append(condition)
                        else:
                            must_conditions.append(condition)
        
        if must_conditions or must_not_conditions:
            return models.Filter(must=must_conditions, must_not=must_not_conditions)
        return models.Filter()
    
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

