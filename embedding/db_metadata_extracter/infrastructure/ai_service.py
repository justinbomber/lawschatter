import json
import logging
import time
from typing import Dict, Any
from openai import OpenAI
from openai import APITimeoutError, APIConnectionError, APIError
from ..domain import MetadataExtractor, JudgmentRecord, MetadataExtractionResult

logger = logging.getLogger(__name__)


class OpenAIMetadataExtractor(MetadataExtractor):
    
    def __init__(self, client: OpenAI, model: str = "gpt-5", timeout: int = 600, max_wait_time: int = 300):
        self.client = client
        self.model = model
        self.timeout = timeout
        self.max_wait_time = max_wait_time  # 最大等待時間（秒），防止等待時間過長
    
    def extract(
        self, 
        judgment: JudgmentRecord, 
        schema: Dict[str, Any]
    ) -> MetadataExtractionResult:
        logger.info(f"使用 OpenAI 提取 metadata: {judgment.jid}")
        
        system_prompt = (
            "你是一名專業的法律判決資料結構化助手。請仔細閱讀提供的判決全文與分類規範，"
            "並嚴格按照 JSON Schema 輸出結構化結果。\n\n"
        )
        user_prompt = judgment.jfull
        
        # 無限重試直到成功
        attempt = 0
        while True:
            attempt += 1
            try:
                if attempt == 1:
                    logger.info(f"嘗試提取 metadata: {judgment.jid}")
                elif attempt % 10 == 0:
                    logger.warning(f"仍在重試提取 metadata (第 {attempt} 次): {judgment.jid}")
                else:
                    logger.debug(f"重試提取 metadata (第 {attempt} 次): {judgment.jid}")
                
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
                    timeout=300,
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
