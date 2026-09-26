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
SPEED = 0.80          # default storyteller pace
SENTENCE_GAP = {"!": 0.40, "?": 0.55, ".": 0.45, ":": 0.35}  # breathing pauses between sentences
# Acting rule: emotion tags in the script -> delivery. Kokoro has no SSML, so emotion is carried by the
# interjection words ("Wow!", "Yay!"), punctuation, tempo and level; whispers are slower and much softer.
STYLES = {
    "excited": {"speed": 0.93, "gain": 1.0, "gap": 0.30},
    "calm": {"speed": 0.82, "gain": 0.85, "gap": 0.45},
    "whisper": {"speed": 0.78, "gain": 0.40, "gap": 0.50},
}
SR = 24000

# Engine selection. "chatterbox" = Resemble AI Chatterbox (MIT) with an emotion-exaggeration control,
# much more theatrical than Kokoro but heavier (PyTorch). Chosen per run via SMARTKIDS_TTS_ENGINE.
ENGINE = os.getenv("SMARTKIDS_TTS_ENGINE", "kokoro")
_cb = None  # persistent worker process (separate venv, see backend/tools/chatterbox_worker.py)


def voice_id() -> str:
    return "chatterbox_default" if ENGINE == "chatterbox" else "af_heart"


def _cb_worker():
    global _cb
    if _cb is None or _cb.poll() is not None:
        import json
        import subprocess
        py = os.getenv("CHATTERBOX_PY", "python3")
        worker = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "chatterbox_worker.py")
        _cb = subprocess.Popen([py, worker], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        while True:  # skip library chatter until the worker says it is ready
            line = _cb.stdout.readline()
            if not line:
                raise RuntimeError("chatterbox worker died during start-up")
            if line.startswith("{") and json.loads(line).get("ready"):
                break
    return _cb


def _synth_chatterbox(text: str, out_wav: str) -> float:
    import json
    w = _cb_worker()
    w.stdin.write(json.dumps({"text": text, "out": os.path.abspath(out_wav)}) + "\n")
    w.stdin.flush()
    while True:
        line = w.stdout.readline()
        if not line:
            raise RuntimeError("chatterbox worker died")
        if line.startswith("{"):
            r = json.loads(line)
            if not r.get("ok"):
                raise RuntimeError(f"chatterbox: {r.get('error')}")
            return float(r["dur"])


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
    if ENGINE == "chatterbox":
        return _synth_chatterbox(text, out_wav)
    import re
    chunks = []
    sr = SR
    # "[excited] Wow! It's red! [whisper] So pretty..." -> [("excited", "Wow! It's red!"), ("whisper", "So pretty...")]
    tagged = re.findall(r"(?:\[([a-z]+)\]\s*)?([^\[]+)", text.strip())
    for tag, body in tagged:
        style = STYLES.get(tag or "calm", STYLES["calm"])
        for part in [p for p in re.split(r"(?<=[.!?:])\s+", body.strip()) if p]:
            audio, sr = _load().create(part, voice=cfg["voice"], speed=speed or style["speed"], lang=cfg["lang"])
            a = np.abs(audio)
            idx = np.where(a > 0.01)[0]
            if len(idx):
                audio = audio[max(0, idx[0] - int(0.04 * sr)): idx[-1] + int(0.12 * sr)]
            chunks.append(audio * style["gain"])
            gap = style["gap"] + (0.15 if part[-1] == "?" else 0.0)
            chunks.append(np.zeros(int(gap * sr), dtype=audio.dtype))
    samples = np.concatenate(chunks[:-1]) if len(chunks) > 1 else chunks[0]
    sf.write(out_wav, samples.astype(np.float32), sr)
    return len(samples) / sr
