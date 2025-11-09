-- 修正註冊觸發器以避免 500 錯誤
-- 主要改進：
-- 1. 添加 ON CONFLICT 避免重複插入錯誤
-- 2. 添加 exception 處理避免觸發器失敗導致註冊失敗
-- 3. 添加 display_name 欄位支援
-- 4. 設定 search_path 確保權限正確

-- ============================================================================
-- 更新觸發器函數
-- ============================================================================
create or replace function lawschatter.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  -- 使用 ON CONFLICT 避免重複插入錯誤
  insert into lawschatter.user_profiles (user_id, email, username, display_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'username', split_part(new.email, '@', 1)),
    coalesce(new.raw_user_meta_data->>'display_name', new.raw_user_meta_data->>'username', split_part(new.email, '@', 1))
  )
  on conflict (user_id) do nothing;
  
  return new;
exception
  when others then
    -- 記錄錯誤但不阻止用戶註冊
    raise warning 'Failed to create user profile for user %: %', new.id, SQLERRM;
    return new;
end;
$$;

-- ============================================================================
-- 確保觸發器已啟用
-- ============================================================================
drop trigger if exists trg_auth_users_create_profile on auth.users;

create trigger trg_auth_users_create_profile
after insert on auth.users
for each row
execute function lawschatter.handle_new_user();

-- ============================================================================
-- 授予必要的權限
-- ============================================================================
grant usage on schema lawschatter to postgres, anon, authenticated, service_role;
grant all on all tables in schema lawschatter to postgres, service_role;
grant select, insert, update, delete on lawschatter.user_profiles to authenticated;

-- ============================================================================
-- 清理可能失敗的註冊記錄（如果需要）
-- ============================================================================
-- 取消註解以清理失敗的註冊記錄
-- delete from auth.users where email_confirmed_at is null and created_at < now() - interval '1 hour';

