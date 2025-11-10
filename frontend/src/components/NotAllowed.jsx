import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import './NotAllowed.css';

function NotAllowed({ message, countdown = 3 }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [seconds, setSeconds] = useState(countdown);

  useEffect(() => {
    if (seconds === 0) {
      navigate('/c/new');
      return;
    }

    const timer = setTimeout(() => {
      setSeconds(seconds - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [seconds, navigate]);

  const handleGoBack = () => {
    navigate('/c/new');
  };

  return (
    <div className="not-allowed-container">
      <div className="not-allowed-content">
        <div className="not-allowed-icon">🚫</div>
        <h2>{t('notAllowed.title')}</h2>
        <p className="not-allowed-message">
          {message || t('notAllowed.defaultMessage')}
        </p>
        <p className="not-allowed-countdown">
          {t('notAllowed.redirecting', { seconds })}
        </p>
        <button className="not-allowed-button" onClick={handleGoBack}>
          {t('notAllowed.goBack')}
        </button>
      </div>
    </div>
  );
}

export default NotAllowed;

