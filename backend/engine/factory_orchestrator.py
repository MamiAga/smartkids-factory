#!/usr/bin/env python3
"""SmartKids Autonomous Cloud Factory — scheduler + dispatcher.

Runs from .github/workflows/smartkids_factory.yml (hourly cron + Android START dispatch).

Decision rules (all state lives in Supabase automation_control / pipeline_jobs):
  1. enabled = false                         -> STANDBY (heartbeat only, nothing produced)
  2. before schedule_time (in `timezone`)    -> WAITING, unless --run-now (Android START)
  3. per language, videos already produced today >= daily_master_episodes -> DONE for today
  4. 3 failures for a language today, or a quota pause today -> that language waits for tomorrow
  5. next episode = first curriculum episode that has no YouTube video for that language
     (no episode left -> CONTENT_EXHAUSTED, never a duplicate upload)
One language failing never stops the other languages.
"""
import argparse
import json
import logging
import os
import platform
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.engine.curriculum import CATALOG  # noqa: E402
from backend.engine.supabase_rest import SupabaseREST, utc_now_iso  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smartkids.factory")

ALLOW_PAID_SERVICES = False
OUTPUT_DIR = "/tmp/smartkids_output"
MAX_FAILURES_PER_LANGUAGE_PER_DAY = 3

PRODUCED_STATES = {"UPLOADED_PRIVATE", "PROCESSING", "PROCESSED_PRIVATE", "COMPLETED"}
FAILED_STATES = {"FAILED_UPLOAD", "FAILED_QA", "QUARANTINED", "QUOTA_PAUSED"}
PERMANENTLY_SKIPPED_STATES = PRODUCED_STATES | {"FAILED_QA", "QUARANTINED"}

DEFAULT_CONTROL = {"enabled": False, "daily_master_episodes": 1, "schedule_time": "04:00",
                   "timezone": "Europe/Istanbul", "active_languages": ["EN"]}


# ----------------------------------------------------------------------------- pure logic
def local_day_bounds(now_utc: datetime, tz_name: str, schedule_time: str):
    tz = ZoneInfo(tz_name or "Europe/Istanbul")
    now_local = now_utc.astimezone(tz)
    midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        hh, mm = (int(x) for x in (schedule_time or "04:00").split(":")[:2])
    except ValueError:
        hh, mm = 4, 0
    slot = midnight.replace(hour=hh, minute=mm)
    return now_local, midnight, slot


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def plan_cycle(control: Dict[str, Any], jobs_today: List[Dict[str, Any]], now_utc: datetime,
               run_now: bool = False, force: bool = False) -> Dict[str, Any]:
    """Decide whether this cycle should produce, and for which languages. Pure & unit-tested."""
    enabled = bool(control.get("enabled")) or force
    langs = [str(l).upper() for l in (control.get("active_languages") or ["EN"])]
    daily = max(1, int(control.get("daily_master_episodes") or 1))
    now_local, midnight, slot = local_day_bounds(now_utc, control.get("timezone"), control.get("schedule_time"))
    next_slot = slot if now_local < slot else slot + timedelta(days=1)

    plan = {"should_run": False, "languages": [], "per_language": {}, "now_local": now_local.isoformat(),
            "slot_local": slot.isoformat(), "next_run_at": next_slot.astimezone(timezone.utc).isoformat()}
    if not enabled:
        plan["reason"] = "STANDBY: automation_control.enabled = false"
        return plan
    due = run_now or now_local >= slot
    for lang in langs:
        mine = [j for j in jobs_today if (j.get("language") or "").upper() == lang]
        produced = sum(1 for j in mine if j.get("state") in PRODUCED_STATES)
        failed = sum(1 for j in mine if j.get("state") in FAILED_STATES)
        quota = any(j.get("state") == "QUOTA_PAUSED" for j in mine)
        remaining = max(0, daily - produced)
        if quota:
            status = "QUOTA_PAUSED_TODAY"
        elif failed >= MAX_FAILURES_PER_LANGUAGE_PER_DAY:
            status = "LANGUAGE_PAUSED_TODAY"
        elif remaining == 0:
            status = "DONE_TODAY"
        elif not due:
            status = "WAITING_FOR_SLOT"
        else:
            status = "RUN"
            plan["languages"].append(lang)
        plan["per_language"][lang] = {"produced_today": produced, "failed_today": failed,
                                      "remaining": remaining, "status": status}
    plan["should_run"] = bool(plan["languages"])
    if plan["should_run"]:
        # if something is still to do today, the next hourly cycle is the retry point
        plan["next_run_at"] = (now_utc + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0).isoformat()
        plan["reason"] = "RUN: " + ", ".join(plan["languages"])
    elif not due:
        plan["reason"] = f"WAITING: schedule slot {slot.strftime('%H:%M')} {control.get('timezone')} not reached"
    else:
        plan["reason"] = "NOTHING TO DO: " + ", ".join(f"{l}={v['status']}" for l, v in plan["per_language"].items())
    return plan


def pick_next_episode(language: str, lang_jobs: List[Dict[str, Any]]) -> Optional[str]:
    done = {j["episode_id"] for j in lang_jobs if j.get("state") in PERMANENTLY_SKIPPED_STATES}
    for ep in CATALOG:
        if ep["episode_id"] not in done:
            return ep["episode_id"]
    return None


# ----------------------------------------------------------------------------- runtime
class AutonomousFactoryOrchestrator:
    def __init__(self, force: bool = False, run_now: bool = False, dry_run: bool = False,
                 strict_supabase: bool = False):
        self.force, self.run_now, self.dry_run = force, run_now, dry_run
        self.strict_supabase = strict_supabase
        self.db = SupabaseREST(dry_run=dry_run)
        self.arch = platform.machine().lower()
        if not self.db.connected and not dry_run:
            raise RuntimeError("Production needs SUPABASE_URL + SUPABASE_SECRET_KEY (use --dry-run for local tests).")

    def _control(self) -> Dict[str, Any]:
        if self.dry_run:
            return dict(DEFAULT_CONTROL, enabled=True)
        ctrl = self.db.get_control()
        if ctrl is None:
            raise RuntimeError("automation_control row id=1 not readable (check secrets / table).")
        return ctrl

    def _jobs_today(self, control: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.db.connected:
            return []
        _, midnight, _ = local_day_bounds(datetime.now(timezone.utc), control.get("timezone"), control.get("schedule_time"))
        return self.db.list_jobs(since_iso=midnight.astimezone(timezone.utc).isoformat())

    def _still_enabled(self) -> bool:
        if self.dry_run or self.force:
            return True
        ctrl = self.db.get_control()
        return bool(ctrl and ctrl.get("enabled"))

    def gate(self) -> Dict[str, Any]:
        control = self._control()
        plan = plan_cycle(control, self._jobs_today(control), datetime.now(timezone.utc),
                          run_now=self.run_now, force=self.force)
        self.db.heartbeat()
        if not plan["should_run"]:
            self.db.patch_control({"next_run_at": plan["next_run_at"]})
        logger.info("[Gate] %s", plan["reason"])
        return plan

    def run_cycle(self) -> Dict[str, Any]:
        logger.info("=" * 64)
        logger.info("SMARTKIDS FACTORY CYCLE  arch=%s  paid_services=%s  dry_run=%s", self.arch, ALLOW_PAID_SERVICES, self.dry_run)
        logger.info("=" * 64)
        plan = self.gate()
        result: Dict[str, Any] = {"plan": plan, "jobs": [], "errors": 0}
        if not plan["should_run"]:
            result["status"] = "IDLE"
            return result

        from backend.engine.production_runner import (ProductionEngine, LanguageNotReady, QuotaExceeded)
        control = self._control()
        engine = ProductionEngine(strict_supabase=self.strict_supabase, dry_run=self.dry_run, db=self.db,
                                  stop_check=lambda: not self._still_enabled(),
                                  publish_mode=str(control.get("publish_mode") or "PRIVATE"))
        self.db.event("FACTORY_CYCLE_START", plan["reason"], details={"plan": plan["per_language"]})
        quota_hit = False

        for lang in plan["languages"]:
            remaining = plan["per_language"][lang]["remaining"]
            lang_jobs = self.db.list_jobs(language=lang) if self.db.connected else []
            for _ in range(remaining):
                if quota_hit:
                    break
                if not self._still_enabled():
                    logger.info("[Factory] STOP received from Android — ending cycle.")
                    result["status"] = "STOPPED"
                    return self._finish(result, plan)
                episode_id = pick_next_episode(lang, lang_jobs)
                if episode_id is None:
                    self.db.event("CONTENT_EXHAUSTED", f"No new curriculum episode left for {lang}", "WARNING")
                    result["jobs"].append({"language": lang, "status": "CONTENT_EXHAUSTED"})
                    break
                try:
                    res = engine.run_production(episode_id, lang)
                    result["jobs"].append(res)
                    lang_jobs.append({"episode_id": episode_id, "state": "PROCESSED_PRIVATE"})
                    if res["status"] == "SUCCESS":
                        self.db.event("EPISODE_PRODUCTION_SUCCESS",
                                      f"{episode_id} [{lang}] -> https://youtu.be/{res['youtube_video_id']}",
                                      details=res)
                except LanguageNotReady as e:
                    logger.warning("[%s] LANGUAGE_PAUSED: %s", lang, e)
                    self.db.event("LANGUAGE_PAUSED", f"{lang}: {e}", "WARNING")
                    result["jobs"].append({"language": lang, "status": "LANGUAGE_PAUSED", "reason": str(e)})
                    break
                except QuotaExceeded as e:
                    logger.warning("[%s] QUOTA_PAUSED: %s", lang, e)
                    self.db.event("QUOTA_PAUSED", f"{lang}: {e}", "WARNING")
                    result["jobs"].append({"language": lang, "status": "QUOTA_PAUSED"})
                    quota_hit = True  # 0 TL rule: pause, never fall back to a paid path
                except Exception as e:
                    logger.exception("[%s] job failed", lang)
                    self.db.event("EPISODE_PRODUCTION_ERROR", f"{episode_id} [{lang}]: {e}", "ERROR")
                    result["jobs"].append({"language": lang, "episode_id": episode_id, "status": "ERROR", "error": str(e)})
                    result["errors"] += 1
                    lang_jobs.append({"episode_id": episode_id, "state": "FAILED_QA"})  # try next episode next time
                    break
        result["status"] = "COMPLETED_WITH_ERRORS" if result["errors"] else "COMPLETED"
        return self._finish(result, plan, control)

    def _finish(self, result: Dict[str, Any], plan: Dict[str, Any], control: Optional[Dict[str, Any]] = None):
        prev_failures = int((control or {}).get("failure_count") or 0)
        self.db.patch_control({
            "last_run_at": utc_now_iso(),
            "last_heartbeat": utc_now_iso(),
            "next_run_at": plan["next_run_at"],
            "current_job_id": None,
            "failure_count": prev_failures + 1 if result["errors"] else 0,
        })
        self.db.health_snapshot(self.arch, "ACTIVE", "QUOTA_PAUSED" if any(
            j.get("status") == "QUOTA_PAUSED" for j in result["jobs"]) else "READY")
        return result


def _write_github_output(plan: Dict[str, Any]) -> None:
    path = os.getenv("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a") as fh:
        fh.write(f"should_run={'true' if plan['should_run'] else 'false'}\n")
        fh.write(f"languages={' '.join(plan['languages']) or 'EN'}\n")


def main():
    ap = argparse.ArgumentParser(description="SmartKids autonomous cloud factory")
    ap.add_argument("--gate-only", action="store_true", help="only decide + heartbeat (cheap cron step)")
    ap.add_argument("--run-now", action="store_true", help="ignore schedule_time (Android START)")
    ap.add_argument("--force", action="store_true", help="ignore enabled=false (manual maintenance run)")
    ap.add_argument("--dry-run", action="store_true", help="no Supabase, no YouTube; render + QA only")
    ap.add_argument("--strict-supabase", action="store_true")
    args = ap.parse_args()

    orch = AutonomousFactoryOrchestrator(force=args.force, run_now=args.run_now, dry_run=args.dry_run,
                                         strict_supabase=args.strict_supabase)
    if args.gate_only:
        plan = orch.gate()
        _write_github_output(plan)
        print(json.dumps(plan, indent=2))
        return

    result = orch.run_cycle()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "production_run_summary.json"), "w") as fh:
        json.dump(result, fh, indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))
    if result.get("errors"):
        sys.exit(1)  # make failures visible as a red run in GitHub Actions


if __name__ == "__main__":
    main()
