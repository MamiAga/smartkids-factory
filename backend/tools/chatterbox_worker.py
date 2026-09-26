#!/usr/bin/env python3
"""Chatterbox TTS worker (runs in its own venv: chatterbox needs numpy<2, Kokoro needs numpy>=2).

Protocol: one JSON request per stdin line {"text": "[excited] Wow! ...", "out": "/path.wav"}
          -> one JSON reply per stdout line {"ok": true, "dur": 3.21}  (model is loaded once)
Emotion tags map to Chatterbox's exaggeration (emotion intensity) control.
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
import torch

torch.set_num_threads(os.cpu_count() or 4)
from chatterbox.tts import ChatterboxTTS  # noqa: E402

EXCITED = float(os.getenv("CB_EXAG_EXCITED", "0.95"))
STYLES = {
    "excited": {"exaggeration": EXCITED, "cfg": 0.3, "gain": 1.0, "gap": 0.25},
    "calm": {"exaggeration": 0.55, "cfg": 0.45, "gain": 0.9, "gap": 0.40},
    "whisper": {"exaggeration": 0.35, "cfg": 0.5, "gain": 0.45, "gap": 0.45},
}
model = ChatterboxTTS.from_pretrained(device="cpu")
sys.stdout.write(json.dumps({"ready": True, "sr": model.sr}) + "\n")
sys.stdout.flush()

for line in sys.stdin:
    try:
        req = json.loads(line)
        chunks, sr = [], model.sr
        for tag, body in re.findall(r"(?:\[([a-z]+)\]\s*)?([^\[]+)", req["text"].strip()):
            body = body.strip()
            if not body:
                continue
            st = STYLES.get(tag or "calm", STYLES["calm"])
            with torch.inference_mode():
                wav = model.generate(body, exaggeration=st["exaggeration"], cfg_weight=st["cfg"], temperature=0.8)
            a = wav.squeeze(0).numpy()
            idx = np.where(np.abs(a) > 0.01)[0]
            if len(idx):
                a = a[max(0, idx[0] - int(0.03 * sr)): idx[-1] + int(0.1 * sr)]
            chunks += [a * st["gain"], np.zeros(int(st["gap"] * sr), dtype=a.dtype)]
        samples = np.concatenate(chunks[:-1])
        sf.write(req["out"], samples.astype(np.float32), sr)
        sys.stdout.write(json.dumps({"ok": True, "dur": len(samples) / sr}) + "\n")
    except Exception as e:  # report, keep serving
        sys.stdout.write(json.dumps({"ok": False, "error": str(e)[:300]}) + "\n")
    sys.stdout.flush()
