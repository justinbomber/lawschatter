import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import './RagSelector.css';

const RagSelector = ({ onClose }) => {
  const { t } = useTranslation();
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedCollections, setSelectedCollections] = useState([]);

  // 從 localStorage 載入之前的設定
  React.useEffect(() => {
    const savedSettings = localStorage.getItem('ragSettings');
    if (savedSettings) {
      try {
        const settings = JSON.parse(savedSettings);
        setSelectedCollections(settings.selectedCollections || []);
        setStartDate(settings.startDate || '');
        setEndDate(settings.endDate || '');
      } catch (error) {
        console.warn('無法載入RAG設定:', error);
      }
    }
  }, []);

  const collections = [
    { id: 'criminal', name: '刑事訴訟', description: '刑事法相關條文與判例' },
    { id: 'civil', name: '民事訴訟', description: '民事法相關條文與判例' },
    { id: 'commercial', name: '商事法', description: '公司法、商業相關法規' },
    { id: 'family', name: '家事法', description: '婚姻、家庭相關法規' },
    { id: 'labor', name: '勞動法', description: '勞工權益相關法規' },
    { id: 'tax', name: '稅法', description: '稅務相關法規' }
  ];

  const handleCollectionToggle = (collectionId) => {
    setSelectedCollections(prev => 
      prev.includes(collectionId)
        ? prev.filter(id => id !== collectionId)
        : [...prev, collectionId]
    );
  };

  const handleSave = () => {
    const ragSettings = {
      selectedCollections,
      startDate,
      endDate,
      timestamp: new Date().toISOString()
    };
    
    // 如果沒有任何設定，則清除localStorage
    const hasCollections = selectedCollections.length > 0;
    const hasDateRange = startDate || endDate;
    
    if (hasCollections || hasDateRange) {
      // 保存到 localStorage
      localStorage.setItem('ragSettings', JSON.stringify(ragSettings));
    } else {
      // 清除設定
      localStorage.removeItem('ragSettings');
    }
    
    console.log('Selected collections:', selectedCollections);
    console.log('Date range:', startDate, 'to', endDate);
    
    // 通知父組件選擇已完成
    if (onClose) {
      onClose(ragSettings);
    }
  };

  const handleClearAll = () => {
    setSelectedCollections([]);
    setStartDate('');
    setEndDate('');
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="rag-selector-overlay" onClick={handleOverlayClick}>
      <div className="rag-selector-popup">
        <div className="rag-selector-header">
          <h2 className="rag-selector-title">法律資料庫設定</h2>
          <button className="close-btn" onClick={onClose}>
            <i className="fas fa-times"></i>
          </button>
        </div>
        
        <div className="rag-selector-content">
          <div className="date-range-section">
            <h3 className="section-title">時間範圍</h3>
            <div className="date-inputs">
              <div className="date-input-group">
                <label>開始時間</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="date-input"
                />
              </div>
              <div className="date-separator">～</div>
              <div className="date-input-group">
                <label>結束時間</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="date-input"
                />
              </div>
            </div>
          </div>
          
          <div className="collections-section">
            <div className="section-header">
              <h3 className="section-title">法律領域</h3>
              <button 
                className="clear-all-btn" 
                onClick={handleClearAll}
                title="清除所有設定"
              >
                <i className="fas fa-trash-alt"></i>
                清除所有
              </button>
            </div>
            <div className="collections-grid">
              {collections.map(collection => (
                <div
                  key={collection.id}
                  className={`collection-item ${selectedCollections.includes(collection.id) ? 'selected' : ''}`}
                  onClick={() => handleCollectionToggle(collection.id)}
                >
                  <div className="collection-checkbox">
                    {selectedCollections.includes(collection.id) && (
                      <i className="fas fa-check"></i>
                    )}
                  </div>
                  <div className="collection-info">
                    <div className="collection-name">{collection.name}</div>
                    <div className="collection-description">{collection.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        <div className="rag-selector-footer">
          <button className="cancel-btn" onClick={onClose}>
            取消
          </button>
          <button className="save-btn" onClick={handleSave}>
            確認設定
          </button>
        </div>
      </div>
    </div>
  );
};

export default RagSelector;
