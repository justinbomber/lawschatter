import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    supabase_url: str
    supabase_key: str
    schema_name: str = "lawschatter"


@dataclass
class OpenAIServiceConfig:
    api_key: str
    model: str = "gpt-5"
    timeout: int = 600


@dataclass
class XAIServiceConfig:
    api_key: str
    base_url: str = "https://api.x.ai/v1"
    model: str = "grok-4-fast-reasoning"
    timeout: int = 600


@dataclass
class SchemaConfig:
    schema_file_path: str


@dataclass
class ProcessConfig:
    target_titles: List[str]
    include_adjudicate: bool = False


@dataclass
class AppConfig:
    database: DatabaseConfig
    openai_service: OpenAIServiceConfig
    xai_service: XAIServiceConfig
    schema: SchemaConfig
    process: ProcessConfig
    output_dir: str
    ai_provider: str = "openai"
    
    @staticmethod
    def from_env() -> "AppConfig":
        return AppConfig(
            database=DatabaseConfig(
                supabase_url=os.getenv("SUPABASE_URL", "https://supalaw.mooo.com/"),
                supabase_key=os.getenv("SUPABASE_KEY"),
                schema_name=os.getenv("SCHEMA_NAME", "lawschatter"),
            ),
            openai_service=OpenAIServiceConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("OPENAI_MODEL", "gpt-5"),
                timeout=int(os.getenv("OPENAI_TIMEOUT", "600")),
            ),
            xai_service=XAIServiceConfig(
                api_key=os.getenv("XAI_API_KEY"),
                base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
                model=os.getenv("XAI_MODEL", "grok-4-fast-reasoning"),
                timeout=int(os.getenv("XAI_TIMEOUT", "600")),
            ),
            schema=SchemaConfig(
                schema_file_path=os.getenv(
                    "SCHEMA_FILE", 
                    "judgment_metadata_schema.json"
                ),
            ),
            process=ProcessConfig(
                target_titles=["詐欺等", "詐欺", "洗錢防制法等", "洗錢防制法"],
                include_adjudicate=os.getenv("INCLUDE_ADJUDICATE", "false").lower() == "true",
            ),
            output_dir=os.getenv("OUTPUT_DIR", ".\\output"),
            ai_provider=os.getenv("AI_PROVIDER", "openai")
        )

