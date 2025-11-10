-- Create shared_conversations table
create table if not exists lawschatter.shared_conversations (
  share_id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references lawschatter.conversations(conversation_id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text,
  is_public boolean not null default true,
  expires_at timestamptz null,
  created_at timestamptz not null default now()
);

-- Create index for public sharing queries
create index if not exists shared_conversations_public_idx 
  on lawschatter.shared_conversations(is_public, expires_at, created_at);

-- Create shared_messages table
create table if not exists lawschatter.shared_messages (
  id bigserial primary key,
  share_id uuid not null references lawschatter.shared_conversations(share_id) on delete cascade,
  sender_type text not null check (sender_type in ('user','assistant')),
  content text not null,
  created_at timestamptz not null
);

-- Create index for querying messages by share_id
create index if not exists shared_messages_share_idx 
  on lawschatter.shared_messages(share_id, created_at);

-- Enable RLS on both tables
alter table lawschatter.shared_conversations enable row level security;
alter table lawschatter.shared_messages enable row level security;

-- Policy: Owner can manage their own shares
create policy shared_conversations_owner_mod on lawschatter.shared_conversations
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Policy: Public read access to public shares (not expired)
create policy shared_conversations_public_read on lawschatter.shared_conversations
  for select using (is_public = true and (expires_at is null or expires_at > now()));

-- Policy: Public read access to messages of public shares
create policy shared_messages_public_read on lawschatter.shared_messages
  for select using (
    exists (
      select 1 from lawschatter.shared_conversations sc
      where sc.share_id = shared_messages.share_id
        and sc.is_public = true
        and (sc.expires_at is null or sc.expires_at > now())
    )
  );

