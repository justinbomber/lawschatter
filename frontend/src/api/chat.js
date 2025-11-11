/**
 * 聊天 API - 支援 SSE 串流
 */

import { validateTokenBeforeRequest, getValidToken } from '../utils/jwtValidator';

// 聊天 API URL - 根據環境變數決定
const CHAT_API_URL = import.meta.env.VITE_CHAT_API_URL || 'https://lawschatter.mooo.com';

export const chatAPI = {
  /**
   * 使用 SSE 串流方式發送聊天訊息
   * @param {Object} messageData - 訊息資料
   * @param {string} messageData.question - 問題內容
   * @param {string} messageData.conversation_id - 對話 ID
   * @param {string} messageData.collection - 集合名稱
   * @param {string} messageData.mode - 搜尋模式
   * @param {number} messageData.limit - 結果數量限制
   * @param {number} messageData.score_threshold - 分數閾值
   * @param {number} messageData.temperature - LLM 溫度
   * @param {number} messageData.max_tokens - 最大 token 數
   * @param {boolean} messageData.streaming - 是否使用串流
   * @param {Object} callbacks - 回調函數
   * @param {Function} callbacks.onStatus - 狀態更新回調
   * @param {Function} callbacks.onToken - LLM token 回調
   * @param {Function} callbacks.onComplete - 完成回調
   * @param {Function} callbacks.onError - 錯誤回調
   */
  sendMessageStream: async (messageData, callbacks = {}) => {
    const {
      onStatus = () => {},
      onToken = () => {},
      onComplete = () => {},
      onError = () => {}
    } = callbacks;

    try {
      if (!validateTokenBeforeRequest()) {
        onError(new Error('Token 已過期'));
        return;
      }
      
      const token = getValidToken();
      const headers = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${CHAT_API_URL}/chat/completion`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          question: messageData.question,
          conversation_id: messageData.conversation_id,
          collection: messageData.collection || 'embedding-seperate',
          mode: messageData.mode || 'hybrid',
          limit: messageData.limit || 10,
          score_threshold: messageData.score_threshold || 0.95,
          temperature: messageData.temperature || 2,
          max_tokens: messageData.max_tokens || 1000,
          streaming: messageData.streaming !== false
        })
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('supabase_access_token');
          localStorage.removeItem('supabase_refresh_token');
          localStorage.removeItem('supabase_user_data');
          localStorage.removeItem('access_token');
          localStorage.removeItem('user_data');
          
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
        }
        
        let errorMessage = `伺服器錯誤 (${response.status})`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (errorData.message) {
            errorMessage = errorData.message;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          }
        } catch (e) {
          const errorText = await response.text().catch(() => '');
          if (errorText) {
            errorMessage = errorText;
          }
        }
        
        throw new Error(errorMessage);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

        // SSE 事件以空行分段（\n\n）；僅處理完整段落
        const events = buffer.split('\n\n');
        if (!done) {
          buffer = events.pop() || '';
        } else {
          buffer = '';
        }

        for (const event of events) {
          // 組合多行 data: 負載
          const dataPayload = event
            .split('\n')
            .filter(line => line.startsWith('data: '))
            .map(line => line.slice(6))
            .join('');

          if (!dataPayload) {
            continue;
          }

          try {
            const data = JSON.parse(dataPayload);
            if (data.type === 'rag_status') {
              onStatus(data.status);
            } else if (data.type === 'llm_start') {
              onStatus(data.status || '開始生成回答');
            } else if (data.type === 'llm_token') {
              onToken(data.content);
            } else if (data.type === 'complete') {
              onComplete(data);
            }
          } catch (e) {
            console.warn('無法解析 SSE 資料:', `data: ${dataPayload}`, e);
          }
        }

        if (done) {
          break;
        }
      }
    } catch (error) {
      console.error('SSE 串流錯誤:', error);
      onError(error);
    }
  },

  /**
   * 使用傳統方式發送聊天訊息（非串流）
   * @param {Object} messageData - 訊息資料
   * @returns {Promise<Object>} 回應資料
   */
  sendMessage: async (messageData) => {
    try {
      if (!validateTokenBeforeRequest()) {
        return {
          success: false,
          error: 'Token 已過期'
        };
      }
      
      const token = getValidToken();
      const headers = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${CHAT_API_URL}/chat/completion`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          question: messageData.question,
          conversation_id: messageData.conversation_id,
          collection: messageData.collection || 'embedding-seperate',
          mode: messageData.mode || 'hybrid',
          limit: messageData.limit || 10,
          score_threshold: messageData.score_threshold || 0.95,
          temperature: messageData.temperature || 2,
          max_tokens: messageData.max_tokens || 1000,
          streaming: false
        })
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('supabase_access_token');
          localStorage.removeItem('supabase_refresh_token');
          localStorage.removeItem('supabase_user_data');
          localStorage.removeItem('access_token');
          localStorage.removeItem('user_data');
          
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
        }
        
        let errorMessage = `伺服器錯誤 (${response.status})`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (errorData.message) {
            errorMessage = errorData.message;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          }
        } catch (e) {
          const errorText = await response.text().catch(() => '');
          if (errorText) {
            errorMessage = errorText;
          }
        }
        
        throw new Error(errorMessage);
      }

      const data = await response.json();
      return {
        success: true,
        data
      };
    } catch (error) {
      console.error('發送訊息失敗:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
};

export default chatAPI;

