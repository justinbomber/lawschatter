import json
import logging
import time
from typing import Dict, Any
from openai import OpenAI
from openai import APITimeoutError, APIConnectionError, APIError
from ..domain import MetadataExtractor, JudgmentRecord, MetadataExtractionResult

logger = logging.getLogger(__name__)


class GrokMetadataExtractor(MetadataExtractor):
    
    def __init__(
        self,
        client: OpenAI,
        model: str = "grok-4-fast-reasoning",
        timeout: int = 600,
        max_wait_time: int = 300,
        max_retries: int = 5
    ):
        self.client = client
        self.model = model
        self.timeout = timeout
        self.max_wait_time = max_wait_time
        self.max_retries = max_retries
    
    def extract(
        self, 
        judgment: JudgmentRecord, 
        schema: Dict[str, Any]
    ) -> MetadataExtractionResult:
        logger.info(f"使用 Grok 提取 metadata: {judgment.jid}")
        
        system_prompt = (
            "你是一名專業的法律判決資料結構化助手。請仔細閱讀提供的判決全文與分類規範，"
            "並嚴格按照 JSON Schema 輸出結構化結果。\n\n"
        )
        user_prompt = judgment.jfull
        
        # 最多重試 max_retries 次
        attempt = 0
        
        while attempt < self.max_retries:
            attempt += 1
            try:
                if attempt == 1:
                    logger.info(f"嘗試提取 metadata: {judgment.jid}")
                else:
                    logger.warning(f"重試提取 metadata (第 {attempt}/{self.max_retries} 次): {judgment.jid}")
                
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "judgment_metadata",
                            "strict": True,
                            "schema": schema["json_schema"]
                        }
                    },
                    timeout=self.timeout,
                    reasoning_effort="medium"
                )
                
                ai_metadata = json.loads(resp.choices[0].message.content)
                
                if attempt > 1:
                    logger.info(f"成功提取 metadata (經過 {attempt} 次嘗試): {judgment.jid}")
                else:
                    logger.info(f"成功提取 metadata: {judgment.jid}")
                    
                return MetadataExtractionResult(
                    defendants=ai_metadata.get("defendants", []),
                    case_metadata=ai_metadata.get("case_metadata", {}),
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
        
        # 理論上不會執行到這裡，但為了安全起見
        logger.error(f"達到最大重試次數 {self.max_retries} 次，提取失敗: {judgment.jid}")
        raise Exception(f"達到最大重試次數 {self.max_retries} 次，需要重新查詢資料: {judgment.jid}")
