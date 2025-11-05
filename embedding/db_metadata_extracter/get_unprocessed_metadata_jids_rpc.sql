-- RPC 函數：獲取指定日期未處理的判決 ID（jid）
-- 條件：
-- 1. jid 存在於 main_judgments table
-- 2. jdate 符合指定日期
-- 3. jtitle 符合指定的標題列表
-- 4. jid 不存在於 judgment_metadata table
CREATE OR REPLACE FUNCTION get_unprocessed_metadata_jids(
    p_jdate INTEGER,
    p_target_titles TEXT[]
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
            SELECT 1
            FROM lawschatter.judgment_metadata m
            WHERE m.jid = j.jid
        )
    ORDER BY j.jid;
END;
$$ LANGUAGE plpgsql;

