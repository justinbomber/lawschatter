import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import './Login.css';
import Footer from './Footer.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import { authAPI } from '../api';

function Register() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { login, clearError, error: authError } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [generalError, setGeneralError] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // 清除錯誤信息
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.name.trim()) {
      newErrors.name = t('auth.register.errors.nameRequired', '姓名為必填項目');
    }
    
    if (!formData.email.trim()) {
      newErrors.email = t('auth.register.errors.emailRequired', '電子郵件為必填項目');
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = t('auth.register.errors.emailInvalid', '請輸入有效的電子郵件地址');
    }
    
    if (!formData.password) {
      newErrors.password = t('auth.register.errors.passwordRequired', '密碼為必填項目');
    } else if (formData.password.length < 6) {
      newErrors.password = t('auth.register.errors.passwordLength', '密碼至少需要6個字符');
    }
    
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = t('auth.register.errors.passwordMismatch', '確認密碼不匹配');
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    setGeneralError('');
    clearError();
    
    try {
      // 使用 Supabase Auth API 註冊
      const result = await authAPI.register({
        email: formData.email,
        password: formData.password,
        username: formData.name, // 使用 name 作為 username
        display_name: formData.name // 使用 name 作為 display_name
      });
      
      if (result.success) {
        // 檢查是否有 access_token (自動登入)
        if (result.data.access_token) {
          // 註冊成功並自動登入
          const loginSuccess = login(result.data);
          if (loginSuccess) {
            console.log('註冊並登入成功:', result.data);
            navigate('/c/new');
          } else {
            setGeneralError('註冊成功，但登入失敗，請手動登入');
          }
        } else if (result.data.message) {
          console.log('註冊成功，需要驗證 email');
          setGeneralError(result.data.message);
          setTimeout(() => navigate('/login'), 3000);
        } else {
          console.log('註冊成功，請登入');
          setGeneralError('註冊成功！請使用您的帳戶登入');
          setTimeout(() => navigate('/login'), 2000);
        }
      } else {
        // API 已統一處理錯誤訊息
        setGeneralError(result.error || '註冊失敗，請稍後再試');
      }
    } catch (error) {
      // 未預期的錯誤
      console.error('註冊失敗:', error);
      setGeneralError('註冊失敗，請稍後再試');
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
            <h1 className="login-title">{t('auth.register.title', '建立新帳戶')}</h1>
            <p className="login-subtitle">{t('auth.register.subtitle', '加入我們，開始您的AI助手之旅')}</p>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="name" className="form-label">
                {t('auth.register.name', '姓名')}
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className={`form-input ${errors.name ? 'error' : ''}`}
                placeholder={t('auth.register.namePlaceholder', '請輸入您的姓名')}
                required
              />
              {errors.name && <span className="error-message">{errors.name}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="email" className="form-label">
                {t('auth.register.email', '電子郵件')}
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className={`form-input ${errors.email ? 'error' : ''}`}
                placeholder={t('auth.register.emailPlaceholder', '請輸入您的電子郵件')}
                required
              />
              {errors.email && <span className="error-message">{errors.email}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="password" className="form-label">
                {t('auth.register.password', '密碼')}
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className={`form-input ${errors.password ? 'error' : ''}`}
                placeholder={t('auth.register.passwordPlaceholder', '請輸入密碼 (至少6個字符)')}
                required
              />
              {errors.password && <span className="error-message">{errors.password}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword" className="form-label">
                {t('auth.register.confirmPassword', '確認密碼')}
              </label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                className={`form-input ${errors.confirmPassword ? 'error' : ''}`}
                placeholder={t('auth.register.confirmPasswordPlaceholder', '請再次輸入密碼')}
                required
              />
              {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
            </div>

            <div className="form-group">
              <label className="checkbox-container">
                <input type="checkbox" className="checkbox-input" required />
                <span className="checkbox-checkmark"></span>
                <span className="checkbox-label">
                  {t('auth.register.terms', '我同意')}
                  <a href="#" className="terms-link">{t('auth.register.termsLink', '服務條款')}</a>
                  {t('auth.register.and', '和')}
                  <a href="#" className="terms-link">{t('auth.register.privacyLink', '隱私政策')}</a>
                </span>
              </label>
            </div>

            {(generalError || authError) && (
              <div className="form-error">
                {generalError || authError}
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
                t('auth.register.submit', '建立帳戶')
              )}
            </button>
          </form>

          <div className="login-divider">
            <span>{t('auth.register.or', '或')}</span>
          </div>

          <div className="social-login">
            <button className="social-button google">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              {t('auth.register.google', '使用 Google 註冊')}
            </button>
          </div>

          <div className="register-prompt">
            <span>{t('auth.register.hasAccount', '已經有帳戶了？')}</span>
            <button 
              type="button" 
              className="register-link"
              onClick={() => navigate('/login')}
            >
              {t('auth.register.signIn', '立即登入')}
            </button>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}

export default Register;
