import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from './contexts/AuthContext.jsx';
import './App.css';
import Sidebar from './components/Sidebar.jsx';
import ChatArea from './components/ChatArea.jsx';
import SettingsPopup from './components/SettingsPopup.jsx';
import Login from './components/Login.jsx';
import Register from './components/Register.jsx';
import { chatAPI } from './api/chat';
import { supabaseConversationAPI } from './api/supabaseConversation';

function App() {
  const { t } = useTranslation();
  const { isAuthenticated, loading, logout: authLogout } = useAuth();
  
  // 視圖狀態
  const [currentView, setCurrentView] = useState('login'); // 'login' | 'register'
  
  // 主應用狀態
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [conversations, setConversations] = useState([]);

  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationsLoading, setConversationsLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      loadConversations();
    }
  }, [isAuthenticated]);

  const loadConversations = async () => {
    setConversationsLoading(true);
    try {
      const token = localStorage.getItem('supabase_access_token');
      console.log('載入對話列表 - Token 存在:', !!token);
      
      const convs = await supabaseConversationAPI.getConversations();
      console.log('載入對話列表成功，共', convs.length, '筆');
      setConversations(convs);
      
      if (convs.length > 0 && !selectedConversation) {
        const lastConv = convs[0];
        setSelectedConversation(lastConv);
        await loadConversationMessages(lastConv.conversation_id);
      }
    } catch (error) {
      console.error('載入對話列表失敗:', error);
      console.error('錯誤詳情:', error.response?.data);
    }
    setConversationsLoading(false);
  };

  const loadConversationMessages = async (conversationId) => {
    try {
      const msgs = await supabaseConversationAPI.getConversationMessages(conversationId);
      setMessages(msgs);
    } catch (error) {
      console.error('載入對話訊息失敗:', error);
      setMessages([]);
    }
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const toggleSettings = () => {
    setShowSettings(!showSettings);
  };

  const handleSelectConversation = async (conversation) => {
    setSelectedConversation(conversation);
    await loadConversationMessages(conversation.conversation_id);
    await supabaseConversationAPI.updateRecentConversation(conversation.conversation_id);
  };

  const handleNewConversation = () => {
    setSelectedConversation(null);
    setMessages([]);
  };

  const handleRenameConversation = async (conversationId, newTitle) => {
    try {
      await supabaseConversationAPI.updateConversationTitle(conversationId, newTitle);
      setConversations(prev => prev.map(conv => 
        conv.conversation_id === conversationId 
          ? { ...conv, title: newTitle }
          : conv
      ));
    } catch (error) {
      console.error('重新命名對話失敗:', error);
    }
  };

  const handleDeleteConversation = async (conversationId) => {
    try {
      await supabaseConversationAPI.deleteConversation(conversationId);
      setConversations(prev => prev.filter(conv => conv.conversation_id !== conversationId));
      
      if (selectedConversation?.conversation_id === conversationId) {
        const remainingConvs = conversations.filter(conv => conv.conversation_id !== conversationId);
        if (remainingConvs.length > 0) {
          const nextConv = remainingConvs[0];
          setSelectedConversation(nextConv);
          await loadConversationMessages(nextConv.conversation_id);
        } else {
          setSelectedConversation(null);
          setMessages([]);
        }
      }
    } catch (error) {
      console.error('刪除對話失敗:', error);
    }
  };

  const handleSendMessage = async (message) => {
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      console.warn('嘗試發送空消息，已忽略');
      return;
    }

    const trimmedMessage = message.trim();
    
    if (trimmedMessage.length > 5000) {
      const errorResponse = {
        id: Date.now(),
        type: 'assistant',
        content: '訊息長度不能超過 5000 個字符，請縮短後重新發送。',
        timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorResponse]);
      return;
    }

    let currentConversation = selectedConversation;
    let isNewConversation = false;
    
    if (!currentConversation) {
      try {
        currentConversation = await supabaseConversationAPI.createConversation('新對話');
        setSelectedConversation(currentConversation);
        isNewConversation = true;
      } catch (error) {
        console.error('建立新對話失敗:', error);
        const errorResponse = {
          id: Date.now(),
          type: 'assistant',
          content: '無法建立新對話，請稍後再試。',
          timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, errorResponse]);
        return;
      }
    }

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
    
    try {
      await chatAPI.sendMessageStream(
        {
          question: trimmedMessage,
          conversation_id: currentConversation.conversation_id,
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
            
            if (isNewConversation && currentConversation) {
              try {
                const updatedConversation = await supabaseConversationAPI.getConversationById(currentConversation.conversation_id);
                if (updatedConversation) {
                  setConversations(prev => [updatedConversation, ...prev]);
                  setSelectedConversation(updatedConversation);
                }
              } catch (error) {
                console.error('重新載入對話失敗:', error);
              }
            }
          },
          onError: (error) => {
            console.error('SSE 串流錯誤:', error);
            setMessages(prev => prev.map(msg => 
              msg.id === aiMessageId
                ? { 
                    ...msg, 
                    content: '抱歉，目前無法連接到後端服務，請檢查網路連接並稍後再試。',
                    isStreaming: false,
                    statusMessages: []
                  }
                : msg
            ));
            setIsLoading(false);
          }
        }
      );
    } catch (error) {
      console.error('Error calling chatbot API:', error);
      setMessages(prev => prev.map(msg => 
        msg.id === aiMessageId
          ? { 
              ...msg, 
              content: '抱歉，發生未預期的錯誤，請稍後再試。',
              isStreaming: false,
              statusMessages: []
            }
          : msg
      ));
      setIsLoading(false);
    }
  };

  // 驗證相關處理函數
  const handleLogin = () => {
    // 登入成功已由 AuthContext 處理
    console.log('登入成功');
  };

  const handleRegister = () => {
    // 註冊成功已由 AuthContext 處理
    console.log('註冊成功');
  };

  const handleLogout = () => {
    authLogout();
    setCurrentView('login');
    // 清空聊天相關狀態
    setMessages([]);
    setSelectedConversation(null);
    setShowSettings(false);
  };

  const handleSwitchToRegister = () => {
    setCurrentView('register');
  };

  const handleSwitchToLogin = () => {
    setCurrentView('login');
  };

  // 載入中狀態
  if (loading) {
    return (
      <div className="app loading-screen">
        <div className="loading-spinner"></div>
        <p>載入中...</p>
      </div>
    );
  }

  // 如果未登入，顯示登入/註冊頁面
  if (!isAuthenticated) {
    if (currentView === 'register') {
      return (
        <Register 
          onRegister={handleRegister}
          onSwitchToLogin={handleSwitchToLogin}
        />
      );
    }
    
    return (
      <Login 
        onLogin={handleLogin}
        onSwitchToRegister={handleSwitchToRegister}
      />
    );
  }

  // 如果已登入，顯示主聊天界面
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

export default App;
