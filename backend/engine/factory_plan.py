#!/usr/bin/env python3
"""Plan one factory cycle for the parallel GitHub Actions pipeline.

  gate (enabled? slot? daily target?)  ->  which (episode, language) jobs to make  ->  GitHub matrices:
    tts_matrix     : N narration shards per language (separate runners, all at the same time)
    produce_matrix : one render/QA/upload runner per video

Why parallel: Chatterbox narration of one 10-minute episode takes ~2 h on one CPU runner. The lines are
independent, so 8 runners narrate 1/8 each (~15 min), then the produce runner finds every line in the
cache and only renders (~15 min). Public repository -> GitHub-hosted runners are free (0 TL).

Writes GITHUB_OUTPUT: should_run, mode, tts_matrix, produce_matrix, reason. Prints the plan as JSON.
"""
import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.engine import languages as LANGS  # noqa: E402
from backend.engine.factory_orchestrator import (DEFAULT_CONTROL, PRODUCED_STATES, local_day_bounds,  # noqa: E402
                                                 pick_next_episode, plan_cycle)
from backend.engine.longform import PACKS_BY_ID, all_narration, available_languages, episode_dna_row  # noqa: E402
from backend.engine.production_runner import MAIN_CHANNEL, make_job_id, master_seed, narrator_for  # noqa: E402
from backend.engine.supabase_rest import SupabaseREST  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smartkids.plan")
DEFAULT_SHARDS = 8
MAX_MATRIX = 240  # GitHub limit is 256 jobs per matrix


def shard_lines(lines: List[str], n: int) -> List[List[str]]:
    """Deterministic balanced split by word count (longest first into the lightest shard)."""
    buckets: List[List[str]] = [[] for _ in range(n)]
    load = [0] * n
    for t in sorted(lines, key=lambda x: (-len(x.split()), x)):
        i = load.index(min(load))
        buckets[i].append(t)
        load[i] += len(t.split()) + 3
    return buckets


def channel_ready(mode: str, language: str) -> bool:
    ch = language if mode == "MULTI_CHANNEL" else MAIN_CHANNEL
    return bool(os.getenv("YOUTUBE_CLIENT_ID") and os.getenv(f"YOUTUBE_REFRESH_TOKEN_{ch}"))


def build_plan(control: Dict[str, Any], jobs_today: List[Dict[str, Any]], jobs_by_lang: Dict[str, List[Dict[str, Any]]],
               now_utc: datetime, run_now: bool = False, force: bool = False, episode: str = "",
               languages: List[str] = None, mode: str = "", narrator: str = "", shards: int = 0,
               dry_run: bool = False, check_channels: bool = True) -> Dict[str, Any]:
    """Pure (unit-tested) planning. `episode`/`languages` given = manual run (no gate)."""
    mode = (mode or control.get("distribution_mode") or LANGS.DEFAULT_DISTRIBUTION_MODE).upper()
    narrator_mode = narrator or control.get("narrator_mode") or "alternate"
    shards = int(shards or control.get("tts_shards") or DEFAULT_SHARDS)
    shards = max(1, min(shards, 20))
    localized = set(available_languages())
    plan: Dict[str, Any] = {"mode": mode, "should_run": False, "videos": [], "skipped": [], "reason": ""}

    if languages:  # manual
        langs = [l.upper() for l in languages]
        wanted = {L: 1 for L in langs}
        plan["gate"] = "MANUAL"
    else:
        gate = plan_cycle(control, jobs_today, now_utc, run_now=run_now, force=force)
        plan["gate"] = gate["reason"]
        plan["next_run_at"] = gate["next_run_at"]
        if not gate["should_run"]:
            plan["reason"] = gate["reason"]
            return plan
        langs = gate["languages"]
        wanted = {L: gate["per_language"][L]["remaining"] for L in langs}

    usable = []
    for L in langs:
        if L not in localized or L not in LANGS.LANGUAGES:
            plan["skipped"].append({"language": L, "status": "LANGUAGE_PAUSED", "reason": "no localisation"})
        elif check_channels and not dry_run and not channel_ready(mode, L):
            ch = L if mode == "MULTI_CHANNEL" else MAIN_CHANNEL
            plan["skipped"].append({"language": L, "status": "LANGUAGE_PAUSED",
                                    "reason": f"channel not connected (secret YOUTUBE_REFRESH_TOKEN_{ch})"})
        else:
            usable.append(L)

    if mode == "SINGLE_CHANNEL_MULTI_AUDIO":
        if usable:
            primary = MAIN_CHANNEL if MAIN_CHANNEL in usable else usable[0]
            ordered = [primary] + [L for L in usable if L != primary]
            ep = episode or pick_next_episode(primary, jobs_by_lang.get(primary, []))
            if ep:
                plan["videos"].append({"episode": ep, "languages": ordered, "narrator": narrator_for(ep, narrator_mode)})
            else:
                plan["skipped"].append({"language": primary, "status": "CONTENT_EXHAUSTED"})
    else:
        for L in usable:
            done = list(jobs_by_lang.get(L, []))
            for _ in range(max(1, wanted.get(L, 1))):
                ep = episode or pick_next_episode(L, done)
                if not ep:
                    plan["skipped"].append({"language": L, "status": "CONTENT_EXHAUSTED"})
                    break
                if episode:  # manual: idempotency is still enforced by the production runner
                    pass
                plan["videos"].append({"episode": ep, "languages": [L], "narrator": narrator_for(ep, narrator_mode)})
                done.append({"episode_id": ep, "state": "PROCESSED_PRIVATE"})
                if episode:
                    break

    tts, produce = [], []
    for v in plan["videos"]:
        seed = master_seed(v["episode"])
        for L in v["languages"]:
            lines = all_narration(PACKS_BY_ID[v["episode"]], seed, L)
            n = max(1, min(shards, len(lines) // 6 or 1))
            for i in range(n):
                tts.append({"episode": v["episode"], "language": L, "narrator": v["narrator"], "shard": i, "of": n})
        produce.append({"episode": v["episode"], "languages": " ".join(v["languages"]), "narrator": v["narrator"],
                        "primary": v["languages"][0], "job_id": make_job_id(v["episode"], v["languages"][0])[0]})
    if len(tts) > MAX_MATRIX:
        raise RuntimeError(f"{len(tts)} narration shards > {MAX_MATRIX}; lower tts_shards or daily_master_episodes")
    plan["tts_matrix"] = tts
    plan["produce_matrix"] = produce
    plan["should_run"] = bool(produce)
    plan["reason"] = (f"RUN {len(produce)} video(s), {len(tts)} narration shard(s), mode {mode}" if produce
                      else "NOTHING TO DO: " + "; ".join(f"{s['language']}={s['status']}" for s in plan["skipped"]))
    return plan


def _write_output(plan: Dict[str, Any]) -> None:
    path = os.getenv("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a") as fh:
        fh.write(f"should_run={'true' if plan['should_run'] else 'false'}\n")
        fh.write(f"mode={plan['mode']}\n")
        fh.write(f"tts_matrix={json.dumps({'include': plan.get('tts_matrix') or [{'episode': '', 'language': '', 'narrator': '', 'shard': 0, 'of': 1}]})}\n")
        fh.write(f"produce_matrix={json.dumps({'include': plan.get('produce_matrix') or [{'episode': '', 'languages': '', 'narrator': '', 'primary': '', 'job_id': ''}]})}\n")
        fh.write(f"reason={plan['reason'][:300]}\n")


def main():
    ap = argparse.ArgumentParser(description="Plan a parallel factory cycle")
    ap.add_argument("--run-now", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--episode", default="")
    ap.add_argument("--languages", default="", help="manual run: space/comma list")
    ap.add_argument("--mode", default="")
    ap.add_argument("--narrator", default="")
    ap.add_argument("--shards", type=int, default=0)
    args = ap.parse_args()

    db = SupabaseREST(dry_run=args.dry_run)
    control = (db.get_control() if db.connected else None) or dict(DEFAULT_CONTROL, enabled=True)
    langs = [l for l in re.split(r"[\s,]+", args.languages.upper()) if l]
    jobs_today, jobs_by_lang = [], {}
    if db.connected:
        _, midnight, _ = local_day_bounds(datetime.now(timezone.utc), control.get("timezone"), control.get("schedule_time"))
        jobs_today = db.list_jobs(since_iso=midnight.astimezone(timezone.utc).isoformat())
        for L in (langs or [str(x).upper() for x in (control.get("active_languages") or ["EN"])]):
            jobs_by_lang[L] = db.list_jobs(language=L)
    plan = build_plan(control, jobs_today, jobs_by_lang, datetime.now(timezone.utc), run_now=args.run_now,
                      force=args.force, episode=args.episode, languages=langs, mode=args.mode,
                      narrator=args.narrator, shards=args.shards, dry_run=args.dry_run)
    if db.connected:
        db.heartbeat()
        for s in plan["skipped"]:
            db.event(s["status"], f"{s['language']}: {s.get('reason', s['status'])}", "WARNING")
        for v in plan["videos"]:
            db.upsert_episode(episode_dna_row(PACKS_BY_ID[v["episode"]]))  # FK target of pipeline_jobs
            for L in v["languages"]:
                job_id, seed = make_job_id(v["episode"], L)
                rec = db.get_job(job_id)
                if rec and rec.get("state") in PRODUCED_STATES:
                    continue
                db.upsert_job({"job_id": job_id, "episode_id": v["episode"], "language": L, "state": "QUEUED",
                               "deterministic_seed": seed, "cost_usd": 0.0, "narrator": v["narrator"],
                               "distribution_mode": plan["mode"], "progress_pct": 2,
                               "stage_detail": f"{sum(1 for t in plan['tts_matrix'] if t['language'] == L and t['episode'] == v['episode'])} narration runners"})
        if not plan["should_run"] and plan.get("next_run_at"):
            db.patch_control({"next_run_at": plan["next_run_at"]})
        db.event("FACTORY_PLAN", plan["reason"], details={"videos": plan["videos"], "skipped": plan["skipped"]})
    logger.info("[Plan] %s", plan["reason"])
    _write_output(plan)
    print(json.dumps({k: v for k, v in plan.items() if k != "tts_matrix"}, indent=2, default=str))


if __name__ == "__main__":
    main()
