import logging
from typing import List, Dict, Any, AsyncGenerator
from domain.interfaces import IChatService, IRAGClient, ILLMProvider, IConversationRepository
from entities.models import RAGSearchRequest, ChatMessage
from config.settings import Settings

logger = logging.getLogger(__name__)


class ChatService(IChatService):
    def __init__(
        self,
        rag_client: IRAGClient,
        llm_provider: ILLMProvider,
        conversation_repository: IConversationRepository,
        settings: Settings
    ):
        self.rag_client = rag_client
        self.llm_provider = llm_provider
        self.conversation_repository = conversation_repository
        self.settings = settings
    
    async def process_chat(
        self,
        question: str,
        conversation_id: str,
        token: str,
        user_id: str,
        collection: str,
        mode: str,
        limit: int,
        score_threshold: float,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        logger.info(f"處理聊天請求: {question}")
        
        is_new_conversation = False
        if not conversation_id:
            is_new_conversation = True
            logger.info("沒有提供 conversation_id，將在獲得標題後創建新對話")
        
        rag_request = RAGSearchRequest(
            query_text=question,
            conversation_id=conversation_id,
            streaming=False,
            search_mode="rrf"
        )
        
        rag_response = await self.rag_client.search(rag_request, token, user_id)
        logger.info(f"RAG 搜尋完成，共 {rag_response.total} 筆結果")
        
        history = []
        if conversation_id:
            history = await self.conversation_repository.get_conversation_messages(
                token, conversation_id, limit=10
            )
        logger.info(f"取得歷史對話，共 {len(history)} 筆")
        
        sources = [
            {
                "page_content": result.page_content,
                "jid": result.jid,
                "defendants": result.defendants
            }
            for result in rag_response.results
        ]
        
        suggested_title = None
        if len(history) == 0:
            suggested_title = await self._generate_conversation_title(question)
            logger.info(f"生成對話標題: {suggested_title}")
        
        if is_new_conversation:
            conversation_id = await self.conversation_repository.create_conversation(
                token, user_id, suggested_title or "新對話"
            )
            logger.info(f"創建新對話: {conversation_id}")
        
        messages = self.build_prompt(question, sources)
        
        answer = await self.llm_provider.generate_response(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            history_messages=history
        )
        logger.info(f"LLM 生成回應完成")
        
        await self.conversation_repository.save_message(
            token, conversation_id, user_id, "user", question
        )
        await self.conversation_repository.save_message(
            token, conversation_id, user_id, "assistant", answer
        )
        
        if len(history) == 0 and not is_new_conversation:
            await self.conversation_repository.update_conversation_title(
                token, conversation_id, suggested_title
            )
        logger.info(f"對話記錄已儲存")
        
        return {
            "answer": answer,
            "sources": sources,
            "query": question,
            "total_sources": len(sources),
            "model": self.llm_provider.__class__.__name__,
            "conversation_id": conversation_id
        }
    
    def build_prompt(
        self,
        question: str,
        rag_results: List[Dict[str, Any]]
    ) -> List[ChatMessage]:
        system_content = """
        角色與目標
- 角色：專業的台灣法律文件助理，負責檢索、解析與總結台灣法院判決、法條與相關法律資料。
- 目標：以檢索到的文件為唯一依據，準確回答使用者問題，並提供清晰、可核對的摘要與重點。

能力範圍
- 回答一般法律問題（以檢索到的法規、見解、判決為依據）。
- 檢索與彙整法院判決。
- 分析與解釋法律條文（以檢索到的條文與立法理由/見解為依據）。
- 提供實務趨勢與操作建議（僅能根據檢索到的案例與法規，不得憑空推論）。

核心原則（務必遵守）
- 若下面內容無法回答, 仍不符即回報「找不到」並提供具體放寬建議。
- 僅根據檢索到的文件作答。不得臆測或補完，找不到就明確說明「找不到」，並解釋可能原因與放寬建議。
- 輸出使用繁體中文、客觀中性，且最後一定要有「總結」。


模糊搜尋思維鏈（隱性步驟，不外顯給使用者）
步驟一：查詢解析
- 主體角色：被告、原告、提款手/車手、共犯、幫助犯等。
- 行為模式：提供帳戶、取款、面交、監控、把風、搬運、收受贓款等。
- 罪名與架構：詐欺（含加重）、洗錢防制法、竊盜、侵占、恐嚇取財、組織犯罪等。
- 認罪態度：否認犯行、辯稱無罪、坦承犯行、部分自白等。
- 程序階段：偵查、一審、二審、上訴、發回更審、定讞等。
- 判決結果：無罪、有罪、緩刑（宣告緩刑/附條件不執行）、減刑、沒收、免訴等。
- 法院層級與別：地院、高院、最高法院、簡易判決、刑事/民事等。
- 其他條件：時間區間、地區、金額範圍、法條名稱與條號、是否累犯/累犯加重、是否少年事件等。

步驟二：條件映射（口語→法律書寫用語）
- 車手→提款手、取款人、領款人、面交車手、取款車手。
- 不認罪→否認犯行、辯稱無罪、不承認犯嫌。
- 緩刑→宣告緩刑、暫緩執行、附條件不執行。
- 詐欺案例→詐欺罪、加重詐欺罪、詐騙集團成員、三人以上共同犯之加重詐欺。
- 其他常見映射：人頭帳戶→提供金融帳戶、盜領→提領贓款、白手套→掩護金流或洗錢、共同正犯/幫助犯→共同行為/幫助行為。

步驟三：搜尋策略
- 以重組後的自然語句進行查詢，句內包含全部條件，避免只丟單詞或標籤。
- 必要時加入負面條件（例如排除特定罪名/法院層級），以自然語句表達。
- 視結果調整條件優先序（例如先鎖定罪名與行為模式，再細化認罪態度與結果）。

步驟四：結果驗證
- 嚴格比對：所有指定條件皆需滿足；不符則重新組合語句再查。
- 核對基礎欄位：法院、裁判日期、案號、案由/罪名、程序階段、主文、理由、適用法條、量刑與是否緩刑等。

步驟五：事實與要旨抽取
- 對於符合條件的文書，萃取：
  - 裁判法院/層級、裁判日期、年度案號、案由/罪名
  - 主文與重點理由（犯罪事實、證據、構成要件詮釋）
  - 量刑理由、是否宣告緩刑及其條件、是否沒收/追徵
  - 依據法條（條號與關鍵用語）
  - 程序資訊（上訴/發回/更審/定讞）
- 去識別化與隱私保護：避免輸出可辨識個資。

輸出格式與範本
- 基本回覆結構（適用於判決檢索）
  1) 檢索結論：是否找到完全符合的判決；數量；若找不到，說明原因與放寬建議。
  2) 代表性判決摘要（2-5 則，視情況）：每則包含
     - 法院、裁判日期、案號、案由/罪名、程序階段與結果
     - 事實要點與行為角色（如：提款手/幫助犯）
     - 法院見解與理由關鍵句（簡述）
     - 量刑與緩刑（含條件）、沒收/追徵
     - 主要適用法條
  3) 規範整理：相關法條重點、實務見解要點
  4) 實務趨勢與差異（如有多則案例可比較）
  5) 操作提醒/風險重點（僅根據檢索結果）
  6) 總結（必填）
- 法條/一般法律問題（無特定判決）：
  - 先檢索法規與解釋資料；輸出條文重點、關鍵構成要件、實務見解摘錄、適用範圍/限制、相關裁判連結（如有）；最後總結。
- 引用格式（不顯示工具）：以「法院、裁判日期、案號」呈現；如文件含唯一識別碼，可一併列示。

嚴格情境規則
- 不得說明或暗示檢索工具與過程。
- 不得臆測或發表無來源的法律意見；可提供「依檢索結果顯示的」實務趨勢與要點。
- 僅在必要時詢問補充條件（例如明顯欠缺關鍵構面且多次檢索皆無果）；否則應盡最大努力給出答案。
- 對敏感資訊採匿名化描述，避免可識別個資。
- 全文採繁體中文、簡潔條列，避免冗長說理。

失敗處理與回報
- 檢索 3 次後仍無完全符合結果：
  - 回覆「找不到完全符合的判決」，列出可能過於嚴格的條件項（例如：法院層級、年份範圍、認罪態度、是否限定加重、是否限定緩刑）。
  - 提出具體放寬建議與下一步（擴大年份/層級、放寬認罪態度、僅鎖定罪名與行為角色等）。
- 工具錯誤：簡短致歉，重試；仍失敗則回報暫時無法檢索。

查詢重組規則（投入 MCP 前的最終檢核）
- 必須以自然語句表述。
- 僅包含客觀、可驗證條件與法律專用語；不得加入主觀推測與多餘語氣。
- 涵蓋各要件（至少：角色/行為/罪名/程序/結果），並視需求補上法院層級、時間區間、地區、金額、條號。
- 範例（示意）：
  - 「被告擔任提款手，涉犯三人以上共同犯之加重詐欺罪，否認犯行，第一審宣告緩刑的判決。」
  - 「高等法院二審，洗錢防制法幫助犯，坦承犯行，未宣告緩刑之量刑理由。」

風格與長度
- 採條列式、重點先行；每則案例摘要 5-9 行為宜。
- 盡量引用判決用語關鍵詞，但保持可讀性。

法律責任聲明（內部原則）
- 回覆為資訊彙整與摘要，非個別法律意見或代理；如需具體法律建議，應諮詢執業律師。

**不得隨意編造或憑印象回答，必須以檢索到的文件為唯一依據，找不到就說找不到，並提供具體放寬建議。**
**不得隨意編造或憑印象回答，必須以檢索到的文件為唯一依據，找不到就說找不到，並提供具體放寬建議。**
**不得隨意編造或憑印象回答，必須以檢索到的文件為唯一依據，找不到就說找不到，並提供具體放寬建議。**
**不得隨意編造或憑印象回答，必須以檢索到的文件為唯一依據，找不到就說找不到，並提供具體放寬建議。**
**不得隨意編造或憑印象回答，必須以檢索到的文件為唯一依據，找不到就說找不到，並提供具體放寬建議。**
**不得隨意編造或憑印象回答，必須以檢索到的文件為唯一依據，找不到就說找不到，並提供具體放寬建議。**
**不得隨意編造或憑印象回答，必須以檢索到的文件為唯一依據，找不到就說找不到，並提供具體放寬建議。**

相關判決資料：
"""
        
        for idx, result in enumerate(rag_results, 1):
            # TODO: 把defendants轉換成中文
            defendants = result.get('defendants', [])
            jid = result.get('jid', '')
            page_content = result.get('page_content', '')
            system_content += f"\n{idx}. [案號：{jid}][被告：{defendants}]\n{page_content}\n"
        
        messages = [
            ChatMessage(role="system", content=system_content),
            ChatMessage(role="user", content=question)
        ]
        
        return messages
    
    async def _generate_conversation_title(self, question: str, answer: str = None) -> str:
        title_prompt = [
            ChatMessage(
                role="system",
                content="你是一個專業的對話標題生成助手。根據使用者的問題和助手的回答，生成一個簡短、精確的對話標題。標題應該：\n1. 不超過 20 個繁體中文字\n2. 準確概括對話的核心主題\n3. 使用法律專業術語（如適用）\n4. 直接輸出標題，不要加引號或其他符號"
            ),
            ChatMessage(
                role="user",
                content=f"使用者問題：{question}\n\n請生成一個簡短的對話標題："
            )
        ]
        
        title = await self.llm_provider.generate_response(
            messages=title_prompt,
            temperature=0.3,
            max_tokens=50,
            history_messages=None
        )
        
        cleaned_title = title.strip().replace('"', '').replace("'", '').replace('\n', ' ')[:30]
        logger.info(f"LLM 生成對話標題: {cleaned_title}")
        
        return cleaned_title or "新對話"
    
    async def process_chat_stream(
        self,
        question: str,
        conversation_id: str,
        token: str,
        user_id: str,
        collection: str,
        mode: str,
        limit: int,
        score_threshold: float,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(f"處理聊天請求 (串流): {question}")
        
        is_new_conversation = False
        if not conversation_id:
            is_new_conversation = True
            logger.info("沒有提供 conversation_id，將在獲得標題後創建新對話")
        
        rag_request = RAGSearchRequest(
            query_text=question,
            conversation_id=conversation_id,
            streaming=True,
            search_mode="rrf"
        )
        
        sources = []
        async for chunk in self.rag_client.search_stream(rag_request, token, user_id):
            if "status" in chunk:
                yield {"type": "rag_status", "status": chunk["status"]}
            elif "type" in chunk and chunk["type"] == "final_results":
                results = chunk.get("results", [])
                logger.info(f"RAG 搜尋完成，共 {len(results)} 筆結果")
                
                sources = [
                    {
                        "page_content": result.get("page_content"),
                        "jid": result.get("jid"),
                        "defendants": result.get("defendants", [])
                    }
                    for result in results
                ]
        
        history = []
        if conversation_id:
            history = await self.conversation_repository.get_conversation_messages(
                token, conversation_id, limit=10
            )
        
        suggested_title = None
        if len(history) == 0:
            suggested_title = await self._generate_conversation_title(question)
            logger.info(f"生成對話標題: {suggested_title}")
        
        if is_new_conversation:
            conversation_id = await self.conversation_repository.create_conversation(
                token, user_id, suggested_title or "新對話"
            )
            logger.info(f"創建新對話: {conversation_id}")
        
        logger.info(f"取得歷史對話，共 {len(history)} 筆")
        
        messages = self.build_prompt(question, sources)
        
        yield {"type": "llm_start", "status": "已獲取資料，開始準備回答"}
        
        full_answer = ""
        async for token_content in self.llm_provider.generate_response_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            history_messages=history
        ):
            full_answer += token_content
            yield {"type": "llm_token", "content": token_content}
        
        await self.conversation_repository.save_message(
            token, conversation_id, user_id, "user", question
        )
        await self.conversation_repository.save_message(
            token, conversation_id, user_id, "assistant", full_answer
        )
        
        if len(history) == 0 and not is_new_conversation:
            await self.conversation_repository.update_conversation_title(
                token, conversation_id, suggested_title
            )
        logger.info(f"對話記錄已儲存")
        
        yield {
            "type": "complete",
            "sources": sources,
            "query": question,
            "total_sources": len(sources),
            "model": self.llm_provider.__class__.__name__,
            "conversation_id": conversation_id
        }

