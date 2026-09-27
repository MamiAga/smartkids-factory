"""SmartKids Production Engine — one master episode -> one language video (or one multi-audio video).

GitHub Actions (ubuntu-24.04-arm) + Chatterbox TTS + FFmpeg + YouTube Data API v3 + Supabase.

Distribution modes (automation_control.distribution_mode, see backend/engine/languages.py):
  MULTI_CHANNEL              every language -> its own channel (YOUTUBE_REFRESH_TOKEN_<LANG>)
  SINGLE_CHANNEL             every language -> its own localized video on the main channel
  SINGLE_CHANNEL_MULTI_AUDIO one video on the main channel, dubbed audio tracks for the other languages

What changed vs. v0.1 (see docs/FACTORY_AUDIT.md):
  * Episodes come from curriculum.py instead of a single hard-coded script.
  * Idempotent: job_id = hash(episode:language:template_version). If that job already
    has a YouTube video id the upload is skipped (no duplicate videos on re-runs/cron).
  * Real progress: every stage is written to pipeline_jobs.state and the runner
    heartbeat (automation_control.last_heartbeat) is refreshed at every stage.
  * Failures are recorded (FAILED_QA / FAILED_UPLOAD / QUOTA_PAUSED / QUARANTINED)
    instead of crashing the whole factory; quota errors never fall back to anything paid.
  * Returns {"status": "SUCCESS", "job_id": ...} — the key the orchestrator expects.
"""
import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.engine.longform import (PACKS, PACKS_BY_ID, TEMPLATE_VERSION, available_languages,  # noqa: E402
                                     build_timeline, episode_dna_row, localize, plain,
                                     starts_with_interjection)
from backend.engine.longform import youtube_metadata as longform_metadata  # noqa: E402
from backend.engine import languages as LANGS  # noqa: E402
from backend.engine import longform_engine, tts  # noqa: E402
from backend.engine.supabase_rest import SupabaseREST, utc_now_iso  # noqa: E402
from backend.engine import visuals  # noqa: E402
from backend.engine.quality import QualityGateError, RULES, STANDARD_ID, evaluate, measure  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smartkids.production")

ALLOW_PAID_SERVICES = False  # 0 TL invariant — never flipped by code
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
SCRATCH_DIR = "/tmp/smartkids_scratch"
OUTPUT_DIR = "/tmp/smartkids_output"
PUBLISH_PRIVACY = {"AUTO": "public", "PUBLIC": "public", "UNLISTED": "unlisted", "PRIVATE": "private"}

# Languages whose localisation file exists (backend/engine/i18n/<CODE>.json). Others are LANGUAGE_PAUSED.
LOCALIZED_LANGUAGES = set(available_languages())
MAIN_CHANNEL = os.getenv("SMARTKIDS_MAIN_CHANNEL", "EN")   # single-channel modes upload here

# States that mean "a video exists on YouTube for this job" -> never upload again.
STATE_PROGRESS = {"QUEUED": 2, "VALIDATING": 5, "TTS_SYNTHESIS": 10, "RENDERING": 55, "QA_TECHNICAL": 80,
                  "QA_PEDAGOGICAL": 84, "UPLOADING": 88, "PROCESSING": 94, "PROCESSED_PRIVATE": 100, "COMPLETED": 100,
                  "DUB_READY_FOR_STUDIO": 100}
UPLOADED_STATES = {"UPLOADED_PRIVATE", "PROCESSING", "PROCESSED_PRIVATE", "COMPLETED"}
FINAL_SUCCESS_STATES = {"PROCESSED_PRIVATE", "COMPLETED"}


class LanguageNotReady(Exception):
    pass


class QuotaExceeded(Exception):
    pass


class UploadError(Exception):
    pass


def make_job_id(episode_id: str, language: str) -> (str, str):
    seed = hashlib.sha256(f"{episode_id}:{language}:{TEMPLATE_VERSION}".encode("utf-8")).hexdigest()
    return f"JOB-{language}-{seed[:8]}", seed


def master_seed(episode_id: str) -> int:
    """Timeline seed shared by all languages of an episode (same quiz order / choices in every language,
    required for one video with several dubbed audio tracks)."""
    return int(hashlib.sha256(f"{episode_id}:{TEMPLATE_VERSION}:master".encode()).hexdigest()[:6], 16)


def narrator_for(episode_id: str, mode: str = "alternate") -> str:
    """Girl / boy narrator alternates per episode unless the control row forces one."""
    mode = (mode or "alternate").lower()
    if mode in tts.NARRATORS:
        return mode
    order = [p["episode_id"] for p in PACKS].index(episode_id)
    return "female" if order % 2 == 0 else "male"


def _run(cmd: List[str], **kw) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    if p.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed ({p.returncode}): {p.stderr.decode('utf-8', 'replace')[-800:]}")
    return p


def probe_duration(path: str) -> float:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", path]).stdout.decode().strip()
    return float(out)


class ProductionEngine:
    def __init__(self, strict_supabase: bool = False, dry_run: bool = False,
                 db: Optional[SupabaseREST] = None, stop_check: Optional[Callable[[], bool]] = None,
                 publish_mode: str = "PRIVATE", distribution_mode: str = LANGS.DEFAULT_DISTRIBUTION_MODE,
                 narrator_mode: str = "alternate"):
        self.dry_run = dry_run
        self.publish_privacy = PUBLISH_PRIVACY.get((publish_mode or "PRIVATE").upper(), "private")
        self.distribution_mode = (distribution_mode or LANGS.DEFAULT_DISTRIBUTION_MODE).upper()
        if self.distribution_mode not in LANGS.DISTRIBUTION_MODES:
            raise ValueError(f"distribution_mode must be one of {LANGS.DISTRIBUTION_MODES}")
        self.narrator_mode = narrator_mode or "alternate"
        self.strict_supabase = strict_supabase and not dry_run
        self.db = db or SupabaseREST(dry_run=dry_run)
        self.stop_check = stop_check
        self.test_tts = os.getenv("SMARTKIDS_TEST_TTS") == "1"
        if self.test_tts and not dry_run:
            raise RuntimeError("SMARTKIDS_TEST_TTS is only allowed together with --dry-run.")
        if self.strict_supabase and not self.db.connected:
            raise RuntimeError("STRICT SUPABASE: SUPABASE_URL and SUPABASE_SECRET_KEY are mandatory.")
        os.makedirs(SCRATCH_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ------------------------------------------------------------ bookkeeping
    def _stage(self, job: Dict[str, Any], state: str, strict: Optional[bool] = None, **extra) -> None:
        job["state"] = state
        job.update(extra)
        if state in STATE_PROGRESS:
            job["progress_pct"] = STATE_PROGRESS[state]
        logger.info("[Job %s] state -> %s", job["job_id"], state)
        if self.db.connected:
            self.db.upsert_job(job, strict=self.strict_supabase if strict is None else strict)
            self.db.heartbeat(current_job_id=job["job_id"])

    def _stage_all(self, jobs: List[Dict[str, Any]], state: str, **extra) -> None:
        for j in jobs:
            self._stage(j, state, **extra)

    # --------------------------------------------------------------------- QA
    @staticmethod
    def run_linguistic_and_pedagogical_qa(language: str, pack: Dict[str, Any]) -> Dict[str, Any]:
        """Content gate on the localized script before any compute is spent."""
        lp = localize(pack, language)
        items = lp["items"]
        if len(items) < 6:
            raise QualityGateError(f"PEDAGOGICAL FAULT: only {len(items)} items (need >= 6)")
        segs = build_timeline(pack, language=language)
        texts = [x["text"] for x in segs if x["text"]]
        if language == "EN":
            joined = " ".join(texts)
            if re.search(r"[çğıöşüİÇĞÖŞÜ]", joined):
                raise QualityGateError("LINGUISTIC FAULT: Turkish characters in EN narration")
            if re.search(r"[^\x20-\x7E]", joined):
                raise QualityGateError("LINGUISTIC FAULT: non-ASCII characters in EN narration")
        for t in texts:
            if "{" in t or "}" in t:
                raise QualityGateError(f"LINGUISTIC FAULT: unfilled placeholder in {t[:60]!r}")
            if not t.lstrip().startswith("["):
                raise QualityGateError(f"ACTING FAULT: line without emotion tag: {t[:60]!r}")
        for it in items:
            if len(it["examples"]) < 3:
                raise QualityGateError(f"PEDAGOGICAL FAULT: item {it['key']} has < 3 examples")
        for x in segs:
            if x["text"] and sum(1 for w in plain(x["text"]).split() if any(c.isalnum() for c in w)) > 45:
                raise QualityGateError(f"PEDAGOGICAL FAULT: one narration line has > 45 words: {x['text'][:60]}")
        n_countdown = sum(1 for x in segs if x["kind"] == "countdown")
        if n_countdown < len(items):
            raise QualityGateError("INTERACTION FAULT: fewer countdowns than items")
        logger.info("[QA] Script gate PASSED (%s, %d items, %d segments, %d countdowns)",
                    language, len(items), len(segs), n_countdown)
        return {"passed": True}

    @staticmethod
    def run_quality_gate(render: Dict[str, Any], meta: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        report = evaluate(measure(render["mp4"]), render["design"], meta)
        with open(os.path.join(OUTPUT_DIR, f"{job_id}_quality_report.json"), "w") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        m = report["measurements"]
        logger.info("[QA %s] %s | %.2fs %sx%s@%sfps | %.1f LUFS / %.1f dBTP | luma step %.1f | min contrast %s",
                    STANDARD_ID, "PASS" if report["passed"] else "FAIL", m["duration"], m["width"], m["height"],
                    m["fps"], m["loudness_lufs"] or 0, m["true_peak_dbtp"] or 0, m["max_luma_step"],
                    report["min_text_contrast"])
        if not report["passed"]:
            raise QualityGateError(f"{STANDARD_ID} FAILED: " + "; ".join(report["failures"]))
        return report

    # ---------------------------------------------------------------- YouTube
    def channel_for(self, language: str) -> str:
        """Which channel's refresh token uploads this language."""
        return language if self.distribution_mode == "MULTI_CHANNEL" else MAIN_CHANNEL

    def _yt_credentials(self, language: str) -> Dict[str, str]:
        ch = self.channel_for(language)
        cid = os.getenv("YOUTUBE_CLIENT_ID")
        csec = os.getenv("YOUTUBE_CLIENT_SECRET")
        rtok = os.getenv(f"YOUTUBE_REFRESH_TOKEN_{ch}")
        if not (cid and csec and rtok):
            raise LanguageNotReady(f"YouTube channel for {language} not connected "
                                   f"(need YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN_{ch})")
        return {"client_id": cid, "client_secret": csec, "refresh_token": rtok}

    @staticmethod
    def _raise_for_youtube(e: urllib.error.HTTPError) -> None:
        body = e.read().decode("utf-8", "replace")
        if e.code == 403 and any(r in body for r in ("quotaExceeded", "uploadLimitExceeded", "rateLimitExceeded", "dailyLimitExceeded")):
            raise QuotaExceeded(f"YouTube quota/limit reached: {body[:300]}")
        raise UploadError(f"YouTube HTTP {e.code}: {body[:300]}")

    def _access_token(self, creds: Dict[str, str]) -> str:
        data = urllib.parse.urlencode({**creds, "grant_type": "refresh_token"}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30) as r:
                return json.loads(r.read().decode())["access_token"]
        except urllib.error.HTTPError as e:
            raise UploadError(f"OAuth refresh failed HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")

    def upload_to_youtube(self, mp4: str, meta: Dict[str, Any], language: str) -> str:
        token = self._access_token(self._yt_credentials(language))
        size = os.path.getsize(mp4)
        yt_lang = LANGS.get(language)["yt"]
        body = {
            "snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                        "categoryId": "27", "defaultLanguage": yt_lang, "defaultAudioLanguage": yt_lang},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": True, "embeddable": True},
        }
        parts = "snippet,status"
        if meta.get("localizations"):  # titles/descriptions shown to viewers of the other languages
            body["localizations"] = meta["localizations"]
            parts += ",localizations"
        last_err: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                init = urllib.request.Request(
                    f"https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part={parts}",
                    data=json.dumps(body).encode(), method="POST",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                             "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"})
                with urllib.request.urlopen(init, timeout=60) as r:
                    upload_url = r.headers.get("Location")
                with open(mp4, "rb") as fh:
                    put = urllib.request.Request(upload_url, data=fh.read(), method="PUT",
                                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4",
                                                          "Content-Length": str(size)})
                with urllib.request.urlopen(put, timeout=900) as r:
                    video_id = json.loads(r.read().decode()).get("id")
                if not video_id:
                    raise UploadError("YouTube returned no video id")
                logger.info("[YouTube] uploaded (%s channel), video id %s", self.channel_for(language), video_id)
                return video_id
            except urllib.error.HTTPError as e:
                if e.code >= 500:
                    last_err = UploadError(f"YouTube HTTP {e.code}")
                else:
                    self._raise_for_youtube(e)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_err = UploadError(f"network: {e}")
            wait = 15 * attempt
            logger.warning("[YouTube] attempt %d failed (%s); retrying in %ds", attempt, last_err, wait)
            time.sleep(wait)
        raise last_err or UploadError("upload failed")

    def poll_processing(self, video_id: str, language: str, max_wait_sec: int = 300) -> Dict[str, str]:
        token = self._access_token(self._yt_credentials(language))
        status, privacy = "processing", "private"
        deadline = time.time() + max_wait_sec
        while time.time() < deadline:
            try:
                url = f"https://www.googleapis.com/youtube/v3/videos?part=status,processingDetails&id={video_id}"
                with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}), timeout=30) as r:
                    items = json.loads(r.read().decode()).get("items", [])
                if items:
                    status = items[0].get("processingDetails", {}).get("processingStatus", "processing")
                    privacy = items[0].get("status", {}).get("privacyStatus", privacy)
                    logger.info("  [poll] processing=%s privacy=%s", status, privacy)
                    if status in ("succeeded", "failed", "terminated"):
                        break
            except urllib.error.HTTPError as e:
                self._raise_for_youtube(e)
            except Exception as e:
                logger.warning("  [poll] %s", e)
            time.sleep(10)
        return {"processing_status": status, "privacy_status": privacy}

    def set_thumbnail(self, video_id: str, jpg: str, language: str) -> bool:
        """Custom thumbnails need a phone-verified channel; failure is a warning, never a blocker."""
        token = self._access_token(self._yt_credentials(language))
        with open(jpg, "rb") as fh:
            req = urllib.request.Request(
                f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}",
                data=fh.read(), method="POST",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"})
        try:
            with urllib.request.urlopen(req, timeout=60):
                logger.info("[YouTube] custom thumbnail set")
                return True
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf-8", "replace")[:200]
            logger.warning("[YouTube] thumbnail not set (HTTP %s): %s", e.code, txt)
            if self.db.connected and e.code == 403:
                self.db.event("THUMBNAIL_BLOCKED", "Custom thumbnail refused (HTTP 403). Verify the channel once at "
                              "youtube.com/verify so thumbnails upload automatically.", "WARNING")
            return False

    def publish(self, video_id: str, language: str, privacy: str) -> str:
        """Switch privacy after processing + quality gate. Returns the privacy YouTube actually reports.
        Unaudited API projects stay locked to private — that is reported, not hidden."""
        if privacy == "private":
            return "private"
        token = self._access_token(self._yt_credentials(language))
        body = {"id": video_id, "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": True,
                                           "embeddable": True, "license": "youtube"}}
        req = urllib.request.Request("https://www.googleapis.com/youtube/v3/videos?part=status",
                                     data=json.dumps(body).encode(), method="PUT",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60):
                pass
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf-8", "replace")[:300]
            logger.warning("[YouTube] publish refused HTTP %s: %s", e.code, txt)
            if self.db.connected:
                self.db.event("PUBLISH_BLOCKED", f"{video_id}: HTTP {e.code} {txt}", "WARNING")
        final = self.poll_processing(video_id, language, max_wait_sec=20)["privacy_status"]
        if final != privacy and self.db.connected:
            self.db.event("PUBLISH_BLOCKED_BY_YOUTUBE",
                          f"{video_id} stays '{final}' (requested '{privacy}'). Unaudited API projects are "
                          "locked to private until the YouTube API compliance audit is approved.", "WARNING")
        logger.info("[YouTube] requested %s -> YouTube reports %s", privacy, final)
        return final

    # ----------------------------------------------------------------- produce
    def produce_longform(self, pack: Dict[str, Any], langs: List[str], job_key: str, narrator: str) -> Dict[str, Any]:
        """Narrate every language track on one shared timeline, render the video once (on-screen text in the
        first language), mix one audio master per language. len(langs) == 1 for the per-language modes."""
        tts.set_narrator(narrator)
        seed = master_seed(pack["episode_id"])
        primary = langs[0]
        tracks = {L: build_timeline(pack, seed=seed, language=L) for L in langs}
        total = longform_engine.plan_tracks(pack, tracks, SCRATCH_DIR, job_key, seed)
        audios = {}
        for L in langs:
            audios[L] = longform_engine.mix_audio(tracks[L], total, SCRATCH_DIR,
                                                  os.path.join(OUTPUT_DIR, f"{job_key}_{L}_master.wav"), seed, L)
        self._stage_all(self._jobs, "RENDERING")
        lp = localize(pack, primary)
        segs = tracks[primary]
        rv = longform_engine.render(lp, segs, SCRATCH_DIR, None, job_key)
        mp4 = os.path.join(OUTPUT_DIR, f"{job_key}_{pack['episode_id'].lower()}.mp4")
        longform_engine.mux(rv["video_only"], audios[primary]["path"], mp4)
        dubs = {}
        for L in langs[1:]:  # dubbed tracks: same timeline, AAC files ready for YouTube Studio "Add language"
            out = os.path.join(OUTPUT_DIR, f"{job_key}_{pack['episode_id'].lower()}_audio_{L}.m4a")
            _run(["ffmpeg", "-y", "-loglevel", "error", "-i", audios[L]["path"], "-af",
                  "aresample=192000,alimiter=limit=0.708:attack=1:release=50:level=false,aresample=48000",
                  "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out])
            dubs[L] = out
        thumb = visuals.render_longform_thumbnail(lp, os.path.join(OUTPUT_DIR, f"{job_key}_thumbnail.jpg"))
        chapters = longform_engine.chapters(segs)
        meta = longform_metadata(pack, chapters, primary)
        meta["made_for_kids"] = True
        if len(langs) > 1:
            meta["localizations"] = {}
            for L in langs[1:]:
                m = longform_metadata(pack, longform_engine.chapters(tracks[L]), L)
                meta["localizations"][LANGS.get(L)["yt"]] = {"title": m["title"], "description": m["description"]}
        lines = [x["text"] for x in segs if x["text"] and x["kind"] != "chant"]
        from backend.engine.longform import COUNT_SFX
        acting = {
            "interjection_ratio": round(sum(1 for t in lines if starts_with_interjection(t, lp["interjections"]))
                                        / max(1, len(lines)), 2),
            "tagged_ratio": round(sum(1 for t in lines if t.lstrip().startswith("[")) / max(1, len(lines)), 2),
            "whisper_lines": sum(1 for t in lines if "[whisper]" in t),
            "countdown_sfx": all(x["sfx"] == COUNT_SFX and x.get("voice_parts") for x in segs if x["kind"] == "countdown"),
        }
        self._write_scene_json(segs, job_key)
        guard = [a for x in tts.CB_LOG for a in x["attempts"]]
        sims = [a["sim_min"] for a in guard if a.get("ok") and "sim_min" in a]
        design = {**acting, "items": len(pack["items"]), "text_checks": rv["text_checks"], "pictures": rv["pictures"],
                  "character_every_scene": True, "decorations": rv["decorations"], "music_bed": audios[primary]["music_bed"],
                  "countdowns": rv["countdowns"], "wpm": audios[primary]["wpm"], "words": audios[primary]["words"],
                  "voice": tts.voice_id(primary), "segments": len(segs), "narrator": narrator,
                  "language": primary, "dub_languages": langs[1:],
                  "dub_wpm": {L: audios[L]["wpm"] for L in langs[1:]},
                  "retakes": sum(1 for a in guard if not a.get("ok")),
                  "voice_guard": {"takes": len(guard), "rejected": sum(1 for a in guard if not a.get("ok")),
                                  "worst_accepted_similarity": min(sims) if sims else None},
                  "voice_fallbacks": len(tts.FALLBACKS)}
        logger.info("[Long-form] %s: %.1fs, %d words @ %.0f wpm, narrator %s, guard %s", mp4, total,
                    audios[primary]["words"], audios[primary]["wpm"], narrator, design["voice_guard"])
        return {"mp4": mp4, "thumbnail": thumb, "design": design, "meta": meta, "dubs": dubs}

    @staticmethod
    def _write_scene_json(segs, job_id):
        """Audit export in the producer's scene template format (one entry per segment)."""
        out = []
        for i, x in enumerate(segs):
            sfx = x["sfx"]
            out.append({
                "scene_id": i + 1, "kind": x["kind"], "start_sec": round(x["t0"], 2), "duration_sec": round(x["dur"], 2),
                "background_music": "smartkids_bed_124bpm (ducked -70% under voice)",
                "sfx_at_start": sfx[0][1] if sfx else None,
                "sfx_timeline": [{"at": round(o, 2), "sfx": k} for o, k in sfx],
                "text_to_speech": x["text"] or " ".join(t for _, t in x.get("voice_parts", [])),
            })
        with open(os.path.join(OUTPUT_DIR, f"{job_id}_scenes.json"), "w") as fh:
            json.dump(out, fh, indent=1, ensure_ascii=False)

    # -------------------------------------------------------------- main flow
    def _check_language(self, language: str) -> None:
        if language not in LOCALIZED_LANGUAGES:
            raise LanguageNotReady(f"{language}: no localisation file backend/engine/i18n/{language}.json")
        LANGS.get(language)

    def _existing_upload(self, job_id: str) -> Optional[Dict[str, Any]]:
        existing = self.db.get_job(job_id) if self.db.connected else None
        if existing and existing.get("youtube_video_id") and existing.get("state") in UPLOADED_STATES:
            return existing
        return None

    def run_production(self, episode_id: str, language: str = "EN", narrator: Optional[str] = None) -> Dict[str, Any]:
        """One language -> one video (MULTI_CHANNEL / SINGLE_CHANNEL)."""
        return self._run(episode_id, [language.upper()], narrator)

    def run_multi_audio(self, episode_id: str, langs: List[str], narrator: Optional[str] = None) -> Dict[str, Any]:
        """One video on the main channel + dubbed audio tracks for the other languages."""
        return self._run(episode_id, [l.upper() for l in langs], narrator)

    def _run(self, episode_id: str, langs: List[str], narrator: Optional[str]) -> Dict[str, Any]:
        if episode_id not in PACKS_BY_ID:
            raise KeyError(f"Unknown episode {episode_id}. Known: {list(PACKS_BY_ID)}")
        episode = PACKS_BY_ID[episode_id]
        narrator = narrator or narrator_for(episode_id, self.narrator_mode)
        primary = langs[0]
        for L in langs:
            self._check_language(L)
        jobs = []
        for L in langs:
            job_id, seed = make_job_id(episode_id, L)
            jobs.append({"job_id": job_id, "episode_id": episode_id, "language": L, "deterministic_seed": seed,
                         "cost_usd": 0.0, "error_message": None, "technical_qa_passed": False,
                         "educational_qa_passed": False, "narrator": narrator,
                         "distribution_mode": self.distribution_mode})
        main = jobs[0]
        job_key = main["job_id"] if len(langs) == 1 else f"{main['job_id']}-MA"
        logger.info("=" * 64)
        logger.info("PRODUCTION %s  %s [%s] narrator=%s mode=%s", job_key, episode_id, "+".join(langs), narrator,
                    self.distribution_mode)
        logger.info("=" * 64)

        # ---- idempotency guard (episode + language + template_version) ----
        existing = self._existing_upload(main["job_id"])
        if existing:
            logger.info("[Idempotency] %s already on YouTube (%s, state=%s) — no re-upload.",
                        main["job_id"], existing["youtube_video_id"], existing["state"])
            if existing.get("state") == "PROCESSING" and not self.dry_run:
                res = self.poll_processing(existing["youtube_video_id"], primary, max_wait_sec=60)
                if res["processing_status"] == "succeeded":
                    rec = dict(existing)
                    self._stage(rec, "PROCESSED_PRIVATE", processing_status="succeeded",
                                youtube_privacy_status=res["privacy_status"])
                    privacy = self.publish(existing["youtube_video_id"], primary, self.publish_privacy)
                    if privacy in ("public", "unlisted"):
                        self._stage(rec, "COMPLETED", youtube_privacy_status=privacy)
            return {"status": "SKIPPED_DUPLICATE", "job_id": main["job_id"], "episode_id": episode_id,
                    "language": primary, "youtube_video_id": existing["youtube_video_id"]}
        if not self.dry_run:
            self._yt_credentials(primary)  # no channel -> LANGUAGE_PAUSED before hours of rendering

        if self.db.connected:
            self.db.upsert_episode(episode_dna_row(episode))  # pipeline_jobs.episode_id is a FK
        self._jobs = jobs
        started = time.time()
        try:
            self._stage_all(jobs, "VALIDATING")
            for L in langs:
                self.run_linguistic_and_pedagogical_qa(L, episode)
            for j in jobs:
                j["educational_qa_passed"] = True

            self._stage_all(jobs, "TTS_SYNTHESIS")
            render = self.produce_longform(episode, langs, job_key, narrator)
            mp4, meta = render["mp4"], render["meta"]

            self._stage_all(jobs, "QA_TECHNICAL", local_mp4_path=mp4)
            report = self.run_quality_gate(render, meta, job_key)
            for j in jobs:
                j.update(technical_qa_passed=True, render_duration_sec=round(report["measurements"]["duration"], 2))
            self._stage_all(jobs, "QA_PEDAGOGICAL")

            if self.dry_run:
                logger.info("[DRY-RUN] upload skipped. MP4: %s", mp4)
                return {"status": "DRY_RUN_OK", "job_id": job_key, "episode_id": episode_id, "languages": langs,
                        "mp4": mp4, "dubs": render["dubs"], "thumbnail": render["thumbnail"], "quality": report,
                        "duration_sec": main["render_duration_sec"], "elapsed_sec": round(time.time() - started, 1)}

            if self.stop_check and self.stop_check():
                raise UploadError("factory stopped from Android before upload (video kept, will resume)")

            self._stage_all(jobs, "UPLOADING")
            video_id = self.upload_to_youtube(mp4, meta, primary)
            self._stage_all(jobs, "PROCESSING", youtube_video_id=video_id, youtube_privacy_status="private",
                            processing_status="processing")
            thumb_ok = self.set_thumbnail(video_id, render["thumbnail"], primary)

            proc = self.poll_processing(video_id, primary)
            if proc["processing_status"] in ("failed", "terminated"):
                self._stage_all(jobs, "QUARANTINED", processing_status=proc["processing_status"],
                                error_message="YouTube processing failed")
                raise UploadError(f"YouTube processing {proc['processing_status']}")
            privacy = proc["privacy_status"]
            if proc["processing_status"] == "succeeded":
                self._stage_all(jobs, "PROCESSED_PRIVATE", processing_status="succeeded", youtube_privacy_status=privacy)
                privacy = self.publish(video_id, primary, self.publish_privacy)
                final_state = "COMPLETED" if privacy in ("public", "unlisted") else "PROCESSED_PRIVATE"
            else:
                final_state = "PROCESSING"  # next cycle reconciles + publishes
            self._stage(main, final_state, youtube_privacy_status=privacy, processing_status=proc["processing_status"])
            for j in jobs[1:]:  # dubbed tracks exist as files; YouTube's API cannot attach audio tracks
                self._stage(j, "DUB_READY_FOR_STUDIO", strict=False, youtube_privacy_status=privacy,
                            error_message=None, stage_detail=os.path.basename(render["dubs"][j["language"]]))
            if self.db.connected:
                self.db.publication(main["job_id"], video_id, primary, privacy, proc["processing_status"])
                if render["dubs"]:
                    self.db.event("DUB_TRACKS_READY", f"{video_id}: dubbed audio for {', '.join(render['dubs'])} is in "
                                  "the run artifacts. YouTube Studio > Languages > Add language > Dub (API has no endpoint).",
                                  "WARNING", details={"video_id": video_id, "tracks": list(render["dubs"])})

            summary = {"status": "SUCCESS", "job_id": main["job_id"], "episode_id": episode_id, "language": primary,
                       "languages": langs, "narrator": narrator, "distribution_mode": self.distribution_mode,
                       "youtube_video_id": video_id, "watch_url": f"https://youtu.be/{video_id}",
                       "state": final_state, "processing_status": proc["processing_status"],
                       "privacy_status": privacy, "requested_privacy": self.publish_privacy,
                       "thumbnail_set": thumb_ok, "quality_standard": STANDARD_ID,
                       "loudness_lufs": report["measurements"]["loudness_lufs"],
                       "duration_sec": main["render_duration_sec"], "dub_tracks": list(render["dubs"]),
                       "elapsed_sec": round(time.time() - started, 1), "cost_usd": 0.0}
            with open(os.path.join(OUTPUT_DIR, f"{job_key}_summary.json"), "w") as fh:
                json.dump(summary, fh, indent=2)
            return summary

        except QuotaExceeded as e:
            self._stage_all(jobs, "QUOTA_PAUSED", error_message=str(e)[:500])
            raise
        except (QualityGateError, tts.VoiceQualityError) as e:
            self._stage_all(jobs, "FAILED_QA", error_message=str(e)[:500])
            raise
        except LanguageNotReady:
            raise
        except UploadError as e:
            self._stage_all(jobs, "FAILED_UPLOAD", error_message=str(e)[:500])
            raise
        except Exception as e:  # TTS / render crash -> quarantine this episode, factory keeps going
            self._stage_all(jobs, "QUARANTINED", error_message=f"{type(e).__name__}: {str(e)[:480]}")
            raise


def main():
    ap = argparse.ArgumentParser(description="SmartKids production engine (one episode)")
    ap.add_argument("--episode", default="EP-COLORS-MEGA-V1")
    ap.add_argument("--language", default="EN", help="one language (per-language modes)")
    ap.add_argument("--languages", default="", help="space/comma list -> one multi-audio video (first = on-screen)")
    ap.add_argument("--narrator", default="", choices=["", "female", "male"])
    ap.add_argument("--mode", default="", help="distribution mode override")
    ap.add_argument("--strict-supabase", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="render + QA only; no YouTube, no Supabase writes")
    ap.add_argument("--publish", default="", choices=["", "PRIVATE", "UNLISTED", "PUBLIC", "AUTO"],
                    help="privacy after processing + quality gate (default: automation_control.publish_mode)")
    ap.add_argument("--respect-stop", action="store_true", help="Android STOP (enabled=false) cancels before upload")
    args = ap.parse_args()
    langs = [l for l in re.split(r"[\s,]+", args.languages.upper()) if l] or [args.language.upper()]
    db = SupabaseREST(dry_run=args.dry_run)
    control = (db.get_control() if db.connected else None) or {}
    mode = args.mode.upper() or ("SINGLE_CHANNEL_MULTI_AUDIO" if len(langs) > 1 else
                                 str(control.get("distribution_mode") or LANGS.DEFAULT_DISTRIBUTION_MODE))
    stop = (lambda: not bool((db.get_control() or {}).get("enabled"))) if args.respect_stop and db.connected else None
    engine = ProductionEngine(strict_supabase=args.strict_supabase, dry_run=args.dry_run, db=db, stop_check=stop,
                              publish_mode=args.publish or str(control.get("publish_mode") or "PRIVATE"),
                              distribution_mode=mode, narrator_mode=str(control.get("narrator_mode") or "alternate"))
    try:
        if len(langs) > 1:
            result = engine.run_multi_audio(args.episode, langs, args.narrator or None)
        else:
            result = engine.run_production(args.episode, langs[0], args.narrator or None)
    except LanguageNotReady as e:
        logger.warning("LANGUAGE_PAUSED: %s", e)
        if db.connected:
            db.event("LANGUAGE_PAUSED", str(e), "WARNING")
            db.patch_control({"current_job_id": None, "last_heartbeat": utc_now_iso()})
        print(json.dumps({"status": "LANGUAGE_PAUSED", "reason": str(e)}))
        return
    except Exception as e:
        if db.connected:
            db.event("EPISODE_PRODUCTION_ERROR", f"{args.episode} [{'+'.join(langs)}]: {str(e)[:300]}", "ERROR")
            db.patch_control({"current_job_id": None, "last_run_at": utc_now_iso(),
                              "failure_count": int(control.get("failure_count") or 0) + 1})
        raise
    if db.connected:
        if result.get("status") == "SUCCESS":
            db.event("EPISODE_PRODUCTION_SUCCESS", f"{args.episode} [{'+'.join(langs)}] -> {result['watch_url']}",
                     details=result)
        db.patch_control({"current_job_id": None, "last_run_at": utc_now_iso(), "failure_count": 0})
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
