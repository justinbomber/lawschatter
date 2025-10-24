import os
import json
import logging
from supabase import create_client, Client
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://supalaw.mooo.com/"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SCHEMA_FILE = os.getenv("SCHEMA_FILE", "judgment_metadata_schema.json")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
    metadata_schema = json.load(f)


def fetch_all_jdates_desc():
    logger.info("Fetching all unique jdates in descending order")
    resp = supabase.table("main_judgments").select("jdate").order("jdate", desc=True).execute()
    unique_dates = sorted({row["jdate"] for row in resp.data}, reverse=True)
    logger.info(f"Found {len(unique_dates)} unique dates")
    return unique_dates

def fetch_unprocessed_jids_for_date_rpc(jdate):
    logger.info(f"Processing date using RPC: {jdate}")

    resp = supabase.rpc("get_unprocessed_jids", {"p_jdate": jdate}).execute()
    unprocessed_jids = resp.data

    logger.info(f"Found {len(unprocessed_jids)} unprocessed jids for {jdate}")
    return unprocessed_jids

def process_single_jid(jid, jdate):
    logger.info(f"Processing jid: {jid}")

    judgment = supabase.table("main_judgments").select("*").eq("jid", jid).single().execute().data

    prompt = (
        "請根據以下JSON schema從判決書中提取metadata，回應必須是有效的JSON格式: "
        + json.dumps(metadata_schema["json_schema"], ensure_ascii=False)
        + "\n\n判決書內容: "
        + json.dumps(judgment, ensure_ascii=False)
    )

    resp = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    ai_metadata = json.loads(resp.choices[0].message.content)

    record_data = {
        "jid": jid,
        "jid_full": judgment.get("jid_full"),
        "jyear": judgment.get("jyear"),
        "jcase": judgment.get("jcase"),
        "jno": judgment.get("jno"),
        "jdate": jdate,
        "jtitle": judgment.get("jtitle"),
        "case_type": judgment.get("case_type"),
        "jtitle_type": judgment.get("jtitle_type"),
        # "chunk_type": "judgment",
        "chunks": [judgment.get("jfull", "")],
        "defendants": ai_metadata.get("defendants"),
        "case_metadata": ai_metadata.get("case_metadata"),
    }

    supabase.table("judgment_metadata").insert(record_data).execute()

    logger.info(f"Successfully processed and inserted metadata for jid: {jid}")

def main():
    logger.info("Starting metadata extraction process (RPC version)")

    total_processed = 0
    for jdate in fetch_all_jdates_desc():
        jids = fetch_unprocessed_jids_for_date_rpc(jdate)

        if not jids:
            continue

        logger.info(f"Processing {len(jids)} jids for date {jdate}")

        for jid in jids:
            process_single_jid(jid, jdate)
            total_processed += 1

    logger.info(f"Metadata extraction completed. Total processed: {total_processed}")

if __name__ == "__main__":
    main()