import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getUserInitials, getUserDisplayName, getAvatarColor } from '../utils/userUtils';
import './ChatArea.css';
import RagSelector from './RagSelector.jsx';
import ReferencePanel from './ReferencePanel.jsx';
import * as MarkdownComponents from './MarkdownComponents.jsx';

const ChatArea = ({ messages, sidebarCollapsed, onSendMessage, isLoading }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [inputMessage, setInputMessage] = useState('');
  const [showRagSelector, setShowRagSelector] = useState(false);
  const [hasRagSettings, setHasRagSettings] = useState(false);
  const [isInitialState, setIsInitialState] = useState(true);

  const [showReferencePanel, setShowReferencePanel] = useState(false);
  const [currentReferences, setCurrentReferences] = useState([]);
  const [copiedMessageId, setCopiedMessageId] = useState(null);

  // 檢查是否還在初始狀態（沒有任何消息）
  useEffect(() => {
    if (messages.length > 0 && isInitialState) {
      setIsInitialState(false);
    } else if (messages.length === 0) {
      // 當訊息為空時（包括有錯誤訊息後按新增對話），立即回到初始狀態
      setIsInitialState(true);
    }
  }, [messages.length]);
  const messagesEndRef = useRef(null);
  const chatMessagesRef = useRef(null);
  const inputRef = useRef(null);
  const inputContainerRef = useRef(null);

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

  // 自動滾動到底部
  const scrollToBottom = () => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTo({
        top: chatMessagesRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  // 僅在最後一則為「使用者」訊息時才自動捲動到底部（LLM 回答時不強制定位最底）
  useEffect(() => {
    const lastMessage = messages && messages.length > 0 ? messages[messages.length - 1] : null;
    if (!lastMessage) {
      return;
    }
    if (lastMessage.type === 'user') {
      scrollToBottom();
    }
  }, [messages]);

  const handleSendMessage = () => {
    if (inputMessage.trim() && onSendMessage) {
      // 如果是初始狀態，直接設定為非初始狀態
      if (isInitialState) {
        setIsInitialState(false);
      }
      
      onSendMessage(inputMessage.trim());
      setInputMessage('');
      
      // 重置 textarea 高度
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
      }
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
    if (e.target.closest('.input-actions-row')) {
      return;
    }
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  // 自動調整 textarea 高度
  const adjustTextareaHeight = () => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    }
  };

  // 當輸入內容變化時自動調整高度
  useEffect(() => {
    adjustTextareaHeight();
  }, [inputMessage]);

  // 複製訊息內容
  const copyMessageContent = (messageId) => {
    const targetMessage = (messages || []).find(m => m.id === messageId);
    if (!targetMessage) {
      return;
    }
    const text = (typeof targetMessage.content === 'string' && targetMessage.content.trim())
      ? targetMessage.content
      : (targetMessage.contentKey ? t(targetMessage.contentKey) : '');
    if (!text) {
      return;
    }
    let usedClipboardApi = false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text);
      usedClipboardApi = true;
    }
    if (!usedClipboardApi) {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'absolute';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    setCopiedMessageId(messageId);
    setTimeout(() => {
      setCopiedMessageId(null);
    }, 1000);
  };

  const MessageActions = ({ messageType, messageId, hasReferences }) => {
    if (messageType === 'user') {
      return (
        <div className="message-actions">
          <button 
            className={`action-btn ${copiedMessageId === messageId ? 'copied' : ''}`} 
            title={copiedMessageId === messageId ? t('chat.actions.copied') || '已複製' : t('chat.actions.copy')}
            onClick={() => copyMessageContent(messageId)}
            disabled={copiedMessageId === messageId}
          >
            <i className={copiedMessageId === messageId ? 'fas fa-check' : 'fas fa-copy'}></i>
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
          <button 
            className={`action-btn ${copiedMessageId === messageId ? 'copied' : ''}`} 
            title={copiedMessageId === messageId ? t('chat.actions.copied') || '已複製' : t('chat.actions.copy')}
            onClick={() => copyMessageContent(messageId)}
            disabled={copiedMessageId === messageId}
          >
            <i className={copiedMessageId === messageId ? 'fas fa-check' : 'fas fa-copy'}></i>
          </button>
          <button className="action-btn" title={t('chat.actions.regenerate')}>
            <i className="fas fa-redo"></i>
          </button>
          <div className="rating-actions">
            <button className="action-btn" title={t('chat.actions.rate')}>
              <i className="fas fa-thumbs-up"></i>
            </button>
            <button className="action-btn" title={t('chat.actions.rate')}>
              <i className="fas fa-thumbs-down"></i>
            </button>
          </div>
          <button className="action-btn" title={t('chat.actions.report')}>
            <i className="fas fa-flag"></i>
          </button>
        </div>
      );
    }
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

  // 獲取用戶顯示資訊
  const userDisplayName = getUserDisplayName(user);
  const userInitials = getUserInitials(user?.display_name, user?.username, user?.email);
  const avatarColor = getAvatarColor(user?.user_id || user?.email);

  return (
    <div className={`chat-area ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="chat-main-content">
        <div className={`content-wrapper ${isInitialState ? 'landing-layout' : 'conversation-layout'}`}>
          {/* 訊息顯示區域 */}
          {!isInitialState && (
            <div className="messages-view">
              <div className="messages-outer">
                <div className="messages-inner">
                  <div className="messages-scroll" ref={chatMessagesRef}>
                    <div className="messages-list">
                  {messages.map(message => {
          // 檢查是否為AI回答且用戶有設定RAG
          const hasReferences = message.type === 'assistant' && hasRagSettings;
          
          return (
            <div key={message.id} className={`message ${message.type} message-container`}>
              <div className="message-header">
                <div className="message-avatar">
                  {message.type === 'user' ? (
                    <div className="avatar user-avatar" style={{ backgroundColor: avatarColor }}>
                      {userInitials}
                    </div>
                  ) : (
                    <div className="avatar ai-avatar">
                      <i className="fas fa-balance-scale"></i>
                    </div>
                  )}
                </div>
                <div className="message-user-name">
                  {message.type === 'user' ? userDisplayName : 'lawschatter'}
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
                            p: MarkdownComponents.p,
                            code: MarkdownComponents.code,
                            a: MarkdownComponents.a,
                            h1: MarkdownComponents.h1,
                            h2: MarkdownComponents.h2,
                            h3: MarkdownComponents.h3,
                            h4: MarkdownComponents.h4,
                            ul: MarkdownComponents.ul,
                            ol: MarkdownComponents.ol,
                            li: MarkdownComponents.li,
                            blockquote: MarkdownComponents.blockquote,
                            table: MarkdownComponents.table,
                            thead: MarkdownComponents.thead,
                            tbody: MarkdownComponents.tbody,
                            tr: MarkdownComponents.tr,
                            th: MarkdownComponents.th,
                            td: MarkdownComponents.td,
                            hr: MarkdownComponents.hr,
                            strong: MarkdownComponents.strong,
                            em: MarkdownComponents.em,
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
        
                      <div ref={messagesEndRef} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* 輸入框區域包裝 */}
          <div className={`input-form-wrapper ${isInitialState ? 'landing-state' : 'conversation-state'}`}>
            {isInitialState && (
              <div className="welcome-message">
                <div className="welcome-text">
                  Welcome to Laws Chatter! Enjoy your experience.
                </div>
              </div>
            )}
            
            <div className="chat-input-container" ref={inputContainerRef}>
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
                <div className="input-actions-row">
                  <div className="left-actions">
                    <button className="input-action-btn" title="附件">
                      <i className="fas fa-paperclip"></i>
                    </button>
                    <button 
                      className={`input-action-btn ${hasRagSettings ? 'active' : ''}`} 
                      title="法律資料庫設定"
                      onClick={() => setShowRagSelector(true)}
                    >
                      <i className="fas fa-balance-scale"></i>
                    </button>
                  </div>
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
