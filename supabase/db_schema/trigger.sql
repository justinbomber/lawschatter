CREATE OR REPLACE FUNCTION auth.handle_user_registration()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, public, lawschatter
AS $$
DECLARE
  v_target_schema text;
  v_username text;
  v_name text;
  v_email text;
BEGIN
  v_target_schema := COALESCE(NEW.raw_user_meta_data->>'target_schema', 'public');
  v_username := NULLIF(TRIM(COALESCE(NEW.raw_user_meta_data->>'username', '')), '');
  v_name := NULLIF(TRIM(COALESCE(NEW.raw_user_meta_data->>'name', '')), '');
  v_email := COALESCE(NEW.email, '');

  -- 白名單，避免任意 schema
  IF v_target_schema NOT IN ('public', 'lawschatter') THEN
    v_target_schema := 'public';
  END IF;

  IF v_target_schema = 'public' THEN
    IF v_username IS NULL THEN
      RAISE EXCEPTION 'username is required for public.users';
    END IF;

    INSERT INTO public.users (id, username, email, created_at, updated_at)
    VALUES (NEW.id, v_username, v_email, now(), now())
    ON CONFLICT (id) DO NOTHING;

  ELSIF v_target_schema = 'lawschatter' THEN
    IF v_username IS NULL OR v_name IS NULL THEN
      RAISE EXCEPTION 'username and name are required for lawschatter.profiles';
    END IF;

    INSERT INTO lawschatter.profiles (id, username, email, name, is_active, created_at, updated_at)
    VALUES (NEW.id, v_username, v_email, v_name, TRUE, now(), now())
    ON CONFLICT (id) DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$;

-- 綁定觸發器
DROP TRIGGER IF EXISTS on_auth_user_registered ON auth.users;

CREATE TRIGGER on_auth_user_registered
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION auth.handle_user_registration();


curl -X POST http://localhost:8000/auth/v1/signup -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJhbm9uIiwKICAgICJpc3MiOiAic3VwYWJhc2UtZGVtbyIsCiAgICAiaWF0IjogMTY0MTc2OTIwMCwKICAgICJleHAiOiAxNzk5NTM1NjAwCn0.dc_X5iR_VP_qT0zsiyj_I_OZ2T9FtRU2BBNWN8Bu4GE" -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJhbm9uIiwKICAgICJpc3MiOiAic3VwYWJhc2UtZGVtbyIsCiAgICAiaWF0IjogMTY0MTc2OTIwMCwKICAgICJleHAiOiAxNzk5NTM1NjAwCn0.dc_X5iR_VP_qT0zsiyj_I_OZ2T9FtRU2BBNWN8Bu4GE" -H "Content-Type: application/json" -d '{
"email": "ye222s@gmail.com",
"password": "yourpassword",
"data": {
"username": "justinbomber2",
"name": "Justin Wang 2",
"target_schema": "lawschatter"
}
}'