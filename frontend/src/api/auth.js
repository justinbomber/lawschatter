import apiClient from './client';
import { supabaseAuth } from './supabaseClient';

/**
 * 認證相關的 API 方法
 */
export const authAPI = {
  /**
   * 使用者登入 (使用 Supabase Auth)
   * @param {Object} credentials - 登入憑證
   * @param {string} credentials.email - 電子郵件
   * @param {string} credentials.password - 密碼
   * @returns {Promise<Object>} 登入回應資料
   */
  login: async (credentials) => {
    try {
      const response = await supabaseAuth.login({
        email: credentials.email,
        password: credentials.password
      });
      
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
   * 使用者註冊 (使用 Supabase Auth)
   * @param {Object} userData - 註冊資料
   * @param {string} userData.email - 電子郵件
   * @param {string} userData.password - 密碼
   * @param {string} userData.username - 使用者名稱
   * @param {string} userData.display_name - 顯示名稱
   * @returns {Promise<Object>} 註冊回應資料
   */
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
      } else {
        return {
          success: true,
          data: {
            message: '註冊成功，請檢查您的電子郵件以驗證帳戶',
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
  },

  /**
   * 登出 (使用 Supabase Auth)
   * @returns {Promise<Object>} 登出回應資料
   */
  logout: async () => {
    try {
      await supabaseAuth.logout();
      
      return {
        success: true,
        data: null
      };
    } catch (error) {
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
  // 檢查 Supabase Auth 特定錯誤訊息
  const errorMsg = error.response?.data?.msg || 
                   error.response?.data?.message || 
                   error.response?.data?.error_description ||
                   error.message;
  
  // Supabase Auth 特定錯誤處理
  if (errorMsg) {
    if (errorMsg.includes('Invalid login credentials') || 
        errorMsg.includes('invalid_grant')) {
      return '電子郵件或密碼錯誤，請檢查後重試';
    }
    
    if (errorMsg.includes('Email not confirmed')) {
      return '請先確認您的電子郵件後再登入';
    }
    
    if (errorMsg.includes('User not found') || 
        errorMsg.includes('user_not_found')) {
      return '此電子郵件尚未註冊，請先註冊';
    }
    
    if (errorMsg.includes('User already registered') ||
        errorMsg.includes('already_registered')) {
      return '此電子郵件已被註冊';
    }
    
    if (errorMsg.includes('Invalid email')) {
      return '電子郵件格式不正確';
    }
    
    if (errorMsg.includes('Password should be at least')) {
      return '密碼至少需要 6 個字符';
    }
    
    if (errorMsg.includes('Signups not allowed')) {
      return '目前暫不開放註冊';
    }
    
    if (errorMsg.includes('rate_limit') || errorMsg.includes('too many requests')) {
      return '請求過於頻繁，請稍後再試';
    }
  }
  
  // 根據狀態碼回傳對應訊息
  switch (error.response?.status) {
    case 400:
      return '請求參數錯誤，請檢查輸入資料';
    case 401:
      return '電子郵件或密碼錯誤，請檢查後重試';
    case 403:
      return '無權限執行此操作';
    case 404:
      return '此電子郵件尚未註冊，請先註冊';
    case 409:
      return '此電子郵件已被註冊';
    case 422:
      return '輸入資料格式不正確';
    case 429:
      return '請求過於頻繁，請稍後再試';
    case 500:
      return '伺服器內部錯誤，請稍後再試';
    case 503:
      return '服務暫時無法使用，請稍後再試';
    default:
      break;
  }
  
  // 檢查網路錯誤
  if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK') {
    return '無法連接到伺服器，請檢查網路連接';
  }
  
  if (error.code === 'ENOTFOUND') {
    return '網路連接失敗，請檢查網路連接';
  }
  
  if (error.code === 'TIMEOUT' || error.code === 'ECONNABORTED') {
    return '請求超時，請檢查網路連接';
  }
  
  // 如果有原始錯誤訊息，返回它
  if (errorMsg && typeof errorMsg === 'string') {
    return errorMsg;
  }
  
  // 預設錯誤訊息
  return '發生未知錯誤，請稍後再試';
};

export default authAPI;
