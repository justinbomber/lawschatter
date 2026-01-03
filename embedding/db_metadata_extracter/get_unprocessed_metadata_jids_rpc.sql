-- RPC 函數：獲取指定日期未處理的判決 ID（jid）
-- 條件：
-- 1. jid 存在於 main_judgments table
-- 2. jdate 符合指定日期
-- 3. jtitle 符合指定的標題列表
-- 4. jid 不存在於 judgment_metadata table
-- 5. 根據 p_include_ruling 參數決定是否包含"裁定"（檢查 jfull 前 20 字元）
--    - TRUE: 包含全部判決（不做裁定篩選）
--    - FALSE: 排除包含"裁定"的判決
CREATE OR REPLACE FUNCTION get_unprocessed_metadata_jids(
    p_jdate INTEGER,
    p_target_titles TEXT[],
    p_include_ruling BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    jid TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        j.jid
    FROM lawschatter.main_judgments j
    WHERE j.jdate = p_jdate
        AND j.jtitle = ANY(p_target_titles)
        AND NOT EXISTS (
            SELECT 1, distinct=True
        
            FROM lawschatter.judgment_metadata m
            WHERE m.jid = j.jid
        )
        AND (
            p_include_ruling = TRUE
            OR LEFT(j.jfull, 20) NOT LIKE '%裁定%'
        )
    ORDER BY j.jid;
END;
$$ LANGUAGE plpgsql;


-- get unique jdates
CREATE OR REPLACE FUNCTION get_unique_jdates()
RETURNS TABLE(jdate DATE) AS $$
BEGIN
    RETURN QUERY 
    SELECT DISTINCT m.jdate 
    FROM lawschatter.main_judgments m
    ORDER BY m.jdate DESC;
END;
$$ LANGUAGE plpgsql;

