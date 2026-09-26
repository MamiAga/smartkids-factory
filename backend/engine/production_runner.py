"""SmartKids Production Engine — one (episode, language) job end to end.

GitHub Actions (ubuntu-24.04-arm) + Piper TTS + FFmpeg + YouTube Data API v3 + Supabase.

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
from backend.engine.longform import PACKS_BY_ID, TEMPLATE_VERSION, build_timeline, episode_dna_row  # noqa: E402
from backend.engine.longform import youtube_metadata as longform_metadata  # noqa: E402
from backend.engine import longform_engine, tts  # noqa: E402
from backend.engine.supabase_rest import SupabaseREST  # noqa: E402
from backend.engine import visuals  # noqa: E402
from backend.engine.quality import QualityGateError, RULES, STANDARD_ID, evaluate, measure  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smartkids.production")

ALLOW_PAID_SERVICES = False  # 0 TL invariant — never flipped by code
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
SCRATCH_DIR = "/tmp/smartkids_scratch"
OUTPUT_DIR = "/tmp/smartkids_output"
PUBLISH_PRIVACY = {"AUTO": "public", "PUBLIC": "public", "UNLISTED": "unlisted", "PRIVATE": "private"}

PRODUCTION_VOICES = {
    "EN": {"voice_id": "en_US-libritts_r-medium", "onnx": "models/piper/en/en_US-libritts_r-medium.onnx", "license": "CC-BY-4.0"},
    "ES": {"voice_id": "es_ES-sharvard-medium", "onnx": "models/piper/es/es_ES-sharvard-medium.onnx", "license": "VERIFY"},
    "DE": {"voice_id": "de_DE-thorsten-medium", "onnx": "models/piper/de/de_DE-thorsten-medium.onnx", "license": "CC0-1.0"},
    "FR": {"voice_id": "fr_FR-siwis-medium", "onnx": "models/piper/fr/fr_FR-siwis-medium.onnx", "license": "CC-BY-4.0"},
    "PT": {"voice_id": "pt_BR-edresson-low", "onnx": "models/piper/pt/pt_BR-edresson-low.onnx", "license": "VERIFY"},
}
# Languages whose narration/QA is actually implemented. Others are LANGUAGE_PAUSED, not crashed.
LOCALIZED_LANGUAGES = {"EN"}

# States that mean "a video exists on YouTube for this job" -> never upload again.
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
                 publish_mode: str = "PRIVATE"):
        self.dry_run = dry_run
        self.publish_privacy = PUBLISH_PRIVACY.get((publish_mode or "PRIVATE").upper(), "private")
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
    def _stage(self, job: Dict[str, Any], state: str, **extra) -> None:
        job["state"] = state
        job.update(extra)
        logger.info("[Job %s] state -> %s", job["job_id"], state)
        if self.db.connected:
            self.db.upsert_job(job, strict=self.strict_supabase)
            self.db.heartbeat(current_job_id=job["job_id"])

    # --------------------------------------------------------------------- QA
    @staticmethod
    def run_linguistic_and_pedagogical_qa(language: str, pack: Dict[str, Any]) -> Dict[str, Any]:
        """Content gate on the script before any compute is spent."""
        items = pack["items"]
        if len(items) < 6:
            raise QualityGateError(f"PEDAGOGICAL FAULT: only {len(items)} items (need >= 6)")
        segs = build_timeline(pack)
        text = " ".join(x["text"] for x in segs if x["text"])
        if language == "EN":
            if re.search(r"[çğıöşüİÇĞÖŞÜ]", text):
                raise QualityGateError("LINGUISTIC FAULT: Turkish characters in EN narration")
            if re.search(r"[^\x20-\x7E]", text):
                raise QualityGateError("LINGUISTIC FAULT: non-ASCII characters in EN narration")
        for it in items:
            if len(it["examples"]) < 3:
                raise QualityGateError(f"PEDAGOGICAL FAULT: item {it['key']} has < 3 examples")
        for x in segs:
            if x["text"] and len(x["text"].split()) > 45:
                raise QualityGateError(f"PEDAGOGICAL FAULT: one narration line has > 45 words: {x['text'][:60]}")
        n_countdown = sum(1 for x in segs if x["kind"] == "countdown")
        if n_countdown < len(items):
            raise QualityGateError("INTERACTION FAULT: fewer countdowns than items")
        logger.info("[QA] Script gate PASSED (%s, %d items, %d segments, %d countdowns)",
                    language, len(items), len(segs), n_countdown)
        return {"passed": True}

    # -------------------------------------------------------------------- TTS
    def _tts_scene(self, language: str, text: str, wav_path: str) -> None:
        if self.test_tts:  # dry-run only: approximate speech length with a quiet tone
            seconds = max(2.0, len(text.split()) / 2.8)
            _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=f=220:d={seconds:.2f}",
                  "-af", "volume=0.2", "-ar", "22050", wav_path])
            return
        onnx = os.path.join(BASE_DIR, PRODUCTION_VOICES[language]["onnx"])
        if not os.path.exists(onnx):
            raise LanguageNotReady(f"Piper model missing: {onnx}")
        _run(["piper", "-m", onnx, "-f", wav_path, "--sentence_silence", "0.4"], input=text.encode("utf-8"))

    def synthesize_audio(self, language: str, episode: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Per scene: soft chime (0.6 s) + narration + interaction pause. 48 kHz stereo, 2-pass EBU R128."""
        scenes = episode["scenes"]
        chime = os.path.join(SCRATCH_DIR, f"{job_id}_chime.wav")
        _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=880:d=0.6", "-f", "lavfi", "-i", "sine=f=1318.5:d=0.6",
              "-filter_complex", "[0][1]amix=inputs=2,volume=0.35,afade=t=in:d=0.01,afade=t=out:st=0.05:d=0.55,"
              "aresample=48000,aformat=channel_layouts=stereo", chime])
        speech, durs = [], []
        for sc in scenes:
            wav = os.path.join(SCRATCH_DIR, f"{job_id}_scene{sc['scene_id']}.wav")
            self._tts_scene(language, sc["speech"], wav)
            d = probe_duration(wav)
            if len(sc["speech"].split()) > RULES["max_words_per_scene"]:
                raise QualityGateError(f"scene {sc['scene_id']} longer than {RULES['max_words_per_scene']} words")
            logger.info("  scene %d (%s): %.2fs speech", sc["scene_id"], sc["key"], d)
            speech.append(wav)
            durs.append(d)

        chime_len = 0.6
        target = episode["min_duration_sec"] + 2.0
        pause = round(max(RULES["min_pause_sec"],
                          min(RULES["max_pause_sec"], (target - sum(durs) - chime_len * len(scenes)) / len(scenes))), 3)
        scene_durs = [chime_len + d + pause for d in durs]
        logger.info("[Audio] speech=%.2fs pause=%.2fs/scene total=%.2fs", sum(durs), pause, sum(scene_durs))

        inputs, filt = [], ""
        for i, w in enumerate(speech):
            inputs += ["-i", chime, "-i", w]
            filt += (f"[{2 * i + 1}:a]aresample=48000,aformat=channel_layouts=stereo,apad=pad_dur={pause:.3f}[s{i}];"
                     f"[{2 * i}:a][s{i}]concat=n=2:v=0:a=1[c{i}];")
        filt += "".join(f"[c{i}]" for i in range(len(speech))) + f"concat=n={len(speech)}:v=0:a=1[out]"
        raw = os.path.join(SCRATCH_DIR, f"{job_id}_master_raw.wav")
        _run(["ffmpeg", "-y"] + inputs + ["-filter_complex", filt, "-map", "[out]", raw])

        # two-pass loudnorm -> accurate -16 LUFS / -1.5 dBTP
        p1 = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af",
                             "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr.decode()
        st = json.loads(p1[p1.rfind("{"):p1.rfind("}") + 1])
        master = os.path.join(OUTPUT_DIR, f"{job_id}_master.wav")
        _run(["ffmpeg", "-y", "-i", raw, "-af",
              "loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:"
              f"measured_I={st['input_i']}:measured_TP={st['input_tp']}:measured_LRA={st['input_lra']}:"
              f"measured_thresh={st['input_thresh']}:offset={st['target_offset']},aresample=48000",
              "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", master])
        return {"path": master, "scene_durations": scene_durs, "pause": pause}

    # ----------------------------------------------------------------- render
    def render_video(self, episode: Dict[str, Any], audio: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Pillow cards + animated picture + Lumi, H.264 High 1080p60 CRF 18, BT.709."""
        n = len(episode["scenes"])
        lumi = visuals.render_lumi(SCRATCH_DIR, job_id)
        clips, text_checks, pictures = [], [], []
        for i, sc in enumerate(episode["scenes"]):
            assets = visuals.render_scene_assets(sc, i, n, SCRATCH_DIR, job_id)
            text_checks += assets["text_checks"]
            pictures.append(bool(assets["picture"]))
            d = audio["scene_durations"][i]
            fade_out = max(0.0, d - 0.5)
            filt = (
                "[1:v]format=rgba[p];[2:v]format=rgba[l];"
                "[0:v][p]overlay=x=(W-w)/2:y=375-h/2+12*sin(2*PI*t/1.8):eval=frame[a];"
                "[a][l]overlay=x=40:y=H-h-10+6*sin(2*PI*t/1.3+1):eval=frame,"
                f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out:.3f}:d=0.5,format=yuv420p[v]"
            )
            clip = os.path.join(SCRATCH_DIR, f"{job_id}_clip{i + 1}.mp4")
            _run(["ffmpeg", "-y",
                  "-loop", "1", "-framerate", "60", "-i", assets["bg"],
                  "-loop", "1", "-framerate", "60", "-i", assets["picture"],
                  "-loop", "1", "-framerate", "60", "-i", lumi,
                  "-filter_complex", filt, "-map", "[v]", "-t", f"{d:.3f}", "-r", "60",
                  "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "18", "-g", "120",
                  "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", clip])
            clips.append(clip)

        concat = os.path.join(SCRATCH_DIR, f"{job_id}_concat.txt")
        with open(concat, "w") as fh:
            fh.writelines(f"file '{c}'\n" for c in clips)
        out = os.path.join(OUTPUT_DIR, f"{job_id}_{episode['episode_id'].lower()}.mp4")
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat, "-i", audio["path"],
              "-map", "0:v", "-map", "1:a", "-c:v", "copy",
              "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
              "-shortest", "-movflags", "+faststart", out])
        thumb = visuals.render_thumbnail(episode, os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail.jpg"))
        logger.info("[Render] %s (%d bytes), thumbnail %s", out, os.path.getsize(out), thumb)
        design = {"scenes": n, "text_checks": text_checks, "pictures": pictures,
                  "character_every_scene": True, "pause_sec": audio["pause"]}
        return {"mp4": out, "thumbnail": thumb, "design": design}

    @staticmethod
    def run_quality_gate(render: Dict[str, Any], meta: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        report = evaluate(measure(render["mp4"]), render["design"], meta)
        with open(os.path.join(OUTPUT_DIR, f"{job_id}_quality_report.json"), "w") as fh:
            json.dump(report, fh, indent=2)
        m = report["measurements"]
        logger.info("[QA %s] %s | %.2fs %sx%s@%sfps | %.1f LUFS / %.1f dBTP | luma step %.1f | min contrast %s",
                    STANDARD_ID, "PASS" if report["passed"] else "FAIL", m["duration"], m["width"], m["height"],
                    m["fps"], m["loudness_lufs"] or 0, m["true_peak_dbtp"] or 0, m["max_luma_step"],
                    report["min_text_contrast"])
        if not report["passed"]:
            raise QualityGateError(f"{STANDARD_ID} FAILED: " + "; ".join(report["failures"]))
        return report

    # ---------------------------------------------------------------- YouTube
    @staticmethod
    def _yt_credentials(language: str) -> Dict[str, str]:
        cid = os.getenv("YOUTUBE_CLIENT_ID")
        csec = os.getenv("YOUTUBE_CLIENT_SECRET")
        rtok = os.getenv(f"YOUTUBE_REFRESH_TOKEN_{language}")
        if not (cid and csec and rtok):
            raise LanguageNotReady(f"YouTube OAuth secrets missing for {language} "
                                   f"(need YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN_{language})")
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
        body = {
            "snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                        "categoryId": "27", "defaultLanguage": language.lower(), "defaultAudioLanguage": language.lower()},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": True, "embeddable": True},
        }
        last_err: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                init = urllib.request.Request(
                    "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                    data=json.dumps(body).encode(), method="POST",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                             "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"})
                with urllib.request.urlopen(init, timeout=60) as r:
                    upload_url = r.headers.get("Location")
                with open(mp4, "rb") as fh:
                    put = urllib.request.Request(upload_url, data=fh.read(), method="PUT",
                                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4",
                                                          "Content-Length": str(size)})
                with urllib.request.urlopen(put, timeout=600) as r:
                    video_id = json.loads(r.read().decode()).get("id")
                if not video_id:
                    raise UploadError("YouTube returned no video id")
                logger.info("[YouTube] uploaded, video id %s", video_id)
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
        """Custom thumbnails need a verified channel; failure is a warning, never a blocker."""
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
            logger.warning("[YouTube] thumbnail not set (HTTP %s): %s", e.code, e.read().decode("utf-8", "replace")[:200])
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

    def produce_longform(self, pack: Dict[str, Any], language: str, job_id: str, seed_int: int) -> Dict[str, Any]:
        segs = build_timeline(pack, seed=seed_int)
        total = longform_engine.plan_audio(pack, segs, language, SCRATCH_DIR, job_id, seed_int)
        audio = longform_engine.mix_audio(segs, total, SCRATCH_DIR, os.path.join(OUTPUT_DIR, f"{job_id}_master.wav"),
                                          seed_int)
        self._stage(self._job, "RENDERING")
        rv = longform_engine.render(pack, segs, SCRATCH_DIR, None, job_id)
        mp4 = os.path.join(OUTPUT_DIR, f"{job_id}_{pack['episode_id'].lower()}.mp4")
        longform_engine.mux(rv["video_only"], audio["path"], mp4)
        thumb = visuals.render_longform_thumbnail(pack, os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail.jpg"))
        meta = longform_metadata(pack, longform_engine.chapters(segs))
        meta["made_for_kids"] = True
        lines = [x["text"] for x in segs if x["text"] and x["kind"] != "chant"]  # chant = single sung words
        from backend.engine.longform import INTERJECTIONS, COUNT_SFX
        plain = [re.sub(r"\[[a-z]+\]\s*", "", t) for t in lines]
        acting = {
            "interjection_ratio": round(sum(1 for t in plain if t.startswith(INTERJECTIONS)) / max(1, len(plain)), 2),
            "tagged_ratio": round(sum(1 for t in lines if t.lstrip().startswith("[")) / max(1, len(lines)), 2),
            "whisper_lines": sum(1 for t in lines if "[whisper]" in t),
            "countdown_sfx": all(x["sfx"] == COUNT_SFX and x.get("voice_parts") for x in segs if x["kind"] == "countdown"),
        }
        self._write_scene_json(segs, job_id)
        design = {**acting, "items": len(pack["items"]), "text_checks": rv["text_checks"], "pictures": rv["pictures"],
                  "character_every_scene": True, "decorations": rv["decorations"], "music_bed": audio["music_bed"],
                  "countdowns": rv["countdowns"], "wpm": audio["wpm"], "words": audio["words"],
                  "voice": tts.voice_id(), "segments": len(segs)}
        logger.info("[Long-form] %s: %.1fs, %d words @ %.0f wpm", mp4, total, audio["words"], audio["wpm"])
        return {"mp4": mp4, "thumbnail": thumb, "design": design, "meta": meta}

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
    def run_production(self, episode_id: str, language: str = "EN") -> Dict[str, Any]:
        language = language.upper()
        if episode_id not in PACKS_BY_ID:
            raise KeyError(f"Unknown episode {episode_id}. Known: {list(PACKS_BY_ID)}")
        episode = PACKS_BY_ID[episode_id]
        job_id, seed = make_job_id(episode_id, language)
        logger.info("=" * 64)
        logger.info("PRODUCTION %s  %s [%s]", job_id, episode_id, language)
        logger.info("=" * 64)

        if language not in LOCALIZED_LANGUAGES:
            raise LanguageNotReady(f"{language}: localized narration + language QA not implemented yet")
        if language not in tts.VOICES:
            raise LanguageNotReady(f"{language}: no approved narrator voice")

        # ---- idempotency guard (episode + language + template_version) ----
        existing = self.db.get_job(job_id) if self.db.connected else None
        if existing and existing.get("youtube_video_id") and existing.get("state") in UPLOADED_STATES:
            logger.info("[Idempotency] %s already on YouTube (%s, state=%s) — no re-upload.",
                        job_id, existing["youtube_video_id"], existing["state"])
            if existing.get("state") == "PROCESSING" and not self.dry_run:
                res = self.poll_processing(existing["youtube_video_id"], language, max_wait_sec=60)
                if res["processing_status"] == "succeeded":
                    rec = dict(existing)
                    self._stage(rec, "PROCESSED_PRIVATE", processing_status="succeeded",
                                youtube_privacy_status=res["privacy_status"])
                    # quality gate already passed before this video was uploaded -> publish now
                    privacy = self.publish(existing["youtube_video_id"], language, self.publish_privacy)
                    if privacy in ("public", "unlisted"):
                        self._stage(rec, "COMPLETED", youtube_privacy_status=privacy)
            return {"status": "SKIPPED_DUPLICATE", "job_id": job_id, "episode_id": episode_id,
                    "language": language, "youtube_video_id": existing["youtube_video_id"]}

        if self.db.connected:
            self.db.upsert_episode(episode_dna_row(episode))  # pipeline_jobs.episode_id is a FK
        job: Dict[str, Any] = {"job_id": job_id, "episode_id": episode_id, "language": language,
                               "deterministic_seed": seed, "cost_usd": 0.0, "error_message": None,
                               "technical_qa_passed": False, "educational_qa_passed": False}
        started = time.time()
        try:
            self._stage(job, "VALIDATING")
            self.run_linguistic_and_pedagogical_qa(language, episode)
            job["educational_qa_passed"] = True

            self._stage(job, "TTS_SYNTHESIS")
            self._job = job
            render = self.produce_longform(episode, language, job_id, int(seed[:6], 16))
            mp4 = render["mp4"]
            meta = render["meta"]

            self._stage(job, "QA_TECHNICAL", local_mp4_path=mp4)
            report = self.run_quality_gate(render, meta, job_id)
            job.update(technical_qa_passed=True, render_duration_sec=round(report["measurements"]["duration"], 2))
            self._stage(job, "QA_PEDAGOGICAL")

            if self.dry_run:
                logger.info("[DRY-RUN] upload skipped. MP4: %s", mp4)
                return {"status": "DRY_RUN_OK", "job_id": job_id, "episode_id": episode_id, "language": language,
                        "mp4": mp4, "thumbnail": render["thumbnail"], "quality": report,
                        "duration_sec": job["render_duration_sec"], "elapsed_sec": round(time.time() - started, 1)}

            if self.stop_check and self.stop_check():
                raise UploadError("factory stopped from Android before upload (video kept, will resume)")

            self._stage(job, "UPLOADING")
            video_id = self.upload_to_youtube(mp4, meta, language)
            self._stage(job, "PROCESSING", youtube_video_id=video_id, youtube_privacy_status="private",
                        processing_status="processing")
            thumb_ok = self.set_thumbnail(video_id, render["thumbnail"], language)

            proc = self.poll_processing(video_id, language)
            if proc["processing_status"] in ("failed", "terminated"):
                self._stage(job, "QUARANTINED", processing_status=proc["processing_status"],
                            error_message="YouTube processing failed")
                raise UploadError(f"YouTube processing {proc['processing_status']}")
            privacy = proc["privacy_status"]
            if proc["processing_status"] == "succeeded":
                self._stage(job, "PROCESSED_PRIVATE", processing_status="succeeded", youtube_privacy_status=privacy)
                privacy = self.publish(video_id, language, self.publish_privacy)
                final_state = "COMPLETED" if privacy in ("public", "unlisted") else "PROCESSED_PRIVATE"
                self._stage(job, final_state, youtube_privacy_status=privacy)
            else:
                final_state = "PROCESSING"  # next cycle reconciles + publishes
                self._stage(job, final_state, processing_status=proc["processing_status"])
            if self.db.connected:
                self.db.publication(job_id, video_id, language, privacy, proc["processing_status"])

            summary = {"status": "SUCCESS", "job_id": job_id, "episode_id": episode_id, "language": language,
                       "youtube_video_id": video_id, "watch_url": f"https://youtu.be/{video_id}",
                       "state": final_state, "processing_status": proc["processing_status"],
                       "privacy_status": privacy, "requested_privacy": self.publish_privacy,
                       "thumbnail_set": thumb_ok, "quality_standard": STANDARD_ID,
                       "loudness_lufs": report["measurements"]["loudness_lufs"],
                       "duration_sec": job["render_duration_sec"],
                       "elapsed_sec": round(time.time() - started, 1), "cost_usd": 0.0}
            with open(os.path.join(OUTPUT_DIR, f"{job_id}_summary.json"), "w") as fh:
                json.dump(summary, fh, indent=2)
            return summary

        except QuotaExceeded as e:
            self._stage(job, "QUOTA_PAUSED", error_message=str(e)[:500])
            raise
        except QualityGateError as e:
            self._stage(job, "FAILED_QA", error_message=str(e)[:500])
            raise
        except LanguageNotReady:
            raise
        except UploadError as e:
            self._stage(job, "FAILED_UPLOAD", error_message=str(e)[:500])
            raise
        except Exception as e:  # TTS / render crash -> quarantine this episode, factory keeps going
            self._stage(job, "QUARANTINED", error_message=f"{type(e).__name__}: {str(e)[:480]}")
            raise


def main():
    ap = argparse.ArgumentParser(description="SmartKids single-job production engine")
    ap.add_argument("--episode", default="EP-COLORS-5-V1")
    ap.add_argument("--language", default="EN")
    ap.add_argument("--strict-supabase", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="render + QA only; no YouTube, no Supabase writes")
    ap.add_argument("--publish", default="PRIVATE", choices=["PRIVATE", "UNLISTED", "PUBLIC", "AUTO"],
                    help="privacy to set after processing + quality gate")
    args = ap.parse_args()
    engine = ProductionEngine(strict_supabase=args.strict_supabase, dry_run=args.dry_run, publish_mode=args.publish)
    result = engine.run_production(args.episode, args.language)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
