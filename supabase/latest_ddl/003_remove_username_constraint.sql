-- 移除 auth.users.username 的唯一性約束以避免註冊衝突
-- 
-- 問題：auth.users 表中的 username 欄位有唯一性約束 "users_username_key"
-- 當多個用戶嘗試使用相同的 username 註冊時會導致 500 錯誤
--
-- 解決方案：
-- 1. 移除 auth.users.username 的唯一性約束
-- 2. 在 lawschatter.user_profiles.username 上保持唯一性約束
-- 3. 這樣可以讓多個用戶在 auth.users 中有相同的 username，
--    但在應用層面（user_profiles）保持唯一性

-- ============================================================================
-- 移除 auth.users.username 的唯一性約束
-- ============================================================================

-- 檢查約束是否存在並移除
do $$ 
begin
  if exists (
    select 1 
    from pg_constraint 
    where conname = 'users_username_key' 
    and connamespace = 'auth'::regnamespace
  ) then
    alter table auth.users drop constraint users_username_key;
    raise notice 'Removed unique constraint users_username_key from auth.users';
  else
    raise notice 'Constraint users_username_key does not exist';
  end if;
end $$;

-- ============================================================================
-- 確保 lawschatter.user_profiles.username 有唯一性約束
-- ============================================================================

-- 檢查並創建唯一性約束（如果不存在）
do $$ 
begin
  if not exists (
    select 1 
    from pg_constraint 
    where conname = 'user_profiles_username_unique' 
    and connamespace = 'lawschatter'::regnamespace
  ) then
    -- 先清理可能的重複資料
    delete from lawschatter.user_profiles a
    using lawschatter.user_profiles b
    where a.user_id > b.user_id
    and a.username = b.username;
    
    -- 添加唯一性約束
    alter table lawschatter.user_profiles 
    add constraint user_profiles_username_unique unique (username);
    
    raise notice 'Added unique constraint to lawschatter.user_profiles.username';
  else
    raise notice 'Unique constraint already exists on lawschatter.user_profiles.username';
  end if;
end $$;

-- ============================================================================
-- 清理重複的 username（如果有）
-- ============================================================================

-- 為重複的 auth.users.username 添加後綴
do $$
declare
  r record;
  counter int;
begin
  for r in (
    select username, array_agg(id) as user_ids
    from auth.users
    where username is not null
    group by username
    having count(*) > 1
  )
  loop
    counter := 1;
    foreach r.user_id in array r.user_ids[2:array_length(r.user_ids, 1)]
    loop
      update auth.users
      set username = r.username || '_' || counter
      where id = r.user_id;
      counter := counter + 1;
    end loop;
  end loop;
  
  raise notice 'Cleaned up duplicate usernames in auth.users';
end $$;

-- ============================================================================
-- 更新觸發器函數以處理 username 衝突
-- ============================================================================

create or replace function lawschatter.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  base_username text;
  final_username text;
  counter int := 0;
begin
  -- 從 metadata 或 email 獲取基礎 username
  base_username := coalesce(
    new.raw_user_meta_data->>'username', 
    split_part(new.email, '@', 1)
  );
  final_username := base_username;
  
  -- 如果 username 已存在，添加數字後綴
  while exists (
    select 1 from lawschatter.user_profiles 
    where username = final_username
  ) loop
    counter := counter + 1;
    final_username := base_username || '_' || counter;
  end loop;
  
  -- 插入 user_profiles
  insert into lawschatter.user_profiles (user_id, email, username, display_name)
  values (
    new.id,
    new.email,
    final_username,
    coalesce(
      new.raw_user_meta_data->>'display_name', 
      new.raw_user_meta_data->>'username', 
      base_username
    )
  )
  on conflict (user_id) do nothing;
  
  return new;
exception
  when others then
    raise warning 'Failed to create user profile for user %: %', new.id, SQLERRM;
    return new;
end;
$$;

-- ============================================================================
-- 驗證腳本
-- ============================================================================

-- 檢查約束狀態
select 
  conname as constraint_name,
  contype as constraint_type,
  connamespace::regnamespace as schema
from pg_constraint
where conname in ('users_username_key', 'user_profiles_username_unique');

-- 檢查是否有重複的 username
select username, count(*) as count
from lawschatter.user_profiles
group by username
having count(*) > 1;

