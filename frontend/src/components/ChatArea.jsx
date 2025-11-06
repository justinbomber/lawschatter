import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import './ChatArea.css';
import RagSelector from './RagSelector.jsx';
import ReferencePanel from './ReferencePanel.jsx';

const ChatArea = ({ messages, sidebarCollapsed, onSendMessage, isLoading }) => {
  const { t } = useTranslation();
  const [inputMessage, setInputMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState('GPT-4');
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [showRagSelector, setShowRagSelector] = useState(false);
  const [hasRagSettings, setHasRagSettings] = useState(false);
  const [isInitialState, setIsInitialState] = useState(true);

  const [showReferencePanel, setShowReferencePanel] = useState(false);
  const [currentReferences, setCurrentReferences] = useState([]);

  // 檢查是否還在初始狀態（沒有任何消息）
  useEffect(() => {
    if (messages.length > 0 && isInitialState) {
      setIsInitialState(false);
    } else if (messages.length === 0 && !isInitialState) {
      setIsInitialState(true);
    }
  }, [messages, isInitialState]);
  const messagesEndRef = useRef(null);
  const chatMessagesRef = useRef(null);
  const inputRef = useRef(null);

  // 檢查是否有有效的RAG設定
  useEffect(() => {
    const checkRagSettings = () => {
      const savedSettings = localStorage.getItem('ragSettings');
      if (savedSettings) {
        try {
          const settings = JSON.parse(savedSettings);
          // 檢查是否有選擇任何法律領域或設定時間範圍
          const hasCollections = settings.selectedCollections && settings.selectedCollections.length > 0;
          const hasDateRange = settings.startDate || settings.endDate;
          setHasRagSettings(hasCollections || hasDateRange);
        } catch (error) {
          console.warn('無法解析RAG設定:', error);
          setHasRagSettings(false);
        }
      } else {
        setHasRagSettings(false);
      }
    };
    
    checkRagSettings();
    // 監聽 storage 事件以便在其他標籤頁更新設定時同步
    window.addEventListener('storage', checkRagSettings);
    
    return () => {
      window.removeEventListener('storage', checkRagSettings);
    };
  }, []);

  const models = [
    { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI' },
    { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'OpenAI' },
    { id: 'gpt-5', name: 'gpt-5', provider: 'OpenAI' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI' }
  ];

  // 自動滾動到底部
  const scrollToBottom = () => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTo({
        top: chatMessagesRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  // 當訊息更新時自動滾動到底部
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (inputMessage.trim() && onSendMessage) {
      // 如果是初始狀態，直接設定為非初始狀態
      if (isInitialState) {
        setIsInitialState(false);
      }
      
      onSendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleWrapperClick = (e) => {
    // 避免點擊按鈕時觸發聚焦
    if (e.target.closest('.input-actions')) {
      return;
    }
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const MessageActions = ({ messageType, messageId, hasReferences }) => {
    if (messageType === 'user') {
      return (
        <div className="message-actions">
          <button className="action-btn" title={t('chat.actions.edit')}>
            <i className="fas fa-edit"></i>
          </button>
          <button className="action-btn" title={t('chat.actions.delete')}>
            <i className="fas fa-trash"></i>
          </button>
          <button className="action-btn" title={t('chat.actions.share')}>
            <i className="fas fa-share"></i>
          </button>
        </div>
      );
    } else {
      return (
        <div className="message-actions">
          {hasReferences && (
            <button 
              className="action-btn reference-btn" 
              title="查看參考資料"
              onClick={() => handleShowReferences(messageId)}
            >
              <i className="fas fa-external-link-alt"></i>
              參考資料
            </button>
          )}
          <button className="action-btn" title={t('chat.actions.copy')}>
            <i className="fas fa-copy"></i>
          </button>
          <button className="action-btn" title={t('chat.actions.regenerate')}>
            <i className="fas fa-redo"></i>
          </button>
          <button className="action-btn" title={t('chat.actions.edit')}>
            <i className="fas fa-edit"></i>
          </button>
          <button className="action-btn" title={t('chat.actions.share')}>
            <i className="fas fa-share"></i>
          </button>
          <div className="rating-actions">
            <button className="action-btn" title={t('chat.actions.rate')}>
              <i className="fas fa-thumbs-up"></i>
            </button>
            <button className="action-btn" title={t('chat.actions.rate')}>
              <i className="fas fa-thumbs-down"></i>
            </button>
          </div>
          <div className="dropdown">
            <button className="action-btn dropdown-toggle" title={t('chat.actions.more')}>
              <i className="fas fa-ellipsis-h"></i>
            </button>
            <div className="dropdown-menu">
              <button className="dropdown-item">
                <i className="fas fa-language"></i>
                {t('chat.actions.translate')}
              </button>
              <button className="dropdown-item">
                <i className="fas fa-save"></i>
                {t('chat.actions.save')}
              </button>
              <button className="dropdown-item">
                <i className="fas fa-flag"></i>
                {t('chat.actions.report')}
              </button>
            </div>
          </div>
        </div>
      );
    }
  };

  const handleModelSelect = (model) => {
    setSelectedModel(model.name);
    setShowModelDropdown(false);
  };

  const handleShowReferences = (messageId) => {
    // 模擬獲取該訊息的參考資料
    // 實際應該從訊息資料中取得對應的references
    const sampleReferences = [
      'https://www.judicial.gov.tw/tw/np-117-1.html'
    ];
    setCurrentReferences(sampleReferences);
    setShowReferencePanel(true);
  };

  return (
    <div className={`chat-area ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="chat-main-content">
        <div className="chat-header">
          <div className="model-selector">
            <button 
              className="model-selector-btn"
              onClick={() => setShowModelDropdown(!showModelDropdown)}
            >
              <div className="model-info">
                <span className="model-icon">🤖</span>
                <span className="model-name">{selectedModel}</span>
              </div>
              <i className={`fas fa-chevron-${showModelDropdown ? 'up' : 'down'}`}></i>
            </button>
            
            {showModelDropdown && (
              <div className="model-dropdown">
                <div className="dropdown-header">
                  <input 
                    type="text" 
                    placeholder="搜尋模型..." 
                    className="model-search"
                  />
                </div>
                <div className="model-list">
                  {models.map(model => (
                    <button
                      key={model.id}
                      className={`model-item ${selectedModel === model.name ? 'selected' : ''}`}
                      onClick={() => handleModelSelect(model)}
                    >
                      <div className="model-provider">
                        <span className="provider-logo">
                          {model.provider === 'OpenAI' && '🔶'}
                          {model.provider === 'xAI' && '❌'}
                          {model.provider === 'Anthropic' && '🟣'}
                          {model.provider === 'Google' && '🟢'}
                        </span>
                        <span className="provider-name">{model.provider}</span>
                      </div>
                      <span className="model-name">{model.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* 歡迎語區域 - 僅在初始狀態顯示 */}
        {isInitialState && (
          <div className="welcome-area">
            <div className="welcome-text">
              Welcome to Laws Chatter! Enjoy your experience.
            </div>
          </div>
        )}

        <div className="chat-messages" ref={chatMessagesRef}>
                  {messages.map(message => {
          // 檢查是否為AI回答且用戶有設定RAG
          const hasReferences = message.type === 'assistant' && hasRagSettings;
          
          return (
            <div key={message.id} className={`message ${message.type} message-container`}>
              <div className="message-header">
                <div className="message-avatar">
                  {message.type === 'user' ? (
                    <div className="avatar user-avatar" style={{ backgroundColor: '#10a37f' }}>
                      JU
                    </div>
                  ) : (
                    <div className="avatar ai-avatar">
                      🤖
                    </div>
                  )}
                </div>
                <div className="message-user-name">
                  {message.type === 'user' ? 'User' : 'AI Assistant'}
                </div>
              </div>
              <div className="message-bubble">
                <div className="message-content">
                  {/* 顯示狀態訊息（灰色） */}
                  {message.statusMessages && message.statusMessages.length > 0 && (
                    <div className="status-messages">
                      {message.statusMessages.map((status, idx) => (
                        <div key={idx} className="status-message">
                          {status}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* 顯示主要內容 */}
                  <div className="message-text">
                    {message.type === 'assistant' ? (
                      <>
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          rehypePlugins={[rehypeRaw]}
                          components={{
                            code({node, inline, className, children, ...props}) {
                              return inline ? (
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              ) : (
                                <pre>
                                  <code className={className} {...props}>
                                    {children}
                                  </code>
                                </pre>
                              );
                            }
                          }}
                        >
                          {message.content || t(message.contentKey)}
                        </ReactMarkdown>
                        {message.isStreaming && <span className="streaming-cursor">▊</span>}
                      </>
                    ) : (
                      message.content || t(message.contentKey)
                    )}
                  </div>
                  <div className="message-timestamp">{message.timestamp}</div>
                </div>
                <MessageActions 
                  messageType={message.type} 
                  messageId={message.id}
                  hasReferences={hasReferences}
                />
              </div>
            </div>
          );
        })}
        
        {isLoading && (
          <div className="message assistant message-container">
            <div className="message-header">
              <div className="message-avatar">
                <div className="avatar ai-avatar">
                  🤖
                </div>
              </div>
              <div className="message-user-name">
                AI Assistant
              </div>
            </div>
            <div className="message-bubble">
              <div className="message-content">
                <div className="message-text">
                  <div className="typing-indicator">
                    <div className="dot"></div>
                    <div className="dot"></div>
                    <div className="dot"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
          <div ref={messagesEndRef} />
        </div>
        
        <div className={`chat-input-container ${
          isInitialState ? 'initial-state' : 'conversation-state'
        }`}>
          <div className="chat-input-wrapper" onClick={handleWrapperClick}>
            <textarea
              ref={inputRef}
              className="chat-input"
              placeholder={t('chat.inputPlaceholder')}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              rows={1}
            />
            <div className="input-actions">
              <button className="input-action-btn" title="附件">
                <i className="fas fa-paperclip"></i>
              </button>
              <button className="input-action-btn" title="語音輸入">
                <i className="fas fa-microphone"></i>
              </button>
              <button 
                className={`input-action-btn ${hasRagSettings ? 'active' : ''}`} 
                title="法律資料庫設定"
                onClick={() => setShowRagSelector(true)}
              >
                <i className="fas fa-balance-scale"></i>
              </button>
              <button 
                className="send-btn"
                onClick={handleSendMessage}
                disabled={!inputMessage.trim()}
              >
                <i className="fas fa-paper-plane"></i>
              </button>
            </div>
          </div>
        </div>
        
        {showRagSelector && (
          <RagSelector onClose={(settings) => {
            setShowRagSelector(false);
            // 無論是否保存設定，都重新檢查RAG設定狀態
            const savedSettings = localStorage.getItem('ragSettings');
            if (savedSettings) {
              try {
                const parsedSettings = JSON.parse(savedSettings);
                const hasCollections = parsedSettings.selectedCollections && parsedSettings.selectedCollections.length > 0;
                const hasDateRange = parsedSettings.startDate || parsedSettings.endDate;
                setHasRagSettings(hasCollections || hasDateRange);
              } catch (error) {
                setHasRagSettings(false);
              }
            } else {
              setHasRagSettings(false);
            }
          }} />
        )}
      </div>
      
      <ReferencePanel 
        isOpen={showReferencePanel}
        onClose={() => setShowReferencePanel(false)}
        references={currentReferences}
      />
    </div>
  );
};

export default ChatArea;
