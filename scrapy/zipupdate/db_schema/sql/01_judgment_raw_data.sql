-- Table 1: 原始 JSON 文檔 (正規化欄位)
CREATE TABLE IF NOT EXISTS lawschatter.main_judgments (
    jid TEXT PRIMARY KEY,
    jid_full TEXT,
    jyear INTEGER,
    jcase TEXT,
    jno TEXT,
    jdate INTEGER,
    jtitle TEXT,
    jfull TEXT,
    jpdf TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_main_judgments_jid ON lawschatter.main_judgments(jid);
CREATE INDEX IF NOT EXISTS idx_main_judgments_jyear ON lawschatter.main_judgments(jyear);
CREATE INDEX IF NOT EXISTS idx_main_judgments_jcase ON lawschatter.main_judgments(jcase);
CREATE INDEX IF NOT EXISTS idx_main_judgments_jdate ON lawschatter.main_judgments(jdate);
CREATE INDEX IF NOT EXISTS idx_main_judgments_created_at ON lawschatter.main_judgments(created_at);

-- 添加註釋
COMMENT ON TABLE lawschatter.main_judgments IS '存儲原始判決書數據（正規化欄位）';
COMMENT ON COLUMN lawschatter.main_judgments.jid IS '判決書唯一識別碼';
COMMENT ON COLUMN lawschatter.main_judgments.jyear IS '判決年份';
COMMENT ON COLUMN lawschatter.main_judgments.jcase IS '案件類型';
COMMENT ON COLUMN lawschatter.main_judgments.jno IS '案件編號';
COMMENT ON COLUMN lawschatter.main_judgments.jdate IS '判決日期';
COMMENT ON COLUMN lawschatter.main_judgments.jtitle IS '案件標題';
COMMENT ON COLUMN lawschatter.main_judgments.jfull IS '判決書完整內容';
COMMENT ON COLUMN lawschatter.main_judgments.jpdf IS 'PDF檔案下載連結';
COMMENT ON COLUMN lawschatter.main_judgments.created_at IS '記錄創建時間';
COMMENT ON COLUMN lawschatter.main_judgments.updated_at IS '記錄更新時間';