#!/usr/bin/env python3
"""Chatterbox narration worker with an acoustic + transcript quality guard (own venv: numpy<2).

Protocol: stdin JSON lines {"text": "[excited] Wow! ...", "out": "/path.wav"}
          stdout JSON lines {"ok": true, "dur": 3.2, "attempts": [...]}     (models load once)

Env:
  CB_LANG         language code (en, es, pt, fr, de, it, tr, ru, ar, hi). en = original English model,
                  others = Chatterbox Multilingual.
  CB_REF_WAV      narrator reference clip (timbre)
  CB_CFG_ZERO     "1" when the reference clip is in another language (stops accent transfer)
  CB_WHISPER      faster-whisper model (base.en for EN, small for the others)
  CB_METRIC       wer | cer        CB_MAX_ERR  e.g. 0.25
  CB_DIGITS       JSON {"3": "three", ...} so "3" in a transcript matches "three" in the script

What changed after the "robot voice" report (v3):
  * NO time-stretching any more (Rubber Band made some lines sound phasey/robotic). Pace comes from
    Chatterbox itself (lower cfg_weight = slower, calmer delivery) plus natural pauses between chunks.
  * NO mixing with another TTS engine inside a video. A line with no clean take fails the job instead
    of being read by a different, flatter voice.
  * Long lines are generated in short chunks (<= 14 words): short generations drift far less.
  * Every take passes voice_guard: timbre drift / dip, flat robotic pitch, transcript and rate.
"""
import json
import os
import re
import sys
import tempfile

import numpy as np
import soundfile as sf
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_guard as VG  # noqa: E402

torch.set_num_threads(os.cpu_count() or 4)
LANG = os.getenv("CB_LANG", "en").lower()
CFG_ZERO = os.getenv("CB_CFG_ZERO") == "1"
METRIC = os.getenv("CB_METRIC", "wer")
MAX_ERR = float(os.getenv("CB_MAX_ERR", "0.25"))
DIGITS = json.loads(os.getenv("CB_DIGITS") or "{}")
EXCITED = float(os.getenv("CB_EXAG_EXCITED", "1.0"))
MAX_CHUNK_WORDS = 14
ATTEMPTS = 6

# pace without stretching: cfg 0.3 = slower, deliberate storyteller delivery (Chatterbox guidance)
STYLES = {
    "excited": {"exaggeration": EXCITED, "cfg": 0.3, "gain": 1.0, "gap": 0.28},
    "calm": {"exaggeration": 0.55, "cfg": 0.4, "gain": 0.9, "gap": 0.38},
    "whisper": {"exaggeration": 0.4, "cfg": 0.4, "gain": 0.5, "gap": 0.42},
}
CHUNK_GAP = 0.16

if LANG == "en":
    from chatterbox.tts import ChatterboxTTS  # noqa: E402
    model = ChatterboxTTS.from_pretrained(device="cpu")
else:
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # noqa: E402
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
ref = os.getenv("CB_REF_WAV")
if ref:
    model.prepare_conditionals(ref, exaggeration=EXCITED)
spk = model.conds.t3.speaker_emb.detach().cpu().numpy().reshape(-1)
REF_EMB = spk / (np.linalg.norm(spk) or 1.0)

from faster_whisper import WhisperModel  # noqa: E402
asr = WhisperModel(os.getenv("CB_WHISPER", "base.en" if LANG == "en" else "small"), device="cpu", compute_type="int8")
sys.stdout.write(json.dumps({"ready": True, "sr": model.sr, "ref": ref, "lang": LANG, "cfg_zero": CFG_ZERO}) + "\n")
sys.stdout.flush()


def trim(a, sr):
    idx = np.where(np.abs(a) > 0.01)[0]
    return a[max(0, idx[0] - int(0.03 * sr)): idx[-1] + int(0.1 * sr)] if len(idx) else a


def transcribe(a, sr) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        sf.write(f.name, a, sr)
        segs, _ = asr.transcribe(f.name, language=LANG, beam_size=1, vad_filter=False)
        return " ".join(s.text for s in segs)


def chunks(body: str):
    sents = [s for s in re.split(r"(?<=[.!?…؟।])\s+", body.strip()) if s]
    out, cur = [], []
    for s in sents:
        if cur and len(" ".join(cur + [s]).split()) > MAX_CHUNK_WORDS:
            out.append(" ".join(cur))
            cur = []
        cur.append(s)
    if cur:
        out.append(" ".join(cur))
    return out


def generate(text, exag, cfg, seed):
    torch.manual_seed(seed)
    with torch.inference_mode():
        if LANG == "en":
            wav = model.generate(text, exaggeration=exag, cfg_weight=cfg, temperature=0.7)
        else:
            wav = model.generate(text, language_id=LANG, exaggeration=exag, cfg_weight=cfg, temperature=0.7)
    return trim(wav.squeeze(0).numpy(), model.sr)


def measure(a, sr, text):
    n = max(1, len(VG.norm_words(text, DIGITS)))
    dur = len(a) / sr
    heard = transcribe(a, sr)
    if n >= 3:
        err = VG.text_error(text, heard, METRIC, DIGITS)
    else:  # 1-2 word exclamations: must hear at least one of the words (or nothing odd)
        err = 0.0 if (set(VG.norm_words(text, DIGITS)) & set(VG.norm_words(heard, DIGITS)) or not heard.strip()) else 1.0
    a16 = VG.to16k(a, sr)
    m = {"err": round(err, 2), "sec_per_word": round(dur / n, 2), "heard": heard.strip()[:80], "dur": round(dur, 2)}
    short = dur < 1.0
    if not short:
        m.update(VG.speaker_drift(model.ve, a16, REF_EMB))
        m.update(VG.flat_pitch(a16))
    m["why"] = VG.judge({**{"sim_min": 1, "sim_drop": 0, "flat_sec": 0}, **m}, n, MAX_ERR, short)
    m["ok"] = not m["why"]
    return m


def best_take(text, st, log):
    tried = []
    for attempt in range(ATTEMPTS):
        calmer = attempt >= 3  # later attempts: less exaggeration = more stable voice
        exag = st["exaggeration"] if not calmer else max(0.45, st["exaggeration"] * 0.7)
        cfg = 0.0 if CFG_ZERO else (st["cfg"] if not calmer else min(0.5, st["cfg"] + 0.1))
        a = generate(text, exag, cfg, 1000 + attempt * 17)
        m = measure(a, model.sr, text)
        m.update({"exag": round(exag, 2), "cfg": cfg, "attempt": attempt, "chunk": text[:50]})
        log.append(m)
        if m["ok"]:
            return a
        tried.append((m, a))
    # nothing fully clean: accept only a take whose ONLY problem is the pace (voice + words are right)
    for m, a in sorted(tried, key=lambda t: t[0]["err"]):
        if all(w.startswith("rate") for w in m["why"]):
            m["accepted_despite"] = m["why"]
            return a
    raise RuntimeError(f"DISTORTION_GUARD: no clean take for {text!r}: {log[-1]}")


for line in sys.stdin:
    try:
        req = json.loads(line)
        sr = model.sr
        pieces, log = [], []
        for tag, body in re.findall(r"(?:\[([a-z]+)\]\s*)?([^\[]+)", req["text"].strip()):
            body = body.strip()
            if not body:
                continue
            st = STYLES.get(tag or "calm", STYLES["calm"])
            parts = chunks(body)
            for i, c in enumerate(parts):
                a = best_take(c, st, log)
                gap = CHUNK_GAP if i < len(parts) - 1 else st["gap"]
                pieces += [a * st["gain"], np.zeros(int(gap * sr), dtype=np.float32)]
        samples = np.concatenate(pieces[:-1]).astype(np.float32)
        sf.write(req["out"], samples, sr)
        sys.stdout.write(json.dumps({"ok": True, "dur": len(samples) / sr, "attempts": log}, ensure_ascii=False) + "\n")
    except Exception as e:  # report, keep serving
        sys.stdout.write(json.dumps({"ok": False, "error": str(e)[:600]}, ensure_ascii=False) + "\n")
    sys.stdout.flush()
