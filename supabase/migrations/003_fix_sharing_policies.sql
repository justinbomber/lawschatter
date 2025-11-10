-- Fix RLS policies for shared_messages table
-- Add policy for owners to insert messages

-- Drop existing policy if it exists (for idempotency)
drop policy if exists shared_messages_owner_insert on lawschatter.shared_messages;

-- Policy: Owner can insert messages for their own shares
create policy shared_messages_owner_insert on lawschatter.shared_messages
  for insert with check (
    exists (
      select 1 from lawschatter.shared_conversations sc
      where sc.share_id = shared_messages.share_id
        and sc.user_id = auth.uid()
    )
  );

-- Ensure the owner policy for shared_conversations allows all operations
drop policy if exists shared_conversations_owner_mod on lawschatter.shared_conversations;

create policy shared_conversations_owner_mod on lawschatter.shared_conversations
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

