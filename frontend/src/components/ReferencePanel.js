import React, { useState, useEffect } from 'react';
import './ReferencePanel.css';

const ReferencePanel = ({ isOpen, onClose, references = [] }) => {
  const [previewData, setPreviewData] = useState([]);

  // 獲取網站預覽資訊
  const fetchPreviewData = async (url) => {
    try {
      const domain = new URL(url).hostname;
      let title = domain;
      let description = '載入中...';
      
      // 嘗試使用代理服務獲取網站meta信息
      try {
        // 使用allorigins.win作為CORS代理
        const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(url)}`;
        const response = await fetch(proxyUrl);
        const data = await response.json();
        
        if (data.contents) {
          const parser = new DOMParser();
          const doc = parser.parseFromString(data.contents, 'text/html');
          
          // 獲取網站標題
          const titleElement = doc.querySelector('title');
          if (titleElement) {
            title = titleElement.textContent.trim();
          }
          
          // 獲取meta描述
          const metaDescription = doc.querySelector('meta[name="description"]') || 
                                 doc.querySelector('meta[property="og:description"]');
          if (metaDescription) {
            description = metaDescription.getAttribute('content').trim();
          } else {
            // 如果沒有meta描述，嘗試獲取第一段文字
            const firstParagraph = doc.querySelector('p');
            if (firstParagraph) {
              description = firstParagraph.textContent.trim().substring(0, 150) + '...';
            } else {
              description = '未能獲取網站描述';
            }
          }
        }
      } catch (fetchError) {
        console.warn('無法獲取網站內容，使用默認描述:', fetchError);
        description = '無法獲取網站描述';
      }
      
      return {
        url: url,
        title: title,
        description: description,
        favicon: `https://www.google.com/s2/favicons?sz=32&domain=${domain}`,
        domain: domain
      };
    } catch (error) {
      console.error('Error processing URL:', error);
      return {
        url: url,
        title: url,
        description: '無法處理此URL',
        favicon: 'https://www.google.com/s2/favicons?sz=32&domain=example.com',
        domain: 'unknown'
      };
    }
  };

  useEffect(() => {
    if (isOpen && references.length > 0) {
      const loadPreviewData = async () => {
        const previews = await Promise.all(
          references.map(ref => fetchPreviewData(ref.url || ref))
        );
        setPreviewData(previews);
      };
      loadPreviewData();
    }
  }, [isOpen, references]);

  return (
    <div className={`reference-panel ${isOpen ? 'open' : ''}`}>
      <div className="reference-header">
        <h3>參考資料</h3>
        <button className="close-btn" onClick={onClose}>
          <i className="fas fa-times"></i>
        </button>
      </div>
      
      <div className="reference-content">
        {previewData.length > 0 ? (
          previewData.map((item, index) => (
            <div key={index} className="reference-item">
              <div className="reference-link">
                <img 
                  src={item.favicon} 
                  alt="" 
                  className="site-favicon"
                  onError={(e) => {
                    e.target.src = 'https://www.google.com/s2/favicons?sz=32&domain=example.com';
                  }}
                />
                <a 
                  href={item.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="reference-url"
                >
                  {item.url}
                </a>
              </div>
              <div className="reference-description">
                {item.description}
              </div>
            </div>
          ))
        ) : (
          <div className="loading-placeholder">
            <i className="fas fa-spinner fa-spin"></i>
            載入中...
          </div>
        )}
      </div>
    </div>
  );
};

export default ReferencePanel;
