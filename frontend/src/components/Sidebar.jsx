import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getUserInitials, getUserDisplayName, getAvatarColor } from '../utils/userUtils';
import './Sidebar.css';

const Sidebar = ({ 
  collapsed, 
  conversations, 
  selectedConversation, 
  onToggle, 
  onSelectConversation, 
  onShowSettings,
  onNewConversation,
  onRenameConversation,
  onDeleteConversation,
  onLogout,
  loading
}) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeMenuId, setActiveMenuId] = useState(null);
  const [renamingId, setRenamingId] = useState(null);
  const [newName, setNewName] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState(null);
  const userMenuRef = useRef(null);
  const menuRefs = useRef({});
  
  // 從 AuthContext 獲取用戶資料
  const userDisplayName = getUserDisplayName(user);
  const userInitials = getUserInitials(user?.display_name, user?.username, user?.email);
  const avatarColor = getAvatarColor(user?.user_id || user?.email);

  // Get conversation icon based on content
  const getConversationIcon = (conversation) => {
    const title = conversation.titleKey || conversation.title || '';
    if (title.includes('Gecko') || title.includes('gecko')) {
      return { icon: 'fas fa-cog', color: '#6b7280' };
    }
    if (title.includes('Chinese') || title.includes('Greeting')) {
      return { icon: 'fab fa-google', color: '#4285f4' };
    }
    if (title.includes('Web') || title.includes('Scraping')) {
      return { icon: 'fab fa-google', color: '#4285f4' };
    }
    if (title.includes('Test') || title.includes('Parser')) {
      return { icon: 'fab fa-google', color: '#4285f4' };
    }
    if (title.includes('Supabase') || title.includes('Oracle')) {
      return { icon: 'fas fa-cog', color: '#6b7280' };
    }
    if (title.includes('Git') || title.includes('部分')) {
      return { icon: 'fas fa-cog', color: '#6b7280' };
    }
    return { icon: 'fas fa-cog', color: '#6b7280' };
  };

  // Group conversations by time
  const groupConversationsByTime = (conversations) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    const groups = {
      today: [],
      yesterday: [],
      week: [],
      older: []
    };

    conversations.forEach(conversation => {
      const conversationDate = new Date(conversation.timestamp);
      const conversationDay = new Date(conversationDate.getFullYear(), conversationDate.getMonth(), conversationDate.getDate());
      
      if (conversationDay.getTime() === today.getTime()) {
        groups.today.push(conversation);
      } else if (conversationDay.getTime() === yesterday.getTime()) {
        groups.yesterday.push(conversation);
      } else if (conversationDate >= weekAgo) {
        groups.week.push(conversation);
      } else {
        groups.older.push(conversation);
      }
    });

    return groups;
  };

  // Filter conversations based on search query
  const filteredConversations = conversations.filter(conversation => {
    if (!searchQuery) return true;
    const title = conversation.title || t(conversation.titleKey) || '';
    return title.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const groupedConversations = groupConversationsByTime(filteredConversations);

  // Render conversation item
  const renderConversationItem = (conversation) => {
    const iconData = getConversationIcon(conversation);
    const isRenaming = renamingId === conversation.id;
    const isMenuActive = activeMenuId === conversation.id;

    return (
      <div 
        key={conversation.id}
        className={`conversation-item ${selectedConversation?.id === conversation.id ? 'selected' : ''}`}
        onClick={() => !isRenaming && onSelectConversation(conversation)}
      >
        <div className="conversation-icon" style={{ color: iconData.color }}>
          <i className={iconData.icon}></i>
        </div>
        <div className="conversation-content">
          {isRenaming ? (
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleRenameSave(conversation.id);
                } else if (e.key === 'Escape') {
                  handleRenameCancel();
                }
              }}
              onBlur={() => handleRenameSave(conversation.id)}
              className="rename-input"
              autoFocus
            />
          ) : (
            <div className="conversation-title">{conversation.title || t(conversation.titleKey) || '新對話'}</div>
          )}
        </div>
        <div className="conversation-menu-container" ref={ref => menuRefs.current[conversation.id] = ref}>
          <button
            className="conversation-actions"
            onClick={(e) => handleConversationMenuToggle(conversation.id, e)}
          >
            <i className="fas fa-ellipsis-h"></i>
          </button>
          {isMenuActive && (
            <div className="conversation-dropdown-menu">
              <button
                className="dropdown-menu-item"
                onClick={() => handleRenameConversation(conversation)}
              >
                <i className="fas fa-edit"></i>
                <span>重新命名</span>
              </button>
              <button
                className="dropdown-menu-item delete"
                onClick={() => handleDeleteConversation(conversation.id)}
              >
                <i className="fas fa-trash"></i>
                <span>刪除</span>
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  // 點擊外部區域關閉選單
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setShowUserMenu(false);
      }
      
      // Check if click is outside of any conversation menu
      const clickedOutsideMenus = !Object.values(menuRefs.current).some(ref => 
        ref && ref.contains(event.target)
      );
      
      if (clickedOutsideMenus) {
        setActiveMenuId(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  const handleNewConversation = () => {
    onNewConversation();
  };

  const handleSettingsClick = () => {
    onShowSettings();
    setShowUserMenu(false);
  };

  const handleUserMenuToggle = () => {
    setShowUserMenu(!showUserMenu);
  };

  const handleUserMenuItemClick = (action) => {
    setShowUserMenu(false);
    
    switch (action) {
      case 'settings':
        onShowSettings();
        break;
      case 'myFiles':
        // TODO: 實現我的檔案功能
        console.log('我的檔案');
        break;
      case 'helpFaq':
        // TODO: 實現說明與常見問題功能
        console.log('說明與常見問題');
        break;
      case 'logout':
        onLogout();
        break;
      default:
        break;
    }
  };

  // Handle conversation menu toggle
  const handleConversationMenuToggle = (conversationId, event) => {
    event.stopPropagation();
    setActiveMenuId(activeMenuId === conversationId ? null : conversationId);
  };

  // Handle conversation rename
  const handleRenameConversation = (conversation) => {
    setRenamingId(conversation.id);
    setNewName(conversation.title || t(conversation.titleKey) || '');
    setActiveMenuId(null);
  };

  // Handle rename save
  const handleRenameSave = (conversationId) => {
    if (newName.trim() && onRenameConversation) {
      onRenameConversation(conversationId, newName);
    }
    setRenamingId(null);
    setNewName('');
  };

  // Handle rename cancel
  const handleRenameCancel = () => {
    setRenamingId(null);
    setNewName('');
  };

  // Handle conversation delete
  const handleDeleteConversation = (conversationId) => {
    setConversationToDelete(conversationId);
    setShowDeleteModal(true);
    setActiveMenuId(null);
  };

  // Confirm delete conversation
  const confirmDeleteConversation = () => {
    if (conversationToDelete && onDeleteConversation) {
      onDeleteConversation(conversationToDelete);
    }
    setShowDeleteModal(false);
    setConversationToDelete(null);
  };

  // Cancel delete conversation
  const cancelDeleteConversation = () => {
    setShowDeleteModal(false);
    setConversationToDelete(null);
  };

  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <button className="sidebar-toggle" onClick={onToggle}>
          <i className="fas fa-bars"></i>
        </button>
        {!collapsed && (
          <button className="new-chat-icon-btn" onClick={handleNewConversation} title="New Chat">
            <i className="fas fa-edit"></i>
          </button>
        )}
      </div>
      
      {!collapsed && (
        <>
          {/* Search Bar */}
          <div className="search-container">
            <div className="search-box">
              <i className="fas fa-search search-icon"></i>
              <input
                type="text"
                placeholder="搜尋訊息"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
            </div>
          </div>
          
          {/* Conversations List with Time Groups */}
          <div className="conversations-list">
            {loading ? (
              <div className="conversations-loading">
                <div className="loading-spinner"></div>
                <p>載入對話中...</p>
              </div>
            ) : conversations.length === 0 ? (
              <div className="no-conversations">
                <i className="fas fa-comments"></i>
                <p>尚無對話記錄</p>
                <p className="hint">點擊上方按鈕開始新對話</p>
              </div>
            ) : (
              <>
            {groupedConversations.today.length > 0 && (
              <div className="time-group">
                <div className="time-group-header">今天</div>
                {groupedConversations.today.map(renderConversationItem)}
              </div>
            )}

            {groupedConversations.yesterday.length > 0 && (
              <div className="time-group">
                <div className="time-group-header">昨天</div>
                {groupedConversations.yesterday.map(renderConversationItem)}
              </div>
            )}

            {groupedConversations.week.length > 0 && (
              <div className="time-group">
                <div className="time-group-header">過去 7 天</div>
                {groupedConversations.week.map(renderConversationItem)}
              </div>
            )}

            {groupedConversations.older.length > 0 && (
              <div className="time-group">
                <div className="time-group-header">更早</div>
                {groupedConversations.older.map(renderConversationItem)}
              </div>
            )}
              </>
            )}
          </div>
          
          <div className="sidebar-footer">
            <div className="user-menu-container" ref={userMenuRef}>
              <button className="user-info-btn" onClick={handleUserMenuToggle}>
                <div className="user-avatar" style={{ backgroundColor: avatarColor }}>
                  {userInitials}
                </div>
                <div className="user-info">
                  <span className="user-name">{userDisplayName}</span>
                </div>
                <i className={`fas fa-chevron-${showUserMenu ? 'up' : 'down'}`}></i>
              </button>
              
              {showUserMenu && (
                <div className="user-menu">
                  <div className="user-menu-email">
                    {user?.email || '未登入'}
                  </div>
                  <div className="user-menu-divider"></div>
                  <button 
                    className="user-menu-item"
                    onClick={() => handleUserMenuItemClick('myFiles')}
                  >
                    <i className="fas fa-file-alt"></i>
                    <span>{t('sidebar.userMenu.myFiles')}</span>
                  </button>
                  <button 
                    className="user-menu-item"
                    onClick={() => handleUserMenuItemClick('helpFaq')}
                  >
                    <i className="fas fa-external-link-alt"></i>
                    <span>{t('sidebar.userMenu.helpFaq')}</span>
                  </button>
                  <button 
                    className="user-menu-item"
                    onClick={() => handleUserMenuItemClick('settings')}
                  >
                    <i className="fas fa-cog"></i>
                    <span>{t('sidebar.userMenu.settings')}</span>
                  </button>
                  <div className="user-menu-divider"></div>
                  <button 
                    className="user-menu-item logout"
                    onClick={() => handleUserMenuItemClick('logout')}
                  >
                    <i className="fas fa-sign-out-alt"></i>
                    <span>{t('sidebar.userMenu.logout')}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
      
      {collapsed && (
        <div className="collapsed-buttons">
          <button className="collapsed-btn" onClick={handleNewConversation} title={t('sidebar.newConversation')}>
            <i className="fas fa-plus"></i>
          </button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={cancelDeleteConversation}>
          <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>刪除對話</h3>
            </div>
            <div className="modal-content">
              <p>確定要刪除這個對話嗎？此操作無法復原。</p>
            </div>
            <div className="modal-actions">
              <button className="cancel-btn" onClick={cancelDeleteConversation}>
                取消
              </button>
              <button className="delete-btn" onClick={confirmDeleteConversation}>
                刪除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Sidebar;
