-- ================================
-- USER MANAGEMENT DATABASE SCHEMA
-- ================================

-- 創建 schema
CREATE SCHEMA IF NOT EXISTS lawschatter;

-- 用戶表
CREATE TABLE lawschatter.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 為 users 表添加註解
COMMENT ON TABLE lawschatter.users IS '用戶表，儲存系統用戶的基本資訊';
COMMENT ON COLUMN lawschatter.users.id IS '用戶唯一識別碼';
COMMENT ON COLUMN lawschatter.users.username IS '用戶名稱，系統內唯一';
COMMENT ON COLUMN lawschatter.users.email IS '電子郵件地址，系統內唯一';
COMMENT ON COLUMN lawschatter.users.name IS '用戶真實姓名';
COMMENT ON COLUMN lawschatter.users.password_hash IS '密碼雜湊值';
COMMENT ON COLUMN lawschatter.users.is_active IS '帳戶是否啟用';
COMMENT ON COLUMN lawschatter.users.created_at IS '帳戶建立時間';
COMMENT ON COLUMN lawschatter.users.updated_at IS '最後更新時間';
COMMENT ON COLUMN lawschatter.users.last_login IS '最後登入時間';

-- 角色表
CREATE TABLE lawschatter.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- 為 roles 表添加註解
COMMENT ON TABLE lawschatter.roles IS '角色表，定義系統中的用戶角色';
COMMENT ON COLUMN lawschatter.roles.id IS '角色唯一識別碼';
COMMENT ON COLUMN lawschatter.roles.name IS '角色名稱，系統內唯一';
COMMENT ON COLUMN lawschatter.roles.description IS '角色描述';

-- 用戶角色關聯表
CREATE TABLE lawschatter.user_roles (
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES lawschatter.users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES lawschatter.roles(id) ON DELETE CASCADE
);

-- 為 user_roles 表添加註解
COMMENT ON TABLE lawschatter.user_roles IS '用戶角色關聯表，記錄用戶與角色的多對多關係';
COMMENT ON COLUMN lawschatter.user_roles.user_id IS '用戶識別碼';
COMMENT ON COLUMN lawschatter.user_roles.role_id IS '角色識別碼';

-- 對話表
CREATE TABLE lawschatter.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES lawschatter.users(id) ON DELETE CASCADE
);

-- 為 conversations 表添加註解
COMMENT ON TABLE lawschatter.conversations IS '對話表，儲存用戶與聊天機器人的對話會話';
COMMENT ON COLUMN lawschatter.conversations.id IS '對話唯一識別碼';
COMMENT ON COLUMN lawschatter.conversations.user_id IS '對話所屬用戶識別碼';
COMMENT ON COLUMN lawschatter.conversations.title IS '對話標題';
COMMENT ON COLUMN lawschatter.conversations.created_at IS '對話建立時間';
COMMENT ON COLUMN lawschatter.conversations.updated_at IS '對話最後更新時間';

-- 訊息表
CREATE TABLE lawschatter.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('user', 'assistant')),
    content TEXT NOT NULL,
    model_used VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES lawschatter.conversations(id) ON DELETE CASCADE
);

-- 為 messages 表添加註解
COMMENT ON TABLE lawschatter.messages IS '訊息表，儲存對話中的每一條訊息';
COMMENT ON COLUMN lawschatter.messages.id IS '訊息唯一識別碼';
COMMENT ON COLUMN lawschatter.messages.conversation_id IS '所屬對話識別碼';
COMMENT ON COLUMN lawschatter.messages.sender_type IS '發送者類型（user用戶, assistant助理）';
COMMENT ON COLUMN lawschatter.messages.content IS '訊息內容';
COMMENT ON COLUMN lawschatter.messages.model_used IS '使用的AI模型名稱';
COMMENT ON COLUMN lawschatter.messages.created_at IS '訊息建立時間';

-- 訊息回饋表
CREATE TABLE lawschatter.message_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL,
    user_id UUID NOT NULL,
    rating VARCHAR(10) NOT NULL CHECK (rating IN ('like', 'dislike')),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES lawschatter.messages(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES lawschatter.users(id) ON DELETE CASCADE
);

-- 為 message_feedback 表添加註解
COMMENT ON TABLE lawschatter.message_feedback IS '訊息回饋表，收集用戶對AI回應的評價';
COMMENT ON COLUMN lawschatter.message_feedback.id IS '回饋唯一識別碼';
COMMENT ON COLUMN lawschatter.message_feedback.message_id IS '被評價的訊息識別碼';
COMMENT ON COLUMN lawschatter.message_feedback.user_id IS '提供回饋的用戶識別碼';
COMMENT ON COLUMN lawschatter.message_feedback.rating IS '評價等級（like喜歡, dislike不喜歡）';
COMMENT ON COLUMN lawschatter.message_feedback.comment IS '回饋評論內容';
COMMENT ON COLUMN lawschatter.message_feedback.created_at IS '回饋建立時間';

-- RAG 設定表
CREATE TABLE lawschatter.rag_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    selected_collections JSONB,
    start_date DATE,
    end_date DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES lawschatter.users(id) ON DELETE CASCADE
);

-- 為 rag_settings 表添加註解
COMMENT ON TABLE lawschatter.rag_settings IS 'RAG設定表，儲存用戶的檢索增強生成設定';
COMMENT ON COLUMN lawschatter.rag_settings.id IS 'RAG設定唯一識別碼';
COMMENT ON COLUMN lawschatter.rag_settings.user_id IS '設定所屬用戶識別碼';
COMMENT ON COLUMN lawschatter.rag_settings.selected_collections IS '選擇的文檔集合（JSON格式）';
COMMENT ON COLUMN lawschatter.rag_settings.start_date IS '搜索起始日期';
COMMENT ON COLUMN lawschatter.rag_settings.end_date IS '搜索結束日期';
COMMENT ON COLUMN lawschatter.rag_settings.updated_at IS '設定最後更新時間';

-- 用戶設置表
CREATE TABLE lawschatter.user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES lawschatter.users(id) ON DELETE CASCADE,
    UNIQUE(user_id, key)
);

-- 為 user_settings 表添加註解
COMMENT ON TABLE lawschatter.user_settings IS '用戶設置表，儲存用戶的個人化設定';
COMMENT ON COLUMN lawschatter.user_settings.id IS '設置唯一識別碼';
COMMENT ON COLUMN lawschatter.user_settings.user_id IS '設置所屬用戶識別碼';
COMMENT ON COLUMN lawschatter.user_settings.key IS '設置項目鍵名';
COMMENT ON COLUMN lawschatter.user_settings.value IS '設置項目值';
COMMENT ON COLUMN lawschatter.user_settings.updated_at IS '設置最後更新時間';

-- 搜索日誌表
CREATE TABLE lawschatter.search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    query_text TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filters_applied TEXT,
    result_count INTEGER,
    FOREIGN KEY (user_id) REFERENCES lawschatter.users(id) ON DELETE SET NULL
);

-- 為 search_logs 表添加註解
COMMENT ON TABLE lawschatter.search_logs IS '搜索日誌表，記錄用戶的搜索行為和結果';
COMMENT ON COLUMN lawschatter.search_logs.id IS '搜索日誌唯一識別碼';
COMMENT ON COLUMN lawschatter.search_logs.user_id IS '執行搜索的用戶識別碼（可為空，支援匿名搜索）';
COMMENT ON COLUMN lawschatter.search_logs.query_text IS '搜索查詢文本';
COMMENT ON COLUMN lawschatter.search_logs.timestamp IS '搜索執行時間';
COMMENT ON COLUMN lawschatter.search_logs.filters_applied IS '套用的搜索篩選條件';
COMMENT ON COLUMN lawschatter.search_logs.result_count IS '搜索結果數量';

-- 創建索引
CREATE INDEX idx_conversations_user_id ON lawschatter.conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON lawschatter.messages(conversation_id);
CREATE INDEX idx_message_feedback_message_id ON lawschatter.message_feedback(message_id);
CREATE INDEX idx_message_feedback_user_id ON lawschatter.message_feedback(user_id);
CREATE INDEX idx_user_settings_user_id ON lawschatter.user_settings(user_id);
CREATE INDEX idx_search_logs_user_id ON lawschatter.search_logs(user_id);
CREATE INDEX idx_search_logs_timestamp ON lawschatter.search_logs(timestamp);

-- 插入預設角色
INSERT INTO lawschatter.roles (name, description) VALUES 
('admin', '系統管理員'),
('user', '一般用戶');