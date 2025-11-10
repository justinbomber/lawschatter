import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import './Login.css';
import Footer from './Footer.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import { authAPI } from '../api';

function Login() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { login, clearError, error: authError } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // 清除錯誤訊息
    if (error) {
      setError('');
    }
    if (authError) {
      clearError();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // 基本驗證
    if (!formData.email.trim()) {
      setError('請輸入電子郵件');
      return;
    }
    
    if (!formData.password) {
      setError('請輸入密碼');
      return;
    }
    
    setLoading(true);
    setError('');
    clearError();
    
    try {
      // 使用 Supabase Auth API 登入
      const result = await authAPI.login({
        email: formData.email.trim(),
        password: formData.password
      });
      
      if (result.success) {
        // 登入成功，使用 AuthContext 的 login 函數
        const loginSuccess = login(result.data);
        if (loginSuccess) {
          console.log('登入成功:', result.data);
          navigate('/c/new');
        } else {
          setError('登入資料處理失敗，請重試');
        }
      } else {
        // 登入失敗，顯示錯誤訊息
        const errorMsg = result.error || '登入失敗';
        
        // 根據錯誤狀態碼提供更友好的錯誤訊息
        if (result.status === 400) {
          setError('電子郵件或密碼格式不正確');
        } else if (result.status === 401) {
          setError('電子郵件或密碼錯誤，請檢查後重試');
        } else if (result.status === 404) {
          setError('此電子郵件尚未註冊，請先註冊');
        } else if (errorMsg.includes('Invalid login credentials')) {
          setError('電子郵件或密碼錯誤，請檢查後重試');
        } else if (errorMsg.includes('Email not confirmed')) {
          setError('請先確認您的電子郵件後再登入');
        } else if (errorMsg.includes('not found') || errorMsg.includes('User not found')) {
          setError('此電子郵件尚未註冊，請先註冊');
        } else {
          setError(errorMsg);
        }
      }
    } catch (error) {
      // 未預期的錯誤
      console.error('登入失敗:', error);
      setError('無法連接到伺服器，請檢查網路連接');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="gradient-orb orb-1"></div>
        <div className="gradient-orb orb-2"></div>
        <div className="gradient-orb orb-3"></div>
      </div>
      
      <div className="login-content">
        <div className="login-card">
          <div className="login-header">
            <h1 className="login-title">{t('auth.login.title', 'AI 聊天助手')}</h1>
            <p className="login-subtitle">{t('auth.login.subtitle', '歡迎回來，請登入您的帳戶')}</p>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="email" className="form-label">
                {t('auth.login.email', '電子郵件')}
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className={`form-input ${(error || authError) ? 'error' : ''}`}
                placeholder={t('auth.login.emailPlaceholder', '請輸入您的電子郵件')}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="password" className="form-label">
                {t('auth.login.password', '密碼')}
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className={`form-input ${(error || authError) ? 'error' : ''}`}
                placeholder={t('auth.login.passwordPlaceholder', '請輸入您的密碼')}
                required
              />
            </div>

            <div className="form-options">
              <label className="checkbox-container">
                <input type="checkbox" className="checkbox-input" />
                <span className="checkbox-checkmark"></span>
                <span className="checkbox-label">{t('auth.login.remember', '記住我')}</span>
              </label>
              <a href="#" className="forgot-password">
                {t('auth.login.forgot', '忘記密碼？')}
              </a>
            </div>

            {(error || authError) && (
              <div className="form-error">
                {error || authError}
              </div>
            )}

            <button 
              type="submit" 
              className={`login-button ${loading ? 'loading' : ''}`}
              disabled={loading}
            >
              {loading ? (
                <div className="loading-spinner"></div>
              ) : (
                t('auth.login.submit', '登入')
              )}
            </button>
          </form>

          <div className="login-divider">
            <span>{t('auth.login.or', '或')}</span>
          </div>

          <div className="social-login">
            <button className="social-button google">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              {t('auth.login.google', '使用 Google 登入')}
            </button>
          </div>

          <div className="register-prompt">
            <span>{t('auth.login.noAccount', '還沒有帳戶？')}</span>
            <button 
              type="button" 
              className="register-link"
              onClick={() => navigate('/register')}
            >
              {t('auth.login.signUp', '立即註冊')}
            </button>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}

export default Login;
