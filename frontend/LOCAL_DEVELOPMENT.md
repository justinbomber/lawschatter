# 本地開發配置說明

## 概述

此專案支援兩種開發模式：

1. **生產模式** (`npm run dev`)：連接到 `https://lawschatter.mooo.com`
2. **本地模式** (`npm run local`)：連接到本地服務

## 使用本地開發模式

### 1. 啟動本地服務

確保以下服務運行：

- **Supabase**: `https://supalaw.mooo.com` (線上服務)
- **RAG API**: `http://127.0.0.1:9500` (本地服務)
- **前端**: `http://127.0.0.1:3000` (本地服務)

### 2. 啟動前端

```bash
cd frontend
npm run local
```

## 配置詳情

### 本地模式配置

使用 `vite.config.local.mjs` 配置檔：

- **API Base URL**: `http://localhost:8090`
- **Chat API URL**: `http://127.0.0.1:9500`
- **Supabase Auth**: 代理到 `https://supalaw.mooo.com/auth/v1` (線上服務)
- **Supabase REST**: 代理到 `https://supalaw.mooo.com/rest/v1` (線上服務)
- **RAG API**: 代理到 `http://127.0.0.1:9500` (本地服務)

### 生產模式配置

使用 `vite.config.mjs` 配置檔：

- **API Base URL**: `https://lawschatter.mooo.com`
- **Chat API URL**: `https://lawschatter.mooo.com`
- **Supabase Auth**: 代理到 `https://supalaw.mooo.com/auth/v1`
- **Supabase REST**: 代理到 `https://supalaw.mooo.com/rest/v1`

## API 端點對照表

### 本地開發端點

| 服務 | 端點 | 說明 |
|------|------|------|
| Supabase Auth | `https://supalaw.mooo.com/auth/v1/*` | 認證服務 (線上) |
| Supabase REST | `https://supalaw.mooo.com/rest/v1/*` | 資料庫 REST API (線上) |
| RAG Chat | `http://127.0.0.1:9500/chat/*` | 聊天 API (本地) |
| RAG Search | `http://127.0.0.1:9500/search/*` | 搜尋 API (本地) |

### 生產環境端點

| 服務 | 生產端點 | 說明 |
|------|---------|------|
| Supabase Auth | `https://supalaw.mooo.com/auth/v1/*` | 認證服務 |
| Supabase REST | `https://supalaw.mooo.com/rest/v1/*` | 資料庫 REST API |
| RAG Chat | `https://lawschatter.mooo.com/chat/*` | 聊天 API |
| RAG Search | `https://lawschatter.mooo.com/search/*` | 搜尋 API |

## Scripts 說明

```json
{
  "start": "vite",                    // 啟動開發伺服器（生產模式）
  "dev": "vite",                      // 啟動開發伺服器（生產模式）
  "local": "vite --config vite.config.local.mjs",  // 啟動開發伺服器（本地模式）
  "build": "vite build",              // 建置生產版本
  "preview": "vite preview"           // 預覽建置結果
}
```

## 環境變數

前端程式碼會根據環境變數自動切換 API 端點：

- `VITE_API_BASE_URL`: 主要 API 基礎 URL
- `VITE_CHAT_API_URL`: 聊天 API 基礎 URL
- `VITE_MODE`: 運行模式 (`local` 或 `production`)

這些變數在 `vite.config.local.mjs` 中定義，會在執行 `npm run local` 時自動注入。

## 故障排除

### 無法連接到本地服務

1. 確認本地服務是否已啟動
2. 檢查防火牆設定
3. 檢查端口是否被占用

### CORS 錯誤

本地開發使用 Vite 的代理功能，應該不會有 CORS 問題。如果遇到，請檢查：

1. `vite.config.local.mjs` 中的代理設定
2. 後端服務的 CORS 設定

### Token 相關錯誤

本地模式使用線上 Supabase 服務，確保：
1. 能夠連接到 `https://supalaw.mooo.com`
2. `SUPABASE_ANON_KEY` 與線上服務配置一致

