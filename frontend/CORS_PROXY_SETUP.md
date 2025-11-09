# CORS 代理設置說明

## 問題描述

當前端直接訪問 `https://supalaw.mooo.com` 的 Supabase Auth API 時，遇到 CORS 錯誤：
```
Access to XMLHttpRequest at 'https://supalaw.mooo.com/auth/v1/token' from origin 'http://localhost:3000' 
has been blocked by CORS policy: The 'Access-Control-Allow-Origin' header contains multiple values '*, *', 
but only one is allowed.
```

## 解決方案：使用 Vite 代理

我們在開發環境中使用 Vite 的代理功能來避免 CORS 問題。

### 1. Vite 配置 (`vite.config.mjs`)

```javascript
server: {
  proxy: {
    // 代理 Supabase Auth API 請求
    '/supabase-auth': {
      target: 'https://supalaw.mooo.com',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/supabase-auth/, '/auth/v1'),
      secure: false
    },
    // 代理 Supabase REST API 請求
    '/supabase-rest': {
      target: 'https://supalaw.mooo.com',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/supabase-rest/, '/rest/v1'),
      secure: false
    }
  }
}
```

### 2. 前端請求路徑

**開發環境** (localhost:3000):
- Auth API: `/supabase-auth/signup`, `/supabase-auth/token`
- REST API: `/supabase-rest/...`

**生產環境**:
- Auth API: `https://supalaw.mooo.com/auth/v1/signup`, `https://supalaw.mooo.com/auth/v1/token`
- REST API: `https://supalaw.mooo.com/rest/v1/...`

### 3. 使用方法

#### 啟動開發服務器

```bash
cd frontend
npm run dev
```

服務器會在 `http://localhost:3000` 啟動，所有對 `/supabase-auth/*` 和 `/supabase-rest/*` 的請求會自動代理到 `https://supalaw.mooo.com`。

#### API 使用範例

```javascript
// 登入
const result = await authAPI.login({
  email: 'user@example.com',
  password: 'yourpassword'
});

// 註冊
const result = await authAPI.register({
  email: 'user@example.com',
  password: 'yourpassword',
  username: 'username'
});
```

## 生產環境部署

### 選項 1: 修復 Supabase CORS 設置（推薦）

需要在 Supabase 服務器端修正 CORS 設置，確保 `Access-Control-Allow-Origin` header 只出現一次。

檢查以下配置：
1. Nginx/反向代理設置
2. Supabase 服務配置
3. 確保沒有重複的 CORS header

### 選項 2: 使用 Nginx 反向代理

在生產環境中設置 Nginx 反向代理：

```nginx
location /api/auth/ {
    proxy_pass https://supalaw.mooo.com/auth/v1/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # CORS headers
    add_header 'Access-Control-Allow-Origin' '*';
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization,apikey';
    
    if ($request_method = 'OPTIONS') {
        return 204;
    }
}
```

### 選項 3: 使用環境變數

在 `.env` 文件中配置 API URL：

```env
# 開發環境
VITE_API_MODE=development

# 生產環境
VITE_API_MODE=production
VITE_SUPABASE_URL=https://your-production-domain.com
```

## 錯誤處理

前端已實現完整的錯誤處理：

- ✅ 電子郵件或密碼錯誤
- ✅ 電子郵件尚未註冊
- ✅ 電子郵件已被註冊
- ✅ 需要確認電子郵件
- ✅ 網路連接失敗
- ✅ 請求過於頻繁

## 測試

### 1. 測試註冊

```bash
curl -X POST 'http://localhost:3000/supabase-auth/signup' \
  -H "Content-Type: application/json" \
  -H "apikey: YOUR_ANON_KEY" \
  -d '{
    "email": "test@example.com",
    "password": "test123456",
    "data": {
      "username": "testuser"
    }
  }'
```

### 2. 測試登入

```bash
curl -X POST 'http://localhost:3000/supabase-auth/token?grant_type=password' \
  -H "Content-Type: application/json" \
  -H "apikey: YOUR_ANON_KEY" \
  -d '{
    "email": "test@example.com",
    "password": "test123456"
  }'
```

## 注意事項

1. **開發環境**: 必須使用 `npm run dev` 啟動，代理才會生效
2. **生產環境**: 需要修復 Supabase CORS 設置或使用反向代理
3. **API Key**: 請勿將 Supabase anon key 提交到公開倉庫
4. **重新啟動**: 修改 `vite.config.mjs` 後需要重新啟動開發服務器

## 相關文件

- `vite.config.mjs` - Vite 代理配置
- `src/api/supabaseClient.js` - Supabase 客戶端配置
- `src/api/auth.js` - 認證 API
- `src/contexts/AuthContext.jsx` - 認證上下文

