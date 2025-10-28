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
class AIServiceConfig:
    openai_api_key: str
    model: str = "gpt-5"


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
        )

