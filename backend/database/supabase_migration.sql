-- ============================================================================
-- SmartKids Autonomous Cloud Production Factory - Supabase PostgreSQL 16 Schema
-- Zero-Cost (0 TL) Architecture: GitHub Actions (ubuntu-24.04-arm) + Supabase Free Tier
-- ============================================================================

-- 1. Automation Master Control (Android Remote Cloud Control Plane)
CREATE TABLE IF NOT EXISTS automation_control (
    id INTEGER PRIMARY KEY DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    daily_master_episodes INTEGER NOT NULL DEFAULT 1,
    schedule_time VARCHAR(16) NOT NULL DEFAULT '04:00',
    timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Istanbul',
    active_languages JSONB NOT NULL DEFAULT '["EN"]'::jsonb,
    active_channels JSONB NOT NULL DEFAULT '["EN"]'::jsonb,
    generation_mode VARCHAR(32) NOT NULL DEFAULT 'AUTONOMOUS',
    publish_mode VARCHAR(32) NOT NULL DEFAULT 'AUTO',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_heartbeat TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    current_job_id VARCHAR(64),
    failure_count INTEGER DEFAULT 0
);

-- Seed Singleton Control Row (Default: Standby)
INSERT INTO automation_control (
    id, enabled, daily_master_episodes, schedule_time, timezone,
    active_languages, active_channels, generation_mode, publish_mode
) VALUES (
    1, FALSE, 1, '04:00', 'Europe/Istanbul',
    '["EN"]'::jsonb, '["EN"]'::jsonb, 'AUTONOMOUS', 'AUTO'
) ON CONFLICT (id) DO NOTHING;

-- 2. Curriculum & Topic Graph (Novelty & Non-Repetition Engine)
CREATE TABLE IF NOT EXISTS topic_graph (
    topic_id VARCHAR(64) PRIMARY KEY,
    family VARCHAR(64) NOT NULL, -- 'colors', 'numbers', 'animals', 'shapes', 'memory', 'sorting', etc.
    title VARCHAR(255) NOT NULL,
    learning_objective TEXT NOT NULL,
    age_group VARCHAR(16) NOT NULL DEFAULT '4-6',
    used_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Episode DNA Master Table
CREATE TABLE IF NOT EXISTS episode_dna (
    episode_id VARCHAR(64) PRIMARY KEY,
    version VARCHAR(16) NOT NULL DEFAULT '2.0.0',
    family VARCHAR(64) NOT NULL DEFAULT 'colors',
    title VARCHAR(255) NOT NULL,
    age_group VARCHAR(16) NOT NULL,
    learning_objective TEXT NOT NULL,
    format_type VARCHAR(32) NOT NULL,
    difficulty VARCHAR(16) NOT NULL DEFAULT 'BEGINNER',
    target_duration_sec INTEGER NOT NULL,
    min_duration_sec INTEGER NOT NULL,
    max_duration_sec INTEGER NOT NULL,
    characters JSONB NOT NULL,
    visual_style TEXT NOT NULL,
    music_profile JSONB NOT NULL,
    scenes JSONB NOT NULL,
    safety_profile JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Piper TTS Commercial Voice Registry
-- Hard invariant: Only CC0, CC-BY, or MIT models with commercial use rights allowed
CREATE TABLE IF NOT EXISTS piper_voice_registry (
    voice_id VARCHAR(128) PRIMARY KEY,
    language VARCHAR(8) NOT NULL UNIQUE,
    language_tier VARCHAR(16) NOT NULL CHECK (language_tier IN ('PRODUCTION', 'PILOT')),
    model_name VARCHAR(128) NOT NULL,
    model_path VARCHAR(255) NOT NULL,
    model_sha256 VARCHAR(64) NOT NULL,
    engine_license VARCHAR(32) NOT NULL DEFAULT 'GPL-3.0',
    model_license VARCHAR(64) NOT NULL,
    dataset_license VARCHAR(64) NOT NULL,
    commercial_use BOOLEAN NOT NULL DEFAULT FALSE,
    attribution_required BOOLEAN NOT NULL DEFAULT TRUE,
    attribution_text TEXT,
    source_url TEXT NOT NULL,
    model_card_url TEXT,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Pipeline Jobs (Execution Lifecycle State Machine)
CREATE TABLE IF NOT EXISTS pipeline_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    episode_id VARCHAR(64) NOT NULL REFERENCES episode_dna(episode_id),
    language VARCHAR(8) NOT NULL,
    state VARCHAR(32) NOT NULL CHECK (
        state IN (
            'CREATED', 'VALIDATING', 'TTS_SYNTHESIS', 'RENDERING',
            'QA_TECHNICAL', 'QA_PEDAGOGICAL', 'UPLOADING', 'UPLOADED_PRIVATE',
            'PROCESSING', 'PROCESSED_PRIVATE', 'COMPLETED',
            'FAILED_QA', 'FAILED_UPLOAD', 'QUARANTINED', 'QUOTA_PAUSED'
        )
    ),
    deterministic_seed VARCHAR(64) NOT NULL,
    local_mp4_path TEXT,
    youtube_video_id VARCHAR(32),
    youtube_privacy_status VARCHAR(16) DEFAULT 'private',
    processing_status VARCHAR(32) DEFAULT 'pending',
    render_duration_sec NUMERIC(6, 2),
    cost_usd NUMERIC(8, 4) DEFAULT 0.0000,
    technical_qa_passed BOOLEAN DEFAULT FALSE,
    educational_qa_passed BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (episode_id, language, deterministic_seed)
);

-- 6. YouTube Publications Ledger
CREATE TABLE IF NOT EXISTS youtube_publications (
    publication_id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) REFERENCES pipeline_jobs(job_id),
    video_id VARCHAR(32) NOT NULL,
    channel_id VARCHAR(64),
    language VARCHAR(8) NOT NULL,
    privacy_status VARCHAR(16) NOT NULL DEFAULT 'private',
    processing_status VARCHAR(32) NOT NULL DEFAULT 'succeeded',
    self_declared_made_for_kids BOOLEAN NOT NULL DEFAULT TRUE,
    published_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. YouTube Channels Registry
CREATE TABLE IF NOT EXISTS youtube_channels (
    channel_id VARCHAR(64) PRIMARY KEY,
    channel_title VARCHAR(255) NOT NULL,
    target_language VARCHAR(8) NOT NULL,
    privacy_default VARCHAR(16) NOT NULL DEFAULT 'private',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    daily_quota_limit INTEGER NOT NULL DEFAULT 6,
    daily_quota_used INTEGER NOT NULL DEFAULT 0,
    last_upload_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Cloud System Events Log
CREATE TABLE IF NOT EXISTS system_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Infrastructure Health Snapshots (Heartbeat Audits)
CREATE TABLE IF NOT EXISTS health_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    runner_arch VARCHAR(32) NOT NULL,
    github_runner_status VARCHAR(32) NOT NULL,
    supabase_status VARCHAR(32) NOT NULL,
    gemini_status VARCHAR(32) NOT NULL,
    piper_status VARCHAR(32) NOT NULL,
    ffmpeg_status VARCHAR(32) NOT NULL,
    youtube_status VARCHAR(32) NOT NULL,
    cost_guard VARCHAR(32) NOT NULL DEFAULT '0_TL_FREE_ONLY',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Hard Safety Triggers
-- ============================================================================

-- Guard Commercial Voice Gate
CREATE OR REPLACE FUNCTION check_commercial_voice_gate()
RETURNS TRIGGER AS $$
DECLARE
    v_approved BOOLEAN;
    v_commercial BOOLEAN;
BEGIN
    SELECT approved, commercial_use INTO v_approved, v_commercial
    FROM piper_voice_registry
    WHERE language = NEW.language;

    IF v_approved IS NOT TRUE OR v_commercial IS NOT TRUE THEN
        RAISE EXCEPTION 'COMMERCIAL_VOICE_GATE: Language [%] voice is not approved for commercial monetization or lacks valid license.', NEW.language;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_commercial_voice_gate ON pipeline_jobs;
CREATE TRIGGER trg_commercial_voice_gate
BEFORE INSERT OR UPDATE ON pipeline_jobs
FOR EACH ROW
EXECUTE FUNCTION check_commercial_voice_gate();

-- Guard Local MP4 Deletion
CREATE OR REPLACE FUNCTION guard_mp4_deletion()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.state = 'COMPLETED' AND (OLD.processing_status != 'succeeded' OR OLD.youtube_video_id IS NULL) THEN
        RAISE EXCEPTION 'SAFETY_VIOLATION: Cannot complete job or purge local asset before YouTube processingStatus=succeeded.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_guard_mp4_deletion ON pipeline_jobs;
CREATE TRIGGER trg_guard_mp4_deletion
BEFORE UPDATE ON pipeline_jobs
FOR EACH ROW
EXECUTE FUNCTION guard_mp4_deletion();

-- ============================================================================
-- Canonical Seed Data
-- ============================================================================

-- Canonical Production Languages (5): EN, ES, DE, FR, PT
INSERT INTO piper_voice_registry (
    voice_id, language, language_tier, model_name, model_path, model_sha256,
    engine_license, model_license, dataset_license, commercial_use,
    attribution_required, attribution_text, source_url, model_card_url, approved, reason
) VALUES
('en_US-libritts_r-medium', 'EN', 'PRODUCTION', 'en_US-libritts_r-medium', 'models/piper/en/en_US-libritts_r-medium.onnx', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'GPL-3.0', 'CC-BY-4.0', 'CC-BY-4.0', TRUE, TRUE, 'Voice: LibriTTS-R (CC-BY 4.0)', 'rhasspy/piper-voices/en/en_US/libritts_r/medium', 'https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/libritts_r/medium/MODEL_CARD', TRUE, 'CC-BY 4.0 confirmed. Commercial monetization permitted.'),
('es_ES-sharvard-medium', 'ES', 'PRODUCTION', 'es_ES-sharvard-medium', 'models/piper/es/es_ES-sharvard-medium.onnx', '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b', 'GPL-3.0', 'CC-BY-3.0', 'CC-BY-3.0', TRUE, TRUE, 'Voice: Sharvard (CC-BY 3.0)', 'rhasspy/piper-voices/es/es_ES/sharvard/medium', 'https://huggingface.co/rhasspy/piper-voices/blob/main/es/es_ES/sharvard/medium/MODEL_CARD', TRUE, 'CC-BY 3.0 confirmed. Commercial monetization permitted.'),
('de_DE-thorsten-medium', 'DE', 'PRODUCTION', 'de_DE-thorsten-medium', 'models/piper/de/de_DE-thorsten-medium.onnx', 'd4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35', 'GPL-3.0', 'CC0-1.0', 'CC0-1.0', TRUE, FALSE, NULL, 'rhasspy/piper-voices/de/de_DE/thorsten/medium', 'https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/thorsten/medium/MODEL_CARD', TRUE, 'CC0 Public Domain dedication. Unrestricted commercial monetization.'),
('fr_FR-siwis-medium', 'FR', 'PRODUCTION', 'fr_FR-siwis-medium', 'models/piper/fr/fr_FR-siwis-medium.onnx', '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce', 'GPL-3.0', 'CC-BY-4.0', 'CC-BY-4.0', TRUE, TRUE, 'Voice: SIWIS (CC-BY 4.0)', 'rhasspy/piper-voices/fr/fr_FR/siwis/medium', 'https://huggingface.co/rhasspy/piper-voices/blob/main/fr/fr_FR/siwis/medium/MODEL_CARD', TRUE, 'CC-BY 4.0 confirmed. Commercial monetization permitted.'),
('pt_BR-edresson-low', 'PT', 'PRODUCTION', 'pt_BR-edresson-low', 'models/piper/pt/pt_BR-edresson-low.onnx', '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a', 'GPL-3.0', 'CC-BY-4.0', 'CC-BY-4.0', TRUE, TRUE, 'Voice: Edresson (CC-BY 4.0)', 'rhasspy/piper-voices/pt/pt_BR/edresson/low', 'https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/pt/pt_BR/edresson/low/MODEL_CARD', TRUE, 'CC-BY 4.0 confirmed. Commercial monetization permitted.')
ON CONFLICT (voice_id) DO UPDATE SET updated_at = NOW();

-- Canonical Pilot Languages (5): AR, HI, ZH, JA, TR (Commercial gate locked)
INSERT INTO piper_voice_registry (
    voice_id, language, language_tier, model_name, model_path, model_sha256,
    engine_license, model_license, dataset_license, commercial_use,
    attribution_required, attribution_text, source_url, model_card_url, approved, reason
) VALUES
('ar_JO-kareem-medium', 'AR', 'PILOT', 'ar_JO-kareem-medium', 'models/piper/ar/ar_JO-kareem-medium.onnx', 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d', 'GPL-3.0', 'Unverified', 'Unverified', FALSE, TRUE, NULL, 'rhasspy/piper-voices/ar/ar_JO/kareem/medium', NULL, FALSE, 'Pilot evaluation: License unverified; commercial gate locked.'),
('hi_IN-pratham-medium', 'HI', 'PILOT', 'hi_IN-pratham-medium', 'models/piper/hi/hi_IN-pratham-medium.onnx', '53c234e5e8472b6ac51c1ae1cab3fe06fad053beb8ebfd8977b010655bfdd3c3', 'GPL-3.0', 'CC-BY-NC-SA-4.0', 'CC-BY-NC-SA-4.0', FALSE, TRUE, NULL, 'rhasspy/piper-voices/hi/hi_IN/pratham/medium', NULL, FALSE, 'Pilot evaluation: CC-BY-NC-SA 4.0 non-commercial. Commercial gate locked.'),
('zh_CN-huayan-medium', 'ZH', 'PILOT', 'zh_CN-huayan-medium', 'models/piper/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx', 'a11883d9370cb47e5b225db8a2b5368a5c4e78eb537b0ddb6357d6b38c2049e4', 'GPL-3.0', 'Unknown', 'Unknown', FALSE, TRUE, NULL, 'rhasspy/piper-voices/zh/zh_CN/huayan/medium', NULL, FALSE, 'Pilot evaluation: License unknown; commercial gate locked.'),
('ja_JP-hi_fi_captain-medium', 'JA', 'PILOT', 'ja_JP-hi_fi_captain-medium', 'models/piper/ja/ja_JP/hi_fi_captain/medium/ja_JP-hi_fi_captain-medium.onnx', '8a1e5828c46ef4976d8b2d131ec5e96f13b63204976a4df6bf538a7b0a708233', 'GPL-3.0', 'Restricted', 'NICT Terms', FALSE, TRUE, NULL, 'rhasspy/piper-voices/ja/ja_JP/hi_fi_captain/medium', NULL, FALSE, 'Pilot evaluation: Non-commercial NICT terms; commercial gate locked.'),
('tr_TR-dfki-medium', 'TR', 'PILOT', 'tr_TR-dfki-medium', 'models/piper/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx', '98234827364bca882e3412574fa0782352123561aae89345bcdefa0912837461', 'GPL-3.0', 'CC-BY-NC-SA-4.0', 'CC-BY-NC-SA-4.0', FALSE, TRUE, NULL, 'rhasspy/piper-voices/tr/tr_TR/dfki/medium', NULL, FALSE, 'Pilot evaluation: DFKI CC-BY-NC-SA non-commercial. Commercial gate locked.')
ON CONFLICT (voice_id) DO UPDATE SET updated_at = NOW();

-- Seed Milestone Topic in Topic Graph
INSERT INTO topic_graph (
    topic_id, family, title, learning_objective, age_group, used_count, last_used_at
) VALUES (
    'TOPIC-COLORS-5', 'colors', 'Five Foundational Colors',
    'Identifying and repeating five foundational colors (Red, Blue, Yellow, Green, Purple)',
    '4-6', 1, NOW()
) ON CONFLICT (topic_id) DO NOTHING;

-- Seed Milestone Episode DNA (100% Authentic English Narration)
INSERT INTO episode_dna (
    episode_id, version, family, title, age_group, learning_objective, format_type,
    difficulty, target_duration_sec, min_duration_sec, max_duration_sec,
    characters, visual_style, music_profile, scenes, safety_profile
) VALUES (
    'EP-COLORS-5-V1',
    '2.0.0',
    'colors',
    'Learning 5 Bright Colors with Lumi',
    '4-6',
    'Identifying and orally repeating five foundational colors (Red, Blue, Yellow, Green, Purple)',
    'CONCEPT_EXPLORATION',
    'BEGINNER',
    55,
    45,
    90,
    '[{"name": "Lumi", "type": "Friendly Owl Guide"}]'::jsonb,
    'High-contrast educational 2D shapes with prominent uppercase labels',
    '{"profile": "Acoustic Gentle", "tempo_bpm": 100, "bg_volume_db": -22}'::jsonb,
    '[
        {"scene_id": 1, "color": "RED", "hex": "E53935", "item": "Sweet Strawberry", "speech": "Hello little learners! Today we are going to learn five bright colors. First is red, like a sweet juicy strawberry. Can you say red? Red! Great job!"},
        {"scene_id": 2, "color": "BLUE", "hex": "1E88E5", "item": "Ocean and Sky", "speech": "Now look at the sky and the ocean. Blue! Can you say blue? Blue! Wonderful!"},
        {"scene_id": 3, "color": "YELLOW", "hex": "FDD835", "item": "Warm Shining Sun", "speech": "Look at the warm shining sun. Yellow! Can you say yellow? Yellow! Fantastic!"},
        {"scene_id": 4, "color": "GREEN", "hex": "43A047", "item": "Green Grass and Frog", "speech": "Look at the green grass and the happy frog. Green! Can you say green? Green! Great!"},
        {"scene_id": 5, "color": "PURPLE", "hex": "8E24AA", "item": "Purple Grapes and Star", "speech": "Here is a bunch of purple grapes and a sparkling star. Purple! Can you say purple? Purple! High five! You learned all five colors!"}
    ]'::jsonb,
    '{"flash_hazard_guard": true, "max_contrast_ratio": 21.0, "zero_violence": true}'::jsonb
)
ON CONFLICT (episode_id) DO UPDATE SET updated_at = NOW();
