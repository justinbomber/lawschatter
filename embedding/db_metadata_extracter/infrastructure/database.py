import logging
from typing import List
from supabase import Client
from ..domain import (
    JudgmentRepository,
    MetadataRepository,
    JudgmentRecord,
    MetadataRecord,
)

logger = logging.getLogger(__name__)


class SupabaseJudgmentRepository(JudgmentRepository):
    
    def __init__(self, client: Client, schema_name: str = "lawschatter"):
        self.client = client
        self.schema_name = schema_name
    
    def get_all_dates_desc(self) -> List[str]:
        logger.info("擷取所有獨特日期（遞減排序）")
        resp = (
            self.client
            .schema(self.schema_name)
            .table("main_judgments")
            .select("jdate", distinct=True)
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
            jid_full=data.get("jid_full", ""),
            jyear=data.get("jyear", ""),
            jcase=data.get("jcase", ""),
            jno=data.get("jno", ""),
            jdate=data.get("jdate", ""),
            jtitle=data.get("jtitle", ""),
            case_type=data.get("case_type", ""),
            jtitle_type=data.get("jtitle_type", ""),
            jfull=data.get("jfull", ""),
        )
    
    def get_judgment_ids_by_date_and_titles(
        self, 
        jdate: str, 
        target_titles: List[str]
    ) -> List[str]:
        logger.info(f"擷取日期 {jdate} 符合標題條件的判決 ID")
        resp = (
            self.client
            .schema(self.schema_name)
            .table("main_judgments")
            .select("jid")
            .eq("jdate", jdate)
            .in_("jtitle", target_titles)
            .execute()
        )
        return [row["jid"] for row in resp.data]
    
    def get_unprocessed_jids_by_date_and_titles(
        self,
        jdate: str,
        target_titles: List[str],
        include_ruling: bool = False
    ) -> List[str]:
        logger.info(f"透過 RPC 獲取日期 {jdate} 未處理的判決 ID")
        jdate_int = int(jdate) if isinstance(jdate, str) else jdate
        resp = (
            self.client
            .rpc("get_unprocessed_metadata_jids", {
                "p_jdate": jdate_int,
                "p_target_titles": target_titles,
                "p_include_ruling": include_ruling
            })
            .execute()
        )
        result = resp.data if resp.data else []
        jids = [row["jid"] for row in result]
        logger.info(f"找到 {len(jids)} 筆未處理的判決")
        return jids


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
    
    def has_metadata(self, jid: str) -> bool:
        logger.info(f"檢查判決 {jid} 是否已存在 metadata")
        resp = (
            self.client
            .schema(self.schema_name)
            .table("judgment_metadata")
            .select("jid")
            .eq("jid", jid)
            .limit(1)
            .execute()
        )
        exists = len(resp.data) > 0 if resp.data else False
        if exists:
            logger.info(f"判決 {jid} 已存在 metadata")
        return exists
    
    def insert_lock_record(self, jid: str, jdate: str) -> None:
        logger.info(f"插入鎖定記錄: {jid}")
        jdate_int = int(jdate) if isinstance(jdate, str) else jdate
        record_data = {
            "jid": jid,
            "jdate": jdate_int,
        }
        self.client.schema(self.schema_name).table("judgment_metadata").upsert(record_data).execute()
    
    def delete_lock_record(self, jid: str) -> None:
        logger.info(f"刪除鎖定記錄: {jid}")
        self.client.schema(self.schema_name).table("judgment_metadata").delete().eq("jid", jid).execute()
    
    def save_metadata(self, metadata: MetadataRecord) -> None:
        logger.info(f"儲存 metadata: {metadata.jid}")
        jdate_int = int(metadata.jdate) if isinstance(metadata.jdate, str) else metadata.jdate
        jyear_int = int(metadata.jyear) if metadata.jyear and isinstance(metadata.jyear, str) else metadata.jyear
        record_data = {
            "jid": metadata.jid,
            "jid_full": metadata.jid_full,
            "jyear": jyear_int,
            "jcase": metadata.jcase,
            "jno": metadata.jno,
            "jdate": jdate_int,
            "jtitle": metadata.jtitle,
            "case_type": metadata.case_metadata.get("case_type", ""),
            "jtitle_type": metadata.case_metadata.get("jtitle_type", ""),
            "defendants": metadata.defendants,
            "case_metadata": metadata.case_metadata,
        }
        self.client.schema(self.schema_name).table("judgment_metadata").insert(record_data).execute()
    
    def update_metadata(self, metadata: MetadataRecord) -> None:
        logger.info(f"更新 metadata: {metadata.jid}")
        jdate_int = int(metadata.jdate) if isinstance(metadata.jdate, str) else metadata.jdate
        jyear_int = int(metadata.jyear) if metadata.jyear and isinstance(metadata.jyear, str) else metadata.jyear
        record_data = {
            "jid_full": metadata.jid_full,
            "jyear": jyear_int,
            "jcase": metadata.jcase,
            "jno": metadata.jno,
            "jdate": jdate_int,
            "jtitle": metadata.jtitle,
            "case_type": metadata.case_metadata.get("case_type", ""),
            "jtitle_type": metadata.case_metadata.get("jtitle_type", ""),
            "defendants": metadata.defendants,
            "case_metadata": metadata.case_metadata,
        }
        self.client.schema(self.schema_name).table("judgment_metadata").update(record_data).eq("jid", metadata.jid).execute()

