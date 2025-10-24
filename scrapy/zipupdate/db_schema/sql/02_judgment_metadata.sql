-- Table 2: 處理過後的 JSON metadata (除了 summary)
CREATE TABLE IF NOT EXISTS lawschatter.judgment_metadata (
    jid TEXT PRIMARY KEY,
    jid_full TEXT,
    jyear INTEGER,
    jcase TEXT,
    jno TEXT,
    jdate INTEGER,
    jtitle TEXT,
    case_type TEXT,
    chunk_type TEXT,
    chunks TEXT[],
    defendants JSONB,
    case_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (jid) REFERENCES lawschatter.main_judgments(jid) ON DELETE CASCADE
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_judgment_metadata_jid ON lawschatter.judgment_metadata(jid);
CREATE INDEX IF NOT EXISTS idx_judgment_metadata_jyear ON lawschatter.judgment_metadata(jyear);
CREATE INDEX IF NOT EXISTS idx_judgment_metadata_jdate ON lawschatter.judgment_metadata(jdate);

-- 添加註釋
COMMENT ON TABLE lawschatter.judgment_metadata IS '存儲判決書處理後的元數據（不包含摘要）';
COMMENT ON COLUMN lawschatter.judgment_metadata.jid IS '判決書唯一識別碼';
COMMENT ON COLUMN lawschatter.judgment_metadata.jid_full IS '完整判決書標識';
COMMENT ON COLUMN lawschatter.judgment_metadata.jyear IS '判決年份';
COMMENT ON COLUMN lawschatter.judgment_metadata.jcase IS '案件類型';
COMMENT ON COLUMN lawschatter.judgment_metadata.jno IS '案件編號';
COMMENT ON COLUMN lawschatter.judgment_metadata.jdate IS '判決日期';
COMMENT ON COLUMN lawschatter.judgment_metadata.jtitle IS '案件標題';
COMMENT ON COLUMN lawschatter.judgment_metadata.case_type IS '案件分類';
COMMENT ON COLUMN lawschatter.judgment_metadata.chunk_type IS '文檔片段類型';
COMMENT ON COLUMN lawschatter.judgment_metadata.chunks IS '文檔內容片段陣列';
COMMENT ON COLUMN lawschatter.judgment_metadata.defendants IS '被告相關資訊';
COMMENT ON COLUMN lawschatter.judgment_metadata.case_metadata IS '案件元數據';