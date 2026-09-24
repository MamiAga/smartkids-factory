-- SmartKids Autonomous Learning Network - Canonical V2 PostgreSQL 16 Schema
-- Strictly enforcing 0 TL Cost Ceiling, Idempotency, and Voice License Gate

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Episode DNA Specification (Canonical Curriculum Unit)
CREATE TABLE IF NOT EXISTS episode_dna (
    episode_id VARCHAR(64) PRIMARY KEY,
    version VARCHAR(16) NOT NULL DEFAULT '2.0.0',
    title VARCHAR(255) NOT NULL,
    age_group VARCHAR(16) NOT NULL CHECK (age_group IN ('2-4', '4-6', '6-8')),
    learning_objective TEXT NOT NULL,
    format_type VARCHAR(32) NOT NULL CHECK (format_type IN ('NURSERY_RHYME', 'COUNTING', 'CONCEPT_EXPLORATION', 'INTERACTIVE_QUIZ')),
    difficulty VARCHAR(16) NOT NULL DEFAULT 'BEGINNER',
    target_duration_sec INT NOT NULL,
    min_duration_sec INT NOT NULL,
    max_duration_sec INT NOT NULL,
    characters JSONB NOT NULL,
    visual_style TEXT NOT NULL,
    music_profile TEXT NOT NULL,
    scenes JSONB NOT NULL,
    safety_profile JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Piper Voice Registry (Static Pre-Verified Audit Gate)
CREATE TABLE IF NOT EXISTS piper_voice_registry (
    voice_id VARCHAR(64) PRIMARY KEY,
    language VARCHAR(8) NOT NULL UNIQUE CHECK (language IN ('EN','ES','DE','FR','PT','AR','HI','ZH','JA','TR')),
    model_name VARCHAR(128) NOT NULL,
    model_path TEXT NOT NULL,
    model_sha256 VARCHAR(64) NOT NULL,
    engine_license VARCHAR(64) NOT NULL DEFAULT 'GPL-3.0',
    model_license VARCHAR(64) NOT NULL,
    dataset_license VARCHAR(64) NOT NULL,
    commercial_use BOOLEAN NOT NULL DEFAULT FALSE,
    attribution_required BOOLEAN NOT NULL DEFAULT TRUE,
    attribution_text TEXT,
    source_url TEXT NOT NULL,
    model_card_url TEXT,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Pipeline Jobs (Full Production State Machine)
CREATE TABLE IF NOT EXISTS pipeline_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    episode_id VARCHAR(64) NOT NULL REFERENCES episode_dna(episode_id),
    language VARCHAR(8) NOT NULL REFERENCES piper_voice_registry(language),
    state VARCHAR(32) NOT NULL CHECK (state IN (
        -- Standard Lifecycle
        'PLANNED',
        'SCRIPTED',
        'LOCALIZED',
        'TTS_READY',
        'RENDERED',
        'QA_PASSED',
        'UPLOADING',
        'UPLOADED',
        'PROCESSING',
        'PROCESSED',
        'PUBLISHED',
        'LOCAL_DELETE_PENDING',
        'COMPLETED',
        -- Safe Failure & Boundary States
        'AUTH_FAILED',
        'QUOTA_PAUSED',
        'UPLOAD_FAILED',
        'TTS_FAILED',
        'RENDER_FAILED',
        'QA_FAILED',
        'PROCESSING_FAILED',
        'QUARANTINED'
    )),
    deterministic_seed VARCHAR(64) NOT NULL,
    local_mp4_path TEXT,
    local_file_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    youtube_video_id VARCHAR(32),
    youtube_channel_id VARCHAR(64),
    render_duration_sec NUMERIC(8,2) DEFAULT 0.0,
    cost_usd NUMERIC(6,4) NOT NULL DEFAULT 0.0000 CHECK (cost_usd = 0.0000), -- 0 TL Gating Guard
    technical_qa_passed BOOLEAN NOT NULL DEFAULT FALSE,
    educational_qa_passed BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_idempotent_job UNIQUE (episode_id, language, deterministic_seed)
);

-- 4. YouTube Channels & OAuth Token Store (Single Google Cloud Project)
CREATE TABLE IF NOT EXISTS youtube_channels (
    language VARCHAR(8) PRIMARY KEY REFERENCES piper_voice_registry(language),
    channel_id VARCHAR(64) NOT NULL,
    channel_name VARCHAR(128) NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    daily_upload_count INT NOT NULL DEFAULT 0,
    last_upload_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'QUOTA_PAUSED', 'AUTH_ERROR', 'SUSPENDED')),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Audit & Security Log
CREATE TABLE IF NOT EXISTS production_audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(64) REFERENCES pipeline_jobs(job_id),
    actor VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    details JSONB NOT NULL,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- INVARIANT TRIGGER 1: Hard Block Job Insertion If Voice Is Not Approved or Commercial Use is False
CREATE OR REPLACE FUNCTION enforce_commercial_voice_gate()
RETURNS TRIGGER AS $$
DECLARE
    v_commercial BOOLEAN;
    v_approved BOOLEAN;
    v_voice_id VARCHAR;
    v_reason TEXT;
BEGIN
    SELECT commercial_use, approved, voice_id, reason 
    INTO v_commercial, v_approved, v_voice_id, v_reason
    FROM piper_voice_registry 
    WHERE language = NEW.language;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRODUCTION GATE BLOCKED: Language % is not registered in piper_voice_registry', NEW.language;
    END IF;

    IF v_commercial IS NOT TRUE OR v_approved IS NOT TRUE THEN
        RAISE EXCEPTION 'PRODUCTION GATE BLOCKED: Voice % for language % is not approved for commercial production. Reason: %', 
            v_voice_id, NEW.language, v_reason;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_voice_gate 
BEFORE INSERT OR UPDATE OF language ON pipeline_jobs
FOR EACH ROW EXECUTE FUNCTION enforce_commercial_voice_gate();

-- INVARIANT TRIGGER 2: Prevent File Deletion Before YouTube Processing Succeeded
CREATE OR REPLACE FUNCTION guard_mp4_deletion()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.local_file_deleted = TRUE AND OLD.local_file_deleted = FALSE THEN
        IF OLD.state NOT IN ('PROCESSED', 'PUBLISHED', 'LOCAL_DELETE_PENDING', 'COMPLETED') THEN
            RAISE EXCEPTION 'CRITICAL DATA SAFETY VIOLATION: Local MP4 cannot be marked deleted until YouTube video processing has reached PROCESSED/PUBLISHED state! Current state: %', OLD.state;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_guard_mp4_deletion
BEFORE UPDATE OF local_file_deleted ON pipeline_jobs
FOR EACH ROW EXECUTE FUNCTION guard_mp4_deletion();
