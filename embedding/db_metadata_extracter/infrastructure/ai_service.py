import json
import logging
from typing import Dict, Any
from openai import OpenAI
from ..domain import MetadataExtractor, JudgmentRecord, MetadataExtractionResult

logger = logging.getLogger(__name__)


class OpenAIMetadataExtractor(MetadataExtractor):
    
    def __init__(self, client: OpenAI, model: str = "gpt-5"):
        self.client = client
        self.model = model
    
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
            timeout=180,
            reasoning_effort="medium"
        )
        
        ai_metadata = json.loads(resp.choices[0].message.content)
        
        return MetadataExtractionResult(
            defendants=ai_metadata.get("defendants", []),
            case_metadata=ai_metadata.get("case_metadata", {}),
        )

