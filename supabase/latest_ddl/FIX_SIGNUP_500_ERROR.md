# 修正註冊 500 錯誤

## 問題描述

當用戶嘗試註冊時，後端返回 500 (Internal Server Error) 錯誤：

```
Supabase 請求: POST /signup
Failed to load resource: the server responded with a status of 500 (Internal Server Error)
Supabase API 錯誤: 500 {
  code: '23505', 
  message: 'duplicate key value violates unique constraint "users_username_key"', 
  detail: 'Key (username)=(tester1) already exists.'
}
```

## 原因分析

此錯誤是由 `auth.users` 表的 `username` 欄位唯一性約束造成的。常見原因包括：

1. **Username 重複** - 嘗試使用已存在的 username 註冊
2. **唯一性約束衝突** - `auth.users.username` 有 `users_username_key` 約束
3. **觸發器錯誤** - user_profiles 插入失敗
4. **權限不足** - 觸發器沒有足夠的權限

## 解決方案

執行以下 SQL 腳本來修正觸發器：

### 1. 透過 Supabase Dashboard

1. 登入 [Supabase Dashboard](https://supabase.com/dashboard)
2. 選擇您的專案
3. 前往 **SQL Editor**
4. 複製並執行 `002_fix_signup_trigger.sql` 的內容
5. 點擊 **Run**

### 2. 透過命令列（如果已安裝 Supabase CLI）

```bash
# 連接到您的 Supabase 專案
supabase db push --db-url "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"

# 或手動執行 SQL
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" -f supabase/latest_ddl/002_fix_signup_trigger.sql
```

### 3. 直接透過 psql

```bash
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" < supabase/latest_ddl/002_fix_signup_trigger.sql
```

## 修正內容

### 1. 添加 ON CONFLICT 處理

```sql
insert into lawschatter.user_profiles (user_id, email, username, display_name)
values (...)
on conflict (user_id) do nothing;  -- 避免重複插入錯誤
```

### 2. 添加例外處理

```sql
exception
  when others then
    raise warning 'Failed to create user profile for user %: %', new.id, SQLERRM;
    return new;  -- 不阻止用戶註冊
end;
```

### 3. 添加 display_name 支援

```sql
coalesce(new.raw_user_meta_data->>'display_name', 
         new.raw_user_meta_data->>'username', 
         split_part(new.email, '@', 1))
```

### 4. 設定 search_path

```sql
security definer
set search_path = public  -- 確保權限正確
```

### 5. 授予必要權限

```sql
grant select, insert, update, delete on lawschatter.user_profiles to authenticated;
```

## 驗證修正

執行腳本後，請測試註冊功能：

1. 開啟前端應用
2. 嘗試註冊新用戶
3. 確認註冊成功且沒有 500 錯誤
4. 檢查 user_profiles 表中是否有新記錄：

```sql
select * from lawschatter.user_profiles 
order by created_at desc 
limit 5;
```

## 清理失敗的註冊記錄（可選）

如果有許多失敗的註冊嘗試，可以清理未確認的舊記錄：

```sql
-- 刪除 1 小時前未確認的註冊記錄
delete from auth.users 
where email_confirmed_at is null 
and created_at < now() - interval '1 hour';
```

## 偵錯工具

如果問題持續存在，請檢查以下日誌：

### Supabase Dashboard
1. **Auth Logs**: Project Settings → Auth → Logs
2. **Postgres Logs**: Project Settings → Logs → Postgres Logs

### 手動查詢日誌
```sql
-- 查看最近的 Postgres 日誌
select * from pg_stat_activity 
where state != 'idle' 
order by query_start desc;

-- 查看觸發器狀態
select * from information_schema.triggers 
where trigger_name = 'trg_auth_users_create_profile';
```

## 相關資源

- [Supabase Auth 疑難排解](https://supabase.com/docs/guides/auth/troubleshooting)
- [Database error saving new user](https://supabase.com/docs/guides/troubleshooting/database-error-saving-new-user)
- [PostgreSQL Trigger Functions](https://www.postgresql.org/docs/current/plpgsql-trigger.html)

