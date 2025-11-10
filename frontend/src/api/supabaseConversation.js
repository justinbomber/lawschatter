import { supabaseRestClient } from './supabaseClient';

const getAuthHeaders = () => {
  const token = localStorage.getItem('supabase_access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const supabaseConversationAPI = {
  getConversations: async () => {
    const response = await supabaseRestClient.get('/conversations', {
      params: {
        select: 'conversation_id,title,created_at,updated_at',
        order: 'updated_at.desc'
      },
      headers: getAuthHeaders()
    });
    
    return response.data.map(conv => ({
      id: conv.conversation_id,
      conversation_id: conv.conversation_id,
      title: conv.title || '新對話',
      timestamp: conv.updated_at || conv.created_at,
      created_at: conv.created_at,
      updated_at: conv.updated_at
    }));
  },

  getConversationMessages: async (conversationId) => {
    const response = await supabaseRestClient.get('/messages', {
      params: {
        conversation_id: `eq.${conversationId}`,
        select: 'message_id,sender_type,content,created_at',
        order: 'created_at.asc'
      },
      headers: getAuthHeaders()
    });
    
    return response.data.map(msg => ({
      id: msg.message_id,
      message_id: msg.message_id,
      type: msg.sender_type,
      content: msg.content,
      timestamp: new Date(msg.created_at).toLocaleTimeString('zh-TW', { 
        hour: '2-digit', 
        minute: '2-digit' 
      }),
      created_at: msg.created_at
    }));
  },

  createConversation: async (title = '新對話') => {
    const response = await supabaseRestClient.post(
      '/conversations',
      { title },
      {
        headers: {
          ...getAuthHeaders(),
          'Prefer': 'return=representation'
        }
      }
    );
    
    const conv = response.data[0];
    return {
      id: conv.conversation_id,
      conversation_id: conv.conversation_id,
      title: conv.title,
      timestamp: conv.created_at,
      created_at: conv.created_at,
      updated_at: conv.updated_at
    };
  },

  updateConversationTitle: async (conversationId, title) => {
    await supabaseRestClient.patch(
      '/conversations',
      { title },
      {
        params: {
          conversation_id: `eq.${conversationId}`
        },
        headers: getAuthHeaders()
      }
    );
  },

  deleteConversation: async (conversationId) => {
    await supabaseRestClient.delete('/conversations', {
      params: {
        conversation_id: `eq.${conversationId}`
      },
      headers: getAuthHeaders()
    });
  },

  updateRecentConversation: async (conversationId) => {
    const now = new Date().toISOString();
    await supabaseRestClient.post(
      '/user_recent_conversations',
      {
        conversation_id: conversationId,
        last_accessed_at: now
      },
      {
        headers: {
          ...getAuthHeaders(),
          'Prefer': 'resolution=merge-duplicates,return=representation'
        }
      }
    );
  },

  getConversationById: async (conversationId) => {
    const response = await supabaseRestClient.get('/conversations', {
      params: {
        conversation_id: `eq.${conversationId}`,
        select: 'conversation_id,title,created_at,updated_at'
      },
      headers: getAuthHeaders()
    });
    
    if (response.data.length === 0) {
      return null;
    }
    
    const conv = response.data[0];
    return {
      id: conv.conversation_id,
      conversation_id: conv.conversation_id,
      title: conv.title || '新對話',
      timestamp: conv.updated_at || conv.created_at,
      created_at: conv.created_at,
      updated_at: conv.updated_at
    };
  },

  createShare: async (conversationId) => {
    console.log('API: 開始創建分享', conversationId);
    
    const existingShareResponse = await supabaseRestClient.get('/shared_conversations', {
      params: {
        conversation_id: `eq.${conversationId}`,
        select: 'share_id,conversation_id,title,is_public,expires_at,created_at'
      },
      headers: getAuthHeaders()
    }).catch(error => {
      console.error('API: 檢查現有分享失敗', error);
      return { data: [] };
    });
    
    if (existingShareResponse.data.length > 0) {
      const existingShare = existingShareResponse.data[0];
      console.log('API: 找到現有分享，直接返回', existingShare);
      
      return {
        share_id: existingShare.share_id,
        conversation_id: existingShare.conversation_id,
        title: existingShare.title,
        is_public: existingShare.is_public,
        expires_at: existingShare.expires_at,
        created_at: existingShare.created_at
      };
    }
    
    console.log('API: 未找到現有分享，創建新的');
    
    const messages = await supabaseConversationAPI.getConversationMessages(conversationId)
      .catch(error => {
        console.error('API: 獲取對話訊息失敗', error);
        throw new Error('無法獲取對話訊息');
      });
    
    console.log('API: 獲取到訊息數量', messages.length);
    
    const conversation = await supabaseConversationAPI.getConversationById(conversationId)
      .catch(error => {
        console.error('API: 獲取對話資訊失敗', error);
        throw new Error('無法獲取對話資訊');
      });
    
    console.log('API: 獲取到對話', conversation);
    
    const shareResponse = await supabaseRestClient.post(
      '/shared_conversations',
      {
        conversation_id: conversationId,
        title: conversation?.title || '新對話',
        is_public: true,
        expires_at: null
      },
      {
        headers: {
          ...getAuthHeaders(),
          'Prefer': 'return=representation'
        }
      }
    ).catch(error => {
      console.error('API: 創建分享對話失敗', error.response?.data || error);
      throw new Error('無法創建分享連結');
    });
    
    console.log('API: 分享對話創建成功', shareResponse.data);
    
    const share = shareResponse.data[0];
    const shareId = share.share_id;
    
    if (messages.length > 0) {
      const shareMessages = messages.map(msg => ({
        share_id: shareId,
        sender_type: msg.type,
        content: msg.content,
        created_at: msg.created_at
      }));
      
      console.log('API: 開始創建分享訊息', shareMessages.length, '條');
      
      await supabaseRestClient.post(
        '/shared_messages',
        shareMessages,
        {
          headers: {
            ...getAuthHeaders(),
            'Prefer': 'return=minimal'
          }
        }
      ).catch(error => {
        console.error('API: 創建分享訊息失敗', error.response?.data || error);
        throw new Error('無法保存分享訊息');
      });
      
      console.log('API: 分享訊息創建成功');
    }
    
    const result = {
      share_id: shareId,
      conversation_id: conversationId,
      title: share.title,
      is_public: share.is_public,
      expires_at: share.expires_at,
      created_at: share.created_at
    };
    
    console.log('API: 分享創建完成', result);
    
    return result;
  },

  getShareMeta: async (shareId) => {
    const response = await supabaseRestClient.get('/shared_conversations', {
      params: {
        share_id: `eq.${shareId}`,
        select: 'share_id,conversation_id,title,is_public,expires_at,created_at'
      },
      headers: {}
    });
    
    if (response.data.length === 0) {
      return null;
    }
    
    const share = response.data[0];
    return {
      share_id: share.share_id,
      conversation_id: share.conversation_id,
      title: share.title || '分享對話',
      is_public: share.is_public,
      expires_at: share.expires_at,
      created_at: share.created_at
    };
  },

  getShareMessages: async (shareId) => {
    const response = await supabaseRestClient.get('/shared_messages', {
      params: {
        share_id: `eq.${shareId}`,
        select: 'id,sender_type,content,created_at',
        order: 'created_at.asc'
      },
      headers: {}
    });
    
    return response.data.map(msg => ({
      id: msg.id,
      type: msg.sender_type,
      content: msg.content,
      timestamp: new Date(msg.created_at).toLocaleTimeString('zh-TW', { 
        hour: '2-digit', 
        minute: '2-digit' 
      }),
      created_at: msg.created_at
    }));
  }
};

export default supabaseConversationAPI;

