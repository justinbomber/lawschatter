import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import './Login.css';
import Footer from './Footer';
import { useAuth } from '../contexts/AuthContext';
import { authAPI } from '../api';

function Login({ onLogin, onSwitchToRegister }) {
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
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    // 直接跳轉到聊天界面，不做任何端點驗證
    setTimeout(() => {
      if (onLogin) {
        onLogin();
      }
      setLoading(false);
    }, 500);
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
                className="form-input"
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
                className="form-input"
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
              onClick={onSwitchToRegister}
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
