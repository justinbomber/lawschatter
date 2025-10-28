import json
import logging
from typing import Dict, Any
from ..domain import SchemaProvider

logger = logging.getLogger(__name__)


class FileSchemaProvider(SchemaProvider):
    
    def __init__(self, schema_file_path: str):
        self.schema_file_path = schema_file_path
        self._schema = None
    
    def get_schema(self) -> Dict[str, Any]:
        if self._schema is None:
            logger.info(f"載入 schema 檔案: {self.schema_file_path}")
            with open(self.schema_file_path, "r", encoding="utf-8") as f:
                self._schema = json.load(f)
        return self._schema

