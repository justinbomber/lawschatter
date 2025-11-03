import json
import logging
import time
from typing import Dict, Any
from openai import OpenAI
from openai import APITimeoutError, APIConnectionError, APIError
from ..domain import (
    SummaryExtractor, 
    JudgmentRecord, 
    SummaryExtractionResult,
    DefendantSummary,
)

logger = logging.getLogger(__name__)


class OpenAISummaryExtractor(SummaryExtractor):
    
    def __init__(
        self, 
        client: OpenAI, 
        model: str = "gpt-5",
        reasoning_effort: str = "medium",
        timeout: int = 600,
        max_wait_time: int = 300
    ):
        self.client = client
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout
        self.max_wait_time = max_wait_time  # 最大等待時間（秒），防止等待時間過長
    
    def extract(
        self, 
        judgment: JudgmentRecord, 
        schema: Dict[str, Any]
    ) -> SummaryExtractionResult:
        logger.info(f"使用 OpenAI 提取 summary: {judgment.jid}")
        
        system_prompt = (
            "你是一名專業的法律判決分析助手。請仔細閱讀提供的判決全文，"
            "並嚴格按照 JSON Schema 輸出結構化分析結果。"
            "必須完整填寫每位被告的所有六個欄位，若資料不足請填寫「未知」。"
        )
        user_prompt = judgment.jfull
        
        # 無限重試直到成功
        attempt = 0
        while True:
            attempt += 1
            try:
                if attempt == 1:
                    logger.info(f"嘗試提取 summary: {judgment.jid}")
                elif attempt % 10 == 0:
                    logger.warning(f"仍在重試提取 summary (第 {attempt} 次): {judgment.jid}")
                else:
                    logger.debug(f"重試提取 summary (第 {attempt} 次): {judgment.jid}")
                
                resp = self.client.chat.completions.create(
                    model=self.model,
                    reasoning_effort=self.reasoning_effort,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "judgment_summary",
                            "strict": True,
                            "schema": schema["json_schema"]
                        }
                    },
                    timeout=self.timeout
                )
                
                logger.info(f"AI summary 回應: {resp.choices[0].message.content}")
                
                ai_summary = json.loads(resp.choices[0].message.content)
                
                if attempt > 1:
                    logger.info(f"成功提取 summary (經過 {attempt} 次嘗試): {judgment.jid}")
                else:
                    logger.info(f"成功提取 summary: {judgment.jid}")
                
                defendants = []
                for defendant_data in ai_summary.get("defendants", []):
                    defendant = DefendantSummary(
                        name=defendant_data.get("name", "未知"),
                        role=defendant_data.get("role", "未知"),
                        A_fact=defendant_data.get("A_fact", "未知"),
                        B_claim=defendant_data.get("B_claim", "未知"),
                        C_court_finding=defendant_data.get("C_court_finding", "未知"),
                        D_court_reason=defendant_data.get("D_court_reason", "未知"),
                        E_legal_eval=defendant_data.get("E_legal_eval", "未知"),
                    )
                    defendants.append(defendant)
                
                return SummaryExtractionResult(
                    case_fact_summary=ai_summary.get("case_fact_summary", ""),
                    defendants=defendants,
                    case_highlights=ai_summary.get("case_highlights", []),
                )
                
            except (APITimeoutError, APIConnectionError) as e:
                # 計算等待時間：指數退避，但限制最大等待時間
                wait_time = min((attempt * 5), self.max_wait_time)
                
                logger.warning(
                    f"API 請求超時或連接錯誤 (第 {attempt} 次): {judgment.jid}. "
                    f"錯誤: {str(e)}. {wait_time} 秒後重試..."
                )
                time.sleep(wait_time)
                # 繼續循環，無限重試
                    
            except APIError as e:
                # 對於其他 API 錯誤，不重試
                logger.error(f"API 錯誤: {judgment.jid}. 錯誤: {str(e)}")
                raise
                
            except Exception as e:
                logger.error(f"未預期的錯誤: {judgment.jid}. 錯誤: {str(e)}")
                raise

