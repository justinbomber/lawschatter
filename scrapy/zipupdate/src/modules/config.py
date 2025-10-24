import os
from dataclasses import dataclass
import logging


@dataclass
class Config:
    supabase_url: str
    supabase_service_key: str
    target_schema: str
    target_table: str
    log_level: int = logging.INFO

    @classmethod
    def from_env(cls):
        return cls(
            supabase_url=os.getenv('SUPABASE_URL'),
            supabase_service_key=os.getenv('SUPABASE_SERVICE_KEY'),
            target_schema=os.getenv('TARGET_SCHEMA'),
            target_table=os.getenv('TARGET_TABLE')
        )

    def validate(self):
        if not self.supabase_url:
            raise EnvironmentError("SUPABASE_URL environment variable is required")
        if not self.supabase_service_key:
            raise EnvironmentError("SUPABASE_SERVICE_KEY environment variable is required")
        if not self.target_schema:
            raise EnvironmentError("TARGET_SCHEMA environment variable is required")
        if not self.target_table:
            raise EnvironmentError("TARGET_TABLE environment variable is required")

    def setup_logging(self):
        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s | %(levelname)s | %(message)s"
        )
        return logging.getLogger("zipupdate")