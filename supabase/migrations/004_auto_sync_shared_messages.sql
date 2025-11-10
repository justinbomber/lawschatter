-- Auto-sync messages to shared_messages when conversation is shared
-- 當對話已被分享時，自動同步新訊息到 shared_messages 表

-- ============================================================================
-- 新增唯一性索引：防止重複訊息
-- ============================================================================
-- 使用 share_id + created_at + sender_type 作為唯一性判斷
create unique index if not exists shared_messages_unique_idx 
  on lawschatter.shared_messages(share_id, created_at, sender_type);

-- ============================================================================
-- Trigger Function: 自動同步新訊息到分享快照
-- ============================================================================
create or replace function lawschatter.sync_message_to_shared()
returns trigger
language plpgsql
security definer
as $$
declare
  v_share_id uuid;
begin
  -- 檢查此對話是否有分享記錄
  for v_share_id in 
    select share_id 
    from lawschatter.shared_conversations 
    where conversation_id = new.conversation_id
  loop
    -- INSERT: 新增訊息到 shared_messages（使用 ON CONFLICT 避免重複）
    if (TG_OP = 'INSERT') then
      insert into lawschatter.shared_messages (share_id, sender_type, content, created_at)
      values (v_share_id, new.sender_type, new.content, new.created_at)
      on conflict (share_id, created_at, sender_type) do nothing;
      
    -- UPDATE: 更新 shared_messages 中對應的訊息
    elsif (TG_OP = 'UPDATE') then
      update lawschatter.shared_messages
      set 
        sender_type = new.sender_type,
        content = new.content
      where share_id = v_share_id
        and created_at = old.created_at
        and sender_type = old.sender_type;
    end if;
  end loop;
  
  return new;
end;
$$;

-- ============================================================================
-- Trigger: 在 messages 表上觸發自動同步
-- ============================================================================
drop trigger if exists trg_messages_sync_to_shared on lawschatter.messages;

create trigger trg_messages_sync_to_shared
after insert or update on lawschatter.messages
for each row
execute function lawschatter.sync_message_to_shared();

-- ============================================================================
-- 註解
-- ============================================================================
comment on function lawschatter.sync_message_to_shared() is 
  '當 messages 表新增或更新訊息時，自動同步到對應的 shared_messages 快照';

