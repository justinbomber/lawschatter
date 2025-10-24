import axios from 'axios';

// API 基礎 URL
const BASE_URL = 'http://localhost:8090/api';

// 建立 axios 實例
const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 10000, // 10 秒超時
  headers: {
    'Content-Type': 'application/json',
  },
});

// 請求攔截器
apiClient.interceptors.request.use(
  (config) => {
    // 如果有 token，自動添加到 headers
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    console.log('API 請求:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('請求攔截器錯誤:', error);
    return Promise.reject(error);
  }
);

// 回應攔截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('API 回應:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('API 錯誤:', error.response?.status, error.config?.url);
    
    // 處理 401 未授權錯誤
    if (error.response?.status === 401) {
      // 清除過期的 token
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_data');
      
      // 如果當前不在登入頁面，重定向到登入頁面
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
