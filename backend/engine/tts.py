"""Narration voices (0 TL, local inference only).

Primary: Kokoro-82M (Apache-2.0) via kokoro-onnx — natural, warm female storyteller voice.
There is deliberately NO silent fallback to a flat/robotic voice: if the approved voice
cannot be loaded, the job fails instead of publishing a lower-quality video.
"""
import os
from typing import Dict, Optional

import numpy as np
import soundfile as sf

MODEL_DIR = os.getenv("KOKORO_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                  "models", "kokoro"))
MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"
MODEL_URLS = {
    MODEL_FILE: "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    VOICES_FILE: "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}

# Approved narrator per language (SKQS-2: female, warm, storytelling). Kokoro has no DE/TR voice.
VOICES: Dict[str, Dict[str, str]] = {
    "EN": {"voice": "af_heart", "lang": "en-us", "license": "Apache-2.0 (Kokoro-82M)"},
    "ES": {"voice": "ef_dora", "lang": "es", "license": "Apache-2.0 (Kokoro-82M)"},
    "FR": {"voice": "ff_siwis", "lang": "fr-fr", "license": "Apache-2.0 (Kokoro-82M)"},
    "PT": {"voice": "pf_dora", "lang": "pt-br", "license": "Apache-2.0 (Kokoro-82M)"},
}
SPEED = 0.80          # calm storyteller pace
SENTENCE_GAP = {"!": 0.50, "?": 0.60, ".": 0.45, ":": 0.35}  # breathing pauses between sentences
SR = 24000

_engine = None


def _load():
    global _engine
    if _engine is None:
        from kokoro_onnx import Kokoro  # imported lazily so unit tests don't need onnxruntime
        m, v = os.path.join(MODEL_DIR, MODEL_FILE), os.path.join(MODEL_DIR, VOICES_FILE)
        if not (os.path.exists(m) and os.path.exists(v)):
            raise FileNotFoundError(f"Kokoro model missing in {MODEL_DIR} (run backend/tools/download_models.py --kokoro)")
        _engine = Kokoro(m, v)
    return _engine


def synth(text: str, language: str, out_wav: str, speed: Optional[float] = None) -> float:
    """Write narration WAV; return duration in seconds."""
    cfg = VOICES[language]
    if os.getenv("SMARTKIDS_TEST_TTS") == "1":  # dry-run test mode only (guarded in production_runner)
        dur = max(1.2, len(text.split()) / 2.2)
        samples = 0.05 * np.sin(2 * np.pi * 220 * np.arange(int(dur * SR)) / SR)
        sf.write(out_wav, samples.astype(np.float32), SR)
        return dur
    import re
    parts = [p for p in re.split(r"(?<=[.!?:])\s+", text.strip()) if p]
    chunks = []
    sr = SR
    for part in parts:
        audio, sr = _load().create(part, voice=cfg["voice"], speed=speed or SPEED, lang=cfg["lang"])
        a = np.abs(audio)
        idx = np.where(a > 0.01)[0]
        if len(idx):
            audio = audio[max(0, idx[0] - int(0.04 * sr)): idx[-1] + int(0.12 * sr)]
        chunks.append(audio)
        gap = SENTENCE_GAP.get(part[-1], 0.35)
        chunks.append(np.zeros(int(gap * sr), dtype=audio.dtype))
    samples = np.concatenate(chunks[:-1]) if len(chunks) > 1 else chunks[0]
    sf.write(out_wav, samples, sr)
    return len(samples) / sr
