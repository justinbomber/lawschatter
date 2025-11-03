-- RPC 函數：獲取所有未嵌入的判決 ID（jid）
-- 條件：
-- 1. jid 同時存在於 judgment_metadata 及 main_judgments table
-- 2. jid 在 judgment_summary table 中有 embedded_1 = false 的記錄
-- 3. 按日期降序排列
CREATE OR REPLACE FUNCTION get_unembedded_jids_2()
RETURNS TABLE (
    jid TEXT,
    jdate TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        s.jid,
        s.jdate::TEXT
    FROM lawschatter.judgment_summary s
    INNER JOIN lawschatter.judgment_metadata m ON s.jid = m.jid
    INNER JOIN lawschatter.main_judgments j ON s.jid = j.jid
    WHERE s.embedded_2 = false
    ORDER BY s.jdate::TEXT DESC;
END;
$$ LANGUAGE plpgsql;

