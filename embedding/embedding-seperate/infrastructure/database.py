import logging
import time
from typing import List, Optional
import httpx
from supabase import Client
from ..domain import (
    SummaryRepository,
    MetadataRepository,
    JudgmentSummary,
    JudgmentMetadata,
)

logger = logging.getLogger(__name__)


def execute_with_retry(query, max_retries=5, initial_delay=2):
    """
    Executes a Supabase query with retry logic for transient errors (5xx).
    """
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return query.execute()
        except Exception as e:
            # Check if it's a retryable error
            is_retryable = False
            error_msg = str(e)
            
            # Check for APIError dict structure in args
            if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict):
                code = e.args[0].get('code')
                if code and str(code).startswith('5'):
                    is_retryable = True
            
            # Check string representation
            if "500" in error_msg or "502" in error_msg or "503" in error_msg or "504" in error_msg:
                is_retryable = True
            
            # Specific Cloudflare/Postgrest error
            if "JSON could not be generated" in error_msg:
                is_retryable = True
            
            # Connection errors usually show up as exceptions as well, 
            # ideally we should catch requests.exceptions.ConnectionError etc.
            # but they might be wrapped.
            if isinstance(e, httpx.RequestError):
                is_retryable = True
                
            if not is_retryable:
                raise e
            
            if attempt < max_retries - 1:
                logger.warning(f"Supabase request failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Supabase request failed after {max_retries} attempts: {e}")
                raise e


class SupabaseSummaryRepository(SummaryRepository):
    
    def __init__(self, client: Client, schema_name: str = "lawschatter"):
        self.client = client
        self.schema_name = schema_name
    
    def get_all_dates_desc(self) -> List[str]:
        logger.info("從 judgment_metadata 擷取所有獨特日期")
        query = (
            self.client
            .schema(self.schema_name)
            .table("judgment_metadata")
            .select("jdate")
            .order("jdate", desc=True)
        )
        resp = execute_with_retry(query)
        unique_dates = sorted({row["jdate"] for row in resp.data}, reverse=True)
        logger.info(f"找到 {len(unique_dates)} 個獨特日期")
        return unique_dates
    
    def get_unprocessed_jids_by_date(self, jdate: str) -> List[str]:
        logger.info(f"透過 RPC 獲取所有未嵌入的判決 ID")
        query = (
            self.client
            .rpc("get_unembedded_jids")
        )
        resp = execute_with_retry(query)
        result = resp.data if resp.data else []
        jids = [row["jid"] for row in result]
        logger.info(f"找到 {len(jids)} 個未嵌入的判決")
        return jids
    
    def get_summaries_by_jid(self, jid: str) -> List[JudgmentSummary]:
        logger.info(f"擷取判決 {jid} 的 summary 記錄")
        query = (
            self.client
            .schema(self.schema_name)
            .table("judgment_summary")
            .select("*")
            .eq("jid", jid)
        )
        resp = execute_with_retry(query)
        
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
        query = self.client.schema(self.schema_name).table("judgment_summary").update(
            {"embedded_1": True}
        ).eq("jid", jid)
        execute_with_retry(query)


class SupabaseMetadataRepository(MetadataRepository):
    
    def __init__(self, client: Client, schema_name: str = "lawschatter"):
        self.client = client
        self.schema_name = schema_name
    
    def get_metadata_by_jid(self, jid: str) -> Optional[JudgmentMetadata]:
        logger.info(f"擷取判決 {jid} 的 metadata")
        query = (
            self.client
            .schema(self.schema_name)
            .table("judgment_metadata")
            .select("*")
            .eq("jid", jid)
        )
        resp = execute_with_retry(query)
        
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


class SupabaseSummaryMultivectorRepository(SummaryRepository):
    
    def __init__(self, client: Client, schema_name: str = "lawschatter"):
        self.client = client
        self.schema_name = schema_name
    
    def get_all_dates_desc(self) -> List[str]:
        logger.info("從 judgment_metadata 擷取所有獨特日期")
        query = (
            self.client
            .schema(self.schema_name)
            .table("judgment_metadata")
            .select("jdate")
            .order("jdate", desc=True)
        )
        resp = execute_with_retry(query)
        unique_dates = sorted({row["jdate"] for row in resp.data}, reverse=True)
        logger.info(f"找到 {len(unique_dates)} 個獨特日期")
        return unique_dates
    
    def get_unprocessed_jids_by_date(self, jdate: str) -> List[str]:
        logger.info(f"透過 RPC 獲取所有未嵌入的判決 ID")
        query = (
            self.client
            .rpc("get_unembedded_jids_multivector")
        )
        resp = execute_with_retry(query)
        result = resp.data if resp.data else []
        jids = [row["jid"] for row in result]
        logger.info(f"找到 {len(jids)} 個未嵌入的判決")
        return jids
    
    def get_summaries_by_jid(self, jid: str) -> List[JudgmentSummary]:
        logger.info(f"擷取判決 {jid} 的 summary 記錄")
        query = (
            self.client
            .schema(self.schema_name)
            .table("judgment_summary")
            .select("*")
            .eq("jid", jid)
        )
        resp = execute_with_retry(query)
        
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
        query = self.client.schema(self.schema_name).table("judgment_summary").update(
            {"embedded_multivector": True}
        ).eq("jid", jid)
        execute_with_retry(query)
