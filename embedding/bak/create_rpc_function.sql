CREATE OR REPLACE FUNCTION lawschatter.get_unprocessed_jids(p_jdate text)
RETURNS SETOF text AS $$
  SELECT mj.jid
  FROM lawschatter.main_judgments mj
  WHERE mj.jdate = p_jdate
    AND mj.jfull IN ('詐欺等','詐欺','洗錢防制法等','洗錢防制法')
    AND NOT EXISTS (
      SELECT 1 FROM lawschatter.judgment_metadata jm WHERE jm.jid = mj.jid
    )
    AND NOT EXISTS (
      SELECT 1 FROM lawschatter.judgment_summary js WHERE js.jid = mj.jid
    );
$$ LANGUAGE sql STABLE;