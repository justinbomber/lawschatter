import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class RAGServerConfig:
    url: str
    timeout: int


@dataclass
class LLMConfig:
    api_key: str
    model: str
    temperature: float
    max_tokens: int


@dataclass
class APIConfig:
    host: str
    port: int
    reload: bool


@dataclass
class RAGSearchConfig:
    collection: str
    mode: str
    limit: int
    score_threshold: float


class Settings:
    def __init__(self):
        load_dotenv()
        
        self.rag_server = RAGServerConfig(
            url=os.getenv("RAG_SERVER_URL", "http://localhost:8000"),
            timeout=int(os.getenv("RAG_SERVER_TIMEOUT", "30"))
        )
        
        self.llm = LLMConfig(
            api_key=self._get_required_env("LLM_API_KEY"),
            model=os.getenv("LLM_MODEL", "gpt-4"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000"))
        )
        
        self.api = APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8001")),
            reload=os.getenv("API_RELOAD", "true").lower() == "true"
        )
        
        self.rag_search = RAGSearchConfig(
            collection=os.getenv("RAG_COLLECTION", "embedding-seperate"),
            mode=os.getenv("RAG_MODE", "hybrid"),
            limit=int(os.getenv("RAG_LIMIT", "10")),
            score_threshold=float(os.getenv("RAG_SCORE_THRESHOLD", "1"))
        )
    
    @staticmethod
    def _get_required_env(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(f"{key} environment variable is required")
        return value

