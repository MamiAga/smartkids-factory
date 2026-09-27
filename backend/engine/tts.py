"""Narration voices (0 TL, local inference only) for all 10 languages.

Engine "chatterbox" (default, production): Resemble AI Chatterbox (MIT). EN = English model,
other languages = Chatterbox Multilingual. Runs in its own venv as a worker process
(backend/tools/chatterbox_worker.py) with the acoustic quality guard (backend/tools/voice_guard.py).
Narrator timbre comes from a reference clip WE generate with Kokoro-82M (Apache-2.0): no third-party
voice or likeness is involved.

Engine "kokoro" is kept only for quick previews / dry runs (EN, ES, FR, PT, IT, HI).

Hard rule since v3: one video = one voice. A line that has no clean Chatterbox take is NOT read by a
different engine (that produced the "voice turns robotic, then comes back" effect) - the job fails its
quality gate instead and nothing is published.
"""
import hashlib
import json
import os
import shutil
from typing import Dict, Optional

import numpy as np
import soundfile as sf

from backend.engine import languages

MODEL_DIR = os.getenv("KOKORO_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                  "models", "kokoro"))
CACHE_DIR = os.getenv("SMARTKIDS_TTS_CACHE", os.path.join(os.path.dirname(MODEL_DIR), "tts_cache"))
MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"
MODEL_URLS = {
    MODEL_FILE: "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    VOICES_FILE: "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
WORKER_VERSION = "cb3-guard"   # part of the cache key: changing the worker invalidates old narration

# Kokoro preview voices (not used for published videos)
KOKORO_PREVIEW = {"EN": ("af_heart", "en-us"), "ES": ("ef_dora", "es"), "FR": ("ff_siwis", "fr-fr"),
                  "PT": ("pf_dora", "pt-br"), "IT": ("if_sara", "it"), "HI": ("hf_alpha", "hi")}
STYLES = {
    "excited": {"speed": 0.93, "gain": 1.0, "gap": 0.30},
    "calm": {"speed": 0.82, "gain": 0.85, "gap": 0.45},
    "whisper": {"speed": 0.78, "gain": 0.40, "gap": 0.50},
}
SR = 24000
DIGITS = {
    "EN": ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"],
    "ES": ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"],
    "PT": ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"],
    "FR": ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix"],
    "DE": ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn"],
    "IT": ["zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove", "dieci"],
    "TR": ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "on"],
    "RU": ["ноль", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять"],
    "AR": ["صفر", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة"],
    "HI": ["शून्य", "एक", "दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ", "दस"],
}

ENGINE = os.getenv("SMARTKIDS_TTS_ENGINE") or "chatterbox"
NARRATORS = ("female", "male")
NARRATOR = os.getenv("SMARTKIDS_NARRATOR", "female")
_cb = None          # worker process
_cb_key = None      # (narrator, language) the worker was started for
FALLBACKS = []      # kept for the quality report; must stay empty (no engine mixing)
CB_LOG = []         # per-line take statistics, exported into the quality report


class VoiceQualityError(RuntimeError):
    pass


def voice_id(language: str = "EN") -> str:
    if ENGINE != "chatterbox":
        return f"kokoro_preview_{KOKORO_PREVIEW.get(language.upper(), ('?',))[0]}"
    rv = languages.reference_voice(language, NARRATOR)
    return f"chatterbox_{NARRATOR}_{(rv['kokoro_voice'] or 'default')}_{language.lower()}"


def set_narrator(name: str) -> None:
    global NARRATOR
    if name not in NARRATORS:
        raise ValueError(f"narrator must be one of {NARRATORS}")
    if name != NARRATOR:
        _stop_worker()
    NARRATOR = name


def _stop_worker():
    global _cb, _cb_key
    if _cb is not None:
        _cb.kill()
    _cb, _cb_key = None, None


# ------------------------------------------------------------------ Kokoro (reference clips / previews)
_kokoro = None


def _load():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro  # lazily: unit tests don't need onnxruntime
        m, v = os.path.join(MODEL_DIR, MODEL_FILE), os.path.join(MODEL_DIR, VOICES_FILE)
        if not (os.path.exists(m) and os.path.exists(v)):
            raise FileNotFoundError(f"Kokoro model missing in {MODEL_DIR} (run backend/tools/download_models.py --kokoro)")
        _kokoro = Kokoro(m, v)
    return _kokoro


def reference_wav(language: str, narrator: Optional[str] = None) -> Dict[str, str]:
    """Narrator reference clip for (language, narrator). Deterministic, so every parallel runner
    builds the identical clip and the voice is the same across the whole video."""
    from backend.engine.longform import load_texts
    narrator = narrator or NARRATOR
    rv = languages.reference_voice(language, narrator)
    if not rv["kokoro_voice"]:
        return {"path": "", "cfg_zero": "0"}
    path = os.path.join(MODEL_DIR, f"ref_{narrator}_{rv['kokoro_voice']}_{rv['lang']}.wav")
    if not os.path.exists(path):
        text = load_texts(rv["lang"])["ref_text"]
        samples, sr = _load().create(text, voice=rv["kokoro_voice"], speed=0.95, lang=rv["kokoro_lang"])
        sf.write(path, samples, sr)
    return {"path": path, "cfg_zero": "0" if rv["native"] else "1"}


# ------------------------------------------------------------------ Chatterbox worker
def _cb_worker(language: str):
    global _cb, _cb_key
    key = (NARRATOR, language)
    if _cb is not None and (_cb.poll() is not None or _cb_key != key):
        _stop_worker()
    if _cb is None:
        import subprocess
        L = languages.get(language)
        ref = reference_wav(language)
        digits = {str(i): w for i, w in enumerate(DIGITS.get(language, DIGITS["EN"]))}
        py = os.getenv("CHATTERBOX_PY", "python3")
        worker = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "chatterbox_worker.py")
        env = dict(os.environ, CB_REF_WAV=ref["path"], CB_CFG_ZERO=ref["cfg_zero"], CB_LANG=L["cb"],
                   CB_WHISPER=L["whisper"], CB_METRIC=L["metric"], CB_MAX_ERR=str(L["max_err"]),
                   CB_DIGITS=json.dumps(digits, ensure_ascii=False))
        _cb = subprocess.Popen([py, worker], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1, env=env)
        _cb_key = key
        while True:  # skip library chatter until the worker says it is ready
            line = _cb.stdout.readline()
            if not line:
                raise RuntimeError("chatterbox worker died during start-up")
            if line.startswith("{") and json.loads(line).get("ready"):
                break
    return _cb


def _synth_chatterbox(text: str, language: str, out_wav: str) -> float:
    w = _cb_worker(language)
    w.stdin.write(json.dumps({"text": text, "out": os.path.abspath(out_wav)}, ensure_ascii=False) + "\n")
    w.stdin.flush()
    while True:
        line = w.stdout.readline()
        if not line:
            raise RuntimeError("chatterbox worker died")
        if line.startswith("{"):
            r = json.loads(line)
            if not r.get("ok"):
                if "DISTORTION_GUARD" in r.get("error", ""):
                    raise VoiceQualityError(r["error"])
                raise RuntimeError(f"chatterbox: {r.get('error')}")
            CB_LOG.append({"text": text[:60], "attempts": r.get("attempts", [])})
            return float(r["dur"])


def cache_key(text: str, language: str) -> str:
    return hashlib.sha1(f"{WORKER_VERSION}|{ENGINE}|{voice_id(language)}|{language.upper()}|{text}".encode()).hexdigest()


def synth(text: str, language: str, out_wav: str, speed: Optional[float] = None) -> float:
    """Write narration WAV; return duration in seconds. Cross-run / cross-runner cache by content hash."""
    language = language.upper()
    if os.getenv("SMARTKIDS_TEST_TTS") == "1":  # dry-run test mode only (guarded in production_runner)
        dur = max(1.2, len(text.split()) / 2.2)
        samples = 0.05 * np.sin(2 * np.pi * 220 * np.arange(int(dur * SR)) / SR)
        sf.write(out_wav, samples.astype(np.float32), SR)
        return dur
    os.makedirs(CACHE_DIR, exist_ok=True)
    cached = os.path.join(CACHE_DIR, cache_key(text, language) + ".wav")
    if os.path.exists(cached):
        shutil.copy(cached, out_wav)
        return sf.info(out_wav).duration
    if ENGINE == "chatterbox":
        dur = _synth_chatterbox(text, language, out_wav)
    else:
        dur = _synth_kokoro(text, language, out_wav, speed)
    shutil.copy(out_wav, cached)
    return dur


def is_cached(text: str, language: str) -> bool:
    return os.path.exists(os.path.join(CACHE_DIR, cache_key(text, language.upper()) + ".wav"))


def _synth_kokoro(text: str, language: str, out_wav: str, speed: Optional[float] = None) -> float:
    import re
    if language not in KOKORO_PREVIEW:
        raise VoiceQualityError(f"no Kokoro preview voice for {language}")
    voice, lang = KOKORO_PREVIEW[language]
    chunks = []
    sr = SR
    for tag, body in re.findall(r"(?:\[([a-z]+)\]\s*)?([^\[]+)", text.strip()):
        style = STYLES.get(tag or "calm", STYLES["calm"])
        for part in [p for p in re.split(r"(?<=[.!?:])\s+", body.strip()) if p]:
            audio, sr = _load().create(part, voice=voice, speed=speed or style["speed"], lang=lang)
            a = np.abs(audio)
            idx = np.where(a > 0.01)[0]
            if len(idx):
                audio = audio[max(0, idx[0] - int(0.04 * sr)): idx[-1] + int(0.12 * sr)]
            chunks.append(audio * style["gain"])
            chunks.append(np.zeros(int((style["gap"] + (0.15 if part[-1] == "?" else 0.0)) * sr), dtype=audio.dtype))
    samples = np.concatenate(chunks[:-1]) if len(chunks) > 1 else chunks[0]
    sf.write(out_wav, samples.astype(np.float32), sr)
    return len(samples) / sr
