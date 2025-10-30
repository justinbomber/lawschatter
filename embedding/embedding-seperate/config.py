import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    supabase_url: str
    supabase_key: str
    schema_name: str = "lawschatter"


@dataclass
class VectorStoreConfig:
    qdrant_url: str
    collection_name: str
    embedding_api_key: str
    embedding_model: str = "gemini-embedding-001"


@dataclass
class TokenizerConfig:
    stopwords_path: str = "zh-t.txt"
    dict_path: str = "dict.txt.big"


@dataclass
class AppConfig:
    database: DatabaseConfig
    vector_store: VectorStoreConfig
    tokenizer: TokenizerConfig
    
    @staticmethod
    def from_env() -> "AppConfig":
        return AppConfig(
            database=DatabaseConfig(
                supabase_url=os.getenv("SUPABASE_URL", "https://supalaw.mooo.com/"),
                supabase_key=os.getenv("SUPABASE_KEY"),
                schema_name=os.getenv("SCHEMA_NAME", "lawschatter"),
            ),
            vector_store=VectorStoreConfig(
                qdrant_url=os.getenv("QDRANT_SERVER", "http://localhost:6333"),
                collection_name=os.getenv("COLLECTION_NAME", "new_judgment_0915"),
                embedding_api_key=os.getenv("GENAI_EMBEDDING_API_KEY"),
                embedding_model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
            ),
            tokenizer=TokenizerConfig(
                stopwords_path=os.getenv("STOPWORDS_PATH", "zh-t.txt"),
                dict_path=os.getenv("DICT_PATH", "dict.txt.big"),
            ),
        )

