"""Acoustic + transcript checks for one generated narration take (runs inside the Chatterbox venv).

Why: a transcript check alone (speech -> text -> compare) cannot hear HOW a line sounds. A take can say
every word correctly and still turn metallic/robotic for a second, or drift into a different timbre.
So every take is also measured acoustically:

  1. speaker drift   - the Chatterbox voice encoder embeds overlapping 1.6 s windows of the take and
                       compares each window with the narrator reference voice. A window that suddenly
                       sounds like someone/something else (robotic, buzzy, other speaker) scores low.
                         sim_min   : lowest window similarity to the reference
                         sim_drop  : median window similarity - lowest window similarity (a dip inside
                                     one take = "talks normally, turns robotic, comes back")
  2. monotone buzz   - pYIN pitch track; a vocoder glitch often produces a flat, machine-like pitch.
                         flat_sec  : longest voiced stretch whose pitch varies < FLAT_SEMITONES
  3. transcript      - Whisper transcript vs script: WER (EN) or CER (other languages)
  4. speaking rate   - seconds per word inside a human range (catches long garbled tails)

Thresholds are environment-configurable and were calibrated with backend/tools/voice_lab.py.
"""
import os
import re
import unicodedata
from typing import Dict, List, Optional

import numpy as np

SIM_MIN = float(os.getenv("VG_SIM_MIN", "0.62"))
SIM_DROP = float(os.getenv("VG_SIM_DROP", "0.16"))
FLAT_SEMITONES = float(os.getenv("VG_FLAT_ST", "0.35"))
FLAT_MAX_SEC = float(os.getenv("VG_FLAT_MAX_SEC", "0.7"))
WIN = 1.6          # voice-encoder partial length (160 frames @ 10 ms)
HOP = 0.4


# ------------------------------------------------------------------ text
def norm_words(s: str, digits: Optional[Dict[str, str]] = None) -> List[str]:
    s = unicodedata.normalize("NFKC", s).lower().replace("-", " ").replace("'", "").replace("’", "")
    s = "".join(ch if (ch.isalnum() or ch.isspace() or unicodedata.category(ch).startswith("M")) else " " for ch in s)
    out = []
    for w in s.split():
        out.append((digits or {}).get(w, w))
    return out


def _edit(a: List[str], b: List[str]) -> int:
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev = cur
    return d[len(b)]


def text_error(ref: str, hyp: str, metric: str = "wer", digits=None) -> float:
    r, h = norm_words(ref, digits), norm_words(hyp, digits)
    if metric == "cer":
        r, h = list("".join(r)), list("".join(h))
    if not r:
        return 0.0
    return _edit(r, h) / len(r)


# ------------------------------------------------------------------ audio
def to16k(a: np.ndarray, sr: int) -> np.ndarray:
    import librosa
    return librosa.resample(a.astype(np.float32), orig_sr=sr, target_sr=16000) if sr != 16000 else a.astype(np.float32)


def speaker_drift(ve, a16: np.ndarray, ref_emb: np.ndarray) -> Dict[str, float]:
    """Window-level similarity to the reference speaker embedding (L2-normalised)."""
    n, w, h = len(a16), int(WIN * 16000), int(HOP * 16000)
    peak = float(np.max(np.abs(a16)) or 1.0)
    wins = []
    if n <= w:
        wins = [a16]
    else:
        for s in range(0, n - w + 1, h):
            seg = a16[s:s + w]
            if np.sqrt(np.mean(seg ** 2)) > 0.06 * peak:   # skip mostly-silent windows
                wins.append(seg)
        if not wins:
            wins = [a16]
    emb = ve.embeds_from_wavs(wins, sample_rate=16000, trim_top_db=None)
    sims = emb @ ref_emb
    med = float(np.median(sims))
    return {"sim_min": round(float(np.min(sims)), 3), "sim_med": round(med, 3),
            "sim_drop": round(med - float(np.min(sims)), 3), "windows": len(wins)}


def flat_pitch(a16: np.ndarray) -> Dict[str, float]:
    """Longest voiced stretch with an unnaturally flat pitch (seconds)."""
    import librosa
    f0, voiced, _ = librosa.pyin(a16, fmin=70, fmax=750, sr=16000, frame_length=1024, hop_length=160)
    st = 12 * np.log2(np.where(voiced & np.isfinite(f0), f0, np.nan) / 100.0)
    win = int(0.3 / 0.01)
    flat = np.zeros(len(st), dtype=bool)
    for i in range(0, max(0, len(st) - win + 1)):
        seg = st[i:i + win]
        if not np.isnan(seg).any() and float(np.std(seg)) < FLAT_SEMITONES:
            flat[i:i + win] = True
    longest = run = 0
    for f in flat:
        run = run + 1 if f else 0
        longest = max(longest, run)
    return {"flat_sec": round(longest * 0.01, 2),
            "pitch_range_st": round(float(np.nanmax(st) - np.nanmin(st)), 1) if np.any(~np.isnan(st)) else 0.0}


def judge(m: Dict[str, float], n_words: int, max_err: float, short: bool) -> List[str]:
    """Reasons a take is rejected (empty list = clean)."""
    why = []
    if m["err"] > max_err:
        why.append(f"text {m['err']:.2f}>{max_err}")
    hi = 1.6 if n_words < 6 else 1.15
    if not (0.16 <= m["sec_per_word"] <= hi):
        why.append(f"rate {m['sec_per_word']}")
    if not short:  # < ~1 s of speech: embeddings/pitch are not meaningful
        if m["sim_min"] < SIM_MIN:
            why.append(f"timbre {m['sim_min']}<{SIM_MIN}")
        if m["sim_drop"] > SIM_DROP:
            why.append(f"timbre-dip {m['sim_drop']}>{SIM_DROP}")
        if m["flat_sec"] > FLAT_MAX_SEC:
            why.append(f"robotic-flat {m['flat_sec']}s")
    return why
