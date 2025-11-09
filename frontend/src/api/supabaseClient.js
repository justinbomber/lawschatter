import axios from 'axios';

const SUPABASE_URL = 'https://supalaw.mooo.com';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJhbm9uIiwKICAgICJpc3MiOiAic3VwYWJhc2UtZGVtbyIsCiAgICAiaWF0IjogMTY0MTc2OTIwMCwKICAgICJleHAiOiAxNzk5NTM1NjAwCn0.dc_X5iR_VP_qT0zsiyj_I_OZ2T9FtRU2BBNWN8Bu4GE';

// 開發環境使用代理，生產環境使用直接 URL
const isDevelopment = import.meta.env.MODE === 'development';
const AUTH_BASE_URL = isDevelopment ? '/supabase-auth' : `${SUPABASE_URL}/auth/v1`;

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
    const token = localStorage.getItem('supabase_access_token');
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
    return Promise.reject(error);
  }
);

export const supabaseAuth = {
  signup: async ({ email, password, username }) => {
    const response = await supabaseAuthClient.post('/signup', {
      email,
      password,
      data: {
        username: username || email.split('@')[0]
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

const REST_BASE_URL = isDevelopment ? '/supabase-rest' : `${SUPABASE_URL}/rest/v1`;

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
    const token = localStorage.getItem('supabase_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default supabaseAuthClient;

