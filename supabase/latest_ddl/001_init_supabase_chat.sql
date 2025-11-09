-- Supabase / PostgreSQL DDL - Minimal chat schema
-- Notes:
-- - Uses auth.users as the user source (Supabase default), referenced via user_id UUID
-- - Uses gen_random_uuid() from pgcrypto for UUIDs
-- - Uses NULL to represent root (no parent) in parent_message_id
-- - Adds RLS policies to ensure row-level isolation per user
-- - Adds generic trigger function to auto-update updated_at
-- - Auto-creates user_profiles when auth.users gets new record

-- ============================================================================
-- Extensions
-- ============================================================================
create extension if not exists pgcrypto;

-- ============================================================================
-- Schema
-- ============================================================================
create schema if not exists lawschatter;

-- ============================================================================
-- Trigger: Auto-create user_profiles on auth.users insert
-- ============================================================================
create or replace function lawschatter.handle_new_user()
returns trigger
language plpgsql
security definer
as $$
begin
  insert into lawschatter.user_profiles (user_id, email, username)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'username', split_part(new.email, '@', 1))
  );
  return new;
end;
$$;

-- ============================================================================
-- Helper: updated_at trigger function
-- ============================================================================
create or replace function lawschatter.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- ============================================================================
-- Table: conversations
-- ============================================================================
create table if not exists lawschatter.conversations (
  conversation_id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text default 'New Chat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists conversations_user_id_idx on lawschatter.conversations(user_id);
create index if not exists conversations_created_at_idx on lawschatter.conversations(created_at);
create index if not exists conversations_updated_at_idx on lawschatter.conversations(updated_at);

create trigger trg_conversations_set_updated_at
before update on lawschatter.conversations
for each row
execute function lawschatter.set_updated_at();

-- ============================================================================
-- Table: messages
-- ============================================================================
create table if not exists lawschatter.messages (
  message_id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references lawschatter.conversations(conversation_id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  parent_message_id uuid null references lawschatter.messages(message_id) on delete set null,
  sender_type text not null check (sender_type in ('user','assistant')),
  content text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists messages_conversation_created_idx on lawschatter.messages(conversation_id, created_at);
create index if not exists messages_user_idx on lawschatter.messages(user_id);
create index if not exists messages_parent_idx on lawschatter.messages(parent_message_id);
create index if not exists messages_created_at_idx on lawschatter.messages(created_at);

create trigger trg_messages_set_updated_at
before update on lawschatter.messages
for each row
execute function lawschatter.set_updated_at();

-- ============================================================================
-- Table: user_profiles (per-user settings/config + pointers)
-- ============================================================================
create table if not exists lawschatter.user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  username text not null,
  display_name text,
  avatar_url text,
  -- 前端使用者設定（UI 偏好、語言、主題、其他個人化設定）
  config jsonb not null default '{}'::jsonb,
  -- 方便前端快速還原最近使用的對話（選填）
  last_selected_conversation_id uuid null references lawschatter.conversations(conversation_id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists user_profiles_last_selected_idx on lawschatter.user_profiles(last_selected_conversation_id);
create index if not exists user_profiles_email_idx on lawschatter.user_profiles(email);
create index if not exists user_profiles_username_idx on lawschatter.user_profiles(username);

create trigger trg_user_profiles_set_updated_at
before update on lawschatter.user_profiles
for each row
execute function lawschatter.set_updated_at();

-- ============================================================================
-- Table: user_recent_conversations (link 多個歷史對話；保留最近開啟時間)
-- ============================================================================
create table if not exists lawschatter.user_recent_conversations (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  conversation_id uuid not null references lawschatter.conversations(conversation_id) on delete cascade,
  last_accessed_at timestamptz not null default now(),
  primary key (user_id, conversation_id)
);

create index if not exists user_recent_conversations_user_last_idx on lawschatter.user_recent_conversations(user_id, last_accessed_at desc);

-- ============================================================================
-- Auth Trigger: Auto-create user_profiles on signup
-- ============================================================================
create trigger trg_auth_users_create_profile
after insert on auth.users
for each row
execute function lawschatter.handle_new_user();

-- ============================================================================
-- RLS: Enable and Policies
-- ============================================================================
alter table lawschatter.conversations enable row level security;
alter table lawschatter.messages enable row level security;
alter table lawschatter.user_profiles enable row level security;
alter table lawschatter.user_recent_conversations enable row level security;

-- conversations: owner-only full access
drop policy if exists conversations_owner_select on lawschatter.conversations;
create policy conversations_owner_select
on lawschatter.conversations for select
using (auth.uid() = user_id);

drop policy if exists conversations_owner_mod on lawschatter.conversations;
create policy conversations_owner_mod
on lawschatter.conversations for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

-- messages: owner-only full access
drop policy if exists messages_owner_select on lawschatter.messages;
create policy messages_owner_select
on lawschatter.messages for select
using (auth.uid() = user_id);

drop policy if exists messages_owner_mod on lawschatter.messages;
create policy messages_owner_mod
on lawschatter.messages for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

-- user_profiles: owner-only full access
drop policy if exists user_profiles_owner_select on lawschatter.user_profiles;
create policy user_profiles_owner_select
on lawschatter.user_profiles for select
using (auth.uid() = user_id);

drop policy if exists user_profiles_owner_mod on lawschatter.user_profiles;
create policy user_profiles_owner_mod
on lawschatter.user_profiles for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

-- user_recent_conversations: owner-only full access
drop policy if exists user_recent_conversations_owner_select on lawschatter.user_recent_conversations;
create policy user_recent_conversations_owner_select
on lawschatter.user_recent_conversations for select
using (auth.uid() = user_id);

drop policy if exists user_recent_conversations_owner_mod on lawschatter.user_recent_conversations;
create policy user_recent_conversations_owner_mod
on lawschatter.user_recent_conversations for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);


-- ============================================================================
-- Helpful comments
-- ============================================================================
comment on schema lawschatter is 'Lawschatter application schema';
comment on table lawschatter.conversations is 'User-scoped chat conversations (minimal)';
comment on table lawschatter.messages is 'User-scoped messages with parent-child relations (branching) and sender/content';
comment on table lawschatter.user_profiles is 'Per-user profile with email, username, and frontend config; auto-created via auth trigger';
comment on table lawschatter.user_recent_conversations is 'Per-user recent conversation links with last accessed timestamp';


