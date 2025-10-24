import os
from langchain_core.documents import Document
import hashlib
import json
from supabase import create_client, Client
from openai import OpenAI
import logging
import time
import dotenv

dotenv.load_dotenv()

SUPABASE_URL = "https://supalaw.mooo.com/"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

with open("judgment_summary_schema.json", "r", encoding="utf-8") as f:
    summary_schema = json.load(f)

def fetch_all_jdates_desc():
    resp = supabase.schema("lawschatter").table("judgment_metadata").select("jdate").order("jdate", desc=True).execute()
    unique_dates = sorted({row["jdate"] for row in resp.data}, reverse=True)
    return unique_dates

def fetch_unprocessed_jids_for_date(jdate):
    main_resp = supabase.schema("lawschatter").table("main_judgments").select("jid").eq("jdate", jdate).execute()
    main_jids = {row["jid"] for row in main_resp.data}

    meta_resp = supabase.schema("lawschatter").table("judgment_metadata").select("jid").eq("jdate", jdate).execute()
    meta_jids = {row["jid"] for row in meta_resp.data}

    sum_resp = supabase.schema("lawschatter").table("judgment_summary").select("jid").eq("jdate", jdate).execute()
    sum_jids = {row["jid"] for row in sum_resp.data}

    unprocessed_jids = list((main_jids & meta_jids) - sum_jids)
    return unprocessed_jids



def process_single_jid(jid, jdate):
    judgment = supabase.schema("lawschatter").table("main_judgments").select("*").eq("jid", jid).single().execute().data

    system_prompt = (
        "你是一名專業的法律判決分析助手。請仔細閱讀提供的判決全文，"
        "並嚴格按照 JSON Schema 輸出結構化分析結果。"
        "必須完整填寫每位被告的所有六個欄位，若資料不足請填寫「未知」。"
    )
    user_prompt = judgment.get("jfull", "")

    logger = logging.getLogger("summary_extractor")
    logger.info(f"Processing jid: {jid}")

    resp = openai_client.chat.completions.create(
        model="gpt-5",
        reasoning_effort="medium",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "judgment_summary",
                "strict": True,
                "schema": summary_schema["json_schema"]
            }
        },
        timeout=180
    )
    logger.info(f"AI summary response: {resp.choices[0].message.content}")
    logger.info(f"AI summary success for jid: {jid}")

    ai_summary = json.loads(resp.choices[0].message.content)

    metadata_resp = supabase.schema("lawschatter").table("judgment_metadata").select("*").eq("jid", jid).execute()
    
    # 處理 case_fact_summary
    case_fact_summary = ai_summary.get("case_fact_summary", "")
    if case_fact_summary:
        unique_string = f"{jid}_case_fact_summary"
        hash_string = hashlib.md5(unique_string.encode('utf-8')).hexdigest()
        summary_data = {
            "point_id": hash_string,
            "jid": jid,
            "jdate": jdate,
            "summary_type": "case_fact_summary",
            "content": case_fact_summary,
            "defendent_name": None
        }
        supabase.schema("lawschatter").table("judgment_summary").insert(summary_data).execute()
    
    # 處理 defendants 陣列
    defendants = ai_summary.get("defendants", [])
    for defendant in defendants:
        defendant_name = defendant.get("name", "未知")
        
        # 為每個被告的每個欄位創建記錄
        defendant_fields = {
            "role": defendant.get("role", "未知"),
            "A_fact": defendant.get("A_fact", "未知"),
            "B_claim": defendant.get("B_claim", "未知"),
            "C_court_finding": defendant.get("C_court_finding", "未知"),
            "D_court_reason": defendant.get("D_court_reason", "未知"),
            "E_legal_eval": defendant.get("E_legal_eval", "未知")
        }
        
        for field_name, field_content in defendant_fields.items():
            unique_string = f"{jid}_{defendant_name}_{field_name}"
            hash_string = hashlib.md5(unique_string.encode('utf-8')).hexdigest()
            summary_data = {
                "point_id": hash_string,
                "jid": jid,
                "jdate": jdate,
                "summary_type": field_name,
                "content": field_content,
                "defendent_name": defendant_name
            }
            supabase.schema("lawschatter").table("judgment_summary").insert(summary_data).execute()
    
    # 處理 case_highlights 陣列
    case_highlights = ai_summary.get("case_highlights", [])
    for idx, highlight in enumerate(case_highlights):
        unique_string = f"{jid}_case_highlights_{idx}"
        hash_string = hashlib.md5(unique_string.encode('utf-8')).hexdigest()
        summary_data = {
            "point_id": hash_string,
            "jid": jid,
            "jdate": jdate,
            "summary_type": "case_highlights",
            "content": highlight,
            "defendent_name": None
        }
        supabase.schema("lawschatter").table("judgment_summary").insert(summary_data).execute()
    
    logger.info(f"Successfully processed and inserted summary for jid: {jid}")
    return True

# TODO: 完成提取邏輯優化
def main():
    total_processed = 0
    for jdate in fetch_all_jdates_desc():
        jids = fetch_unprocessed_jids_for_date(jdate)

        if not jids:
            print(f"No jids found for date: {jdate}")
            continue

        for jid in jids:
            if process_single_jid(jid, jdate):
                total_processed += 1
        time.sleep(60)

if __name__ == "__main__":
    main()