#!/usr/bin/env python3
"""Narrate 1/N of an episode's lines on this runner (parallel narration, "several servers").

All runners of a cycle compute the SAME line list (longform.all_narration with the episode's master
seed) and the SAME deterministic split, so every line is synthesised exactly once. Results are written
into the content-addressed narration cache (tts.cache_key) and copied to --out for upload as a GitHub
artifact; the produce runner downloads all shards and finds every line already narrated.

Exit code 0 = all my lines are clean. 1 = some lines had no clean take (logged; the produce runner will
try them once more and the quality gate decides).
"""
import argparse
import json
import logging
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.engine import tts  # noqa: E402
from backend.engine.factory_plan import shard_lines  # noqa: E402
from backend.engine.longform import PACKS_BY_ID, all_narration  # noqa: E402
from backend.engine.production_runner import make_job_id, master_seed  # noqa: E402
from backend.engine.supabase_rest import SupabaseREST  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("smartkids.tts_shard")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True)
    ap.add_argument("--language", required=True)
    ap.add_argument("--narrator", required=True, choices=list(tts.NARRATORS))
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--of", type=int, required=True)
    ap.add_argument("--out", default="/tmp/tts_shard_out")
    ap.add_argument("--force", action="store_true", help="ignore enabled=false (manual runs)")
    args = ap.parse_args()
    lang = args.language.upper()
    os.makedirs(args.out, exist_ok=True)
    db = SupabaseREST()
    if db.connected and not args.force:
        ctrl = db.get_control() or {}
        if not ctrl.get("enabled"):
            log.info("factory disabled from Android - shard exits without work")
            return 0

    tts.set_narrator(args.narrator)
    lines = all_narration(PACKS_BY_ID[args.episode], master_seed(args.episode), lang)
    mine = shard_lines(lines, args.of)[args.shard]
    todo = [t for t in mine if not tts.is_cached(t, lang)]
    log.info("shard %d/%d %s %s narrator=%s: %d lines (%d already cached)", args.shard + 1, args.of, args.episode, lang,
             args.narrator, len(mine), len(mine) - len(todo))
    job_id = make_job_id(args.episode, lang)[0]
    failed, t0 = [], time.time()
    scratch = os.path.join(args.out, "_scratch")
    os.makedirs(scratch, exist_ok=True)
    for n, text in enumerate(todo, 1):
        wav = os.path.join(scratch, f"{n:03d}.wav")
        try:
            tts.synth(text, lang, wav)
            key = tts.cache_key(text, lang)
            shutil.copy(os.path.join(tts.CACHE_DIR, key + ".wav"), os.path.join(args.out, key + ".wav"))
        except tts.VoiceQualityError as e:
            failed.append({"text": text[:80], "error": str(e)[:300]})
            log.warning("no clean take: %s", text[:60])
        if db.connected and (n % 8 == 0 or n == len(todo)):
            db.heartbeat()
            db.upsert_job({"job_id": job_id, "episode_id": args.episode, "language": lang, "state": "TTS_SYNTHESIS",
                           "deterministic_seed": make_job_id(args.episode, lang)[1],
                           "stage_detail": f"narration runner {args.shard + 1}/{args.of}: {n}/{len(todo)} lines"})
        log.info("  %d/%d lines (%.0fs)", n, len(todo), time.time() - t0)
    shutil.rmtree(scratch, ignore_errors=True)
    for text in mine:  # ship the complete share (also lines cached by earlier runs) to the produce runner
        key = tts.cache_key(text, lang)
        src = os.path.join(tts.CACHE_DIR, key + ".wav")
        if os.path.exists(src) and not os.path.exists(os.path.join(args.out, key + ".wav")):
            shutil.copy(src, os.path.join(args.out, key + ".wav"))
    guard = [a for x in tts.CB_LOG for a in x["attempts"]]
    report = {"episode": args.episode, "language": lang, "narrator": args.narrator, "shard": args.shard, "of": args.of,
              "lines": len(mine), "synthesised": len(todo) - len(failed), "failed": failed,
              "takes": len(guard), "rejected_takes": sum(1 for a in guard if not a.get("ok")),
              "reject_reasons": sorted({w.split(" ")[0] for a in guard for w in a.get("why", [])}),
              "seconds": round(time.time() - t0, 1)}
    with open(os.path.join(args.out, f"shard_report_{lang}_{args.shard}.json"), "w") as fh:
        json.dump({**report, "log": tts.CB_LOG}, fh, indent=1, ensure_ascii=False)
    log.info("SHARD DONE %s", json.dumps(report, ensure_ascii=False))
    if db.connected:
        db.event("TTS_SHARD_DONE" if not failed else "TTS_SHARD_PARTIAL",
                 f"{args.episode} [{lang}] runner {args.shard + 1}/{args.of}: {report['synthesised']}/{len(todo)} lines "
                 f"in {report['seconds']:.0f}s", "INFO" if not failed else "WARNING", details=report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
