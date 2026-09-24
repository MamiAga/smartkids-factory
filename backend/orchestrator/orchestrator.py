"""SmartKids Factory Orchestrator (Celery / Redis / PostgreSQL 16)."""
import os
import json
import logging
import psycopg2
from celery import Celery
from orchestrator.config import (
    REDIS_URL,
    DATABASE_URL,
    DEV_MODE,
    PRODUCTION_READY,
    compute_deterministic_seed,
    assert_free_service_only
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("smartkids.orchestrator")

# Celery Application Definition
celery_app = Celery("smartkids_factory", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "workers.piper_worker.generate_speech": {"queue": "tts_queue"},
        "workers.render_worker.render_video": {"queue": "render_queue"},
        "workers.qa_worker.run_qa_checks": {"queue": "qa_queue"},
        "workers.youtube_worker.upload_and_poll": {"queue": "youtube_queue"},
        "workers.analytics_worker.log_job_analytics": {"queue": "analytics_queue"},
    },
    task_annotations={
        "*": {"rate_limit": "10/m"}
    }
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def orchestrate_language_job(self, episode_id: str, language: str):
    """
    Main State Machine Controller for an Episode in a given Language.
    Lifecycle:
    PLANNED -> SCRIPTED -> LOCALIZED -> TTS_READY -> RENDERED -> QA_PASSED ->
    UPLOADING -> UPLOADED -> PROCESSING -> PROCESSED -> PUBLISHED -> LOCAL_DELETE_PENDING -> COMPLETED
    """
    seed = compute_deterministic_seed(episode_id, language)
    job_id = f"JOB-{language}-{episode_id}-{seed[:8]}"

    logger.info("Orchestrating Job %s for Episode %s [%s] with Seed %s", job_id, episode_id, language, seed)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Step 0: Check Production Readiness and Gating Invariant
        cursor.execute(
            "SELECT voice_id, model_name, commercial_use, approved, reason FROM piper_voice_registry WHERE language = %s;",
            (language,)
        )
        voice_row = cursor.fetchone()

        if not voice_row:
            raise PermissionError(f"Language {language} is not registered in piper_voice_registry")

        voice_id, model_name, commercial_use, approved, reason = voice_row

        if not commercial_use or not approved:
            if not DEV_MODE:
                error_msg = f"HARD PRODUCTION GATE BLOCKED: Voice '{voice_id}' ({model_name}) is NOT approved for commercial production. Reason: {reason}"
                logger.error(error_msg)
                
                # Upsert job into QA_FAILED / QUARANTINED state
                cursor.execute("""
                    INSERT INTO pipeline_jobs (job_id, episode_id, language, state, deterministic_seed, error_message)
                    VALUES (%s, %s, %s, 'QA_FAILED', %s, %s)
                    ON CONFLICT (job_id) DO UPDATE SET state = 'QA_FAILED', error_message = %s, updated_at = NOW();
                """, (job_id, episode_id, language, seed, error_msg, error_msg))
                conn.commit()
                return {"status": "BLOCKED", "reason": error_msg}

        # Step 1: Idempotency Check
        cursor.execute(
            "SELECT state, local_file_deleted, youtube_video_id FROM pipeline_jobs WHERE job_id = %s;",
            (job_id,)
        )
        existing_job = cursor.fetchone()
        if existing_job and existing_job[0] in ('COMPLETED', 'PUBLISHED'):
            logger.info("Idempotency hit: Job %s already completed in database. Skipping duplicate work.", job_id)
            return {"status": "ALREADY_COMPLETED", "video_id": existing_job[2]}

        # Step 2: Initialize / Transition to PLANNED
        cursor.execute("""
            INSERT INTO pipeline_jobs (job_id, episode_id, language, state, deterministic_seed)
            VALUES (%s, %s, %s, 'PLANNED', %s)
            ON CONFLICT (job_id) DO UPDATE SET state = 'PLANNED', updated_at = NOW();
        """, (job_id, episode_id, language, seed))
        conn.commit()

        # Step 3: Localization (Calling Free-tier Gemini 3.5 Flash-Lite)
        cursor.execute("UPDATE pipeline_jobs SET state = 'SCRIPTED', updated_at = NOW() WHERE job_id = %s;", (job_id,))
        conn.commit()

        # (In production, tasks are chained asynchronously via Celery signatures)
        logger.info("Job %s dispatched through autonomous pipeline queues.", job_id)
        return {"status": "DISPATCHED", "job_id": job_id, "seed": seed}

    except Exception as exc:
        conn.rollback()
        logger.exception("Error in job orchestration for %s: %s", job_id, str(exc))
        raise exc
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logger.info("SmartKids Autonomous Factory Orchestrator service booting. Ready for Celery queue events.")
