# 專案 API 設計與資料庫結構 (DB Schema)

本文檔根據前端 React 應用程式的程式碼分析，定義了支援其功能所需的後端 API 端點和資料庫結構。

## 1. 功能分析

前端應用程式是一個聊天機器人介面，具備以下核心功能：
- **使用者認證**: 登入、登出、顯示使用者資訊。
- **對話管理**: 建立、選取、列出歷史對話。
- **即時通訊**: 使用者與 AI 之間的問答互動。
- **AI 模型選擇**: 允許使用者切換不同的 AI 模型 (例如 GPT-4, GPT-4o)。
- **RAG (Retrieval-Augmented Generation) 整合**: 連接外部法律資料庫，根據使用者設定的領域和時間範圍進行檢索，以增強回答的準確性。
- **訊息回饋**: 使用者可以對 AI 的回答進行評價 (讚/倒讚)。

---

## 2. API 端點設計

為了支援上述功能，建議設計以下 RESTful API 端點：

### 認證 API (`/api/auth`)
- `POST /api/auth/login`
  - **功能**: 使用者登入。
  - **請求 Body**: `{ "email": "user@example.com", "password": "user_password" }`
  - **回應**: `{ "token": "jwt_token", "user": { ... } }`

- `POST /api/auth/logout`
  - **功能**: 使用者登出。

- `GET /api/auth/me`
  - **功能**: 獲取當前已登入使用者的資訊。
  - **需要驗證**: 是
  - **回應**: `{ "id": 1, "name": "User", "email": "w0913706494@gmail.com" }`

### 對話 API (`/api/conversations`)
- `GET /api/conversations`
  - **功能**: 獲取目前使用者的所有對話列表。
  - **需要驗證**: 是
  - **回應**: `[{ "id": 1, "title": "昨天的對話", "created_at": "..." }, ...]`

- `POST /api/conversations`
  - **功能**: 建立一個新的對話。
  - **需要驗證**: 是
  - **回應**: `{ "id": 2, "title": "新對話", "created_at": "..." }`

- `GET /api/conversations/:conversationId`
  - **功能**: 獲取特定對話的詳細資訊，包含所有訊息。
  - **需要驗證**: 是
  - **回應**: `{ "id": 1, "title": "...", "messages": [{...}, {...}] }`

- `DELETE /api/conversations/:conversationId`
  - **功能**: 刪除一個對話及其所有訊息。
  - **需要驗證**: 是

### 訊息 API (`/api/messages`)
- `POST /api/conversations/:conversationId/messages`
  - **功能**: 在特定對話中傳送新訊息，並觸發 AI 回應。這是與聊天機器人互動的核心端點。
  - **需要驗證**: 是
  - **請求 Body**: `{ "content": "使用者輸入的訊息", "model": "gpt-4o", "rag_settings": { ... } }`
  - **回應**: `Stream` 或 `JSON` 形式的 AI 回應訊息。

- `POST /api/messages/:messageId/feedback`
  - **功能**: 對 AI 的回答提交評價。
  - **需要驗證**: 是
  - **請求 Body**: `{ "rating": "like" }` 或 `{ "rating": "dislike" }`

### RAG 設定 API (`/api/rag`)
- `GET /api/rag/settings`
  - **功能**: 獲取使用者的 RAG 設定。
  - **需要驗證**: 是
  - **回應**: `{ "selected_collections": ["勞動基準法"], "start_date": "2023-01-01", "end_date": "2023-12-31" }`

- `PUT /api/rag/settings`
  - **功能**: 更新使用者的 RAG 設定。
  - **需要驗證**: 是
  - **請求 Body**: `{ "selected_collections": ["勞動基準法", "民法"], "start_date": "...", "end_date": "..." }`

- `GET /api/rag/collections`
  - **功能**: 獲取所有可用的 RAG 資料庫（法律領域）。
  - **回應**: `[{ "id": "labor_law", "name": "勞動基準法", "description": "..." }, ...]`

---

## 3. 資料庫結構 (DB Schema)

建議使用關聯式資料庫，並設計以下資料表：

### `users`
儲存使用者帳號資訊。

| 欄位名 | 資料類型 | 說明 |
| :--- | :--- | :--- |
| `id` | `INT` / `UUID` | Primary Key |
| `email` | `VARCHAR(255)` | 使用者信箱 (唯一) |
| `name` | `VARCHAR(255)` | 使用者名稱 |
| `password_hash` | `VARCHAR(255)` | 加密後的密碼 |
| `created_at` | `TIMESTAMP` | 建立時間 |
| `updated_at` | `TIMESTAMP` | 更新時間 |

### `conversations`
儲存使用者建立的對話。

| 欄位名 | 資料類型 | 說明 |
| :--- | :--- | :--- |
| `id` | `INT` / `UUID` | Primary Key |
| `user_id` | `INT` / `UUID` | Foreign Key to `users.id` |
| `title` | `VARCHAR(255)` | 對話標題 |
| `created_at` | `TIMESTAMP` | 建立時間 |
| `updated_at` | `TIMESTAMP` | 更新時間 |

### `messages`
儲存每個對話中的訊息。

| 欄位名 | 資料類型 | 說明 |
| :--- | :--- | :--- |
| `id` | `INT` / `UUID` | Primary Key |
| `conversation_id` | `INT` / `UUID` | Foreign Key to `conversations.id` |
| `sender_type` | `ENUM('user', 'assistant')` | 訊息傳送者類型 |
| `content` | `TEXT` | 訊息內容 |
| `model_used` | `VARCHAR(100)` | (若為 assistant) 使用的 AI 模型 |
| `created_at` | `TIMESTAMP` | 建立時間 |

### `message_feedback`
儲存使用者對 AI 訊息的評價。

| 欄位名 | 資料類型 | 說明 |
| :--- | :--- | :--- |
| `id` | `INT` / `UUID` | Primary Key |
| `message_id` | `INT` / `UUID` | Foreign Key to `messages.id` |
| `user_id` | `INT` / `UUID` | Foreign Key to `users.id` |
| `rating` | `ENUM('like', 'dislike')` | 評價 |
| `comment` | `TEXT` | (選填) 額外意見 |
| `created_at` | `TIMESTAMP` | 建立時間 |

### `rag_settings`
儲存每位使用者的 RAG 設定，與 `users` 為一對一關係。

| 欄位名 | 資料類型 | 說明 |
| :--- | :--- | :--- |
| `id` | `INT` / `UUID` | Primary Key |
| `user_id` | `INT` / `UUID` | Foreign Key to `users.id` (唯一) |
| `selected_collections` | `JSON` / `TEXT[]` | 選擇的資料庫 ID 列表 |
| `start_date` | `DATE` | (選填) 起始日期 |
| `end_date` | `DATE` | (選填) 結束日期 |
| `updated_at` | `TIMESTAMP` | 更新時間 |

### `rag_collections`
儲存可用的 RAG 資料庫（例如不同的法律領域）。

| 欄位名 | 資料類型 | 說明 |
| :--- | :--- | :--- |
| `id` | `VARCHAR(100)` | Primary Key (例如 "labor_law") |
| `name` | `VARCHAR(255)` | 顯示名稱 (例如 "勞動基準法") |
| `description` | `TEXT` | (選填) 詳細描述 |


