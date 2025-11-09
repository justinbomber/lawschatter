-- Migration: 修復 user_id 欄位的默認值
-- 目的: 讓 Supabase 自動使用 auth.uid() 填充 user_id，避免 403 Forbidden 錯誤
-- 日期: 2025-11-09

-- ============================================================================
-- 修改 conversations 表的 user_id 默認值
-- ============================================================================
alter table lawschatter.conversations
  alter column user_id set default auth.uid();

-- ============================================================================
-- 修改 messages 表的 user_id 默認值
-- ============================================================================
alter table lawschatter.messages
  alter column user_id set default auth.uid();

-- ============================================================================
-- 修改 user_recent_conversations 表的 user_id 默認值
-- ============================================================================
alter table lawschatter.user_recent_conversations
  alter column user_id set default auth.uid();

-- ============================================================================
-- 完成通知
-- ============================================================================
comment on table lawschatter.conversations is 'User-scoped chat conversations (minimal) - user_id auto-filled via auth.uid()';
comment on table lawschatter.messages is 'User-scoped messages with parent-child relations (branching) and sender/content - user_id auto-filled via auth.uid()';
comment on table lawschatter.user_recent_conversations is 'Per-user recent conversation links with last accessed timestamp - user_id auto-filled via auth.uid()';

