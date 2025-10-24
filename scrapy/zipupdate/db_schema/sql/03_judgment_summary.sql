-- 建立摘要類型的enum
CREATE TYPE lawschatter.summary_type AS ENUM (
    'case_fact_summary',
    'role',
    'A_fact',
    'B_claim',
    'C_court_finding',
    'D_court_reason',
    'E_legal_eval',
    'case_highlights'
);

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

create index IF not exists idx_judgment_summary_defendent_name on lawschatter.judgment_summary using btree (defendent_name) TABLESPACE pg_default;

-- 添加註釋
COMMENT ON TYPE lawschatter.summary_type IS '判決書摘要分類類型：case_fact_summary(案件事實概要)、role(被告角色)、A_fact(行為事實)、B_claim(被告主張)、C_court_finding(法院認定)、D_court_reason(法院推論)、E_legal_eval(法律評價)、case_highlights(案件特殊點)';
COMMENT ON TABLE lawschatter.judgment_summary IS '存儲判決書摘要內容，支援分類與被告層級分析';
COMMENT ON COLUMN lawschatter.judgment_summary.point_id IS '摘要內容雜湊值';
COMMENT ON COLUMN lawschatter.judgment_summary.jid IS '判決書唯一識別碼';
COMMENT ON COLUMN lawschatter.judgment_summary.summary_type IS '摘要類型分類';
COMMENT ON COLUMN lawschatter.judgment_summary.content IS '摘要內容';
COMMENT ON COLUMN lawschatter.judgment_summary.defendent_name IS '被告姓名，僅被告層級欄位使用';