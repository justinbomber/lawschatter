import apiClient from './client';

/**
 * 認證相關的 API 方法
 */
export const authAPI = {
  /**
   * 使用者登入
   * @param {Object} credentials - 登入憑證
   * @param {string} credentials.email - 電子郵件
   * @param {string} credentials.password - 密碼
   * @returns {Promise<Object>} 登入回應資料
   */
  login: async (credentials) => {
    try {
      const response = await apiClient.post('/login', {
        email: credentials.email,
        password: credentials.password
      });
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      // 統一錯誤處理
      const errorMessage = getErrorMessage(error);
      return {
        success: false,
        error: errorMessage,
        status: error.response?.status
      };
    }
  },

  /**
   * 使用者註冊
   * @param {Object} userData - 註冊資料
   * @param {string} userData.email - 電子郵件
   * @param {string} userData.password - 密碼
   * @param {string} userData.username - 使用者名稱
   * @param {string} userData.display_name - 顯示名稱
   * @returns {Promise<Object>} 註冊回應資料
   */
  register: async (userData) => {
    try {
      const response = await apiClient.post('/register', {
        email: userData.email,
        password: userData.password,
        username: userData.username,
        display_name: userData.display_name
      });
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      return {
        success: false,
        error: errorMessage,
        status: error.response?.status
      };
    }
  },

  /**
   * 登出
   * @returns {Promise<Object>} 登出回應資料
   */
  logout: async () => {
    try {
      const response = await apiClient.post('/logout');
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      // 即使登出失敗，也清除本地存儲
      console.warn('登出 API 呼叫失敗，但仍會清除本地存儲:', error);
      return {
        success: true,
        data: null
      };
    }
  },

  /**
   * 重新整理 token
   * @returns {Promise<Object>} 重新整理回應資料
   */
  refreshToken: async () => {
    try {
      const response = await apiClient.post('/refresh');
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      return {
        success: false,
        error: errorMessage,
        status: error.response?.status
      };
    }
  },

  /**
   * 獲取使用者資訊
   * @returns {Promise<Object>} 使用者資訊
   */
  getUserInfo: async () => {
    try {
      const response = await apiClient.get('/user/profile');
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      return {
        success: false,
        error: errorMessage,
        status: error.response?.status
      };
    }
  },

  /**
   * 忘記密碼
   * @param {string} email - 電子郵件
   * @returns {Promise<Object>} 忘記密碼回應資料
   */
  forgotPassword: async (email) => {
    try {
      const response = await apiClient.post('/forgot-password', { email });
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      return {
        success: false,
        error: errorMessage,
        status: error.response?.status
      };
    }
  },

  /**
   * 重置密碼
   * @param {Object} resetData - 重置密碼資料
   * @param {string} resetData.token - 重置令牌
   * @param {string} resetData.password - 新密碼
   * @returns {Promise<Object>} 重置密碼回應資料
   */
  resetPassword: async (resetData) => {
    try {
      const response = await apiClient.post('/reset-password', {
        token: resetData.token,
        password: resetData.password
      });
      
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      return {
        success: false,
        error: errorMessage,
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
      return '電子郵件或密碼錯誤';
    case 403:
      return '無權限執行此操作';
    case 404:
      return '請求的資源不存在';
    case 409:
      return '資料衝突，該電子郵件可能已被使用';
    case 429:
      return '請求過於頻繁，請稍後再試';
    case 500:
      return '伺服器內部錯誤';
    case 503:
      return '服務暫時無法使用';
    default:
      break;
  }
  
  // 檢查網路錯誤
  if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK') {
    return '無法連接到伺服器，請確認伺服器是否正在運行';
  }
  
  if (error.code === 'ENOTFOUND') {
    return '網路連接失敗';
  }
  
  if (error.code === 'TIMEOUT' || error.code === 'ECONNABORTED') {
    return '請求超時，請檢查網路連接';
  }
  
  // 預設錯誤訊息
  return '發生未知錯誤，請稍後再試';
};

export default authAPI;
