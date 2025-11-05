import logging
from typing import Dict, Any
from openai import AsyncOpenAI
from entities.filters import Filter
from domain.interfaces import ILLMExtractionService
from config.settings import Settings


logger = logging.getLogger(__name__)


class OpenAIExtractionService(ILLMExtractionService):
    def __init__(self, settings: Settings):
        self.client = AsyncOpenAI(api_key=settings.openai.api_key)
        self.settings = settings
    
    async def extract_structured_filter(self, user_question: str) -> Dict[str, Any]:
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

分類類別填入規則：
- 優先使用量化欄位（defendants.defendant_name、defendants.is_conviction、defendants.has_probation 等）表達用戶需求
- 「僅當」用戶需求涉及案件內容描述、角色描述、犯罪手法、法院論理等「語義性內容」時，才填入對應的分類類別
- 若用戶需求已完全被量化欄位覆蓋（例如：僅查詢被告姓名、判決年份、是否有罪等結構化條件），則「不填入」任何分類類別
- 若用戶需求已完全被量化欄位覆蓋（例如：僅查詢被告姓名、判決年份、是否有罪等結構化條件），則「不填入」任何分類類別
- 若用戶需求已完全被量化欄位覆蓋（例如：僅查詢被告姓名、判決年份、是否有罪等結構化條件），則「不填入」任何分類類別
- 範例：
  * "給我被告姓名為xxx的判決" → 僅填 defendants.defendant_name = "xxx"，不填分類類別
  * "給我車手角色且有罪的判決" → 填 defendants_role + defendants.is_conviction
  * "給我提供帳戶手法的無罪判決" → 填 A_fact + defendants.is_conviction

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
        
        response = await self.client.responses.parse(
            model="gpt-5",
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
        
        return structured_output

