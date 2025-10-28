import logging
from typing import List
from supabase import Client
from ..domain import (
    JudgmentRepository,
    MetadataRepository,
    SummaryRepository,
    JudgmentRecord,
    SummaryRecord,
)

logger = logging.getLogger(__name__)


class SupabaseJudgmentRepository(JudgmentRepository):
    
    def __init__(self, client: Client, schema_name: str = "lawschatter"):
        self.client = client
        self.schema_name = schema_name
    
    def get_all_dates_from_metadata_desc(self) -> List[str]:
        logger.info("從 judgment_metadata 擷取所有獨特日期（遞減排序）")
        resp = (
            self.client
            .schema(self.schema_name)
            .table("judgment_metadata")
            .select("jdate")
            .order("jdate", desc=True)
            .execute()
        )
        unique_dates = sorted({row["jdate"] for row in resp.data}, reverse=True)
        logger.info(f"找到 {len(unique_dates)} 個獨特日期")
        return unique_dates
    
    def get_judgment(self, jid: str) -> JudgmentRecord:
        logger.info(f"擷取判決: {jid}")
        data = (
            self.client
            .schema(self.schema_name)
            .table("main_judgments")
            .select("*")
            .eq("jid", jid)
            .single()
            .execute()
            .data
        )
        return JudgmentRecord(
            jid=data["jid"],
            jdate=data.get("jdate", ""),
            jfull=data.get("jfull", ""),
        )
    
    def get_judgment_ids_by_date(self, jdate: str) -> List[str]:
        logger.info(f"擷取日期 {jdate} 的判決 ID")
        resp = (
            self.client
            .schema(self.schema_name)
            .table("main_judgments")
            .select("jid")
            .eq("jdate", jdate)
            .execute()
        )
        return [row["jid"] for row in resp.data]


class SupabaseMetadataRepository(MetadataRepository):
    
    def __init__(self, client: Client, schema_name: str = "lawschatter"):
        self.client = client
        self.schema_name = schema_name
    
    def get_metadata_ids_by_date(self, jdate: str) -> List[str]:
        logger.info(f"擷取日期 {jdate} 已有 metadata 的判決 ID")
        resp = (
            self.client
            .schema(self.schema_name)
            .table("judgment_metadata")
            .select("jid")
            .eq("jdate", jdate)
            .execute()
        )
        return [row["jid"] for row in resp.data]


class SupabaseSummaryRepository(SummaryRepository):
    
    def __init__(self, client: Client, schema_name: str = "lawschatter"):
        self.client = client
        self.schema_name = schema_name
    
    def get_summary_ids_by_date(self, jdate: str) -> List[str]:
        logger.info(f"擷取日期 {jdate} 已有 summary 的判決 ID")
        resp = (
            self.client
            .schema(self.schema_name)
            .table("judgment_summary")
            .select("jid")
            .eq("jdate", jdate)
            .execute()
        )
        return list({row["jid"] for row in resp.data})
    
    def save_summary(self, summary: SummaryRecord) -> None:
        logger.info(f"儲存 summary: {summary.jid} - {summary.summary_type}")
        record_data = {
            "point_id": summary.point_id,
            "jid": summary.jid,
            "jdate": summary.jdate,
            "summary_type": summary.summary_type,
            "content": summary.content,
            "defendent_name": summary.defendent_name,
        }
        self.client.schema(self.schema_name).table("judgment_summary").insert(record_data).execute()

