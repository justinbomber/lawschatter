// 解碼 Base64url（JWT 使用的編碼格式）
const decodeBase64Url = (str) => {
  // 將 Base64url 轉換為標準 Base64
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/');
  
  // 添加填充（padding）
  const padding = base64.length % 4;
  if (padding) {
    base64 += '='.repeat(4 - padding);
  }
  
  // 解碼並處理 UTF-8
  const decoded = atob(base64);
  return decodeURIComponent(
    decoded.split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
  );
};

const isTokenExpired = (token) => {
  if (!token) return true;
  
  const parts = token.split('.');
  if (parts.length !== 3) return true;
  
  const payload = JSON.parse(decodeBase64Url(parts[1]));
  const currentTime = Date.now() / 1000;
  
  return payload.exp <= currentTime;
};

const handleExpiredToken = () => {
  localStorage.removeItem('supabase_access_token');
  localStorage.removeItem('supabase_refresh_token');
  localStorage.removeItem('supabase_user_data');
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_data');
  
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
};

export const validateTokenBeforeRequest = () => {
  const token = localStorage.getItem('supabase_access_token');
  
  if (isTokenExpired(token)) {
    handleExpiredToken();
    return false;
  }
  
  return true;
};

export const getValidToken = () => {
  const token = localStorage.getItem('supabase_access_token');
  
  if (isTokenExpired(token)) {
    handleExpiredToken();
    return null;
  }
  
  return token;
};

