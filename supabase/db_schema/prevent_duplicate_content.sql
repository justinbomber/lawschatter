-- ================================
-- 防止重複判決書內容的解決方案
-- 針對 jfull 欄位內容重複的防範機制
-- ================================

-- ================================
-- 注意：此方案不使用任何 PostgreSQL 擴展
-- 使用內建函數實現防重複機制
-- ================================

-- 1. 為 main_judgments 表新增內容雜湊欄位
ALTER TABLE lawschatter.main_judgments 
ADD COLUMN IF NOT EXISTS jfull_hash VARCHAR(64) UNIQUE;

-- 2. 建立文字搜索索引（使用預設配置）
-- 為 jfull 欄位建立 GIN 索引用於全文搜索，使用 simple 配置
CREATE INDEX IF NOT EXISTS idx_main_judgments_jfull_gin 
ON lawschatter.main_judgments 
USING gin (to_tsvector('simple', jfull));

-- 為 jfull_hash 建立索引（用於精確重複檢查）
CREATE INDEX IF NOT EXISTS idx_main_judgments_jfull_hash 
ON lawschatter.main_judgments (jfull_hash);

-- 為 jfull 前 100 字元建立 B-tree 索引（用於前綴匹配）
CREATE INDEX IF NOT EXISTS idx_main_judgments_jfull_md5 
ON lawschatter.main_judgments (md5(jfull));-- 3. 建立內容雜湊計算函數（只對第300-500字元進行hash）
-- 使用 PostgreSQL 內建的 hashtext 函數，不需要擴展
CREATE OR REPLACE FUNCTION calculate_jfull_hash(content TEXT)
RETURNS VARCHAR(64) AS $$
DECLARE
    cleaned_content TEXT;
    content_length INTEGER;
    hash_content TEXT;
    hash_int INTEGER;
    hash_hex TEXT;
BEGIN
    -- 移除多餘空白並標準化
    cleaned_content := trim(regexp_replace(content, '\s+', ' ', 'g'));
    content_length := length(cleaned_content);
    
    -- 處理不同長度的內容
    IF content_length < 300 THEN
        -- 如果內容少於300字元，使用全部內容
        hash_content := cleaned_content;
    ELSIF content_length < 500 THEN
        -- 如果內容在300-500字元之間，取第300字元到結尾
        hash_content := substring(cleaned_content FROM 300);
    ELSE
        -- 如果內容超過500字元，取第300-500字元（共300個字元）
        hash_content := substring(cleaned_content FROM 300 FOR 300);
    END IF;
    
    -- 使用內建 hashtext 函數計算雜湊值
    hash_int := hashtext(hash_content);
    
    -- 將整數轉換為16進制字串，並加上內容長度增加唯一性
    hash_hex := lpad(to_hex(abs(hash_int)), 8, '0') || 
                lpad(to_hex(length(hash_content)), 8, '0') ||
                lpad(to_hex(content_length), 8, '0');
    
    RETURN hash_hex;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 4. 建立重複內容檢查函數
CREATE OR REPLACE FUNCTION check_duplicate_jfull_content(new_content TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    content_hash VARCHAR(64);
    existing_count INTEGER;
BEGIN
    -- 計算新內容的雜湊值
    content_hash := calculate_jfull_hash(new_content);
    
    -- 檢查是否已存在相同雜湊值
    SELECT COUNT(*) INTO existing_count
    FROM lawschatter.main_judgments
    WHERE jfull_hash = content_hash;
    
    -- 如果找到重複，回傳 true
    RETURN existing_count > 0;
END;
$$ LANGUAGE plpgsql;

-- 5. 建立基本文字相似度檢查函數（使用字串長度和內容匹配）
-- 不使用 pg_trgm 擴展，改用簡單的相似度計算
CREATE OR REPLACE FUNCTION check_similar_jfull_content(
    new_content TEXT, 
    length_diff_threshold INTEGER DEFAULT 100,
    sample_match_threshold INTEGER DEFAULT 3
)
RETURNS TABLE(jid VARCHAR(100), similarity_type TEXT, match_info TEXT) AS $$
DECLARE
    new_content_length INTEGER;
    sample_text TEXT;
BEGIN
    -- 計算新內容的長度
    new_content_length := length(trim(regexp_replace(new_content, '\s+', ' ', 'g')));
    
    -- 取得用於比較的樣本文字（第200-400字元）
    sample_text := substring(trim(regexp_replace(new_content, '\s+', ' ', 'g')) FROM 200 FOR 200);
    
    RETURN QUERY
    SELECT 
        mj.jid,
        CASE 
            WHEN abs(length(trim(regexp_replace(mj.jfull, '\s+', ' ', 'g'))) - new_content_length) <= length_diff_threshold 
                 AND position(sample_text IN mj.jfull) > 0 
            THEN '高度相似（長度+內容匹配）'
            WHEN abs(length(trim(regexp_replace(mj.jfull, '\s+', ' ', 'g'))) - new_content_length) <= length_diff_threshold 
            THEN '中度相似（長度相近）'
            WHEN position(sample_text IN mj.jfull) > 0 
            THEN '內容片段匹配'
            ELSE '其他'
        END AS similarity_type,
        format('原文長度: %s, 新文長度: %s, 長度差: %s', 
               length(trim(regexp_replace(mj.jfull, '\s+', ' ', 'g'))), 
               new_content_length,
               abs(length(trim(regexp_replace(mj.jfull, '\s+', ' ', 'g'))) - new_content_length)
        ) AS match_info
    FROM lawschatter.main_judgments mj
    WHERE mj.jfull IS NOT NULL
      AND (
          -- 長度相近的記錄
          abs(length(trim(regexp_replace(mj.jfull, '\s+', ' ', 'g'))) - new_content_length) <= length_diff_threshold
          OR
          -- 包含相同文字片段的記錄
          position(sample_text IN mj.jfull) > 0
      )
    ORDER BY 
        CASE 
            WHEN abs(length(trim(regexp_replace(mj.jfull, '\s+', ' ', 'g'))) - new_content_length) <= length_diff_threshold 
                 AND position(sample_text IN mj.jfull) > 0 
            THEN 1
            WHEN abs(length(trim(regexp_replace(mj.jfull, '\s+', ' ', 'g'))) - new_content_length) <= length_diff_threshold 
            THEN 2
            WHEN position(sample_text IN mj.jfull) > 0 
            THEN 3
            ELSE 4
        END,
        abs(length(trim(regexp_replace(mj.jfull, '\s+', ' ', 'g'))) - new_content_length)
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- 6. 建立防重複插入觸發器函數
CREATE OR REPLACE FUNCTION prevent_duplicate_jfull_insert()
RETURNS TRIGGER AS $$
DECLARE
    content_hash VARCHAR(64);
    duplicate_found BOOLEAN;
    similar_records RECORD;
BEGIN
    -- 計算新內容的雜湊值
    content_hash := calculate_jfull_hash(NEW.jfull);
    NEW.jfull_hash := content_hash;
    
    -- 檢查雜湊值重複（精確匹配）
    duplicate_found := check_duplicate_jfull_content(NEW.jfull);
    
    IF duplicate_found THEN
        RAISE EXCEPTION '判決書內容重複：已存在相同內容的判決書記錄 (Hash: %)', content_hash
        USING HINT = '請檢查是否為重複資料',
              ERRCODE = '23505'; -- unique_violation
    END IF;
    
    -- 可選：檢查高相似度內容（警告但不阻止）
    FOR similar_records IN 
        SELECT * FROM check_similar_jfull_content(NEW.jfull, 50, 3)
    LOOP
        RAISE NOTICE '發現相似判決書內容：JID = %, 類型 = %, 資訊 = %', 
            similar_records.jid, similar_records.similarity_type, similar_records.match_info;
    END LOOP;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7. 建立觸發器
CREATE OR REPLACE TRIGGER prevent_duplicate_jfull_trigger
    BEFORE INSERT ON lawschatter.main_judgments
    FOR EACH ROW EXECUTE FUNCTION prevent_duplicate_jfull_insert();

-- 8. 為現有資料生成雜湊值的更新函數
CREATE OR REPLACE FUNCTION update_existing_jfull_hashes()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER := 0;
    record_data RECORD;
BEGIN
    FOR record_data IN 
        SELECT jid, jfull 
        FROM lawschatter.main_judgments 
        WHERE jfull_hash IS NULL AND jfull IS NOT NULL
    LOOP
        UPDATE lawschatter.main_judgments 
        SET jfull_hash = calculate_jfull_hash(record_data.jfull)
        WHERE jid = record_data.jid;
        
        updated_count := updated_count + 1;
    END LOOP;
    
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- 9. 建立重複檢查視圖（用於管理和監控）
CREATE OR REPLACE VIEW lawschatter.duplicate_content_analysis AS
SELECT 
    jfull_hash,
    COUNT(*) as duplicate_count,
    array_agg(jid) as duplicate_jids,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM lawschatter.main_judgments 
WHERE jfull_hash IS NOT NULL
GROUP BY jfull_hash
HAVING COUNT(*) > 1;

-- 10. 建立內容清理和合併函數（處理已存在的重複）
CREATE OR REPLACE FUNCTION merge_duplicate_content_records(target_hash VARCHAR(64))
RETURNS TEXT AS $$
DECLARE
    keep_jid VARCHAR(100);
    delete_jids VARCHAR(100)[];
    result_message TEXT;
BEGIN
    -- 選擇要保留的記錄（通常是最早的）
    SELECT jid INTO keep_jid
    FROM lawschatter.main_judgments
    WHERE jfull_hash = target_hash
    ORDER BY created_at ASC
    LIMIT 1;
    
    -- 取得要刪除的記錄列表
    SELECT array_agg(jid) INTO delete_jids
    FROM lawschatter.main_judgments
    WHERE jfull_hash = target_hash AND jid != keep_jid;
    
    -- 刪除重複記錄
    DELETE FROM lawschatter.main_judgments
    WHERE jfull_hash = target_hash AND jid != keep_jid;
    
    result_message := format(
        '已合併重複內容記錄。保留 JID: %s，刪除 JID: %s',
        keep_jid,
        array_to_string(delete_jids, ', ')
    );
    
    RETURN result_message;
END;
$$ LANGUAGE plpgsql;

-- ================================
-- 使用說明和建議
-- ================================

-- 立即為現有資料生成雜湊值：
-- SELECT update_existing_jfull_hashes();

-- 檢查現有重複資料：
-- SELECT * FROM lawschatter.duplicate_content_analysis;

-- 合併特定重複資料（例子）：
-- SELECT merge_duplicate_content_records('your_hash_value_here');

-- 檢查新內容是否重複（插入前檢查）：
-- SELECT check_duplicate_jfull_content('您的判決書內容...');

-- 檢查相似內容（新版本）：
-- SELECT * FROM check_similar_jfull_content('您的判決書內容...', 100, 3);

-- 測試 hash 計算（查看不同長度內容的處理方式）：
-- SELECT 
--     length('您的內容') as original_length,
--     calculate_jfull_hash('您的內容') as hash_value;

-- 11. 建立 hash 機制測試和說明函數
CREATE OR REPLACE FUNCTION test_hash_mechanism(content TEXT)
RETURNS TABLE(
    original_length INTEGER,
    cleaned_length INTEGER,
    hash_range_start INTEGER,
    hash_range_end INTEGER,
    hash_content_preview TEXT,
    hash_value VARCHAR(64)
) AS $$
DECLARE
    cleaned_content TEXT;
    content_length INTEGER;
    hash_content TEXT;
    range_start INTEGER;
    range_end INTEGER;
BEGIN
    -- 清理內容
    cleaned_content := trim(regexp_replace(content, '\s+', ' ', 'g'));
    content_length := length(cleaned_content);
    
    -- 決定hash範圍
    IF content_length < 300 THEN
        range_start := 1;
        range_end := content_length;
        hash_content := cleaned_content;
    ELSIF content_length < 500 THEN
        range_start := 300;
        range_end := content_length;
        hash_content := substring(cleaned_content FROM 300);
    ELSE
        range_start := 300;
        range_end := 500;
        hash_content := substring(cleaned_content FROM 300 FOR 300);
    END IF;
    
    RETURN QUERY SELECT 
        length(content),
        content_length,
        range_start,
        range_end,
        left(hash_content, 50) || '...' AS preview,
        calculate_jfull_hash(content);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_jfull_hash(TEXT) IS '計算判決書內容的雜湊值，使用內建 hashtext 函數，專注於第300-500字元範圍的核心內容，用於精確重複檢測';
COMMENT ON FUNCTION check_duplicate_jfull_content(TEXT) IS '檢查判決書內容是否已存在（精確匹配）';
COMMENT ON FUNCTION check_similar_jfull_content(TEXT, INTEGER, INTEGER) IS '使用字串長度和內容片段匹配檢查相似的判決書內容，不需要任何 PostgreSQL 擴展';
COMMENT ON FUNCTION test_hash_mechanism(TEXT) IS '測試和分析 hash 機制的運作方式，顯示不同長度內容的處理邏輯';
COMMENT ON VIEW lawschatter.duplicate_content_analysis IS '重複內容分析視圖，用於識別和管理重複的判決書';
