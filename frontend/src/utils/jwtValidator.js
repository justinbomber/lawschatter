// 解碼 Base64url（JWT 使用的編碼格式）
const decodeBase64Url = (str) => {
  if (!str || typeof str !== 'string') return null;
  
  // 移除可能的空白字符
  let base64 = str.trim();
  
  // 將 Base64url 轉換為標準 Base64
  base64 = base64.replace(/-/g, '+').replace(/_/g, '/');
  
  // 移除非 Base64 字符
  base64 = base64.replace(/[^A-Za-z0-9+/]/g, '');
  
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

// 安全解析 JWT payload
const safeParseJWTPayload = (token) => {
  if (!token || typeof token !== 'string') return null;
  
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  
  // 驗證 payload 部分是否有效
  const payloadPart = parts[1];
  if (!payloadPart || payloadPart.length < 4) return null;
  
  // 安全解碼
  let decoded;
  let base64 = payloadPart.trim().replace(/-/g, '+').replace(/_/g, '/');
  base64 = base64.replace(/[^A-Za-z0-9+/]/g, '');
  const padding = base64.length % 4;
  if (padding) base64 += '='.repeat(4 - padding);
  
  // 使用 atob 解碼
  let binaryString;
  try {
    binaryString = atob(base64);
  } catch (e) {
    return null;
  }
  
  // 處理 UTF-8
  try {
    decoded = decodeURIComponent(
      binaryString.split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
    );
  } catch (e) {
    // 如果 UTF-8 解碼失敗，使用原始字串
    decoded = binaryString;
  }
  
  // 解析 JSON
  try {
    return JSON.parse(decoded);
  } catch (e) {
    return null;
  }
};

const isTokenExpired = (token) => {
  if (!token) return true;
  
  const payload = safeParseJWTPayload(token);
  if (!payload || !payload.exp) return true;
  
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

