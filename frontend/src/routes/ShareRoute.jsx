import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import NotAllowed from '../components/NotAllowed.jsx';
import Footer from '../components/Footer.jsx';
import { supabaseConversationAPI } from '../api/supabaseConversation';
import * as MarkdownComponents from '../components/MarkdownComponents.jsx';
import './ShareRoute.css';

function ShareRoute() {
  const { shareId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  
  const [shareMeta, setShareMeta] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSharedConversation();
  }, [shareId]);

  const loadSharedConversation = async () => {
    console.log('ShareRoute: 載入分享對話', shareId);
    setIsLoading(true);
    setNotFound(false);
    setError('');

    const meta = await supabaseConversationAPI.getShareMeta(shareId)
      .catch(err => {
        console.error('ShareRoute: 載入分享元資料失敗', err);
        return null;
      });

    if (!meta) {
      console.error('ShareRoute: 未找到分享對話');
      setNotFound(true);
      setError(t('share.notFound'));
      setIsLoading(false);
      return;
    }

    console.log('ShareRoute: 分享元資料', meta);
    setShareMeta(meta);

    const msgs = await supabaseConversationAPI.getShareMessages(shareId)
      .catch(err => {
        console.error('ShareRoute: 載入分享訊息失敗', err);
        return [];
      });

    console.log('ShareRoute: 載入訊息數量', msgs.length);
    setMessages(msgs);
    setIsLoading(false);
  };

  const handleGoHome = () => {
    navigate('/c/new');
  };

  if (notFound) {
    return <NotAllowed message={error} />;
  }

  if (isLoading) {
    return (
      <div className="share-loading">
        <div className="loading-spinner"></div>
        <p>{t('share.loading')}</p>
      </div>
    );
  }

  return (
    <div className="share-container">
      <div className="share-header">
        <div className="share-header-content">
          <div className="share-title-section">
            <h1 className="share-title">{shareMeta?.title || t('share.untitled')}</h1>
            <span className="share-badge">{t('share.sharedConversation')}</span>
          </div>
          <button className="share-home-btn" onClick={handleGoHome}>
            <i className="fas fa-rocket"></i>
            <span>{t('share.tryIt')}</span>
          </button>
        </div>
      </div>

      <div className="share-content">
        <div className="share-messages">
          {messages.length === 0 ? (
            <div className="share-empty">
              <i className="fas fa-comments"></i>
              <p>{t('share.noMessages')}</p>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className={`share-message ${message.type}`}>
                <div className="message-avatar">
                  {message.type === 'user' ? (
                    <i className="fas fa-user"></i>
                  ) : (
                    <i className="fas fa-balance-scale"></i>
                  )}
                </div>
                <div className="message-content">
                  <div className="message-header">
                    <span className="message-sender">
                      {message.type === 'user' ? t('share.user') : t('share.assistant')}
                    </span>
                    <span className="message-time">{message.timestamp}</span>
                  </div>
                  <div className="message-text">
                    {message.type === 'assistant' ? (
                      <ReactMarkdown components={MarkdownComponents}>
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      message.content
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <Footer />
    </div>
  );
}

export default ShareRoute;

