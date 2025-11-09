Supabase / PostgreSQL DDL（最小版對話系統）
=========================================

這份資料夾提供以 Supabase（PostgreSQL）為基礎的「極簡」聊天對話資料結構（DDL），僅保留：
- `conversations`：對話主檔
- `messages`：訊息（含 `parent_message_id` 支援重新生成/分支與接續對話）
- `user_profiles`：使用者個人設定（含 `config` JSON 與最近一次選取的對話）
- `user_recent_conversations`：使用者與多個歷史對話的連結（含最新開啟時間）
- RLS（Row Level Security）與 Policies
- `updated_at` 自動更新 Trigger

檔案清單
--------
- `001_init_supabase_chat.sql`：最小版資料表、索引、擴充套件、Trigger、RLS Policies。

相依/假設
---------
- Supabase 預設的 `auth.users`（UUID）做使用者來源。
- 已啟用 `pgcrypto` 擴充套件以使用 `gen_random_uuid()`。
- 使用 `NULL` 表示訊息根節點（沒有父訊息）；`parent_message_id` 參照 `messages(message_id)`。

如何使用
--------
你有兩種常見方式可套用：

1) 直接在 Supabase SQL Editor 執行
- 開啟 Supabase 專案的 SQL Editor。
- 複製 `001_init_supabase_chat.sql` 全文貼上並執行。

2) 以 CLI（或自動化）執行
- 將 `@latest_ddl/001_init_supabase_chat.sql` 內容整合到你的 `supabase/migrations/{timestamp}_init.sql` 或新建一個 migration。
- 使用 `supabase db push` 或 CI/CD 將 migration 送上。

注意事項
--------
- 本最小版僅包含 `conversations` 與 `messages`；其餘（agents、assistants、presets、files、tool_calls、tags、shares、memory 等）均已刪除。
- 已預設啟用 RLS 並提供 Policies（擁有者可存取/修改）。
- 若要支援 TTL/自動過期，建議以排程或應用層自行清理。

對照（核心欄位）
----------------
- conversations：`conversation_id (uuid PK)`、`user_id`、`title`、`created_at/updated_at`
- messages：`message_id (uuid PK)`、`conversation_id`、`user_id`、`parent_message_id (uuid|null)`、`sender_type ('user'|'assistant')`、`content (text)`、`created_at/updated_at`
- user_profiles：`user_id (uuid PK)`、`display_name`、`avatar_url`、`config (jsonb)`、`last_selected_conversation_id (uuid|null)`、`created_at/updated_at`
- user_recent_conversations：`(user_id, conversation_id) PK`、`last_accessed_at`（可依時間排序最近對話）

小抄（常見查詢）
----------------
- 取某使用者的會話列表：
  ```sql
  select * from lawschatter.conversations
  where user_id = auth.uid()
  order by updated_at desc
  limit 50;
  ```
- 取某會話的訊息（按時間）：
  ```sql
  select * from lawschatter.messages
  where user_id = auth.uid()
    and conversation_id = :conversation_id
  order by created_at asc;
  ```
- 讀取使用者前端設定（config）：
  ```sql
  select config
  from lawschatter.user_profiles
  where user_id = auth.uid();
  ```
- 更新使用者前端設定（config）與最近選取對話：
  ```sql
  update lawschatter.user_profiles
  set
    config = :json_config, -- e.g. '{"theme":"dark","lang":"zh-TW"}'
    last_selected_conversation_id = :conversation_id,
    updated_at = now()
  where user_id = auth.uid();
  ```
- 寫入/刷新最近對話連結：
  ```sql
  insert into lawschatter.user_recent_conversations (user_id, conversation_id, last_accessed_at)
  values (auth.uid(), :conversation_id, now())
  on conflict (user_id, conversation_id) do update
  set last_accessed_at = excluded.last_accessed_at;
  ```
- 以 parent 追溯單一路徑（由應用層依 `parent_message_id` 自行回溯/組裝）。

版本調整
--------
- 若之後需要新增欄位或索引，請新增新的 migration 檔（不要直接修改已生效的 migration）。
- 若你已有既有資料（例如從 Mongo 匯入），記得對照欄位型別與 ID 生成方式（可自行指定 `message_id/conversation_id` 而非使用 `gen_random_uuid()` 預設值）。

安全性
------
- 所有表格已啟用 RLS 並設有 Policies；務必以已驗證的身份執行。
- 若應用層需要管理者/系統等特權角色，可另外新增更寬鬆的 Policies（或以 RPC/functions 包裝）。


