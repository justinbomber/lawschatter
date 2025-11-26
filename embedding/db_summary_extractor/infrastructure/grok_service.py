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


class GrokSummaryExtractor(SummaryExtractor):
    
    def __init__(
        self,
        client: OpenAI,
        model: str = "grok-4-fast-reasoning",
        reasoning_effort: str = "medium",
        timeout: int = 600,
        max_wait_time: int = 300,
        max_retries: int = 5
    ):
        self.client = client
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout
        self.max_wait_time = max_wait_time
        self.max_retries = max_retries
    
    def extract(
        self, 
        judgment: JudgmentRecord, 
        schema: Dict[str, Any]
    ) -> SummaryExtractionResult:
        logger.info(f"使用 Grok 提取 summary: {judgment.jid}")
        
        system_prompt = (
            "你是一名專業的法律判決分析助手。請仔細閱讀提供的判決全文，"
            "並嚴格按照 JSON Schema 輸出結構化分析結果。"
            "必須完整填寫每位被告的所有六個欄位，若資料不足請填寫「未知」。"
        )
        user_prompt = judgment.jfull
        
        attempt = 0
        
        while attempt < self.max_retries:
            attempt += 1
            try:
                if attempt == 1:
                    logger.info(f"嘗試提取 summary: {judgment.jid}")
                else:
                    logger.warning(f"重試提取 summary (第 {attempt}/{self.max_retries} 次): {judgment.jid}")
                
                resp = self.client.chat.completions.create(
                    model=self.model,
                    # reasoning_effort=self.reasoning_effort,
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
                if attempt >= self.max_retries:
                    logger.error(
                        f"達到最大重試次數 {self.max_retries} 次，API 請求仍然失敗: {judgment.jid}. "
                        f"錯誤: {str(e)}"
                    )
                    raise Exception(
                        f"達到最大重試次數 {self.max_retries} 次，需要重新查詢資料: {judgment.jid}. "
                        f"最後錯誤: {str(e)}"
                    )
                
                wait_time = min((attempt * 5), self.max_wait_time)
                logger.warning(
                    f"API 請求超時或連接錯誤 (第 {attempt}/{self.max_retries} 次): {judgment.jid}. "
                    f"錯誤: {str(e)}. {wait_time} 秒後重試..."
                )
                time.sleep(wait_time)
                    
            except APIError as e:
                logger.error(f"API 錯誤: {judgment.jid}. 錯誤: {str(e)}")
                raise
                
            except Exception as e:
                logger.error(f"未預期的錯誤: {judgment.jid}. 錯誤: {str(e)}")
                raise
        
        logger.error(f"達到最大重試次數 {self.max_retries} 次，提取失敗: {judgment.jid}")
        raise Exception(f"達到最大重試次數 {self.max_retries} 次，需要重新查詢資料: {judgment.jid}")

