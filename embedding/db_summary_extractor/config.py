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
class AIServiceConfig:
    openai_api_key: str
    model: str = "gpt-5"
    reasoning_effort: str = "medium"
    timeout: int = 300


@dataclass
class SchemaConfig:
    schema_file_path: str


@dataclass
class ProcessConfig:
    sleep_interval: int = 60


@dataclass
class AppConfig:
    database: DatabaseConfig
    ai_service: AIServiceConfig
    schema: SchemaConfig
    process: ProcessConfig
    
    @staticmethod
    def from_env() -> "AppConfig":
        return AppConfig(
            database=DatabaseConfig(
                supabase_url=os.getenv("SUPABASE_URL", "https://supalaw.mooo.com/"),
                supabase_key=os.getenv("SUPABASE_KEY"),
                schema_name=os.getenv("SCHEMA_NAME", "lawschatter"),
            ),
            ai_service=AIServiceConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("AI_MODEL", "gpt-5"),
                reasoning_effort=os.getenv("REASONING_EFFORT", "medium"),
                timeout=int(os.getenv("AI_TIMEOUT", "300")),
            ),
            schema=SchemaConfig(
                schema_file_path=os.getenv(
                    "SCHEMA_FILE", 
                    "judgment_summary_schema.json"
                ),
            ),
            process=ProcessConfig(
                sleep_interval=int(os.getenv("SLEEP_INTERVAL", "60")),
            ),
        )

