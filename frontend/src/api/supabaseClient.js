import axios from 'axios';
import { validateTokenBeforeRequest, getValidToken } from '../utils/jwtValidator';

// const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL; // 讀取完整的 URL

// --- 修改點 1: Auth Base URL 指向官方標準路徑 ---
const AUTH_BASE_URL = `${SUPABASE_URL}/auth/v1`;
// 一律走同網域的反向代理前綴，對應 Nginx 設定
// const AUTH_BASE_URL = '/supabase-auth';

const supabaseAuthClient = axios.create({
  baseURL: AUTH_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'apikey': SUPABASE_ANON_KEY
  }
});

supabaseAuthClient.interceptors.request.use(
  (config) => {
    const isLoginOrSignup = config.url?.includes('/token') || config.url?.includes('/signup');
    
    if (!isLoginOrSignup && !validateTokenBeforeRequest()) {
      return Promise.reject(new Error('Token 已過期'));
    }
    
    const token = getValidToken();
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log('Supabase 請求:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('Supabase 請求攔截器錯誤:', error);
    return Promise.reject(error);
  }
);

supabaseAuthClient.interceptors.response.use(
  (response) => {
    console.log('Supabase 回應:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('Supabase API 錯誤:', error.response?.status, error.response?.data);
    
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

export const supabaseAuth = {
  signup: async ({ email, password, username }) => {
    // 將 username 存放在 user metadata 中，而不是 auth.users.username
    // 這樣可以避免唯一性約束衝突
    const response = await supabaseAuthClient.post('/signup', {
      email,
      password,
      data: {
        username: username || email.split('@')[0],
        display_name: username || email.split('@')[0]
      }
    });
    return response.data;
  },

  login: async ({ email, password }) => {
    const response = await supabaseAuthClient.post('/token', {
      email,
      password
    }, {
      params: {
        grant_type: 'password'
      }
    });
    return response.data;
  },

  logout: async () => {
    const response = await supabaseAuthClient.post('/logout');
    return response.data;
  },

  getUser: async () => {
    const response = await supabaseAuthClient.get('/user');
    return response.data;
  },

  refreshToken: async (refreshToken) => {
    const response = await supabaseAuthClient.post('/token', {
      refresh_token: refreshToken
    }, {
      params: {
        grant_type: 'refresh_token'
      }
    });
    return response.data;
  }
};

// const REST_BASE_URL = '/supabase-rest';

const REST_BASE_URL = `${SUPABASE_URL}/rest/v1`;

export const supabaseRestClient = axios.create({
  baseURL: REST_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'apikey': SUPABASE_ANON_KEY,
    'Prefer': 'return=representation',
    'Accept-Profile': 'lawschatter',
    'Content-Profile': 'lawschatter'
  }
});

supabaseRestClient.interceptors.request.use(
  (config) => {
    const isPublicEndpoint = (config.url?.includes('/shared_conversations') || 
                              config.url?.includes('/shared_messages')) &&
                             config.method?.toLowerCase() === 'get';
    
    if (!isPublicEndpoint) {
      if (!validateTokenBeforeRequest()) {
        return Promise.reject(new Error('Token 已過期'));
      }
      
      const token = getValidToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

supabaseRestClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      const isPublicEndpoint = error.config?.url?.includes('/shared_conversations') || 
                               error.config?.url?.includes('/shared_messages');
      
      if (!isPublicEndpoint) {
        localStorage.removeItem('supabase_access_token');
        localStorage.removeItem('supabase_refresh_token');
        localStorage.removeItem('supabase_user_data');
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_data');
        
        if (window.location.pathname !== '/login' && !window.location.pathname.startsWith('/share/')) {
          window.location.href = '/login';
        }
      }
    }
    
    return Promise.reject(error);
  }
);

export default supabaseAuthClient;

