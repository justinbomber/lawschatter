import logging
from typing import List, Optional
from supabase import Client
from ..domain import (
    SummaryRepository,
    MetadataRepository,
    JudgmentSummary,
    JudgmentMetadata,
)

logger = logging.getLogger(__name__)


class SupabaseSummaryRepository(SummaryRepository):
    
    def __init__(self, client: Client, schema_name: str = "lawschatter"):
        self.client = client
        self.schema_name = schema_name
    
    def get_all_dates_desc(self) -> List[str]:
        logger.info("從 judgment_metadata 擷取所有獨特日期")
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
    
    def get_unprocessed_jids_by_date(self, jdate: str) -> List[str]:
        logger.info(f"擷取日期 {jdate} 未嵌入的判決 ID")
        
        main_resp = (
            self.client
            .schema(self.schema_name)
            .table("main_judgments")
            .select("jid")
            .eq("jdate", jdate)
            .execute()
        )
        main_jids = {row["jid"] for row in main_resp.data}
        
        meta_resp = (
            self.client
            .schema(self.schema_name)
            .table("judgment_metadata")
            .select("jid")
            .eq("jdate", jdate)
            .execute()
        )
        meta_jids = {row["jid"] for row in meta_resp.data}
        
        sum_resp = (
            self.client
            .schema(self.schema_name)
            .table("judgment_summary")
            .select("jid")
            .eq("jdate", jdate)
            .eq("embedded_1", False)
            .execute()
        )
        sum_jids = {row["jid"] for row in sum_resp.data}
        
        unprocessed = list(main_jids & meta_jids & sum_jids)
        logger.info(f"找到 {len(unprocessed)} 個未嵌入的判決")
        
        return unprocessed
    
    def get_summaries_by_jid(self, jid: str) -> List[JudgmentSummary]:
        logger.info(f"擷取判決 {jid} 的 summary 記錄")
        resp = (
            self.client
            .schema(self.schema_name)
            .table("judgment_summary")
            .select("*")
            .eq("jid", jid)
            .execute()
        )
        
        summaries = []
        for row in resp.data:
            summary = JudgmentSummary(
                point_id=row["point_id"],
                jid=row["jid"],
                jdate=row["jdate"],
                summary_type=row["summary_type"],
                content=row["content"],
                defendent_name=row.get("defendent_name"),
            )
            summaries.append(summary)
        
        logger.info(f"找到 {len(summaries)} 筆 summary 記錄")
        return summaries
    
    def mark_as_embedded(self, jid: str) -> None:
        logger.info(f"標記判決 {jid} 為已嵌入")
        self.client.schema(self.schema_name).table("judgment_summary").update(
            {"embedded_1": True}
        ).eq("jid", jid).execute()


class SupabaseMetadataRepository(MetadataRepository):
    
    def __init__(self, client: Client, schema_name: str = "lawschatter"):
        self.client = client
        self.schema_name = schema_name
    
    def get_metadata_by_jid(self, jid: str) -> Optional[JudgmentMetadata]:
        logger.info(f"擷取判決 {jid} 的 metadata")
        resp = (
            self.client
            .schema(self.schema_name)
            .table("judgment_metadata")
            .select("*")
            .eq("jid", jid)
            .execute()
        )
        
        if not resp.data:
            logger.warning(f"找不到判決 {jid} 的 metadata")
            return None
        
        row = resp.data[0]
        metadata = JudgmentMetadata(
            jid=row["jid"],
            jid_full=row["jid_full"],
            jyear=row["jyear"],
            jcase=row["jcase"],
            jno=row["jno"],
            jdate=row["jdate"],
            jtitle=row["jtitle"],
            case_type=row.get("case_type", ""),
            defendants=row.get("defendants", []),
            case_metadata=row.get("case_metadata", {}),
        )
        
        return metadata

