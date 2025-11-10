import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import '../App.css';
import Sidebar from '../components/Sidebar.jsx';
import ChatArea from '../components/ChatArea.jsx';
import SettingsPopup from '../components/SettingsPopup.jsx';
import NotAllowed from '../components/NotAllowed.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import { chatAPI } from '../api/chat';
import { supabaseConversationAPI } from '../api/supabaseConversation';

function ChatRoute() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { logout: authLogout } = useAuth();
  
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);
  const [accessDeniedMessage, setAccessDeniedMessage] = useState('');

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (conversationId && conversationId !== 'new') {
      loadConversationById(conversationId);
    } else {
      setSelectedConversation(null);
      setMessages([]);
      setAccessDenied(false);
    }
  }, [conversationId]);

  const loadConversations = async () => {
    setConversationsLoading(true);
    const convs = await supabaseConversationAPI.getConversations();
    setConversations(convs);
    setConversationsLoading(false);
  };

  const loadConversationById = async (convId) => {
    const conv = await supabaseConversationAPI.getConversationById(convId)
      .catch(error => {
        if (error.response?.status === 403 || error.response?.status === 404) {
          setAccessDenied(true);
          setAccessDeniedMessage(
            error.response.status === 403 
              ? t('notAllowed.forbidden')
              : t('notAllowed.notFound')
          );
          return null;
        }
        throw error;
      });

    if (!conv) {
      if (!accessDenied) {
        setAccessDenied(true);
        setAccessDeniedMessage(t('notAllowed.notFound'));
      }
      return;
    }

    setSelectedConversation(conv);
    await loadConversationMessages(convId);
    await supabaseConversationAPI.updateRecentConversation(convId);
  };

  const loadConversationMessages = async (convId) => {
    const msgs = await supabaseConversationAPI.getConversationMessages(convId)
      .catch(error => {
        if (error.response?.status === 403 || error.response?.status === 404) {
          return [];
        }
        throw error;
      });
    setMessages(msgs);
  };

  const handleSelectConversation = (conversation) => {
    navigate(`/c/${conversation.conversation_id}`);
  };

  const handleNewConversation = () => {
    navigate('/c/new');
  };

  const handleRenameConversation = async (convId, newTitle) => {
    await supabaseConversationAPI.updateConversationTitle(convId, newTitle);
    setConversations(prev => prev.map(conv => 
      conv.conversation_id === convId 
        ? { ...conv, title: newTitle }
        : conv
    ));
    if (selectedConversation?.conversation_id === convId) {
      setSelectedConversation(prev => ({ ...prev, title: newTitle }));
    }
  };

  const handleDeleteConversation = async (convId) => {
    await supabaseConversationAPI.deleteConversation(convId);
    setConversations(prev => prev.filter(conv => conv.conversation_id !== convId));
    
    if (selectedConversation?.conversation_id === convId) {
      navigate('/c/new');
    }
  };

  const handleShareConversation = async (convId) => {
    console.log('分享對話:', convId);
    const share = await supabaseConversationAPI.createShare(convId)
      .catch(error => {
        console.error('分享對話失敗:', error);
        alert('分享對話失敗，請稍後再試');
        return null;
      });
    
    if (!share) {
      return null;
    }
    
    console.log('分享成功:', share);
    return share.share_id;
  };

  const handleSendMessage = async (message) => {
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      return;
    }

    const trimmedMessage = message.trim();
    
    if (trimmedMessage.length > 5000) {
      const errorResponse = {
        id: Date.now(),
        type: 'assistant',
        content: t('chat.messageTooLong'),
        timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorResponse]);
      return;
    }

    const currentConversation = selectedConversation;
    const isNewConversation = !currentConversation;
    
    const timestamp = new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });
    
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: trimmedMessage,
      timestamp: timestamp
    };
    
    setMessages(prev => [...prev, userMessage]);
    
    const aiMessageId = Date.now() + 1;
    const aiMessage = {
      id: aiMessageId,
      type: 'assistant',
      content: '',
      statusMessages: [],
      isStreaming: true,
      timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
    };
    
    setMessages(prev => [...prev, aiMessage]);
    setIsLoading(true);
    
    await chatAPI.sendMessageStream(
      {
        question: trimmedMessage,
        conversation_id: currentConversation?.conversation_id || null,
        collection: 'embedding-seperate',
        mode: 'hybrid',
        limit: 10,
        score_threshold: 0.95,
        temperature: 2,
        max_tokens: 1000,
        streaming: true
      },
      {
        onStatus: (status) => {
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId
              ? { ...msg, statusMessages: [...(msg.statusMessages || []), status] }
              : msg
          ));
        },
        onToken: (token) => {
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId
              ? { ...msg, content: msg.content + token }
              : msg
          ));
        },
        onComplete: async (data) => {
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId
              ? { ...msg, isStreaming: false, sources: data.sources }
              : msg
          ));
          setIsLoading(false);
          
          if (isNewConversation && data.conversation_id) {
            const newConversation = await supabaseConversationAPI.getConversationById(data.conversation_id)
              .catch(() => null);
            
            if (newConversation) {
              setConversations(prev => [newConversation, ...prev]);
              setSelectedConversation(newConversation);
              navigate(`/c/${newConversation.conversation_id}`, { replace: true });
            }
          } else if (!isNewConversation && selectedConversation?.conversation_id) {
            // 既有對話：更新最近存取時間，並刷新清單排序（將此對話移到最上方）
            await supabaseConversationAPI.updateRecentConversation(selectedConversation.conversation_id).catch(() => {});
            const updatedConversation = await supabaseConversationAPI
              .getConversationById(selectedConversation.conversation_id)
              .catch(() => null);
            if (updatedConversation) {
              setConversations(prev => {
                const filtered = prev.filter(c => c.conversation_id !== updatedConversation.conversation_id);
                return [updatedConversation, ...filtered];
              });
              setSelectedConversation(updatedConversation);
            }
          }
        },
        onError: (error) => {
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId
              ? { 
                  ...msg, 
                  content: t('chat.connectionError'),
                  isStreaming: false,
                  statusMessages: []
                }
              : msg
          ));
          setIsLoading(false);
        }
      }
    );
  };

  const handleLogout = () => {
    authLogout();
    navigate('/login');
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const toggleSettings = () => {
    setShowSettings(!showSettings);
  };

  if (accessDenied) {
    return <NotAllowed message={accessDeniedMessage} />;
  }

  return (
    <div className="app">
      <Sidebar 
        collapsed={sidebarCollapsed}
        conversations={conversations}
        selectedConversation={selectedConversation}
        onToggle={toggleSidebar}
        onSelectConversation={handleSelectConversation}
        onShowSettings={toggleSettings}
        onNewConversation={handleNewConversation}
        onRenameConversation={handleRenameConversation}
        onDeleteConversation={handleDeleteConversation}
        onShareConversation={handleShareConversation}
        onLogout={handleLogout}
        loading={conversationsLoading}
      />
      
      <ChatArea 
        messages={messages}
        sidebarCollapsed={sidebarCollapsed}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
      />
      
      {showSettings && (
        <SettingsPopup onClose={toggleSettings} />
      )}
    </div>
  );
}

export default ChatRoute;

