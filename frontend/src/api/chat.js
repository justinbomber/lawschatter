/**
 * 聊天 API - 支援 SSE 串流
 */

const CHAT_API_URL = 'http://localhost:9500';

export const chatAPI = {
  /**
   * 使用 SSE 串流方式發送聊天訊息
   * @param {Object} messageData - 訊息資料
   * @param {string} messageData.question - 問題內容
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
      const response = await fetch(`${CHAT_API_URL}/chat/completion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: messageData.question,
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
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
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
              console.warn('無法解析 SSE 資料:', line, e);
            }
          }
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
      const response = await fetch(`${CHAT_API_URL}/chat/completion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: messageData.question,
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
        throw new Error(`HTTP error! status: ${response.status}`);
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

