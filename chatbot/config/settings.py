import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class RAGServerConfig:
    url: str
    timeout: int


@dataclass
class OpenAIConfig:
    api_key: str
    model: str


@dataclass
class XAIConfig:
    api_key: str
    model: str
    base_url: str


@dataclass
class LLMConfig:
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


@dataclass
class SupabaseConfig:
    url: str
    key: str
    schema_name: str


class Settings:
    def __init__(self):
        load_dotenv()
        
        self.rag_server = RAGServerConfig(
            url=os.getenv("RAG_SERVER_URL", "http://localhost:8000"),
            timeout=int(os.getenv("RAG_SERVER_TIMEOUT", "30"))
        )
        
        self.openai = OpenAIConfig(
            api_key=self._get_required_env("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-5")
        )
        
        self.xai = XAIConfig(
            api_key=os.getenv("XAI_API_KEY", ""),
            model=os.getenv("XAI_MODEL", "grok-3"),
            base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
        )
        
        self.llm = LLMConfig(
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
        
        self.supabase = SupabaseConfig(
            url=self._get_required_env("SUPABASE_URL"),
            key=self._get_required_env("SUPABASE_KEY"),
            schema_name=os.getenv("SUPABASE_SCHEMA", "lawschatter")
        )
    
    @staticmethod
    def _get_required_env(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(f"{key} environment variable is required")
        return value

