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
- negated_fields：否定欄位列表。confession_status, has_probation, defendants_role, A_fact, B_claim, C_court_finding, D_court_reason, E_legal_eval不得加入否定列表欄位。

以下為可直接給語言模型使用的正規化提示，已加入「動作／手法」行話的改寫規則與範例。

目標
- 將文本中的俗稱／行話（角色與動作/手法）改寫為中性法律描述，著重具體職責與行為。
- 採用動詞與客觀職能描述，不加入文本未明示之細節。
- 可於描述末尾附註（俗稱：…），但不得只用俗稱。

通用原則
- 用語中立、客觀，以可觀察的行為與職責為主（使用動詞）。
- 不臆測未明示之手法、工具、金額、層級、意圖或關係。
- 同一主體若兼具多項角色或行為，分別列示（以分號或分項）。
- 無角色資訊時，不新增 defendants_role；無動作/手法資訊時，不新增對應欄位。
- 對專有名詞或行話，改寫為功能性描述並可附註俗稱（俗稱：…）。

角色正規化規則（示例）
- 把風 → 於犯案過程中負責警戒、通風報信、監看周遭動態以協助犯罪順利實施之成員（俗稱：把風）。
- 水房 → 集中管理、分拆或匯兌涉案款項，指示或分配資金流向之成員（俗稱：水房）。
- 車手 → 依指示提領、搬運、收受或交付款項或物品之成員（俗稱：車手）。
- 主嫌 → 負責策劃、指示或統籌涉案行為之成員（俗稱：主嫌）。
- 掮客 → 居間聯絡、撮合資源或傳遞資訊以促成交易或合作之成員（俗稱：掮客）。
- 白手套 → 以其名義代為持有、簽署或處理資產、帳戶或文件，以掩飾實際控制者身分之成員（俗稱：白手套）。

動作／手法正規化規則（示例）
- 美化金流 → 以處理帳務或交易紀錄以掩飾資金來源、性質或去向之行為（俗稱：美化金流）。
- 跑分 → 以分拆或多點轉移方式處理資金以規避監管或提高交易通過率之行為（俗稱：跑分）。
- 養帳 → 長期操作或維護帳戶以提高信任度或通過審核，供後續交易使用之行為（俗稱：養帳）。
- 套現 → 將非現金資產或額度轉換為可自由支配資金之行為（俗稱：套現）。
- 洗白 → 將資產或資金之來源外觀加以合法化或正當化之包裝或申報行為（俗稱：洗白）。
- 引流 → 以訊息、廣告或其他方式引導目標對象進入指定聯絡或交易管道之行為（俗稱：引流）。
- 話術 → 使用預先編寫或既定說辭誘導對方作出特定回應或決策之行為（俗稱：話術）。
- 刷單 → 虛構或不以真實交易為目的之下單、評價或互動以影響平台數據之行為（俗稱：刷單）。
- 洗錢 → 掩飾或隱匿犯罪所得來源、性質、所在或去向之處理資金行為（俗稱：洗錢）。

輸出要求
- 先給出中性法律描述，後附（俗稱：…）保留原行話。
- 若文字中同時出現多個角色或多個動作，逐一改寫並以分號分隔或分項列示。
- 僅根據文本已有資訊改寫；未提及者不推測、不補充。

輸出要求：
- 僅輸出問題中明示條件；不推測/添加/預設。
- 未明示欄位不填。
- 所有條件須放入 metadata 或類別；不漏掉任何條件。

量化欄位優先原則（重要！）：
- 若某條件可用量化欄位表達，就「只」填量化欄位，「不」填描述性類別。
- 已量化不再重複：
  * 「有罪判決」「被判刑」→ defendants.is_conviction = true，不填 E_legal_eval
  * 「無罪」→ defendants.is_conviction = false，不填 E_legal_eval
  * 「緩刑」→ defendants.has_probation = true，不填 E_legal_eval
  * 「未認罪」「否認」→ defendants.confession_status = "完全否認"，不填 E_legal_eval
  * 「完全認罪」→ defendants.confession_status = "完全認罪"，不填 E_legal_eval
  * 「部分認罪」→ defendants.confession_status = "部分認罪"，不填 E_legal_eval

分類類別使用時機：
- defendants_role：角色描述（車手、水房、把風等）
- A_fact：具體犯罪手法或事實行為（美化金流、提供帳戶、提領款項等）
- B_claim、C_court_finding、D_court_reason：訴訟主張、法院認定、判決理由等敘述性內容
- E_legal_eval：「僅」在無法用量化欄位表達的法律評價時使用（如特殊量刑理由、法律適用爭議等）
- 每次至少選填一個分類類別（優先填 defendants_role 或 A_fact）

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
            model="gpt-5-mini",
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
                                            if t.strip()
                                        ]
                                        # 為每個分詞結果創建條件
                                        for token in tokens:
                                            condition = models.FieldCondition(
                                                key=f"metadata.defendants[].{key}",
                                                match=models.MatchPhrase(phrase=token)
                                            )
                                            if is_negated:
                                                must_not_conditions.append(condition)
                                            else:
                                                must_conditions.append(condition)
                                    else:
                                        # 其他列表類型字段維持原本邏輯
                                        condition = models.FieldCondition(
                                            key=f"metadata.defendants[].{key}",
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
        logger.info(f"retrieve_results_by_jids 接收到 {len(aggregated_jids)} 個 jid")
        logger.info(f"jid 列表: {list(aggregated_jids)}")
        
        for jid in list(aggregated_jids)[:limit]:
            logger.info(f"正在檢索 jid: {jid}")
            scroll_results, _ = await qdrant_client.scroll(
                collection_name=collection,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="metadata.jid", match=models.MatchValue(value=jid))]
                ),
                limit=50,
                with_payload=True,
                with_vectors=False
            )
            logger.info(f"  從 Qdrant 取回 {len(scroll_results or [])} 條記錄")
            
            for idx, record in enumerate(scroll_results or []):
                record_jid = record.payload.get('metadata', {}).get('jid', 'unknown')
                record_jid_full = record.payload.get('metadata', {}).get('jid_full', 'unknown')
                if idx == 0:
                    logger.info(f"    第一條記錄 - jid: {record_jid}, jid_full: {record_jid_full}")
                final_results.append({
                    "id": record.id,
                    "score": None,
                    "payload": record.payload
                })
        
        logger.info(f"retrieve_results_by_jids 總共返回 {len(final_results)} 條記錄")
        return final_results

