const isTokenExpired = (token) => {
  if (!token) return true;
  
  const parts = token.split('.');
  if (parts.length !== 3) return true;
  
  const payload = JSON.parse(atob(parts[1]));
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

