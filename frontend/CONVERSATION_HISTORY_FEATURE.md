# 歷史對話記錄功能

## 功能概述

實現了完整的歷史對話記錄功能，使用者登入後可以查看、選擇、重命名和刪除歷史對話。

## 主要功能

### 1. 對話列表顯示
- 登入後自動載入所有歷史對話
- 依照更新時間排序（最新的在最上方）
- 按時間分組顯示：今天、昨天、過去 7 天、更早

### 2. 對話操作
- **選擇對話**：點擊對話項目即可切換並載入該對話的歷史訊息
- **新建對話**：點擊側邊欄頂部的新建按鈕建立新對話
- **重命名對話**：右鍵選單中選擇重新命名
- **刪除對話**：右鍵選單中選擇刪除（會跳出確認視窗）

### 3. 訊息持久化
- 所有對話和訊息都儲存在 Supabase 資料庫
- 使用 Bearer Token 進行身份驗證
- 切換對話時自動載入該對話的歷史訊息

## 技術實作

### 新增檔案

#### `frontend/src/api/supabaseConversation.js`
對話管理 API，包含以下方法：
- `getConversations()` - 獲取所有對話列表
- `getConversationMessages(conversationId)` - 獲取指定對話的訊息
- `createConversation(title)` - 建立新對話
- `updateConversationTitle(conversationId, title)` - 更新對話標題
- `deleteConversation(conversationId)` - 刪除對話
- `updateRecentConversation(conversationId)` - 更新最近訪問時間

### 修改檔案

#### `frontend/src/api/chat.js`
- 在發送訊息時加入 `conversation_id` 參數
- 自動從 localStorage 讀取 Bearer Token 並加入到請求標頭

#### `frontend/src/App.jsx`
主要變更：
- 新增 `loadConversations()` - 載入對話列表
- 新增 `loadConversationMessages()` - 載入對話訊息
- 新增 `handleSelectConversation()` - 處理選擇對話
- 修改 `handleNewConversation()` - 與 Supabase 整合
- 新增 `handleRenameConversation()` - 重命名對話
- 新增 `handleDeleteConversation()` - 刪除對話
- 修改 `handleSendMessage()` - 加入 conversation_id 支持

#### `frontend/src/components/Sidebar.jsx`
主要變更：
- 新增 `loading` prop 顯示載入狀態
- 新增 `onRenameConversation` 和 `onDeleteConversation` props
- 修改對話顯示邏輯，支持真實的對話資料
- 新增載入狀態和空狀態顯示

#### `frontend/src/components/Sidebar.css`
新增樣式：
- `.conversations-loading` - 載入狀態樣式
- `.no-conversations` - 空狀態樣式

## 資料庫結構

使用 `lawschatter` schema 中的表格：

### `conversations` 表
```sql
conversation_id (UUID) - 主鍵
user_id (UUID) - 使用者 ID
title (TEXT) - 對話標題
created_at (TIMESTAMPTZ) - 建立時間
updated_at (TIMESTAMPTZ) - 更新時間
```

### `messages` 表
```sql
message_id (UUID) - 主鍵
conversation_id (UUID) - 所屬對話
user_id (UUID) - 使用者 ID
sender_type (TEXT) - 'user' 或 'assistant'
content (TEXT) - 訊息內容
created_at (TIMESTAMPTZ) - 建立時間
```

## API 端點

### Supabase REST API
- `GET /lawschatter.conversations` - 取得對話列表
- `POST /lawschatter.conversations` - 建立新對話
- `PATCH /lawschatter.conversations?conversation_id=eq.{id}` - 更新對話
- `DELETE /lawschatter.conversations?conversation_id=eq.{id}` - 刪除對話
- `GET /lawschatter.messages?conversation_id=eq.{id}` - 取得對話訊息

### 聊天 API (localhost:9500)
- `POST /chat/completion` - 發送訊息（需要 Bearer Token 和 conversation_id）

## 使用流程

1. **使用者登入**
   - 取得 Bearer Token 並存入 localStorage
   - 自動觸發 `loadConversations()`

2. **載入對話列表**
   - 從 Supabase 取得所有對話
   - 顯示在左側 Sidebar
   - 自動選擇最新的對話並載入訊息

3. **發送訊息**
   - 如果沒有選擇對話，自動建立新對話
   - 帶上 Bearer Token 和 conversation_id 發送到後端
   - 後端儲存訊息到 Supabase

4. **切換對話**
   - 點擊對話項目
   - 載入該對話的歷史訊息
   - 更新最近訪問時間

## 注意事項

1. **Token 管理**
   - Token 存在 localStorage 的 `supabase_access_token` 中
   - 所有 API 請求都需要帶上 Bearer Token
   - 每個 API 調用都會從 localStorage 讀取最新的 token
   - Token 在登入時由 `AuthContext` 自動保存

2. **錯誤處理**
   - 載入失敗時會在 console 顯示錯誤
   - UI 會顯示空狀態或錯誤訊息
   - 403 錯誤通常表示 token 過期或無效

3. **效能考量**
   - 訊息載入預設限制為 100 條
   - 對話列表按更新時間排序

4. **安全性**
   - 使用 Supabase RLS（Row Level Security）
   - 使用者只能存取自己的對話和訊息
   - 使用 `Accept-Profile` 和 `Content-Profile` headers 指定 schema

## 調試技巧

如果遇到 403 或 404 錯誤：

1. **檢查 Token**
   ```javascript
   console.log('Token:', localStorage.getItem('supabase_access_token'));
   ```

2. **檢查 Headers**
   打開瀏覽器開發者工具 → Network → 查看請求 Headers：
   - `Authorization: Bearer {token}`
   - `Accept-Profile: lawschatter`
   - `Content-Profile: lawschatter`

3. **檢查 RLS 政策**
   確保 Supabase 資料庫中的 RLS 政策已正確設定

4. **重新登入**
   如果 token 過期，需要重新登入以獲取新 token

