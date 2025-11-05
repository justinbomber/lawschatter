import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class QdrantConfig:
    url: str
    collection_name: str


@dataclass
class OpenAIConfig:
    api_key: str
    model: str


@dataclass
class GoogleAIConfig:
    api_key: str
    model: str


@dataclass
class CohereConfig:
    api_key: str
    model: str


@dataclass
class XAIConfig:
    api_key: str
    model: str
    base_url: str


@dataclass
class APIConfig:
    host: str
    port: int
    reload: bool


@dataclass
class EmbeddingConfig:
    dense_name: str
    sparse_name: str
    stopwords_path: str


class Settings:
    def __init__(self):
        load_dotenv()
        
        self.qdrant = QdrantConfig(
            url=os.getenv("QDRANT_CLIENT", "http://localhost:6333"),
            collection_name=os.getenv("COLLECTION_NAME", "default_collection")
        )
        
        self.openai = OpenAIConfig(
            api_key=self._get_required_env("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-5")
        )
        
        self.google_ai = GoogleAIConfig(
            api_key=self._get_required_env("GENAI_EMBEDDING_API_KEY"),
            model=os.getenv("GOOGLE_EMBEDDING_MODEL", "gemini-embedding-001")
        )
        
        self.cohere = CohereConfig(
            api_key=os.getenv("COHERE_API_KEY", ""),
            model=os.getenv("COHERE_MODEL", "rerank-v3.5")
        )
        
        self.xai = XAIConfig(
            api_key=os.getenv("XAI_API_KEY", ""),
            model=os.getenv("XAI_MODEL", "grok-3"),
            base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
        )
        
        self.api = APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            reload=os.getenv("API_RELOAD", "true").lower() == "true"
        )
        
        self.embedding = EmbeddingConfig(
            dense_name=os.getenv("DENSE_VECTOR_NAME", "dense"),
            sparse_name=os.getenv("SPARSE_VECTOR_NAME", "bm25"),
            stopwords_path=os.getenv("STOPWORDS_PATH", "zh-t.txt")
        )
    
    @staticmethod
    def _get_required_env(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(f"{key} environment variable is required")
        return value

