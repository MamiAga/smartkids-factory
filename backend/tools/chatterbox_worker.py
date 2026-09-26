#!/usr/bin/env python3
"""Chatterbox TTS worker with a distortion guard (runs in its own venv: needs numpy<2).

Protocol: stdin JSON lines {"text": "[excited] Wow! ...", "out": "/path.wav"}
          stdout JSON lines {"ok": true, "dur": 3.2, "attempts": [...]}   (models load once)

Env:
  CB_REF_WAV        reference voice (e.g. a Kokoro female/male sample) -> narrator timbre
  CB_EXAG_EXCITED   emotion intensity for [excited] lines (default 1.1)

Distortion guard (why: at high emotion Chatterbox sometimes produces garbled / growling audio):
  every sentence is generated up to 4 times; each take is transcribed with Whisper (faster-whisper,
  MIT) and must match the script (word error rate <= 0.25) and have a human speaking rate.
  Takes 3-4 use a lower emotion level as a safer fallback. If no take passes -> error -> the job
  fails its quality gate and nothing is published.
Pace: accepted takes faster than the target words/sec are slowed with Rubber Band (pitch kept).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
import torch

torch.set_num_threads(os.cpu_count() or 4)
from chatterbox.tts import ChatterboxTTS  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

EXCITED = float(os.getenv("CB_EXAG_EXCITED", "1.1"))
STYLES = {  # target_wps = words per second after pacing (2.2 wps ~ 132 wpm)
    "excited": {"exaggeration": EXCITED, "cfg": 0.5, "gain": 1.0, "gap": 0.30, "target_wps": 2.3},
    "calm": {"exaggeration": 0.6, "cfg": 0.5, "gain": 0.9, "gap": 0.40, "target_wps": 2.1},
    "whisper": {"exaggeration": 0.4, "cfg": 0.5, "gain": 0.45, "gap": 0.45, "target_wps": 1.9},
}
MAX_WER = 0.25
NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
       "7": "seven", "8": "eight", "9": "nine", "10": "ten"}

model = ChatterboxTTS.from_pretrained(device="cpu")
ref = os.getenv("CB_REF_WAV")
if ref:
    model.prepare_conditionals(ref, exaggeration=EXCITED)
asr = WhisperModel("base.en", device="cpu", compute_type="int8")
sys.stdout.write(json.dumps({"ready": True, "sr": model.sr, "ref": ref}) + "\n")
sys.stdout.flush()


def words(s: str):
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower().replace("-", " ").replace("'", ""))
    return [NUM.get(w, w) for w in s.split()]


def wer(ref_text: str, hyp: str) -> float:
    r, h = words(ref_text), words(hyp)
    if not r:
        return 0.0
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return d[len(h)] / len(r)


def trim(a, sr):
    idx = np.where(np.abs(a) > 0.01)[0]
    return a[max(0, idx[0] - int(0.03 * sr)): idx[-1] + int(0.1 * sr)] if len(idx) else a


def transcribe(a, sr) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        sf.write(f.name, a, sr)
        segs, _ = asr.transcribe(f.name, language="en", beam_size=1, vad_filter=False)
        return " ".join(s.text for s in segs)


def pace(a, sr, n_words, target_wps):
    dur = len(a) / sr
    wps = n_words / max(dur, 0.1)
    if n_words < 3 or wps <= target_wps * 1.03:
        return a
    tempo = max(0.78, target_wps / wps)  # < 1 = slower, pitch preserved
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        sf.write(src, a, sr)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", f"rubberband=tempo={tempo:.3f}", dst],
                       check=True)
        b, _ = sf.read(dst, dtype="float32")
    return b


def take(body, st, exag, seed, sr):
    torch.manual_seed(seed)
    with torch.inference_mode():
        wav = model.generate(body, exaggeration=exag, cfg_weight=st["cfg"], temperature=0.7)
    a = trim(wav.squeeze(0).numpy(), sr)
    n = max(1, len(words(body)))
    spw = (len(a) / sr) / n
    heard = transcribe(a, sr)
    w = wer(body, heard) if n >= 3 else (0.0 if set(words(body)) & set(words(heard)) or not heard.strip() else 1.0)
    rate_ok = 0.2 <= spw <= (1.2 if n < 3 else 0.85)
    return a, {"exag": exag, "seed": seed, "wer": round(w, 2), "sec_per_word": round(spw, 2), "heard": heard.strip()[:80],
               "ok": w <= MAX_WER and rate_ok}


for line in sys.stdin:
    try:
        req = json.loads(line)
        sr = model.sr
        chunks, log = [], []
        for tag, body in re.findall(r"(?:\[([a-z]+)\]\s*)?([^\[]+)", req["text"].strip()):
            body = body.strip()
            if not body:
                continue
            st = STYLES.get(tag or "calm", STYLES["calm"])
            best = None
            for attempt in range(4):
                exag = st["exaggeration"] if attempt < 2 else max(0.5, st["exaggeration"] * 0.65)
                a, info = take(body, st, exag, 1000 + attempt * 17, sr)
                log.append(info)
                if info["ok"]:
                    best = a
                    break
            if best is None:
                raise RuntimeError(f"DISTORTION_GUARD: no clean take for {body!r}: {log[-1]}")
            best = pace(best, sr, len(words(body)), st["target_wps"])
            chunks += [best * st["gain"], np.zeros(int(st["gap"] * sr), dtype=np.float32)]
        samples = np.concatenate(chunks[:-1]).astype(np.float32)
        sf.write(req["out"], samples, sr)
        sys.stdout.write(json.dumps({"ok": True, "dur": len(samples) / sr, "attempts": log}) + "\n")
    except Exception as e:  # report, keep serving
        sys.stdout.write(json.dumps({"ok": False, "error": str(e)[:400]}) + "\n")
    sys.stdout.flush()
