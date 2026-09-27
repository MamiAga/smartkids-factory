-- ============================================================================
-- OPTIONAL: least-privilege access for the Android app (anon / publishable key)
-- Run in Supabase SQL editor AFTER the new factory is deployed and tested.
--
-- Result:
--   Android (anon) can READ automation_control, pipeline_jobs, system_events
--   Android (anon) can UPDATE only the 5 control columns (enabled, daily target,
--   languages, schedule_time, timezone) of the single row id=1.
--   Everything else (jobs, heartbeats, episode_dna, voice registry) is written only by
--   the GitHub runner with SUPABASE_SECRET_KEY (service role bypasses RLS).
--
-- NOTE: RLS policies are OR-ed. If an older, broader policy exists (e.g. "allow all for anon"),
-- it keeps working until you drop it. List them first:
--   select tablename, policyname, cmd, roles from pg_policies where schemaname = 'public';
-- ============================================================================

ALTER TABLE automation_control ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_jobs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_events      ENABLE ROW LEVEL SECURITY;

-- table/column privileges
REVOKE INSERT, UPDATE, DELETE ON automation_control FROM anon;
GRANT SELECT ON automation_control TO anon;
GRANT UPDATE (enabled, daily_master_episodes, active_languages, schedule_time, timezone, updated_at)
  ON automation_control TO anon;

REVOKE INSERT, UPDATE, DELETE ON pipeline_jobs FROM anon;
GRANT SELECT ON pipeline_jobs TO anon;

REVOKE INSERT, UPDATE, DELETE ON system_events FROM anon;
GRANT SELECT ON system_events TO anon;

-- row policies
DROP POLICY IF EXISTS sk_anon_read_control   ON automation_control;
DROP POLICY IF EXISTS sk_anon_update_control ON automation_control;
DROP POLICY IF EXISTS sk_anon_read_jobs      ON pipeline_jobs;
DROP POLICY IF EXISTS sk_anon_read_events    ON system_events;

CREATE POLICY sk_anon_read_control   ON automation_control FOR SELECT TO anon USING (id = 1);
CREATE POLICY sk_anon_update_control ON automation_control FOR UPDATE TO anon USING (id = 1) WITH CHECK (
  id = 1 AND daily_master_episodes BETWEEN 1 AND 10
);
CREATE POLICY sk_anon_read_jobs      ON pipeline_jobs      FOR SELECT TO anon USING (true);
CREATE POLICY sk_anon_read_events    ON system_events      FOR SELECT TO anon USING (true);
