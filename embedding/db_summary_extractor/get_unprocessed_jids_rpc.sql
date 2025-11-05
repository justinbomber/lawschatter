-- RPC 函數：獲取所有未處理的判決 ID（jid 和 jdate）
-- 條件：
-- 1. jid 同時存在於 judgment_metadata 及 main_judgments table
-- 2. jid 不存在於 judgment_summary table
-- 3. judgment_metadata 的所有欄位不能為空值
-- 4. 按日期降序排列
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
    AND m.jid IS NOT NULL
    AND m.jid_full IS NOT NULL
    AND m.jyear IS NOT NULL
    AND m.jcase IS NOT NULL
    AND m.jno IS NOT NULL
    AND m.jdate IS NOT NULL
    AND m.jtitle IS NOT NULL
    AND m.case_type IS NOT NULL
    AND m.defendants IS NOT NULL
    AND m.case_metadata IS NOT NULL
    AND m.jtitle_type IS NOT NULL
    ORDER BY m.jdate::TEXT DESC;
END;
$$ LANGUAGE plpgsql;

