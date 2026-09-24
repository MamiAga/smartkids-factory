#!/usr/bin/env python3
"""
SmartKids Autonomous Cloud Production Factory Engine
Zero-Cost (0 TL) Architecture:
  GitHub Actions (ubuntu-24.04-arm) + Supabase PostgreSQL + Piper TTS + FFmpeg + YouTube Data API v3

Source of Truth: Supabase PostgreSQL 'automation_control' table.
The Android app acts as the Remote Kumanda (Control Center).
When the user clicks [START], automation_control.enabled = true.
When the phone is off, this factory runs continuously and autonomously in GitHub Actions ARM64.
"""

import os
import sys
import json
import time
import math
import wave
import struct
import logging
import argparse
import platform
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("SmartKidsFactory")

# Invariants
ALLOW_PAID_SERVICES = False
OUTPUT_DIR = "/tmp/smartkids_output"
SCRATCH_DIR = "/tmp/smartkids_scratch"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCRATCH_DIR, exist_ok=True)


class CloudControlClient:
    """Manages reading and updating Supabase PostgreSQL state via REST."""
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SECRET_KEY", "")
        self.is_connected = bool(self.supabase_url and self.supabase_key)
        if not self.is_connected:
            logger.warning("[Supabase] No remote credentials found; running in local sandbox fallback mode.")

    def get_automation_control(self) -> Dict[str, Any]:
        """Fetch singleton automation_control record (id=1)."""
        if not self.is_connected:
            # Fallback to local SQLite db_manager if present
            try:
                sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
                from backend.database.db_manager import DatabaseManager
                db = DatabaseManager()
                return db.get_automation_control()
            except Exception as e:
                logger.warning("[Local DB] Failed to read local sqlite automation_control: %s", e)
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

        url = f"{self.supabase_url}/rest/v1/automation_control?id=eq.1&select=*"
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Accept": "application/json"
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    ctrl = data[0]
                    if isinstance(ctrl.get("active_languages"), str):
                        ctrl["active_languages"] = json.loads(ctrl["active_languages"])
                    if isinstance(ctrl.get("active_channels"), str):
                        ctrl["active_channels"] = json.loads(ctrl["active_channels"])
                    return ctrl
        except Exception as e:
            logger.error("[Supabase] Error reading automation_control: %s", e)

        return {
            "id": 1,
            "enabled": False,
            "daily_master_episodes": 1,
            "active_languages": ["EN"]
        }

    def update_heartbeat(self, runner_arch: str, current_job_id: Optional[str] = None):
        """Update last_heartbeat timestamp in automation_control."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.is_connected:
            try:
                sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
                from backend.database.db_manager import DatabaseManager
                db = DatabaseManager()
                db.update_heartbeat(runner_arch=runner_arch, current_job_id=current_job_id)
            except Exception:
                pass
            return

        url = f"{self.supabase_url}/rest/v1/automation_control?id=eq.1"
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        payload = {"last_heartbeat": now_iso}
        if current_job_id:
            payload["current_job_id"] = current_job_id

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PATCH")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("[Supabase] Heartbeat recorded successfully at %s", now_iso)
        except Exception as e:
            logger.warning("[Supabase] Heartbeat update warning: %s", e)

    def record_system_event(self, event_type: str, message: str, severity: str = "INFO", details: Optional[Dict[str, Any]] = None):
        """Log system event to Supabase system_events table."""
        if not self.is_connected:
            return
        url = f"{self.supabase_url}/rest/v1/system_events"
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        payload = {
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "details": details or {}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as e:
            logger.warning("[Supabase] record_system_event warning: %s", e)

    def record_health_snapshot(self, runner_arch: str, runner_status: str, yt_status: str):
        """Record health check in Supabase health_snapshots table."""
        if not self.is_connected:
            return
        url = f"{self.supabase_url}/rest/v1/health_snapshots"
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        payload = {
            "runner_arch": runner_arch,
            "github_runner_status": runner_status,
            "supabase_status": "ONLINE" if self.is_connected else "SANDBOX",
            "gemini_status": "AUTHENTICATED" if os.getenv("GEMINI_API_KEY") else "MISSING",
            "piper_status": "READY",
            "ffmpeg_status": "READY",
            "youtube_status": yt_status,
            "cost_guard": "0_TL_FREE_ONLY"
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as e:
            logger.warning("[Supabase] record_health_snapshot warning: %s", e)

    def complete_job_cycle(self, job_id: str, video_id: str, language: str):
        """Mark job completed and record publication ledger."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.is_connected:
            return

        # 1. Update automation_control
        url_ctrl = f"{self.supabase_url}/rest/v1/automation_control?id=eq.1"
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        req_ctrl = urllib.request.Request(
            url_ctrl,
            data=json.dumps({"last_run_at": now_iso, "current_job_id": job_id}).encode("utf-8"),
            headers=headers,
            method="PATCH"
        )
        try:
            with urllib.request.urlopen(req_ctrl, timeout=10):
                pass
        except Exception as e:
            logger.warning("[Supabase] complete_job_cycle ctrl update warning: %s", e)

        # 2. Insert into youtube_publications
        url_pub = f"{self.supabase_url}/rest/v1/youtube_publications"
        pub_payload = {
            "publication_id": f"PUB-{job_id}",
            "job_id": job_id,
            "video_id": video_id,
            "language": language,
            "privacy_status": "private",
            "processing_status": "succeeded",
            "self_declared_made_for_kids": True
        }
        req_pub = urllib.request.Request(
            url_pub,
            data=json.dumps(pub_payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req_pub, timeout=10):
                logger.info("[Supabase] Logged publication PUB-%s for video %s", job_id, video_id)
        except Exception as e:
            logger.warning("[Supabase] publication insert warning: %s", e)


class AutonomousFactoryOrchestrator:
    """End-to-end Autonomous Cloud Factory."""

    def __init__(self, force_run: bool = False, strict_supabase: bool = False):
        self.force_run = force_run
        self.strict_supabase = strict_supabase
        self.client = CloudControlClient()
        self.runner_arch = platform.machine().lower()

    def run_cycle(self) -> Dict[str, Any]:
        logger.info("================================================================")
        logger.info("SMARTKIDS AUTONOMOUS CLOUD FACTORY — EXECUTION CYCLE")
        logger.info("================================================================")
        logger.info("Host Architecture: %s", self.runner_arch)
        logger.info("Strict Zero-Cost Guard: ALLOW_PAID_SERVICES=%s (0 TL Invariant)", ALLOW_PAID_SERVICES)

        # 1. Read automation control
        control = self.client.get_automation_control()
        is_enabled = control.get("enabled", False)
        daily_episodes = control.get("daily_master_episodes", 1)
        active_languages = control.get("active_languages", ["EN"])

        logger.info("[Control State] enabled = %s", is_enabled)
        logger.info("[Control State] daily_master_episodes = %d", daily_episodes)
        logger.info("[Control State] active_languages = %s", active_languages)

        # Update heartbeat
        self.client.update_heartbeat(runner_arch=self.runner_arch)

        # 2. Check if factory is enabled
        if not is_enabled and not self.force_run:
            logger.info("----------------------------------------------------------------")
            logger.info("FACTORY STANDBY: automation_control.enabled is FALSE.")
            logger.info("User has stopped the factory from the Android Control Center.")
            logger.info("Standby mode engaged — no videos will be generated or uploaded.")
            logger.info("Heartbeat confirmed. Exiting cleanly.")
            logger.info("----------------------------------------------------------------")
            self.client.record_system_event(
                event_type="FACTORY_STANDBY",
                message="Autonomous cycle skipped: factory paused by remote Android control.",
                severity="INFO"
            )
            self.client.record_health_snapshot(self.runner_arch, "STANDBY", "IDLE")
            return {
                "status": "STANDBY",
                "message": "Factory is disabled by remote Android kumanda. Heartbeat updated.",
                "enabled": False,
                "produced": 0
            }

        logger.info("----------------------------------------------------------------")
        logger.info("FACTORY ACTIVE: automation_control.enabled is TRUE.")
        logger.info("Autonomous cloud production cycle initiated!")
        logger.info("----------------------------------------------------------------")

        self.client.record_system_event(
            event_type="FACTORY_CYCLE_START",
            message=f"Starting autonomous factory run for {len(active_languages)} languages: {active_languages}",
            severity="INFO"
        )

        # Target video count calculation
        expected_daily_videos = daily_episodes * len(active_languages)
        logger.info("[Target Calculation] Daily Expected Videos = %d master × %d langs = %d videos",
                    daily_episodes, len(active_languages), expected_daily_videos)

        # 3. Import and execute ProductionEngine for active languages
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        from backend.engine.production_runner import ProductionEngine

        engine = ProductionEngine(strict_supabase=self.strict_supabase)
        results = []

        # Milestone episode: EP-COLORS-5-V1
        episode_id = "EP-COLORS-5-V1"

        for lang in active_languages:
            logger.info(">>> Processing Autonomous Job: Episode %s [%s]", episode_id, lang)
            res = engine.run_production(episode_id=episode_id, language=lang)
            results.append(res)

            if res.get("status") == "SUCCESS":
                job_id = res.get("job_id", f"JOB-{lang}-{datetime.now().strftime('%Y%m%d')}")
                video_id = res.get("youtube_video_id", "")
                self.client.complete_job_cycle(job_id=job_id, video_id=video_id, language=lang)
                self.client.record_system_event(
                    event_type="EPISODE_PRODUCTION_SUCCESS",
                    message=f"Successfully synthesized, rendered, verified, and uploaded {episode_id} [{lang}]. Video ID: {video_id}",
                    severity="INFO",
                    details={"job_id": job_id, "video_id": video_id, "language": lang}
                )
            else:
                self.client.record_system_event(
                    event_type="EPISODE_PRODUCTION_ERROR",
                    message=f"Production error on {episode_id} [{lang}]: {res.get('error')}",
                    severity="ERROR",
                    details={"error": res.get("error"), "language": lang}
                )

        self.client.record_health_snapshot(self.runner_arch, "ACTIVE", "READY")

        # Summary output
        logger.info("================================================================")
        logger.info("AUTONOMOUS FACTORY CYCLE COMPLETED")
        logger.info("Processed: %d jobs", len(results))
        logger.info("================================================================")

        return {
            "status": "COMPLETED",
            "enabled": True,
            "jobs_processed": len(results),
            "results": results
        }


def main():
    parser = argparse.ArgumentParser(description="SmartKids Autonomous Cloud Production Factory Engine")
    parser.add_argument("--force", action="store_true", help="Force production run even if automation_control.enabled is false")
    parser.add_argument("--strict-supabase", action="store_true", help="Fail if Supabase credentials are not found in environment")
    args = parser.parse_args()

    orchestrator = AutonomousFactoryOrchestrator(
        force_run=args.force,
        strict_supabase=args.strict_supabase
    )
    result = orchestrator.run_cycle()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
