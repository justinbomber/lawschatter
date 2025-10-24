from hybrid_embed import get_qdrant_hybrid_vector_store
import logging
import requests
from typing import List
# from qdrant_client.models import Document
from langchain_core.documents import Document
import dotenv
import os
from supabase import create_client, Client
import time
import supabase

dotenv.load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

SUPABASE_URL = "https://supalaw.mooo.com/"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
QDRANT_COLLECTION = os.getenv("COLLECTION_NAME", "new_judgment_0915")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def add_documents_to_qdrant(documents: List[Document], ids: List[str]):
    logger = logging.getLogger(__name__)
    qdrant_url = os.getenv("QDRANT_SERVER", "http://localhost:6333")
    collection_url = f"{qdrant_url}/collections/{QDRANT_COLLECTION}"
    
    logger.info(f"開始將 {len(documents)} 個 documents 加入到 Qdrant")
    
    response = requests.get(collection_url)
    before_count = response.json()["result"]["points_count"]
    logger.info(f"加入前 Qdrant 點數: {before_count}")
    
    vector_store = get_qdrant_hybrid_vector_store()
    vector_store.add_documents(documents=documents, ids=ids)
    
    response = requests.get(collection_url)
    after_count = response.json()["result"]["points_count"]
    logger.info(f"加入後 Qdrant 點數: {after_count}, 新增 {after_count - before_count} 個點")

def fetch_all_jdates_desc():
    resp = supabase.schema("lawschatter").table("judgment_metadata").select("jdate").order("jdate", desc=True).execute()
    unique_dates = sorted({row["jdate"] for row in resp.data}, reverse=True)
    return unique_dates

def fetch_unprocessed_jids_for_date(jdate):
    main_resp = supabase.schema("lawschatter").table("main_judgments").select("jid").eq("jdate", jdate).execute()
    main_jids = {row["jid"] for row in main_resp.data}

    meta_resp = supabase.schema("lawschatter").table("judgment_metadata").select("jid").eq("jdate", jdate).execute()
    meta_jids = {row["jid"] for row in meta_resp.data}

    sum_resp = supabase.schema("lawschatter").table("judgment_summary").select("jid").eq("jdate", jdate).eq("embedded_1", False).execute()
    sum_jids = {row["jid"] for row in sum_resp.data}

    unprocessed_jids = list(main_jids & meta_jids & sum_jids)
    return unprocessed_jids

def process_jid(jid):
    judgment_summary = supabase.schema("lawschatter").table("judgment_summary").select("*").eq("jid", jid).execute().data
    judgment_metadata = supabase.schema("lawschatter").table("judgment_metadata").select("*").eq("jid", jid).execute().data
    
    if not judgment_metadata or not judgment_summary:
        print(f"跳過 jid {jid}: 缺少 metadata 或 summary")
        return
    
    metadata_record = judgment_metadata[0]
    documents = []
    ids = []
    
    for summary in judgment_summary:
        base_metadata = {
            'jid': metadata_record['jid'],
            'jid_full': metadata_record['jid_full'],
            'jyear': metadata_record['jyear'],
            'jcase': metadata_record['jcase'],
            'jno': metadata_record['jno'],
            'jdate': metadata_record['jdate'],
            'jtitle': metadata_record['jtitle'],
            'case_type': metadata_record.get('case_type'),
            'summary_type': summary['summary_type'],
            'case_metadata': metadata_record.get('case_metadata'),
        }
        
        if summary.get('defendent_name'):
            matching_defendant = None
            for defendant in metadata_record.get('defendants', []):
                if defendant.get('defendant_name') == summary['defendent_name']:
                    matching_defendant = defendant
                    break
            
            if matching_defendant:
                base_metadata['defendant'] = matching_defendant
                base_metadata['defendant_name'] = summary['defendent_name']
        else:
            base_metadata['defendants'] = metadata_record.get('defendants', [])
        
        doc = Document(
            page_content=summary['content'],
            metadata=base_metadata
        )
        
        documents.append(doc)
        ids.append(summary['point_id'])
    
    if documents:
        print(f"處理 jid {jid}: 準備加入 {len(documents)} 個 documents")
        add_documents_to_qdrant(documents, ids)
        
        update_data = supabase.schema("lawschatter").table("judgment_summary").update({"embedded_1": True}).eq("jid", jid).execute()
        print(f"完成 jid {jid}: 已更新 embedded_1 標記")
    
    return len(documents)

def main():
    total_date_count = 0
    total_jid_count = 0
    
    for jdate in fetch_all_jdates_desc():
        jids = fetch_unprocessed_jids_for_date(jdate)
        
        if not jids:
            print(f"日期 {jdate}: 無待處理的 jids")
            continue
        
        total_date_count += 1
        print(f"處理第 {total_date_count} 個日期: {jdate}, 共 {len(jids)} 個 jids")
        
        for jid in jids:
            doc_count = process_jid(jid)
            if doc_count:
                total_jid_count += 1
        
        if total_date_count >= 10:
            print(f"已達到處理上限，停止處理")
            break
    
    print(f"處理完成: 共處理 {total_date_count} 個日期, {total_jid_count} 個 jids")

if __name__ == "__main__":
    main()