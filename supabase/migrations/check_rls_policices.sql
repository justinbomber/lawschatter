WITH policies AS (
  SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    p.polname AS policy_name,
    p.polcmd AS command,
    CASE
      WHEN p.polcmd = 'r' THEN 'SELECT'
      WHEN p.polcmd = 'a' THEN 'INSERT'
      WHEN p.polcmd = 'w' THEN 'UPDATE'
      WHEN p.polcmd = 'd' THEN 'DELETE'
      WHEN p.polcmd = 'r,a,w,d' OR p.polcmd = 'all' THEN 'ALL'
      ELSE p.polcmd
    END AS for_clause,
    pg_get_expr(p.polqual, p.polrelid) AS using_expr,
    pg_get_expr(p.polwithcheck, p.polrelid) AS with_check_expr,
    array_to_string(ARRAY(
      SELECT rolname FROM pg_roles WHERE oid = ANY(p.polroles)
    ), ',') AS roles
  FROM pg_policy p
  JOIN pg_class c ON c.oid = p.polrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'lawschatter'
)
SELECT
  '-- Table: ' || quote_ident(schema_name::text) || '.' || quote_ident(table_name::text) AS comment,
  'ALTER TABLE ' || quote_ident(schema_name::text) || '.' || quote_ident(table_name::text) || ' ENABLE ROW LEVEL SECURITY;' AS enable_rls,
  (
    'CREATE POLICY ' || quote_ident(policy_name::text)
    || ' ON ' || quote_ident(schema_name::text) || '.' || quote_ident(table_name::text)
    || ' FOR ' || COALESCE(for_clause::text, '')
    || CASE WHEN roles IS NOT NULL AND roles <> '' THEN ' TO ' || roles::text ELSE '' END
    || CASE WHEN using_expr IS NOT NULL THEN ' USING (' || using_expr::text || ')' ELSE '' END
    || CASE WHEN with_check_expr IS NOT NULL THEN ' WITH CHECK (' || with_check_expr::text || ')' ELSE '' END
    || ';'
  ) AS create_policy
FROM policies
ORDER BY schema_name, table_name, policy_name;