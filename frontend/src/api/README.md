# API 管理模組

這個資料夾包含所有與後端 API 通訊相關的程式碼，採用模組化設計，便於維護和擴展。

## 檔案結構

```
src/api/
├── client.js       # axios 客戶端基礎配置和攔截器
├── auth.js         # 認證相關 API 方法
├── index.js        # 統一匯出入口
└── README.md       # 說明文件
```

## 使用方式

### 1. 匯入 API 方法

```javascript
import { authAPI } from '../api';
// 或者
import { authAPI, apiClient } from '../api';
```

### 2. 使用認證 API

```javascript
// 登入
const result = await authAPI.login({
  email: 'user@example.com',
  password: 'password123'
});

if (result.success) {
  console.log('登入成功:', result.data);
} else {
  console.error('登入失敗:', result.error);
}

// 註冊
const registerResult = await authAPI.register({
  email: 'user@example.com',
  password: 'password123',
  username: 'username',
  display_name: '使用者姓名'
});

// 登出
const logoutResult = await authAPI.logout();

// 獲取使用者資訊
const userInfo = await authAPI.getUserInfo();
```

### 3. 使用 API 客戶端（適用於其他 API）

```javascript
import { apiClient } from '../api';

// 發送自訂請求
const response = await apiClient.get('/custom-endpoint');
const postResponse = await apiClient.post('/data', { key: 'value' });
```

## 功能特色

### 1. 統一錯誤處理
- 自動處理常見的 HTTP 狀態碼
- 提供使用者友善的錯誤訊息
- 網路錯誤的特殊處理

### 2. 自動 Token 管理
- 自動在請求中添加 Authorization header
- Token 過期時自動清除並重定向到登入頁面

### 3. 請求/回應攔截器
- 自動記錄 API 請求和回應
- 統一的錯誤處理
- 自動 token 驗證

### 4. 型別安全的回應格式

所有 API 方法都返回統一的格式：

```javascript
{
  success: boolean,
  data: any,           // 成功時的資料
  error: string,       // 失敗時的錯誤訊息
  status: number       // HTTP 狀態碼（失敗時）
}
```

## 新增新的 API 模組

1. 在 `src/api/` 下建立新的 `.js` 檔案
2. 按照 `auth.js` 的模式建立 API 方法
3. 在 `index.js` 中匯出新模組

例如，建立聊天 API：

```javascript
// src/api/chat.js
import apiClient from './client';

export const chatAPI = {
  sendMessage: async (message) => {
    try {
      const response = await apiClient.post('/chat/send', { message });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: getErrorMessage(error) };
    }
  }
};

// src/api/index.js
export { chatAPI } from './chat';
```

## 設定

可以在 `client.js` 中調整以下設定：

- `BASE_URL`: API 伺服器地址
- `timeout`: 請求超時時間
- `headers`: 預設請求 headers

## 注意事項

1. 所有 API 方法都是異步的，需要使用 `await` 或 `.then()`
2. 錯誤處理已統一，不需要在組件中重複處理常見錯誤
3. Token 會自動管理，不需要手動添加到請求中
4. 開發時請確保後端服務運行在正確的端口
