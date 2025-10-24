import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import './App.css';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import SettingsPopup from './components/SettingsPopup';
import Login from './components/Login';
import Register from './components/Register';

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
    setIsLoading(true);
    
    try {
      // 確保會話 ID 是有效的字符串
      const sessionId = selectedConversation?.id?.toString() || 'default';
      
      const requestBody = {
        message: trimmedMessage,
        session_id: sessionId
      };

      console.log('發送聊天請求:', requestBody);

      const response = await fetch('https://lawschatter.mooo.com/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        const data = await response.json();
        const aiResponse = {
          id: Date.now() + 1,
          type: 'assistant',
          content: data.response,
          timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, aiResponse]);
      } else {
        // 處理具體的 HTTP 錯誤狀態
        let errorMessage = '抱歉，服務器回應異常，請稍後再試。';
        
        if (response.status === 422) {
          errorMessage = '請求格式錯誤，請檢查您的輸入並重新發送。';
        } else if (response.status === 503) {
          errorMessage = '服務暫時不可用，請稍後再試。';
        } else if (response.status >= 500) {
          errorMessage = '服務器內部錯誤，請聯繫管理員。';
        }

        const errorResponse = {
          id: Date.now() + 1,
          type: 'assistant',
          content: errorMessage,
          timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, errorResponse]);

        // 記錄詳細錯誤信息
        console.error(`API 請求失敗: ${response.status} ${response.statusText}`);
        try {
          const errorData = await response.json();
          console.error('錯誤詳情:', errorData);
        } catch (e) {
          console.error('無法解析錯誤回應');
        }
      }
    } catch (error) {
      console.error('Error calling chatbot API:', error);
      const errorResponse = {
        id: Date.now() + 1,
        type: 'assistant',
        content: '抱歉，目前無法連接到後端服務，請檢查網路連接並稍後再試。',
        timestamp: new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorResponse]);
    } finally {
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
