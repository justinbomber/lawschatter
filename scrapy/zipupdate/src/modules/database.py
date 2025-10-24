from supabase import create_client, Client
from .config import Config
import logging


class DatabaseConnection:
    def __init__(self, config: Config, logger: logging.Logger = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.client: Client = create_client(
            config.supabase_url,
            config.supabase_service_key
        )

    def insert_judgment(self, judgment_data: dict):
        result = self.client.schema(self.config.target_schema).table(self.config.target_table).insert(judgment_data).execute()
        return result

    def check_judgment_exists(self, jid: str):
        result = self.client.schema(self.config.target_schema).table(self.config.target_table).select("jid").eq("jid", jid).execute()
        return len(result.data) > 0

    def insert_judgments_individually(self, judgments: list):
        inserted_count = 0
        skipped_count = 0
        total_count = len(judgments)
        
        self.logger.info(f"開始逐筆插入 {total_count} 筆判決資料")
        
        for index, judgment in enumerate(judgments, 1):
            jid = judgment.get('jid', 'Unknown')
            
            if not self.check_judgment_exists(jid):
                result = self.client.schema(self.config.target_schema).table(self.config.target_table).insert(judgment).execute()
                inserted_count += 1
                self.logger.info(f"[{index}/{total_count}] 成功插入: {jid}")
            else:
                skipped_count += 1
                self.logger.info(f"[{index}/{total_count}] 已存在跳過: {jid}")
        
        self.logger.info(f"插入完成 - 總計: {total_count}, 新增: {inserted_count}, 跳過: {skipped_count}")
        return {"inserted": inserted_count, "skipped": skipped_count}