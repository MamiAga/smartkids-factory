#!/usr/bin/env python3
"""Voice audition: render the SAME ~70 s opening of EP-COLORS-MEGA-V1 with several narrator setups,
mixed exactly like production (music bed, 70 % ducking, countdown tick-tock, pop/tada SFX), so a human
can pick the most theatrical voice by ear. Output: /tmp/smartkids_output/audition_*.mp3 + audition.json
"""
import json
import logging
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.engine import longform_engine as L, tts  # noqa: E402
from backend.engine.longform import PACKS, build_timeline  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("audition")
OUT = "/tmp/smartkids_output"
N_SEGMENTS = 12  # intro, mystery, countdown, reveal, repeat, 3 examples, quiz, countdown, answer, ...


def pitch_up(path: str, ratio: float) -> None:
    tmp = path.replace(".wav", "_p.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-af", f"rubberband=pitch={ratio}", tmp], check=True)
    os.replace(tmp, path)


def render(name: str, engine: str, kokoro_styles=None, pitch=None, exag=None) -> dict:
    tts.ENGINE = engine
    if exag is not None:  # restart the worker with a new emotion intensity
        os.environ["CB_EXAG_EXCITED"] = str(exag)
        if tts._cb is not None:
            tts._cb.kill()
            tts._cb = None
    saved = dict(tts.STYLES)
    if kokoro_styles:
        tts.STYLES.update(kokoro_styles)
    L._PART_CACHE.clear()
    scratch = f"/tmp/aud_{name}"
    os.makedirs(scratch, exist_ok=True)
    pack = PACKS[0]
    segs = build_timeline(pack, seed=5)[:N_SEGMENTS]
    for s in segs:
        s["pad"] = s["visual"].pop("pad", 0) if "pad" in s["visual"] else 0
    t0 = time.time()
    L.narrate(segs, "EN", scratch, name)
    synth_sec = time.time() - t0
    if pitch:
        for s in segs:
            if s.get("voice_path"):
                pitch_up(s["voice_path"], pitch)
        for p in L._PART_CACHE.values():
            pitch_up(p, pitch)
    total = L._durations(segs)
    speech = sum(s.get("speech_sec", 0) for s in segs)
    wav = os.path.join(scratch, "mix.wav")
    L.mix_audio(segs, total, scratch, wav, 5)
    mp3 = os.path.join(OUT, f"audition_{name}.mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-b:a", "192k", mp3], check=True)
    tts.STYLES.clear()
    tts.STYLES.update(saved)
    res = {"name": name, "engine": engine, "seconds": round(total, 1), "speech_sec": round(speech, 1),
           "synth_sec": round(synth_sec, 1), "realtime_factor": round(synth_sec / max(speech, 0.1), 2), "file": mp3}
    log.info("AUDITION %s", res)
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    variants = [
        ("A_kokoro_current", dict(engine="kokoro")),
        ("B_kokoro_bright_pitch", dict(engine="kokoro", pitch=1.12, kokoro_styles={
            "excited": {"speed": 1.02, "gain": 1.0, "gap": 0.22}, "calm": {"speed": 0.9, "gain": 0.9, "gap": 0.35}})),
        ("C_chatterbox_exag070", dict(engine="chatterbox", exag=0.70)),
        ("D_chatterbox_exag100", dict(engine="chatterbox", exag=1.00)),
        ("E_chatterbox_exag130", dict(engine="chatterbox", exag=1.30)),
    ]
    only = os.getenv("AUDITION_ONLY")
    results = []
    for name, kw in variants:
        if only and not name.startswith(tuple(only.split(","))):
            continue
        try:
            results.append(render(name, **kw))
        except Exception as e:  # one broken engine must not hide the others
            log.exception("variant %s failed", name)
            results.append({"name": name, "error": str(e)[:400]})
    with open(os.path.join(OUT, "audition.json"), "w") as fh:
        json.dump(results, fh, indent=2)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
