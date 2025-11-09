# 修正註冊 500 錯誤指南

## 問題症狀

當用戶嘗試註冊時，瀏覽器 Console 顯示：

```
Supabase 請求: POST /signup
:3000/supabase-auth/signup:1 Failed to load resource: the server responded with a status of 500 (Internal Server Error)
Supabase API 錯誤: 500 Object
```

## 問題原因

此錯誤是由後端資料庫觸發器造成的，而非前端問題。當新用戶註冊時，Supabase 會執行一個觸發器來創建 `user_profiles` 記錄，但該觸發器可能因以下原因失敗：

1. **重複插入衝突** - 之前失敗的註冊嘗試留下的記錄
2. **權限不足** - 觸發器沒有足夠權限寫入 user_profiles 表
3. **欄位遺失** - 資料庫 schema 與觸發器不匹配
4. **未處理的例外** - 觸發器中的錯誤導致整個註冊失敗

## 解決步驟

### 步驟 1: 更新後端資料庫

請後端管理員執行以下 SQL 腳本（位於 `supabase/latest_ddl/002_fix_signup_trigger.sql`）：

1. 登入 [Supabase Dashboard](https://supabase.com/dashboard)
2. 選擇專案
3. 前往 **SQL Editor**
4. 執行 `002_fix_signup_trigger.sql` 的內容

詳細說明請參考：`supabase/latest_ddl/FIX_SIGNUP_500_ERROR.md`

### 步驟 2: 驗證前端資料格式

前端發送的註冊資料格式應該如下：

```javascript:frontend/src/api/supabaseClient.js
signup: async ({ email, password, username }) => {
  const response = await supabaseAuthClient.post('/signup', {
    email,
    password,
    data: {
      username: username || email.split('@')[0]
    }
  });
  return response.data;
}
```

✅ 此格式已正確實作，無需修改。

### 步驟 3: 測試註冊功能

1. 確保後端資料庫已更新
2. 重新啟動前端開發伺服器（如果需要）：
   ```bash
   cd frontend
   npm run dev
   ```
3. 開啟瀏覽器訪問 http://localhost:3000
4. 嘗試註冊新帳號
5. 確認註冊成功且沒有 500 錯誤

### 步驟 4: 清理失敗的註冊記錄（可選）

如果之前有多次失敗的註冊嘗試，可能需要清理這些記錄。請後端管理員執行：

```sql
-- 刪除 1 小時前未確認的註冊記錄
delete from auth.users 
where email_confirmed_at is null 
and created_at < now() - interval '1 hour';
```

## 前端錯誤處理

前端已經實作了完整的錯誤處理機制：

### auth.js 中的錯誤處理

```javascript:frontend/src/api/auth.js
register: async (userData) => {
  try {
    const response = await supabaseAuth.signup({
      email: userData.email,
      password: userData.password,
      username: userData.username || userData.display_name
    });
    
    if (response.access_token) {
      return {
        success: true,
        data: {
          access_token: response.access_token,
          refresh_token: response.refresh_token,
          user_id: response.user.id,
          email: response.user.email,
          user: response.user
        }
      };
    }
  } catch (error) {
    const errorMessage = getErrorMessage(error);
    return {
      success: false,
      error: errorMessage,
      status: error.response?.status
    };
  }
}
```

### Register.jsx 中的錯誤顯示

```javascript:frontend/src/components/Register.jsx
if (result.success) {
  // 註冊成功處理
} else {
  // 顯示錯誤訊息
  setGeneralError(result.error || '註冊失敗，請稍後再試');
}
```

✅ 錯誤處理已完整實作，500 錯誤會自動顯示給用戶。

## 除錯技巧

### 1. 檢查瀏覽器 Console

開啟瀏覽器開發者工具（F12），查看 Console 標籤的錯誤訊息：

```
Supabase 請求: POST /signup
Supabase 回應: 500 /signup
Supabase API 錯誤: 500 {error: "..."}
```

### 2. 檢查 Network 標籤

在 Network 標籤中找到 `/supabase-auth/signup` 請求：

- **Status**: 500 (表示後端錯誤)
- **Preview**: 查看後端返回的錯誤訊息
- **Request Payload**: 確認發送的資料格式正確

### 3. 檢查 Vite 代理設定

確保 `vite.config.mjs` 正確設定代理：

```javascript:frontend/vite.config.mjs
proxy: {
  '/supabase-auth': {
    target: 'https://supalaw.mooo.com',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/supabase-auth/, '/auth/v1'),
    secure: false
  }
}
```

✅ 代理設定已正確配置。

### 4. 檢查後端日誌

如果前端一切正常但仍有錯誤，請檢查後端日誌：

- **Supabase Dashboard** → **Logs** → **Auth Logs**
- **Supabase Dashboard** → **Logs** → **Postgres Logs**

## 常見問題

### Q: 為什麼註冊失敗但沒有顯示具體錯誤？

A: 500 錯誤通常不會包含詳細訊息。需要檢查後端日誌才能看到具體錯誤。

### Q: 我可以繞過這個錯誤嗎？

A: 不行，這必須從後端修正。前端無法繞過資料庫觸發器錯誤。

### Q: 修正後需要重新部署前端嗎？

A: 不需要。這是後端問題，只需更新資料庫即可。

### Q: 如何確認修正是否成功？

A: 嘗試註冊新用戶，如果註冊成功且沒有 500 錯誤，表示修正成功。

## 相關文件

- [後端修正指南](../supabase/latest_ddl/FIX_SIGNUP_500_ERROR.md)
- [CORS 代理設置](./CORS_PROXY_SETUP.md)
- [資料庫 Schema](./db_schema.md)
- [API 文件](./src/api/README.md)

## 聯絡支援

如果問題持續存在，請提供以下資訊：

1. 瀏覽器 Console 完整錯誤訊息
2. Network 標籤中的請求/回應內容
3. 註冊時使用的 email 格式
4. 後端日誌（如果有權限查看）

