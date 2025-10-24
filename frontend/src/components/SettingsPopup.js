import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import './SettingsPopup.css';

const SettingsPopup = ({ onClose }) => {
  const { t, i18n } = useTranslation();
  const [activeSection, setActiveSection] = useState('general');
  const [activeTab, setActiveTab] = useState('basic');
  const [settings, setSettings] = useState({
    theme: 'light',
    language: i18n.language,
    markdownFormatting: true,
    instantPreview: false,
    showBorder: false
  });

  const sections = [
    { id: 'general', name: t('settings.general'), icon: 'fas fa-cog' },
    { id: 'theme', name: t('settings.theme'), icon: 'fas fa-palette' },
    { id: 'language', name: t('settings.language'), icon: 'fas fa-globe' },
    { id: 'display', name: t('settings.display'), icon: 'fas fa-desktop' },
    { id: 'privacy', name: t('settings.privacy'), icon: 'fas fa-shield-alt' },
    { id: 'account', name: t('settings.account'), icon: 'fas fa-user' },
    { id: 'others', name: t('settings.others'), icon: 'fas fa-ellipsis-h' }
  ];

  const tabs = {
    general: [
      { id: 'basic', name: t('settings.tabs.basic') },
      { id: 'advanced', name: t('settings.tabs.advanced') }
    ],
    theme: [
      { id: 'appearance', name: t('settings.tabs.appearance') },
      { id: 'colors', name: t('settings.tabs.colors') }
    ],
    display: [
      { id: 'layout', name: t('settings.tabs.layout') },
      { id: 'formatting', name: t('settings.tabs.formatting') }
    ]
  };

  const handleLanguageChange = (language) => {
    setSettings(prev => ({ ...prev, language }));
    i18n.changeLanguage(language);
  };

  const handleThemeChange = (theme) => {
    setSettings(prev => ({ ...prev, theme }));
  };

  const handleToggleChange = (key) => {
    setSettings(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = () => {
    console.log('Settings saved:', settings);
    onClose();
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const renderContent = () => {
    if (activeSection === 'general') {
      if (activeTab === 'basic') {
        return (
          <div className="settings-content-section">
            <div className="setting-item toggle-item">
              <div className="toggle-content">
                <div className="toggle-info">
                  <label className="setting-label">{t('settings.toggles.markdownFormatting')}</label>
                  <p className="setting-description">{t('settings.toggles.markdownFormattingDesc')}</p>
                </div>
                <div className="toggle-wrapper">
                  <input
                    type="checkbox"
                    id="markdownFormatting"
                    className="toggle-input"
                    checked={settings.markdownFormatting}
                    onChange={() => handleToggleChange('markdownFormatting')}
                  />
                  <label htmlFor="markdownFormatting" className="toggle-label"></label>
                </div>
              </div>
            </div>
            
            <div className="setting-item toggle-item">
              <div className="toggle-content">
                <div className="toggle-info">
                  <label className="setting-label">{t('settings.toggles.instantPreview')}</label>
                  <p className="setting-description">{t('settings.toggles.instantPreviewDesc')}</p>
                </div>
                <div className="toggle-wrapper">
                  <input
                    type="checkbox"
                    id="instantPreview"
                    className="toggle-input"
                    checked={settings.instantPreview}
                    onChange={() => handleToggleChange('instantPreview')}
                  />
                  <label htmlFor="instantPreview" className="toggle-label"></label>
                </div>
              </div>
            </div>
            
            <div className="setting-item toggle-item">
              <div className="toggle-content">
                <div className="toggle-info">
                  <label className="setting-label">{t('settings.toggles.showBorder')}</label>
                  <p className="setting-description">{t('settings.toggles.showBorderDesc')}</p>
                </div>
                <div className="toggle-wrapper">
                  <input
                    type="checkbox"
                    id="showBorder"
                    className="toggle-input"
                    checked={settings.showBorder}
                    onChange={() => handleToggleChange('showBorder')}
                  />
                  <label htmlFor="showBorder" className="toggle-label"></label>
                </div>
              </div>
            </div>
          </div>
        );
      }
    } else if (activeSection === 'theme') {
      return (
        <div className="settings-content-section">
          <div className="setting-item">
            <label className="setting-label">{t('settings.theme')}</label>
            <select 
              className="setting-select"
              value={settings.theme}
              onChange={(e) => handleThemeChange(e.target.value)}
            >
              <option value="light">{t('settings.themes.light')}</option>
              <option value="dark">{t('settings.themes.dark')}</option>
              <option value="system">{t('settings.themes.system')}</option>
            </select>
          </div>
        </div>
      );
    } else if (activeSection === 'language') {
      return (
        <div className="settings-content-section">
          <div className="setting-item">
            <label className="setting-label">{t('settings.language')}</label>
            <select 
              className="setting-select"
              value={settings.language}
              onChange={(e) => handleLanguageChange(e.target.value)}
            >
              <option value="zh-TW">{t('settings.languages.zhTW')}</option>
              <option value="en">{t('settings.languages.en')}</option>
            </select>
          </div>
        </div>
      );
    }
    return <div className="settings-content-section">選擇左側項目以查看設定選項</div>;
  };

  return (
    <div className="settings-overlay" onClick={handleOverlayClick}>
      <div className="settings-popup">
        <div className="settings-header">
          <h2 className="settings-title">{t('settings.title')}</h2>
          <button className="close-btn" onClick={onClose}>
            <i className="fas fa-times"></i>
          </button>
        </div>
        
        <div className="settings-body">
          <div className="settings-sidebar">
            {sections.map(section => (
              <button
                key={section.id}
                className={`settings-nav-item ${activeSection === section.id ? 'active' : ''}`}
                onClick={() => {
                  setActiveSection(section.id);
                  setActiveTab(tabs[section.id]?.[0]?.id || 'basic');
                }}
              >
                <i className={section.icon}></i>
                <span>{section.name}</span>
              </button>
            ))}
          </div>
          
          <div className="settings-content">
            {tabs[activeSection] && (
              <div className="settings-tabs">
                {tabs[activeSection].map(tab => (
                  <button
                    key={tab.id}
                    className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.name}
                  </button>
                ))}
              </div>
            )}
            
            <div className="settings-content-wrapper">
              {renderContent()}
            </div>
          </div>
        </div>
        
        <div className="settings-footer">
          <button className="save-btn" onClick={handleSave}>
            {t('settings.saveButton')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsPopup;
