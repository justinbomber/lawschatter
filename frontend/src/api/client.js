import axios from 'axios';
import { validateTokenBeforeRequest, getValidToken } from '../utils/jwtValidator';

// API 基礎 URL - 根據環境變數決定
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://lawschatter.mooo.com';

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
    if (!validateTokenBeforeRequest()) {
      return Promise.reject(new Error('Token 已過期'));
    }
    
    const token = getValidToken();
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
    
    if (error.response?.status === 401) {
      localStorage.removeItem('supabase_access_token');
      localStorage.removeItem('supabase_refresh_token');
      localStorage.removeItem('supabase_user_data');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_data');
      
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
