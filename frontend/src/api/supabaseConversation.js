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
  }
};

export default supabaseConversationAPI;

