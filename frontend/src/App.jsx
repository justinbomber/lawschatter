import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import './App.css';
import Sidebar from './components/Sidebar.jsx';
import ChatArea from './components/ChatArea.jsx';
import SettingsPopup from './components/SettingsPopup.jsx';
import Login from './components/Login.jsx';
import Register from './components/Register.jsx';
import { chatAPI } from './api/chat';

function App() {
  const { t } = useTranslation();
  
  // 驗證狀態
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentView, setCurrentView] = useState('login'); // 'login' | 'register'
  
  // 主應用狀態
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [conversations, setConversations] = useState([
    { id: 1, titleKey: 'sidebar.conversations.yesterday', timestamp: '2023-10-01' },
    { id: 2, titleKey: 'sidebar.conversations.aiPrompt', timestamp: '2023-09-30' },
    { id: 3, titleKey: 'sidebar.conversations.settingsIssue', timestamp: '2023-09-29' }
  ]);

  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const toggleSettings = () => {
    setShowSettings(!showSettings);
  };

  const handleNewConversation = async () => {
    const newConversation = {
      id: Date.now(),
      titleKey: 'sidebar.conversations.newConversation',
      timestamp: new Date().toISOString().split('T')[0]
    };
    setConversations(prev => [newConversation, ...prev]);
    setSelectedConversation(newConversation);
    
    // 清空消息，回到初始狀態顯示歡迎語
    setMessages([]);
    
    // 呼叫清除對話API
    try {
      await fetch('https://lawschatter.mooo.com/conversation/clear', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
    } catch (error) {
      console.error('Error clearing conversation:', error);
    }
  };

  const handleSendMessage = async (message) => {
    // 驗證消息不為空
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      console.warn('嘗試發送空消息，已忽略');
      return;
    }

    // 限制消息長度
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

    const timestamp = new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });
    
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: trimmedMessage,
      timestamp: timestamp
    };
    
    setMessages(prev => [...prev, userMessage]);
    
    // 建立 AI 訊息的 placeholder，用於即時更新
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
          onComplete: (data) => {
            setMessages(prev => prev.map(msg => 
              msg.id === aiMessageId
                ? { ...msg, isStreaming: false, sources: data.sources }
                : msg
            ));
            setIsLoading(false);
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
    setIsAuthenticated(true);
  };

  const handleRegister = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
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
        onSelectConversation={setSelectedConversation}
        onShowSettings={toggleSettings}
        onNewConversation={handleNewConversation}
        onLogout={handleLogout}
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
