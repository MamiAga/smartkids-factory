"""SmartKids Database Manager (Unified SQLite / PostgreSQL 16 adapter)."""
import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

logger = logging.getLogger("smartkids.db")

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "smartkids_production.db")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://smartkids_admin:secure_pg_pass@postgres:5432/smartkids_production")

class DatabaseManager:
    def __init__(self):
        self.use_postgres = False
        if psycopg2 and "postgres" in DATABASE_URL:
            try:
                conn = psycopg2.connect(DATABASE_URL, connect_timeout=2)
                conn.close()
                self.use_postgres = True
                logger.info("Connected to PostgreSQL: %s", DATABASE_URL)
            except Exception:
                self.use_postgres = False
                logger.info("PostgreSQL unavailable, using persistent SQLite: %s", SQLITE_PATH)
        else:
            self.use_postgres = False

        self._init_tables()

    def get_connection(self):
        if self.use_postgres:
            return psycopg2.connect(DATABASE_URL)
        else:
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            return conn

    def _init_tables(self):
        conn = self.get_connection()
        cur = conn.cursor()

        if self.use_postgres:
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    cur.execute(f.read())
            conn.commit()
        else:
            # SQLite schema equivalent
            cur.execute("""
            CREATE TABLE IF NOT EXISTS automation_control (
                id INTEGER PRIMARY KEY DEFAULT 1,
                enabled INTEGER NOT NULL DEFAULT 0,
                daily_master_episodes INTEGER NOT NULL DEFAULT 1,
                schedule_time TEXT NOT NULL DEFAULT '04:00',
                timezone TEXT NOT NULL DEFAULT 'Europe/Istanbul',
                active_languages TEXT NOT NULL DEFAULT '["EN"]',
                active_channels TEXT NOT NULL DEFAULT '["EN"]',
                generation_mode TEXT NOT NULL DEFAULT 'AUTONOMOUS',
                publish_mode TEXT NOT NULL DEFAULT 'AUTO',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_heartbeat TIMESTAMP,
                last_run_at TIMESTAMP,
                next_run_at TIMESTAMP,
                current_job_id TEXT,
                failure_count INTEGER DEFAULT 0
            );
            """)

            cur.execute("""
            INSERT OR IGNORE INTO automation_control (id, enabled, daily_master_episodes, schedule_time, timezone, active_languages, active_channels, generation_mode, publish_mode)
            VALUES (1, 0, 1, '04:00', 'Europe/Istanbul', '["EN"]', '["EN"]', 'AUTONOMOUS', 'AUTO');
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS episode_dna (
                episode_id TEXT PRIMARY KEY,
                version TEXT NOT NULL DEFAULT '2.0.0',
                title TEXT NOT NULL,
                age_group TEXT NOT NULL,
                learning_objective TEXT NOT NULL,
                format_type TEXT NOT NULL,
                difficulty TEXT NOT NULL DEFAULT 'BEGINNER',
                target_duration_sec INTEGER NOT NULL,
                min_duration_sec INTEGER NOT NULL,
                max_duration_sec INTEGER NOT NULL,
                characters TEXT NOT NULL,
                visual_style TEXT NOT NULL,
                music_profile TEXT NOT NULL,
                scenes TEXT NOT NULL,
                safety_profile TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS piper_voice_registry (
                voice_id TEXT PRIMARY KEY,
                language TEXT NOT NULL UNIQUE,
                model_name TEXT NOT NULL,
                model_path TEXT NOT NULL,
                model_sha256 TEXT NOT NULL,
                engine_license TEXT NOT NULL DEFAULT 'GPL-3.0',
                model_license TEXT NOT NULL,
                dataset_license TEXT NOT NULL,
                commercial_use INTEGER NOT NULL DEFAULT 0,
                attribution_required INTEGER NOT NULL DEFAULT 1,
                attribution_text TEXT,
                source_url TEXT NOT NULL,
                model_card_url TEXT,
                approved INTEGER NOT NULL DEFAULT 0,
                reason TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_jobs (
                job_id TEXT PRIMARY KEY,
                episode_id TEXT NOT NULL,
                language TEXT NOT NULL,
                state TEXT NOT NULL,
                deterministic_seed TEXT NOT NULL,
                local_mp4_path TEXT,
                local_file_deleted INTEGER NOT NULL DEFAULT 0,
                youtube_video_id TEXT,
                youtube_channel_id TEXT,
                render_duration_sec REAL DEFAULT 0.0,
                cost_usd REAL NOT NULL DEFAULT 0.0000,
                technical_qa_passed INTEGER NOT NULL DEFAULT 0,
                educational_qa_passed INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                log_history TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (episode_id, language, deterministic_seed)
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS youtube_channels (
                language TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                encrypted_refresh_token TEXT NOT NULL,
                daily_upload_count INTEGER NOT NULL DEFAULT 0,
                last_upload_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.commit()

        cur.close()
        conn.close()

    def seed_voice_registry(self, voices_json_path: str):
        if not os.path.exists(voices_json_path):
            return
        with open(voices_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        conn = self.get_connection()
        cur = conn.cursor()
        for v in data.get("voices", []):
            lang = v["language"]
            voice_id = v["voice_id"]
            model_name = v.get("model_name", f"{voice_id}.onnx")
            model_path = v.get("model_url", "")
            sha256 = v.get("model_sha256", "")
            engine_lic = v.get("engine_license", "GPL-3.0")
            model_lic = v.get("model_license", "")
            data_lic = v.get("dataset_license", "")
            comm_use = 1 if v.get("commercial_use") else 0
            attr_req = 1 if v.get("attribution_required") else 0
            attr_txt = v.get("attribution_text", "")
            source = v.get("source", "")
            card_url = v.get("model_card_url", "")
            approved = 1 if v.get("approved") else 0
            reason = v.get("reason", "")

            if self.use_postgres:
                cur.execute("""
                    INSERT INTO piper_voice_registry (
                        voice_id, language, model_name, model_path, model_sha256,
                        engine_license, model_license, dataset_license, commercial_use,
                        attribution_required, attribution_text, source_url, model_card_url,
                        approved, reason
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (language) DO UPDATE SET
                        model_name = EXCLUDED.model_name,
                        approved = EXCLUDED.approved,
                        commercial_use = EXCLUDED.commercial_use,
                        reason = EXCLUDED.reason;
                """, (voice_id, lang, model_name, model_path, sha256, engine_lic,
                      model_lic, data_lic, bool(comm_use), bool(attr_req), attr_txt,
                      source, card_url, bool(approved), reason))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO piper_voice_registry (
                        voice_id, language, model_name, model_path, model_sha256,
                        engine_license, model_license, dataset_license, commercial_use,
                        attribution_required, attribution_text, source_url, model_card_url,
                        approved, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (voice_id, lang, model_name, model_path, sha256, engine_lic,
                      model_lic, data_lic, comm_use, attr_req, attr_txt,
                      source, card_url, approved, reason))
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Voice registry successfully synchronized with canonical licenses.")

    def save_episode_dna(self, episode_dict: Dict[str, Any]):
        conn = self.get_connection()
        cur = conn.cursor()

        ep_id = episode_dict["episode_id"]
        version = episode_dict.get("version", "2.0.0")
        title = episode_dict["title"]
        age_group = episode_dict["age_group"]
        learning_objective = episode_dict["learning_objective"]
        format_type = episode_dict["format_type"]
        difficulty = episode_dict.get("difficulty", "BEGINNER")
        target_sec = int(episode_dict["target_duration_sec"])
        min_sec = int(episode_dict["min_duration_sec"])
        max_sec = int(episode_dict["max_duration_sec"])
        characters = json.dumps(episode_dict.get("characters", []))
        visual_style = episode_dict.get("visual_style", "")
        music_profile = episode_dict.get("music_profile", "")
        scenes = json.dumps(episode_dict.get("scenes", []))
        safety_profile = json.dumps(episode_dict.get("safety_profile", {}))

        if self.use_postgres:
            cur.execute("""
                INSERT INTO episode_dna (
                    episode_id, version, title, age_group, learning_objective,
                    format_type, difficulty, target_duration_sec, min_duration_sec,
                    max_duration_sec, characters, visual_style, music_profile,
                    scenes, safety_profile
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (episode_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    learning_objective = EXCLUDED.learning_objective,
                    scenes = EXCLUDED.scenes;
            """, (ep_id, version, title, age_group, learning_objective, format_type,
                  difficulty, target_sec, min_sec, max_sec, characters, visual_style,
                  music_profile, scenes, safety_profile))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO episode_dna (
                    episode_id, version, title, age_group, learning_objective,
                    format_type, difficulty, target_duration_sec, min_duration_sec,
                    max_duration_sec, characters, visual_style, music_profile,
                    scenes, safety_profile
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (ep_id, version, title, age_group, learning_objective, format_type,
                  difficulty, target_sec, min_sec, max_sec, characters, visual_style,
                  music_profile, scenes, safety_profile))

        conn.commit()
        cur.close()
        conn.close()
        logger.info("Episode DNA %s ('%s') saved in database.", ep_id, title)

    def get_episode_dna(self, episode_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        if self.use_postgres:
            cur.execute("SELECT * FROM episode_dna WHERE episode_id = %s;", (episode_id,))
        else:
            cur.execute("SELECT * FROM episode_dna WHERE episode_id = ?;", (episode_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        d = dict(row)
        if isinstance(d.get("characters"), str):
            d["characters"] = json.loads(d["characters"])
        if isinstance(d.get("scenes"), str):
            d["scenes"] = json.loads(d["scenes"])
        if isinstance(d.get("safety_profile"), str):
            d["safety_profile"] = json.loads(d["safety_profile"])
        return d

    def upsert_job(self, job_dict: Dict[str, Any]):
        conn = self.get_connection()
        cur = conn.cursor()

        job_id = job_dict["job_id"]
        ep_id = job_dict["episode_id"]
        lang = job_dict["language"]
        state = job_dict["state"]
        seed = job_dict["deterministic_seed"]
        mp4_path = job_dict.get("local_mp4_path")
        deleted = 1 if job_dict.get("local_file_deleted") else 0
        yt_id = job_dict.get("youtube_video_id")
        render_dur = float(job_dict.get("render_duration_sec", 0.0))
        cost = 0.0000
        tech_qa = 1 if job_dict.get("technical_qa_passed") else 0
        edu_qa = 1 if job_dict.get("educational_qa_passed") else 0
        err_msg = job_dict.get("error_message")
        log_hist = job_dict.get("log_history", "")

        if self.use_postgres:
            cur.execute("""
                INSERT INTO pipeline_jobs (
                    job_id, episode_id, language, state, deterministic_seed,
                    local_mp4_path, local_file_deleted, youtube_video_id,
                    render_duration_sec, cost_usd, technical_qa_passed,
                    educational_qa_passed, error_message, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (job_id) DO UPDATE SET
                    state = EXCLUDED.state,
                    local_mp4_path = EXCLUDED.local_mp4_path,
                    local_file_deleted = EXCLUDED.local_file_deleted,
                    youtube_video_id = EXCLUDED.youtube_video_id,
                    render_duration_sec = EXCLUDED.render_duration_sec,
                    technical_qa_passed = EXCLUDED.technical_qa_passed,
                    educational_qa_passed = EXCLUDED.educational_qa_passed,
                    error_message = EXCLUDED.error_message,
                    updated_at = NOW();
            """, (job_id, ep_id, lang, state, seed, mp4_path, bool(deleted), yt_id,
                  render_dur, cost, bool(tech_qa), bool(edu_qa), err_msg))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO pipeline_jobs (
                    job_id, episode_id, language, state, deterministic_seed,
                    local_mp4_path, local_file_deleted, youtube_video_id,
                    render_duration_sec, cost_usd, technical_qa_passed,
                    educational_qa_passed, error_message, log_history, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
            """, (job_id, ep_id, lang, state, seed, mp4_path, deleted, yt_id,
                  render_dur, cost, tech_qa, edu_qa, err_msg, log_hist))

        conn.commit()
        cur.close()
        conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.cursor()
        if self.use_postgres:
            cur.execute("SELECT * FROM pipeline_jobs WHERE job_id = %s;", (job_id,))
        else:
            cur.execute("SELECT * FROM pipeline_jobs WHERE job_id = ?;", (job_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None

    def get_automation_control(self) -> Dict[str, Any]:
        conn = self.get_connection()
        cur = conn.cursor()
        if self.use_postgres:
            cur.execute("SELECT * FROM automation_control WHERE id = 1;")
        else:
            cur.execute("SELECT * FROM automation_control WHERE id = 1;")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return {
                "id": 1,
                "enabled": False,
                "daily_master_episodes": 1,
                "schedule_time": "04:00",
                "timezone": "Europe/Istanbul",
                "active_languages": ["EN"],
                "active_channels": ["EN"],
                "generation_mode": "AUTONOMOUS",
                "publish_mode": "AUTO"
            }
        d = dict(row)
        if isinstance(d.get("active_languages"), str):
            try:
                d["active_languages"] = json.loads(d["active_languages"])
            except Exception:
                d["active_languages"] = ["EN"]
        if isinstance(d.get("active_channels"), str):
            try:
                d["active_channels"] = json.loads(d["active_channels"])
            except Exception:
                d["active_channels"] = ["EN"]
        d["enabled"] = bool(d.get("enabled", 0))
        return d

    def update_automation_control(self, enabled: bool, daily_master_episodes: int = 1, active_languages: List[str] = None):
        if active_languages is None:
            active_languages = ["EN"]
        conn = self.get_connection()
        cur = conn.cursor()
        lang_json = json.dumps(active_languages)
        enabled_val = True if enabled else False
        if self.use_postgres:
            cur.execute("""
                UPDATE automation_control
                SET enabled = %s, daily_master_episodes = %s, active_languages = %s::jsonb, updated_at = NOW()
                WHERE id = 1;
            """, (enabled_val, daily_master_episodes, lang_json))
        else:
            cur.execute("""
                UPDATE automation_control
                SET enabled = ?, daily_master_episodes = ?, active_languages = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1;
            """, (1 if enabled else 0, daily_master_episodes, lang_json))
        conn.commit()
        cur.close()
        conn.close()

    def update_heartbeat(self, runner_arch: str = "aarch64", current_job_id: Optional[str] = None):
        conn = self.get_connection()
        cur = conn.cursor()
        if self.use_postgres:
            cur.execute("""
                UPDATE automation_control
                SET last_heartbeat = NOW(), current_job_id = COALESCE(%s, current_job_id)
                WHERE id = 1;
            """, (current_job_id,))
        else:
            cur.execute("""
                UPDATE automation_control
                SET last_heartbeat = CURRENT_TIMESTAMP, current_job_id = COALESCE(?, current_job_id)
                WHERE id = 1;
            """, (current_job_id,))
        conn.commit()
        cur.close()
        conn.close()
