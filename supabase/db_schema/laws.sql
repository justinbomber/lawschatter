-- ================================
-- 法律判決書資料庫架構 (lawschatter schema)
-- 基於 cat_explain_fine-tune.md 的完整欄位定義
-- ================================

-- 建立 schema
CREATE SCHEMA IF NOT EXISTS lawschatter;

-- 主要判決資料表 (來源：原始JSON格式)
create table IF NOT EXISTS lawschatter.main_judgments (
  jid text not null,      -- JID: 案件識別碼
  jid_full text null,     -- JID_FULL: 案件識別碼全文
  jyear integer null,     -- JYEAR: 年度
  jcase text null,        -- JCASE: 案件類型
  jno text null,          -- JNO: 案件編號
  jdate integer null,     -- JDATE: 判決日期
  jtitle text null,       -- JTITLE: 標題
  jfull text null,        -- JFULL: 全文內容
  jpdf text null,         -- JPDF: PDF連結
  created_at timestamp with time zone null default CURRENT_TIMESTAMP,
  updated_at timestamp with time zone null default CURRENT_TIMESTAMP,
  constraint main_judgments_pkey1 primary key (jid) -- 主鍵
) TABLESPACE pg_default; -- 表空間

create index IF not exists idx_main_judgments_jid on lawschatter.main_judgments using btree (jid) TABLESPACE pg_default; -- 索引

create index IF not exists idx_main_judgments_jyear on lawschatter.main_judgments using btree (jyear) TABLESPACE pg_default;

create index IF not exists idx_main_judgments_jcase on lawschatter.main_judgments using btree (jcase) TABLESPACE pg_default;

create index IF not exists idx_main_judgments_jdate on lawschatter.main_judgments using btree (jdate) TABLESPACE pg_default;


create table lawschatter.judgment_summary (
  point_id uuid not null,
  jid text not null,
  summary_type lawschatter.summary_type not null,
  content text not null,
  created_at timestamp with time zone null default CURRENT_TIMESTAMP,
  updated_at timestamp with time zone null default CURRENT_TIMESTAMP,
  jdate integer null,
  defendent_name text null,
  constraint judgment_summary_pkey primary key (point_id),
  constraint judgment_summary_jid_fkey foreign KEY (jid) references lawschatter.main_judgments (jid) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_judgment_summary_hash_id on lawschatter.judgment_summary using btree (point_id) TABLESPACE pg_default;

create index IF not exists idx_judgment_summary_jdate on lawschatter.judgment_summary using btree (jdate) TABLESPACE pg_default;


-- 判決書分析資料表 (Embedding部分 - 完全依照cat_explain_fine-tune.md)
CREATE TABLE IF NOT EXISTS lawschatter.judgment_analysis (
    jid VARCHAR(100) PRIMARY KEY REFERENCES lawschatter.main_judgments(jid) ON DELETE CASCADE,
    
    -- Embedding 分析內容 (按照cat_explain_fine-tune.md順序)
    full_judgment_summary TEXT,                 -- 全文綜合摘要
    fraud_process TEXT,                         -- 詐騙手法與流程
    defendant_role_behavior TEXT,               -- 被告角色與行為
    witness_testimony TEXT,                     -- 證人證詞
    evidence_admissibility_analysis TEXT,       -- 證據能力評估
    conviction_sentencing TEXT,                 -- 定罪與量刑分析
    sentencing_factors TEXT,                    -- 量刑因素
    property_disposal_and_forfeiture TEXT,      -- 財產處置與沒收
    appeal_trial_information TEXT,              -- 上訴審相關資訊
    court_findings_summary TEXT,                -- 法院認定摘要
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 判決書元資料表 (Metadata部分 - 完全依照cat_explain_fine-tune.md)
CREATE TABLE IF NOT EXISTS lawschatter.judgment_metadata (
    jid VARCHAR(100) PRIMARY KEY REFERENCES lawschatter.main_judgments(jid) ON DELETE CASCADE,
    
    -- 分類一：基本案件資訊
    judgment_number VARCHAR(100),               -- 裁判字號
    judgment_date DATE,                         -- 裁判日期
    case_type TEXT[],                          -- 案由 (陣列)
    defendant_names TEXT[],                    -- 被告姓名 (陣列)
    defendant_count INTEGER,                   -- 被告人數
    defense_lawyer VARCHAR(200),               -- 辯護人姓名
    prosecutor_office VARCHAR(200),            -- 公訴機關
    court_name VARCHAR(200),                   -- 法院名稱與庭別
    judge_name VARCHAR(200),                   -- 法官姓名與職稱
    merged_case_number VARCHAR(100),           -- 合併審理案號
    is_appealed BOOLEAN,                       -- 是否上訴
    indictment_number VARCHAR(100),            -- 起訴字號
    is_additional_prosecution BOOLEAN,         -- 是否追加起訴
    involves_other_cases BOOLEAN,              -- 是否涉及其他案件
    defense_participation TEXT,                -- 辯護人參與程度
    is_reconciled_with_victim BOOLEAN,         -- 是否與被害人和解
    plea_status VARCHAR(20),                   -- 是否認罪 (true/false/partial)
    is_summary_judgment BOOLEAN,               -- 是否為簡易判決
    
    -- 分類三：被告角色與行為分析
    money_flow_participation BOOLEAN,          -- 是否參與金流操作
    court_credibility BOOLEAN,                 -- 法院是否採信
    is_principal_offender BOOLEAN,             -- 是否認定為正犯
    common_claim_pattern BOOLEAN,              -- 是否為常見主張模式
    
    -- 分類四：證人證詞
    has_witnesses BOOLEAN,                     -- 是否有證人
    witness_summoned_by TEXT[],                -- 證人由誰所傳喚 (陣列)
    witness_count INTEGER,                     -- 證人有幾位
    
    -- 分類五：證據能力評估
    involves_hearsay_evidence BOOLEAN,         -- 是否涉及傳聞證據條文
    
    -- 分類六：定罪與量刑分析
    ideal_concurrence BOOLEAN,                 -- 是否構成想像競合處理
    concurrence_charges TEXT[],                -- 想像競合所涵蓋罪名 (陣列)
    
    -- 分類七：量刑因素
    sentence_reduction_provisions BOOLEAN,     -- 是否有適用特定法條上之減刑事由
    
    -- 分類八：財產處置與沒收
    victim_names_amounts JSONB,                -- 被害人姓名與金額 (JSON格式)
    
    -- 分類九：上訴審相關資訊
    is_appeal_court BOOLEAN,                   -- 是否為上訴審
    original_case_number VARCHAR(100),         -- 原審案號
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================
-- 索引建立
-- ================================

-- 主要查詢索引
CREATE INDEX IF NOT EXISTS idx_main_judgments_jyear ON lawschatter.main_judgments(jyear);
CREATE INDEX IF NOT EXISTS idx_main_judgments_jcase ON lawschatter.main_judgments(jcase);
CREATE INDEX IF NOT EXISTS idx_main_judgments_jdate ON lawschatter.main_judgments(jdate);
CREATE INDEX IF NOT EXISTS idx_main_judgments_jtitle ON lawschatter.main_judgments(jtitle);
CREATE INDEX IF NOT EXISTS idx_main_judgments_jfull_hash ON lawschatter.main_judgments(jfull_hash);

-- 關聯查詢索引
CREATE INDEX IF NOT EXISTS idx_judgment_analysis_jid ON lawschatter.judgment_analysis(jid);
CREATE INDEX IF NOT EXISTS idx_judgment_metadata_jid ON lawschatter.judgment_metadata(jid);

-- 元資料查詢索引
CREATE INDEX IF NOT EXISTS idx_judgment_metadata_case_type ON lawschatter.judgment_metadata USING GIN(case_type);
CREATE INDEX IF NOT EXISTS idx_judgment_metadata_defendant_names ON lawschatter.judgment_metadata USING GIN(defendant_names);
CREATE INDEX IF NOT EXISTS idx_judgment_metadata_plea_status ON lawschatter.judgment_metadata(plea_status);
CREATE INDEX IF NOT EXISTS idx_judgment_metadata_is_appealed ON lawschatter.judgment_metadata(is_appealed);
CREATE INDEX IF NOT EXISTS idx_judgment_metadata_victim_names_amounts ON lawschatter.judgment_metadata USING GIN(victim_names_amounts);

-- ================================
-- 時間戳記觸發器
-- ================================

CREATE OR REPLACE FUNCTION set_created_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- UPDATE 觸發器函數 (設定updated_at)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 自動建立分析和元資料記錄觸發器函數 (當main_judgments插入時，自動在judgment_analysis和judgment_metadata建立對應記錄)
CREATE OR REPLACE FUNCTION create_judgment_analysis_and_metadata_records()
RETURNS TRIGGER AS $$
BEGIN
    -- 在judgment_analysis表中插入對應記錄
    INSERT INTO lawschatter.judgment_analysis (jid, created_at, updated_at)
    VALUES (NEW.jid, NOW(), NOW());
    
    -- 在judgment_metadata表中插入對應記錄
    INSERT INTO lawschatter.judgment_metadata (jid, created_at, updated_at)
    VALUES (NEW.jid, NOW(), NOW());
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- INSERT 觸發器 (設定created_at)
CREATE OR REPLACE TRIGGER set_main_judgments_created_at 
    BEFORE INSERT ON lawschatter.main_judgments 
    FOR EACH ROW EXECUTE FUNCTION set_created_at_column();

-- 自動建立分析和元資料記錄觸發器 (當main_judgments插入後，自動在judgment_analysis和judgment_metadata建立對應記錄)
CREATE OR REPLACE TRIGGER create_analysis_and_metadata_records_trigger
    AFTER INSERT ON lawschatter.main_judgments
    FOR EACH ROW EXECUTE FUNCTION create_judgment_analysis_and_metadata_records();

CREATE OR REPLACE TRIGGER set_judgment_analysis_created_at 
    BEFORE INSERT ON lawschatter.judgment_analysis 
    FOR EACH ROW EXECUTE FUNCTION set_created_at_column();

CREATE OR REPLACE TRIGGER set_judgment_metadata_created_at 
    BEFORE INSERT ON lawschatter.judgment_metadata 
    FOR EACH ROW EXECUTE FUNCTION set_created_at_column();

-- UPDATE 觸發器 (設定updated_at)
CREATE OR REPLACE TRIGGER update_main_judgments_updated_at 
    BEFORE UPDATE ON lawschatter.main_judgments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 清空相關表資料觸發器函數 (當main_judgments更新時，清空其他兩張表除了jid以外的所有資料)
CREATE OR REPLACE FUNCTION clear_analysis_and_metadata_data()
RETURNS TRIGGER AS $$
BEGIN
    -- 清空judgment_analysis表中除了jid以外的所有欄位
    UPDATE lawschatter.judgment_analysis 
    SET 
        full_judgment_summary = NULL,
        fraud_process = NULL,
        defendant_role_behavior = NULL,
        witness_testimony = NULL,
        evidence_admissibility_analysis = NULL,
        conviction_sentencing = NULL,
        sentencing_factors = NULL,
        property_disposal_and_forfeiture = NULL,
        appeal_trial_information = NULL,
        court_findings_summary = NULL,
        updated_at = NOW()
    WHERE jid = NEW.jid;
    
    -- 清空judgment_metadata表中除了jid以外的所有欄位
    UPDATE lawschatter.judgment_metadata 
    SET 
        judgment_number = NULL,
        judgment_date = NULL,
        case_type = NULL,
        defendant_names = NULL,
        defendant_count = NULL,
        defense_lawyer = NULL,
        prosecutor_office = NULL,
        court_name = NULL,
        judge_name = NULL,
        merged_case_number = NULL,
        is_appealed = NULL,
        indictment_number = NULL,
        is_additional_prosecution = NULL,
        involves_other_cases = NULL,
        defense_participation = NULL,
        is_reconciled_with_victim = NULL,
        plea_status = NULL,
        is_summary_judgment = NULL,
        money_flow_participation = NULL,
        court_credibility = NULL,
        is_principal_offender = NULL,
        common_claim_pattern = NULL,
        has_witnesses = NULL,
        witness_summoned_by = NULL,
        witness_count = NULL,
        involves_hearsay_evidence = NULL,
        ideal_concurrence = NULL,
        concurrence_charges = NULL,
        sentence_reduction_provisions = NULL,
        victim_names_amounts = NULL,
        is_appeal_court = NULL,
        original_case_number = NULL,
        updated_at = NOW()
    WHERE jid = NEW.jid;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 清空相關表資料觸發器 (當main_judgments更新後，清空其他兩張表的資料)
CREATE OR REPLACE TRIGGER clear_related_data_on_update_trigger
    AFTER UPDATE ON lawschatter.main_judgments
    FOR EACH ROW EXECUTE FUNCTION clear_analysis_and_metadata_data();

-- 注意：judgment_analysis 和 judgment_metadata 不再有獨立的 UPDATE 觸發器
-- 這兩張表的資料會在 main_judgments 更新時被清空重置

-- ================================
-- 註解說明
-- ================================

COMMENT ON TABLE lawschatter.main_judgments IS '主要判決資料表，存放原始JSON格式的判決書基本資訊。INSERT時會自動在相關表建立對應記錄，UPDATE時會清空相關表的分析資料';
COMMENT ON TABLE lawschatter.judgment_analysis IS '判決書分析結果，存放Embedding部分的各項分析內容，以jid為主鍵關聯main_judgments。當主表更新時會被清空重置';
COMMENT ON TABLE lawschatter.judgment_metadata IS '判決書元資料，存放Metadata部分的各項結構化資訊，以jid為主鍵關聯main_judgments。當主表更新時會被清空重置';

-- 主要欄位註解
COMMENT ON COLUMN lawschatter.main_judgments.jid IS '案件識別碼，格式如：CHDM,112,易,956,20250428,1';
COMMENT ON COLUMN lawschatter.main_judgments.jfull_hash IS '判決書核心內容（第300-500字元）SHA256 雜湊值，用於防止重複內容插入';
COMMENT ON COLUMN lawschatter.judgment_analysis.full_judgment_summary IS '全文綜合摘要，199-400字';
COMMENT ON COLUMN lawschatter.judgment_analysis.fraud_process IS '詐騙手法與流程分析，200-300字';
COMMENT ON COLUMN lawschatter.judgment_metadata.case_type IS '案由，以陣列形式儲存多個罪名';
COMMENT ON COLUMN lawschatter.judgment_metadata.defendant_names IS '被告姓名，以陣列形式儲存';
COMMENT ON COLUMN lawschatter.judgment_metadata.victim_names_amounts IS '被害人姓名與損失金額，JSON格式：{"姓名": 金額}';