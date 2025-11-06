import json
import logging
import time
from typing import Dict, Any, List
from openai import OpenAI
from openai import APITimeoutError, APIConnectionError, APIError
from ..domain import MetadataExtractor, JudgmentRecord, MetadataExtractionResult

logger = logging.getLogger(__name__)


class OpenAIMetadataExtractor(MetadataExtractor):
    
    def __init__(
        self, 
        client: OpenAI, 
        model: str = "gpt-5", 
        timeout: int = 600, 
        max_wait_time: int = 300, 
        max_retries: int = 5,
        chunk_size: int = 7500,
        overlap_ratio: float = 0.25
    ):
        self.client = client
        self.model = model
        self.timeout = timeout
        self.max_wait_time = max_wait_time
        self.max_retries = max_retries
        self.chunk_size = chunk_size
        self.overlap_ratio = overlap_ratio
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        text_length = len(text)
        
        if text_length <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < text_length:
            if start + self.chunk_size >= text_length:
                chunks.append(text[start:])
                break
            
            end_limit = start + self.chunk_size
            
            best_split_pos = -1
            for i in range(end_limit, start, -1):
                if i < len(text) and text[i] in ['。', '，', '、', '；', '：', '！', '？', '\n']:
                    best_split_pos = i + 1
                    break
            
            if best_split_pos == -1:
                logger.warning(f"在位置 {start}-{end_limit} 找不到標點符號，強制切分")
                best_split_pos = end_limit
            
            chunk = text[start:best_split_pos]
            chunks.append(chunk)
            
            overlap_size = int(self.chunk_size * self.overlap_ratio)
            overlap_start = max(start, best_split_pos - overlap_size)
            
            for i in range(overlap_start, best_split_pos):
                if text[i] in ['。', '，', '、', '；', '：', '！', '？', '\n']:
                    start = i + 1
                    break
            else:
                start = best_split_pos
        
        logger.info(f"文本長度 {text_length} 字，在標點符號處切分為 {len(chunks)} 個 chunks")
        return chunks
    
    def _extract_single_chunk(
        self,
        chunk_text: str,
        previous_result: Dict[str, Any],
        schema: Dict[str, Any],
        jid: str,
        chunk_index: int,
        total_chunks: int
    ) -> Dict[str, Any]:
        
        if chunk_index == 0:
            system_prompt = (
                "你是一名專業的法律判決資料結構化助手。\n\n"
                "重要規則：\n"
                "1. 必須準確輸出繁體中文法律專有名詞，絕對不可使用同音字或形似字替換\n"
                "2. 常見法律術語務必正確：詐欺（不是誚喻）、洗錢（不是洗錯）、銀行（不是銏行）\n"
                "3. 請仔細閱讀判決原文，直接複製原文中的法律用語，不要自行改寫\n"
                "4. 嚴格按照 JSON Schema 輸出結構化結果\n\n"
            )
            user_prompt = chunk_text
        else:
            system_prompt = (
                "你是一名專業的法律判決資料結構化助手。\n\n"
                "重要規則：\n"
                "1. 必須準確輸出繁體中文法律專有名詞，絕對不可使用同音字或形似字替換\n"
                "2. 常見法律術語務必正確：詐欺（不是誚喻）、洗錢（不是洗錯）、銀行（不是銏行）\n"
                "3. 請仔細閱讀判決原文片段，直接複製原文中的法律用語\n"
                "4. 繼續提取當前片段的資訊，合併並更新結構化結果\n"
                "5. 若當前片段資訊與前一片段衝突，以當前片段（原文）為準\n"
                "6. 嚴格按照 JSON Schema 輸出結構化結果\n\n"
            )
            user_prompt = (
                f"參考資訊（前一個片段的提取結果，僅供參考，若有錯誤請以原文為準）：\n"
                f"{json.dumps(previous_result, ensure_ascii=False)}\n\n"
                f"當前判決片段（請以此為準）：\n{chunk_text}"
            )
        
        attempt = 0
        
        while attempt < self.max_retries:
            attempt += 1
            previous_result_str = json.dumps(previous_result, ensure_ascii=False)
            
            try:
                if attempt == 1:
                    logger.info(f"處理 chunk {chunk_index + 1}/{total_chunks}: {jid}, length: {len(chunk_text)+len(previous_result_str)}")
                else:
                    logger.warning(f"重試處理 chunk {chunk_index + 1}/{total_chunks} (第 {attempt}/{self.max_retries} 次): {jid}")
                
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
                    reasoning_effort="high"
                )
                
                ai_metadata = json.loads(resp.choices[0].message.content)
                
                if attempt > 1:
                    logger.info(f"成功處理 chunk {chunk_index + 1}/{total_chunks} (經過 {attempt} 次嘗試): {jid}")
                else:
                    logger.info(f"成功處理 chunk {chunk_index + 1}/{total_chunks}: {jid}")
                
                return ai_metadata
                
            except (APITimeoutError, APIConnectionError) as e:
                if attempt >= self.max_retries:
                    logger.error(
                        f"達到最大重試次數 {self.max_retries} 次，chunk {chunk_index + 1}/{total_chunks} 處理失敗: {jid}. "
                        f"錯誤: {str(e)}"
                    )
                    raise Exception(
                        f"達到最大重試次數 {self.max_retries} 次，chunk {chunk_index + 1}/{total_chunks} 處理失敗: {jid}. "
                        f"最後錯誤: {str(e)}"
                    )
                
                wait_time = min((attempt * 5), self.max_wait_time)
                logger.warning(
                    f"API 請求超時或連接錯誤 (chunk {chunk_index + 1}/{total_chunks} 第 {attempt}/{self.max_retries} 次): {jid}. "
                    f"錯誤: {str(e)}. {wait_time} 秒後重試..."
                )
                time.sleep(wait_time)
                    
            except APIError as e:
                logger.error(f"API 錯誤 (chunk {chunk_index + 1}/{total_chunks}): {jid}. 錯誤: {str(e)}")
                raise
                
            except Exception as e:
                logger.error(f"未預期的錯誤 (chunk {chunk_index + 1}/{total_chunks}): {jid}. 錯誤: {str(e)}")
                raise
        
        logger.error(f"達到最大重試次數，chunk {chunk_index + 1}/{total_chunks} 處理失敗: {jid}")
        raise Exception(f"達到最大重試次數，chunk {chunk_index + 1}/{total_chunks} 處理失敗: {jid}")
    
    def extract(
        self, 
        judgment: JudgmentRecord, 
        schema: Dict[str, Any]
    ) -> MetadataExtractionResult:
        logger.info(f"使用 OpenAI 提取 metadata: {judgment.jid}")
        
        text_length = len(judgment.jfull)
        
        if text_length > self.chunk_size:
            logger.info(f"文本長度 {text_length} 超過 {self.chunk_size}，啟動切塊處理")
            chunks = self._split_text_into_chunks(judgment.jfull)
            
            previous_result = {}
            
            for i, chunk in enumerate(chunks):
                ai_metadata = self._extract_single_chunk(
                    chunk_text=chunk,
                    previous_result=previous_result,
                    schema=schema,
                    jid=judgment.jid,
                    chunk_index=i,
                    total_chunks=len(chunks)
                )
                previous_result = ai_metadata
            
            logger.info(f"完成所有 chunks 處理: {judgment.jid}")
            
            return MetadataExtractionResult(
                defendants=previous_result.get("defendants", []),
                case_metadata=previous_result.get("case_metadata", {}),
            )
        
        system_prompt = (
            "你是一名專業的法律判決資料結構化助手。\n\n"
            "重要規則：\n"
            "1. 必須準確輸出繁體中文法律專有名詞，絕對不可使用同音字或形似字替換\n"
            "2. 常見法律術語務必正確：詐欺（不是誚喻）、洗錢（不是洗錯）、銀行（不是銏行）\n"
            "3. 請仔細閱讀判決原文，直接複製原文中的法律用語，不要自行改寫\n"
            "4. 嚴格按照 JSON Schema 輸出結構化結果\n\n"
        )
        user_prompt = judgment.jfull
        
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
                    reasoning_effort="high"
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
        
        logger.error(f"達到最大重試次數 {self.max_retries} 次，提取失敗: {judgment.jid}")
        raise Exception(f"達到最大重試次數 {self.max_retries} 次，需要重新查詢資料: {judgment.jid}")
