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

