-- Grant permissions for all tables
-- 授予所有表的權限
-- 
-- 在 Supabase 中，即使有 RLS 政策，也需要授予 anon 和 authenticated 角色對表的權限
-- 否則會出現 42501 permission denied 錯誤
--
-- 安全性說明：
-- 1. RLS 政策確保使用者只能操作自己擁有的資料
-- 2. INSERT 政策會檢查 conversation_id 對應的對話是否屬於當前使用者
-- 3. UPDATE/DELETE 政策確保使用者只能管理自己的記錄

-- ============================================================================
-- 授予 schema 使用權限（如果尚未授予）
-- ============================================================================
grant usage on schema lawschatter to anon, authenticated;

-- ============================================================================
-- 加強 RLS 政策：確保使用者只能分享自己擁有的對話
-- ============================================================================
-- 刪除舊的政策（如果存在）
drop policy if exists shared_conversations_owner_mod on lawschatter.shared_conversations;
drop policy if exists shared_conversations_owner_select on lawschatter.shared_conversations;
drop policy if exists shared_conversations_owner_insert on lawschatter.shared_conversations;
drop policy if exists shared_conversations_owner_update on lawschatter.shared_conversations;
drop policy if exists shared_conversations_owner_delete on lawschatter.shared_conversations;

-- 政策 1: 使用者可以讀取自己的分享記錄
create policy shared_conversations_owner_select on lawschatter.shared_conversations
  for select using (auth.uid() = user_id);

-- 政策 2: 使用者可以插入分享記錄，但必須確保：
--   a) user_id 等於當前使用者 (由 default auth.uid() 自動處理)
--   b) conversation_id 對應的對話必須屬於當前使用者（關鍵安全檢查）
create policy shared_conversations_owner_insert on lawschatter.shared_conversations
  for insert with check (
    auth.uid() = user_id
    and exists (
      select 1 from lawschatter.conversations c
      where c.conversation_id = shared_conversations.conversation_id
        and c.user_id = auth.uid()
    )
  );

-- 政策 3: 使用者可以更新自己的分享記錄
create policy shared_conversations_owner_update on lawschatter.shared_conversations
  for update using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- 政策 4: 使用者可以刪除自己的分享記錄
create policy shared_conversations_owner_delete on lawschatter.shared_conversations
  for delete using (auth.uid() = user_id);

-- 注意：公開讀取政策已在 002_add_sharing_tables.sql 中定義，不需要重複創建

-- ============================================================================
-- 授予 shared_conversations 表權限
-- ============================================================================
-- authenticated 角色：可以對自己的分享進行所有操作（由 RLS 政策控制）
grant select, insert, update, delete on lawschatter.shared_conversations to authenticated;

-- anon 角色：只能讀取公開的分享（由 RLS 政策控制）
grant select on lawschatter.shared_conversations to anon;

-- ============================================================================
-- 授予 shared_messages 表權限
-- ============================================================================
-- authenticated 角色：可以插入自己分享的訊息（由 RLS 政策控制）
grant select, insert on lawschatter.shared_messages to authenticated;

-- anon 角色：只能讀取公開分享的訊息（由 RLS 政策控制）
grant select on lawschatter.shared_messages to anon;

-- ============================================================================
-- 授予 user_recent_conversations 表權限
-- ============================================================================
-- authenticated 角色：可以對自己的最近對話記錄進行所有操作（由 RLS 政策控制）
grant select, insert, update, delete on lawschatter.user_recent_conversations to authenticated;

-- ============================================================================
-- 授予 conversations 表權限
-- ============================================================================
-- authenticated 角色：可以對自己的對話進行所有操作（由 RLS 政策控制）
-- 這包括：查詢、創建、更新標題、刪除對話
grant select, insert, update, delete on lawschatter.conversations to authenticated;

-- ============================================================================
-- 授予 messages 表權限
-- ============================================================================
-- authenticated 角色：可以對自己對話的訊息進行所有操作（由 RLS 政策控制）
-- 這包括：查詢、創建、更新、刪除訊息
grant select, insert, update, delete on lawschatter.messages to authenticated;

-- ============================================================================
-- 授予 user_profiles 表權限（如果尚未授予）
-- ============================================================================
-- authenticated 角色：可以對自己的個人資料進行所有操作（由 RLS 政策控制）
-- 注意：此權限可能在 002_fix_signup_trigger.sql 中已授予，但為了完整性仍包含在此
grant select, insert, update, delete on lawschatter.user_profiles to authenticated;

-- ============================================================================
-- 授予序列權限（shared_messages 使用 bigserial）
-- ============================================================================
grant usage, select on sequence lawschatter.shared_messages_id_seq to authenticated;

-- 1. 允許 service_role 進入 lawschatter schema
GRANT USAGE ON SCHEMA "lawschatter" TO service_role;

-- 2. 關鍵：允許 service_role 對該 schema 下的所有表格進行 CRUD (包含 INSERT)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA "lawschatter" TO service_role;

-- 3. (非常重要) 如果你的表有 ID 是自動遞增 (Serial/Identity)，必須給 Sequence 權限，不然插入會失敗
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA "lawschatter" TO service_role;

-- 4. 未來保險：確保以後在此 schema 新建立的 table，service_role 也能自動擁有權限
ALTER DEFAULT PRIVILEGES IN SCHEMA "lawschatter" GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA "lawschatter" GRANT USAGE, SELECT ON SEQUENCES TO service_role;

-- 1. 針對 case_types 開啟 RLS
ALTER TABLE "lawschatter"."case_types" ENABLE ROW LEVEL SECURITY;

-- 2. 針對 judgment_metadata 開啟 RLS
ALTER TABLE "lawschatter"."judgment_metadata" ENABLE ROW LEVEL SECURITY;

-- 3. 針對 judgment_summary 開啟 RLS
ALTER TABLE "lawschatter"."judgment_summary" ENABLE ROW LEVEL SECURITY;

-- 4. 針對 main_judgments 開啟 RLS
ALTER TABLE "lawschatter"."main_judgments" ENABLE ROW LEVEL SECURITY;
-- 這樣一般人連 "嘗試讀取" 的資格都沒有，會直接報錯 403
REVOKE ALL ON "lawschatter"."case_types" FROM anon, authenticated;
REVOKE ALL ON "lawschatter"."judgment_metadata" FROM anon, authenticated;
REVOKE ALL ON "lawschatter"."judgment_summary" FROM anon, authenticated;
REVOKE ALL ON "lawschatter"."main_judgments" FROM anon, authenticated;

-- 1. 確保 service_role 擁有讀取這個 View 的權限
GRANT SELECT ON lawschatter.v_judgment_summary_full TO service_role;

-- 2. 撤銷一般使用者的所有權限 (包含讀取)
REVOKE ALL ON lawschatter.v_judgment_summary_full FROM anon, authenticated;

-- 3. (額外保險) 確保 public 角色也沒有權限
-- Postgres 的 public 角色有時會預設包含所有人，明確撤銷比較安全
REVOKE ALL ON lawschatter.v_judgment_summary_full FROM public;