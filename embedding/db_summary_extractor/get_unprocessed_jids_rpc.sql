-- RPC 函數：獲取所有未處理的判決 ID（jid 和 jdate）
-- 條件：
-- 1. jid 同時存在於 judgment_metadata 及 main_judgments table
-- 2. jid 不存在於 judgment_summary table
-- 3. 按日期降序排列
CREATE OR REPLACE FUNCTION get_unprocessed_summary_jids()
RETURNS TABLE (
    jid TEXT,
    jdate TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        m.jid,
        m.jdate::TEXT
    FROM lawschatter.judgment_metadata m
    INNER JOIN lawschatter.main_judgments j ON m.jid = j.jid
    WHERE NOT EXISTS (
        SELECT 1
        FROM lawschatter.judgment_summary s
        WHERE s.jid = m.jid
    )
    ORDER BY m.jdate::TEXT DESC;
END;
$$ LANGUAGE plpgsql;

