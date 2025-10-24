import apiClient from './client';

/**
 * 對話相關的 API 方法
 */
export const conversationAPI = {
  /**
   * 獲取使用者的所有對話
   * @param {string} userId - 使用者 ID
   * @returns {Promise<Object>} 對話列表
   */
  getConversations: async (userId) => {
    try {
      const response = await apiClient.get('/conversations', {
        headers: {
          'X-User-Id': userId
        }
      });
      // 正規化回傳：支援 {ok, data: []} 或直接 [] 或 {items: []} 等格式
      const raw = response.data;
      const payload = (raw && typeof raw === 'object' && 'data' in raw) ? raw.data : raw;
      const list = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.items)
          ? payload.items
          : Array.isArray(payload?.conversations)
            ? payload.conversations
            : [];

      return {
        success: true,
        data: list
      };
    } catch (error) {
      console.error('獲取對話列表失敗:', error);
      return {
        success: false,
        error: getErrorMessage(error),
        status: error.response?.status
      };
    }
  },

  /**
   * 獲取特定對話的訊息
   * @param {string} conversationId - 對話 ID
   * @param {string} userId - 使用者 ID
   * @param {number} limit - 訊息數量限制，預設 100
   * @returns {Promise<Object>} 對話訊息列表
   */
  getConversationMessages: async (conversationId, userId, limit = 100) => {
    try {
      const response = await apiClient.get(`/conversations/${conversationId}/messages`, {
        params: { limit },
        headers: {
          'X-User-Id': userId
        }
      });
      // 正規化回傳：支援 {ok, data: []} 或直接 [] 或 {items: []} 等格式
      const raw = response.data;
      const payload = (raw && typeof raw === 'object' && 'data' in raw) ? raw.data : raw;
      const list = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.items)
          ? payload.items
          : Array.isArray(payload?.messages)
            ? payload.messages
            : [];

      return {
        success: true,
        data: list
      };
    } catch (error) {
      console.error('獲取對話訊息失敗:', error);
      return {
        success: false,
        error: getErrorMessage(error),
        status: error.response?.status
      };
    }
  },

  /**
   * 建立新對話
   * @param {Object} conversationData - 對話資料
   * @param {string} conversationData.title - 對話標題
   * @param {string} conversationData.userId - 使用者 ID
   * @returns {Promise<Object>} 新建對話資料
   */
  createConversation: async (conversationData) => {
    try {
      const response = await apiClient.post('/conversations', {
        title: (conversationData.title && conversationData.title.trim()) ? conversationData.title : '新對話',
        user_id: conversationData.userId
      }, {
        headers: {
          'X-User-Id': conversationData.userId
        }
      });
      // 正規化回傳：支援 {ok, data: {...}} 或直接 {...}
      const raw = response.data;
      const payload = (raw && typeof raw === 'object' && 'data' in raw) ? raw.data : raw;

      return {
        success: true,
        data: payload
      };
    } catch (error) {
      console.error('建立對話失敗:', error);
      return {
        success: false,
        error: getErrorMessage(error),
        status: error.response?.status
      };
    }
  },

  /**
   * 發送訊息到對話
   * @param {Object} messageData - 訊息資料
   * @param {string} messageData.conversationId - 對話 ID
   * @param {string} messageData.message - 訊息內容
   * @param {string} messageData.userId - 使用者 ID
   * @returns {Promise<Object>} 發送結果
   */
  sendMessage: async (messageData) => {
    try {
      const response = await apiClient.post(`/conversations/${messageData.conversationId}/messages`, {
        message: messageData.message,
        user_id: messageData.userId
      }, {
        headers: {
          'X-User-Id': messageData.userId
        }
      });
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('發送訊息失敗:', error);
      return {
        success: false,
        error: getErrorMessage(error),
        status: error.response?.status
      };
    }
  },

  /**
   * 更新對話標題
   * @param {string} conversationId - 對話 ID
   * @param {string} title - 新標題
   * @param {string} userId - 使用者 ID
   * @returns {Promise<Object>} 更新結果
   */
  updateConversationTitle: async (conversationId, title, userId) => {
    try {
      const response = await apiClient.patch(`/conversations/${conversationId}`, {
        title: title
      }, {
        headers: {
          'X-User-Id': userId
        }
      });
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('更新對話標題失敗:', error);
      return {
        success: false,
        error: getErrorMessage(error),
        status: error.response?.status
      };
    }
  },

  /**
   * 刪除對話
   * @param {string} conversationId - 對話 ID
   * @param {string} userId - 使用者 ID
   * @returns {Promise<Object>} 刪除結果
   */
  deleteConversation: async (conversationId, userId) => {
    try {
      const response = await apiClient.delete(`/conversations/${conversationId}`, {
        headers: {
          'X-User-Id': userId
        }
      });
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('刪除對話失敗:', error);
      return {
        success: false,
        error: getErrorMessage(error),
        status: error.response?.status
      };
    }
  },

  /**
   * 獲取對話詳情
   * @param {string} conversationId - 對話 ID
   * @param {string} userId - 使用者 ID
   * @returns {Promise<Object>} 對話詳情
   */
  getConversationDetail: async (conversationId, userId) => {
    try {
      const response = await apiClient.get(`/conversations/${conversationId}`, {
        headers: {
          'X-User-Id': userId
        }
      });
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('獲取對話詳情失敗:', error);
      return {
        success: false,
        error: getErrorMessage(error),
        status: error.response?.status
      };
    }
  }
};

/**
 * 統一錯誤訊息處理
 * @param {Error} error - 錯誤物件
 * @returns {string} 錯誤訊息
 */
const getErrorMessage = (error) => {
  // 檢查後端回傳的錯誤訊息
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  
  // 根據狀態碼回傳對應訊息
  switch (error.response?.status) {
    case 400:
      return '請求參數錯誤';
    case 401:
      return '未授權，請重新登入';
    case 403:
      return '無權限存取此對話';
    case 404:
      return '對話不存在';
    case 429:
      return '請求過於頻繁，請稍後再試';
    case 500:
      return '伺服器內部錯誤';
    default:
      break;
  }
  
  // 檢查網路錯誤
  if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK') {
    return '無法連接到伺服器';
  }
  
  if (error.code === 'TIMEOUT' || error.code === 'ECONNABORTED') {
    return '請求超時';
  }
  
  // 預設錯誤訊息
  return '操作失敗，請稍後再試';
};

export default conversationAPI;
