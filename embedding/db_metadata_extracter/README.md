# 判決書 Metadata 提取器（最終版）

此模組用於從判決書中提取 Metadata，並寫入 Supabase 中的 `lawschatter.judgment_metadata`。本版本重點：

- 從「最新日期」一路處理到「較舊日期」（近到遠）。
- 程式若中斷，重新啟動會自動接續未完成的工作（依賴資料庫狀態，無需額外狀態表）。
- 符合 Fail Fast 原則：不做重試、不做例外攔截，讓錯誤直接浮出並以資料狀態支援續跑。

## 資料來源與條件

- 連線：`https://supalaw.mooo.com/`，Schema：`lawschatter`
- 一次處理單位：以天為單位（`jdate`）。
- 來源表：`lawschatter.main_judgments`
- 寫入表：`lawschatter.judgment_metadata`
- 過濾條件：僅處理 `jfull` 屬於以下任一字串的資料：`詐欺等`、`詐欺`、`洗錢防制法等`、`洗錢防制法`
- 僅處理「只存在於 `main_judgments`，且不存在於 `judgment_metadata` 與 `judgment_summary`」之 `jid`

## 運作流程（近到遠、可中斷續跑）

1. 擷取 `main_judgments` 的所有獨特 `jdate`，以遞減排序（新到舊）。
2. 逐日處理：
   - 撈出當日符合 `jfull` 條件的 `main_jids`。
   - 同步撈出該日已存在於 `judgment_metadata` 與 `judgment_summary` 的 `jid` 集合。
   - 以差集取得「未處理 `jid`」。
3. 逐 `jid`：
   - 讀取該 `jid` 的完整判決資料。
   - 依 `judgment_metadata_schema.json` 呼叫 OpenAI（`gpt-4o`）產生結構化 metadata。
   - 立即插入 `judgment_metadata`（含 `jid`、`jdate`、`metadata`）。
4. 若程式中斷：
   - 重新啟動後重跑步驟 1～3；已插入的 `jid` 會被差集邏輯自動略過，只處理剩餘未完成者。
5. 結束條件：所有 `jdate` 均無未處理 `jid` 即結束。

## 子查詢限制的兩條路

- 方法 A（預設）：分步查詢以集合差集完成過濾，不使用資料庫子查詢。
- 方法 B（可選）：建立 Postgres RPC，於後端以 `NOT EXISTS` 完成過濾，前端透過 PostgREST `/rest/v1/rpc` 呼叫。

## 參考實作（Python，Fail Fast／最小必要碼）

```python
import os
import json
from supabase import create_client, Client
from openai import OpenAI

# 環境變數
SUPABASE_URL = "https://supalaw.mooo.com/"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SCHEMA_FILE = "judgment_metadata_schema.json"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

with open(SCHEMA_FILE, "r") as f:
    metadata_schema = json.load(f)

TARGET_JFULL = ["詐欺等", "詐欺", "洗錢防制法等", "洗錢防制法"]

def fetch_all_jdates_desc():
    resp = supabase.table("main_judgments").select("jdate").order("jdate", desc=True).execute()
    return sorted({row["jdate"] for row in resp.data}, reverse=True)

def fetch_unprocessed_jids_for_date(jdate):
    main_resp = (
        supabase
        .table("main_judgments")
        .select("jid")
        .eq("jdate", jdate)
        .in_("jfull", TARGET_JFULL)
        .execute()
    )
    main_jids = {row["jid"] for row in main_resp.data}

    meta_resp = supabase.table("judgment_metadata").select("jid").eq("jdate", jdate).execute()
    meta_jids = {row["jid"] for row in meta_resp.data}

    sum_resp = supabase.table("judgment_summary").select("jid").eq("jdate", jdate).execute()
    sum_jids = {row["jid"] for row in sum_resp.data}

    return list(main_jids - meta_jids - sum_jids)

def process_single_jid(jid, jdate):
    judgment = supabase.table("main_judgments").select("*").eq("jid", jid).single().execute().data
    prompt = (
        "Extract metadata from this judgment based on the schema: "
        + json.dumps(metadata_schema, ensure_ascii=False)
        + "\nJudgment: "
        + json.dumps(judgment, ensure_ascii=False)
    )
    resp = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    metadata = json.loads(resp.choices[0].message.content)
    supabase.table("judgment_metadata").insert({
        "jid": jid,
        "jdate": jdate,
        "metadata": metadata,
    }).execute()

def main():
    for jdate in fetch_all_jdates_desc():
        jids = fetch_unprocessed_jids_for_date(jdate)
        if not jids:
            continue
        for jid in jids:
            process_single_jid(jid, jdate)

if __name__ == "__main__":
    main()
```

說明：
- 無例外攔截、無重試，讓問題直接拋出；重新啟動後透過差集自動續跑。
- 若 `judgment_metadata` 無 `jdate` 欄位，請改以 `jid` 查已處理清單再取差集。

##（可選）RPC 方案：把過濾邏輯下放到資料庫

SQL：

```sql
CREATE OR REPLACE FUNCTION lawschatter.get_unprocessed_jids(p_jdate text)
RETURNS SETOF text AS $$
  SELECT mj.jid
  FROM lawschatter.main_judgments mj
  WHERE mj.jdate = p_jdate
    AND mj.jfull IN ('詐欺等','詐欺','洗錢防制法等','洗錢防制法')
    AND NOT EXISTS (
      SELECT 1 FROM lawschatter.judgment_metadata jm WHERE jm.jid = mj.jid
    )
    AND NOT EXISTS (
      SELECT 1 FROM lawschatter.judgment_summary js WHERE js.jid = mj.jid
    );
$$ LANGUAGE sql STABLE;
```

呼叫（PostgREST）：

```bash
curl -X POST "$SUPABASE_URL/rest/v1/rpc/get_unprocessed_jids" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Authorization: Bearer $SUPABASE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_jdate": "20250101"}' | cat
```

Python 亦可使用 `supabase-py` 的 `rpc("get_unprocessed_jids", {"p_jdate": jdate})` 呼叫。

## 環境變數

- `SUPABASE_KEY`
- `OPENAI_API_KEY`
- `SCHEMA_FILE`（預設：`judgment_metadata_schema.json`）

## 參考

- Supabase REST API（PostgREST）：[連結](https://supabase.com/docs/guides/api)
- Supabase Database Functions（RPC）：[連結](https://supabase.com/docs/guides/database/functions)
- Supabase Python RPC 參考：[連結](https://supabase.com/docs/reference/python/rpc)
