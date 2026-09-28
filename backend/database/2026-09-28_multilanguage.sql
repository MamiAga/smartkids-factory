-- ============================================================================
-- SmartKids 2026-09-28 — 10 languages, distribution modes, parallel narration
-- Run ONCE in the Supabase SQL editor. Additive and idempotent (safe to run twice).
-- ============================================================================

-- 1) automation_control: new remote-control settings (Android writes them)
ALTER TABLE automation_control ADD COLUMN IF NOT EXISTS distribution_mode VARCHAR(32) NOT NULL DEFAULT 'SINGLE_CHANNEL_MULTI_AUDIO';
ALTER TABLE automation_control ADD COLUMN IF NOT EXISTS narrator_mode     VARCHAR(16) NOT NULL DEFAULT 'alternate';
ALTER TABLE automation_control ADD COLUMN IF NOT EXISTS tts_shards        INTEGER     NOT NULL DEFAULT 8;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'automation_control_distribution_mode_check') THEN
    ALTER TABLE automation_control ADD CONSTRAINT automation_control_distribution_mode_check
      CHECK (distribution_mode IN ('MULTI_CHANNEL', 'SINGLE_CHANNEL', 'SINGLE_CHANNEL_MULTI_AUDIO'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'automation_control_narrator_mode_check') THEN
    ALTER TABLE automation_control ADD CONSTRAINT automation_control_narrator_mode_check
      CHECK (narrator_mode IN ('alternate', 'female', 'male'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'automation_control_tts_shards_check') THEN
    ALTER TABLE automation_control ADD CONSTRAINT automation_control_tts_shards_check CHECK (tts_shards BETWEEN 1 AND 20);
  END IF;
END $$;

-- 2) pipeline_jobs: progress columns + the two new states (QUEUED, DUB_READY_FOR_STUDIO)
ALTER TABLE pipeline_jobs ADD COLUMN IF NOT EXISTS narrator          VARCHAR(16);
ALTER TABLE pipeline_jobs ADD COLUMN IF NOT EXISTS distribution_mode VARCHAR(32);
ALTER TABLE pipeline_jobs ADD COLUMN IF NOT EXISTS progress_pct      INTEGER;
ALTER TABLE pipeline_jobs ADD COLUMN IF NOT EXISTS stage_detail      TEXT;

DO $$ DECLARE c TEXT; BEGIN
  FOR c IN SELECT conname FROM pg_constraint
           WHERE conrelid = 'pipeline_jobs'::regclass AND contype = 'c'
             AND pg_get_constraintdef(oid) ILIKE '%state%IN%' LOOP
    EXECUTE format('ALTER TABLE pipeline_jobs DROP CONSTRAINT %I', c);
  END LOOP;
END $$;
ALTER TABLE pipeline_jobs ADD CONSTRAINT pipeline_jobs_state_check CHECK (state IN (
  'CREATED', 'QUEUED', 'VALIDATING', 'TTS_SYNTHESIS', 'RENDERING',
  'QA_TECHNICAL', 'QA_PEDAGOGICAL', 'UPLOADING', 'UPLOADED_PRIVATE',
  'PROCESSING', 'PROCESSED_PRIVATE', 'COMPLETED', 'DUB_READY_FOR_STUDIO',
  'FAILED_QA', 'FAILED_UPLOAD', 'QUARANTINED', 'QUOTA_PAUSED'
));

-- 3) Voice registry: every language is narrated by Chatterbox (MIT), timbre from a Kokoro-82M
--    (Apache-2.0) reference clip made by the factory itself. The old Piper rows (some non-commercial)
--    are replaced, so the commercial-voice trigger lets the 10 languages through.
INSERT INTO piper_voice_registry (
    voice_id, language, language_tier, model_name, model_path, model_sha256,
    engine_license, model_license, dataset_license, commercial_use,
    attribution_required, attribution_text, source_url, model_card_url, approved, reason
)
SELECT 'chatterbox_' || lower(l), l, 'PRODUCTION',
       CASE WHEN l = 'EN' THEN 'ResembleAI/chatterbox (English)' ELSE 'ResembleAI/chatterbox (Multilingual v2)' END,
       'huggingface:ResembleAI/chatterbox', 'pip chatterbox-tts==0.1.7',
       'MIT', 'MIT', 'Resemble AI model card (MIT)', TRUE, TRUE,
       'Voice: Chatterbox TTS (MIT License); reference voice Kokoro-82M (Apache License 2.0)',
       'https://github.com/resemble-ai/chatterbox', 'https://huggingface.co/ResembleAI/chatterbox', TRUE,
       'MIT licensed model + Apache-2.0 synthetic reference voice made in-house: commercial use permitted.'
FROM unnest(ARRAY['EN','ES','PT','FR','DE','IT','TR','RU','AR','HI']) AS l
ON CONFLICT (language) DO UPDATE SET
    voice_id = EXCLUDED.voice_id, language_tier = EXCLUDED.language_tier, model_name = EXCLUDED.model_name,
    model_path = EXCLUDED.model_path, model_sha256 = EXCLUDED.model_sha256, engine_license = EXCLUDED.engine_license,
    model_license = EXCLUDED.model_license, dataset_license = EXCLUDED.dataset_license,
    commercial_use = TRUE, attribution_required = TRUE, attribution_text = EXCLUDED.attribution_text,
    source_url = EXCLUDED.source_url, model_card_url = EXCLUDED.model_card_url, approved = TRUE,
    reason = EXCLUDED.reason, updated_at = NOW();

-- 4) Android (anon key) may change the new control columns too (only matters if
--    supabase_rls_hardening.sql was applied; harmless otherwise)
GRANT UPDATE (distribution_mode, narrator_mode, tts_shards) ON automation_control TO anon;

-- check
SELECT id, enabled, active_languages, distribution_mode, narrator_mode, tts_shards FROM automation_control;
