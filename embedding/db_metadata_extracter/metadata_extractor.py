import os
import json
import logging
from supabase import create_client, Client
from openai import OpenAI
from dotenv import load_dotenv

# 自動載入當前資料夾下的 .env
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://supalaw.mooo.com/"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SCHEMA_FILE = os.getenv("SCHEMA_FILE", "judgment_metadata_schema.json")

TARGET_JTITLE = ["詐欺等", "詐欺", "洗錢防制法等", "洗錢防制法"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
    metadata_schema = json.load(f)

def should_ignore_file(json_data):
    if 'jfull' not in json_data:
        return False # 無JFULL欄位
    
    jfull_content = json_data['jfull']
    
    # 條件1: 前20個字中包含"裁定"
    first_20_chars = jfull_content[:20]
    if "裁定" in first_20_chars:
        return True # 裁定案件
    
    # 條件2: 不包含"詐騙"或"欺詐"
    # if "詐騙" not in jfull_content and "欺詐" not in jfull_content:
    #     return True # 不包含'詐騙'或'欺詐'
    
    return False

def fetch_all_jdates_desc():
    logger.info("Fetching all unique jdates in descending order")
    resp = supabase.schema("lawschatter").table("main_judgments").select("jdate").order("jdate", desc=True).execute()
    unique_dates = sorted({row["jdate"] for row in resp.data}, reverse=True)
    logger.info(f"Found {len(unique_dates)} unique dates")
    return unique_dates

def fetch_unprocessed_jids_for_date(jdate):
    logger.info(f"Processing date: {jdate}")

    main_resp = (
        supabase
        .schema("lawschatter")
        .table("main_judgments")
        .select("jid")
        .eq("jdate", jdate)
        .in_("jtitle", TARGET_JTITLE)
        .execute()
    )
    main_jids = {row["jid"] for row in main_resp.data}
    logger.info(f"Found {len(main_jids)} judgments matching jfull criteria for {jdate}")

    meta_resp = supabase.schema("lawschatter").table("judgment_metadata").select("jid").eq("jdate", jdate).execute()
    meta_jids = {row["jid"] for row in meta_resp.data}

    # sum_resp = supabase.schema("lawschatter").table("judgment_summary").select("jid").eq("jdate", jdate).execute()
    # sum_jids = {row["jid"] for row in sum_resp.data}

    unprocessed_jids = list(main_jids - meta_jids)
    logger.info(f"Found {len(unprocessed_jids)} unprocessed jids for {jdate}")

    return unprocessed_jids

def process_single_jid(jid, jdate, is_adjudicate=False):
    logger.info(f"Processing jid: {jid}")

    judgment = supabase.schema("lawschatter").table("main_judgments").select("*").eq("jid", jid).single().execute().data
    
    # 是否包含裁定案件
    if is_adjudicate: # 包含裁定案件
        pass
    else: # 不包含裁定案件
        if should_ignore_file(judgment):
            # 為裁定案件
            return False

    system_prompt = (
        "你是一名專業的法律判決資料結構化助手。請仔細閱讀提供的判決全文與分類規範，"
        "並嚴格按照 JSON Schema 輸出結構化結果。\n\n"
    )
    user_prompt = (
        judgment.get("jfull", "")
    )

    print("準備開始處理...jid: ", jid)

    resp = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "judgment_metadata",
                "strict": True,
                "schema": metadata_schema["json_schema"]
            }
        }
    )

    ai_metadata = json.loads(resp.choices[0].message.content)
    # save in json file
    # with open(f"output_{jid}_ai_metadata.json", "w", encoding="utf-8") as f:
    #     json.dump(ai_metadata, f, ensure_ascii=False, indent=4)

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
        # "chunks": [judgment.get("jfull", "")],
        "defendants": ai_metadata.get("defendants"),
        "case_metadata": ai_metadata.get("case_metadata"),
    }
    # with open(f"output_{jid}_record_data.json", "w", encoding="utf-8") as f:
    #     json.dump(record_data, f, ensure_ascii=False, indent=4)

    supabase.schema("lawschatter").table("judgment_metadata").insert(record_data).execute()
    

    logger.info(f"Successfully processed and inserted metadata for jid: {jid}")
    return True

def main():
    logger.info("Starting metadata extraction process")

    total_processed = 0
    for jdate in fetch_all_jdates_desc():
        jids = fetch_unprocessed_jids_for_date(jdate)

        if not jids:
            continue

        logger.info(f"Processing {len(jids)} jids for date {jdate}")

        for jid in jids:
            if process_single_jid(jid, jdate, False):
                total_processed += 1
            else:
                continue

    logger.info(f"Metadata extraction completed. Total processed: {total_processed}")

if __name__ == "__main__":
    main()