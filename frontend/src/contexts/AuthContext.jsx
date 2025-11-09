import React, { createContext, useContext, useReducer, useEffect } from 'react';

// 初始狀態
const initialState = {
  isAuthenticated: false,
  user: null,
  token: null,
  loading: true,
  error: null
};

// Action types
const AUTH_ACTIONS = {
  SET_LOADING: 'SET_LOADING',
  LOGIN_SUCCESS: 'LOGIN_SUCCESS',
  LOGOUT: 'LOGOUT',
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
  SET_USER: 'SET_USER'
};

// Reducer
const authReducer = (state, action) => {
  switch (action.type) {
    case AUTH_ACTIONS.SET_LOADING:
      return {
        ...state,
        loading: action.payload
      };
    case AUTH_ACTIONS.LOGIN_SUCCESS:
      return {
        ...state,
        isAuthenticated: true,
        user: action.payload.user,
        token: action.payload.token,
        loading: false,
        error: null
      };
    case AUTH_ACTIONS.LOGOUT:
      return {
        ...initialState,
        loading: false
      };
    case AUTH_ACTIONS.SET_ERROR:
      return {
        ...state,
        error: action.payload,
        loading: false
      };
    case AUTH_ACTIONS.CLEAR_ERROR:
      return {
        ...state,
        error: null
      };
    case AUTH_ACTIONS.SET_USER:
      return {
        ...state,
        user: action.payload
      };
    default:
      return state;
  }
};

// 建立 Context
const AuthContext = createContext();

// AuthProvider 組件
export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // 從 localStorage 載入用戶資訊
  useEffect(() => {
    const loadStoredAuth = () => {
      try {
        const storedToken = localStorage.getItem('supabase_access_token');
        const storedRefreshToken = localStorage.getItem('supabase_refresh_token');
        const storedUser = localStorage.getItem('supabase_user_data');
        
        if (storedToken && storedUser) {
          const userData = JSON.parse(storedUser);
          
          // 檢查 token 是否過期
          if (isTokenValid(storedToken)) {
            dispatch({
              type: AUTH_ACTIONS.LOGIN_SUCCESS,
              payload: {
                user: userData,
                token: storedToken
              }
            });
          } else if (storedRefreshToken) {
            console.log('Token 過期，需要重新整理');
            dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: false });
          } else {
            // Token 過期且無 refresh token，清除存儲的資料
            localStorage.removeItem('supabase_access_token');
            localStorage.removeItem('supabase_refresh_token');
            localStorage.removeItem('supabase_user_data');
            dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: false });
          }
        } else {
          dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: false });
        }
      } catch (error) {
        console.error('載入存儲的認證資訊時發生錯誤:', error);
        // 清除可能損壞的資料
        localStorage.removeItem('supabase_access_token');
        localStorage.removeItem('supabase_refresh_token');
        localStorage.removeItem('supabase_user_data');
        dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: false });
      }
    };

    loadStoredAuth();
  }, []);

  // 檢查 JWT token 是否有效
  const isTokenValid = (token) => {
    try {
      if (!token) return false;
      
      const payload = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;
      
      return payload.exp > currentTime;
    } catch (error) {
      console.error('Token 驗證錯誤:', error);
      return false;
    }
  };

  // 登入函數
  const login = (responseData) => {
    try {
      const { user_id, email, access_token, refresh_token, user } = responseData;
      
      // 處理 Supabase 用戶資料
      const userData = {
        user_id: user_id || user?.id,
        email: email || user?.email,
        username: user?.user_metadata?.username || email?.split('@')[0],
        display_name: user?.user_metadata?.display_name || user?.user_metadata?.username || email?.split('@')[0],
        // 從 JWT token 中解析更多用戶資訊
        ...parseJWTUserData(access_token)
      };

      // 存儲到 localStorage (使用 Supabase 專用的 key)
      localStorage.setItem('supabase_access_token', access_token);
      if (refresh_token) {
        localStorage.setItem('supabase_refresh_token', refresh_token);
      }
      localStorage.setItem('supabase_user_data', JSON.stringify(userData));

      // 更新 context 狀態
      dispatch({
        type: AUTH_ACTIONS.LOGIN_SUCCESS,
        payload: {
          user: userData,
          token: access_token
        }
      });

      return true;
    } catch (error) {
      console.error('登入處理錯誤:', error);
      dispatch({
        type: AUTH_ACTIONS.SET_ERROR,
        payload: '登入資料處理失敗'
      });
      return false;
    }
  };

  // 從 JWT token 解析用戶資訊
  const parseJWTUserData = (token) => {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      
      // 清理和驗證 display_name，移除亂碼字元
      let displayName = payload.user_metadata?.display_name || '';
      if (displayName) {
        // 過濾掉非可讀字元，只保留基本字母、數字、中文、空格和常用標點
        displayName = displayName.replace(/[^\u4e00-\u9fa5a-zA-Z0-9\s\-_\.]/g, '');
        // 如果清理後為空，使用 username 或 email 前綴
        if (!displayName.trim()) {
          displayName = payload.user_metadata?.username || 
                       payload.email?.split('@')[0] || 
                       '使用者';
        }
      }
      
      return {
        display_name: displayName,
        username: payload.user_metadata?.username || '',
        email_verified: payload.user_metadata?.email_verified || false,
        role: payload.role || 'authenticated',
        session_id: payload.session_id || '',
        exp: payload.exp,
        iat: payload.iat
      };
    } catch (error) {
      console.error('解析 JWT token 失敗:', error);
      return {};
    }
  };

  // 登出函數
  const logout = () => {
    // 清除 localStorage (包含 Supabase 相關的 keys)
    localStorage.removeItem('supabase_access_token');
    localStorage.removeItem('supabase_refresh_token');
    localStorage.removeItem('supabase_user_data');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_data');
    
    // 更新 context 狀態
    dispatch({ type: AUTH_ACTIONS.LOGOUT });
  };

  // 更新用戶資訊
  const updateUser = (userData) => {
    const updatedUser = { ...state.user, ...userData };
    localStorage.setItem('supabase_user_data', JSON.stringify(updatedUser));
    dispatch({
      type: AUTH_ACTIONS.SET_USER,
      payload: updatedUser
    });
  };

  // 清除錯誤
  const clearError = () => {
    dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });
  };

  // 獲取帶有 Authorization header 的 axios 配置
  const getAuthHeaders = () => {
    if (state.token) {
      return {
        'Authorization': `Bearer ${state.token}`,
        'Content-Type': 'application/json'
      };
    }
    return {
      'Content-Type': 'application/json'
    };
  };

  const value = {
    // 狀態
    isAuthenticated: state.isAuthenticated,
    user: state.user,
    token: state.token,
    loading: state.loading,
    error: state.error,
    
    // 方法
    login,
    logout,
    updateUser,
    clearError,
    getAuthHeaders,
    isTokenValid: () => isTokenValid(state.token)
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook 來使用 AuthContext
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth 必須在 AuthProvider 內使用');
  }
  return context;
};

export default AuthContext;
