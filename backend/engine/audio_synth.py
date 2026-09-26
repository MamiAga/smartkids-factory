"""Procedural, license-free audio (0 TL): cheerful music bed + sound effects.

Everything is synthesised from sine/noise with numpy, so there is no third-party music
license to track. Deterministic per seed (same episode -> same music).

Music: 112 BPM, C major, I-V-vi-IV progression, marimba-like lead on a pentatonic melody,
soft bass, light shaker and claps. Sections vary every 8 bars so a 10-minute bed does not
sound like a 4-second loop.
"""
import numpy as np
import soundfile as sf

SR = 48000


def _env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / decay)


def _tone(freq: float, dur: float, decay: float, harmonics=((1, 1.0),), attack=0.004) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = sum(amp * np.sin(2 * np.pi * freq * h * t) for h, amp in harmonics)
    return sig * _env(n, attack, decay)


def _marimba(freq, dur):
    return _tone(freq, dur, 0.28, ((1, 1.0), (4.0, 0.25), (9.2, 0.06)))


def _bass(freq, dur):
    return _tone(freq, dur, 0.45, ((1, 1.0), (2, 0.35)), attack=0.01)


def _pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.001 * t) for f in freqs)
    env = np.minimum(1, t / 0.3) * np.minimum(1, (dur - t) / 0.3)
    return sig * env / len(freqs)


def _noise_hit(dur, decay, rng, hp=True):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    if hp:
        x = np.diff(x, prepend=0)  # crude high-pass -> shaker/clap
    return x * _env(n, 0.001, decay)


def midi(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


CHORDS = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]  # C  G  Am  F
PENTA = [60, 62, 64, 67, 69, 72, 74, 76]


def music_bed(seconds: float, seed: int = 7, bpm: float = 112.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bar = 4 * beat
    total = int((seconds + 2) * SR)
    L = np.zeros(total)
    R = np.zeros(total)

    def add(sig, t0, gain, pan=0.0):
        i = int(t0 * SR)
        if i >= total:
            return
        s = sig[: total - i] * gain
        L[i:i + len(s)] += s * (1 - pan) / 2 * 2
        R[i:i + len(s)] += s * (1 + pan) / 2 * 2

    # a few melodic motifs (2 bars each, 8th notes) reused with variation -> catchy but not static
    motifs = []
    for _ in range(4):
        steps = rng.choice(len(PENTA), size=16)
        rests = rng.random(16) < 0.25
        motifs.append([(None if r else PENTA[s]) for s, r in zip(steps, rests)])

    n_bars = int(seconds / bar) + 2
    for b in range(n_bars):
        t_bar = b * bar
        section = (b // 8) % 4           # changes every 8 bars
        chord = CHORDS[b % 4]
        # pad + bass
        add(_pad([midi(m) for m in chord], bar), t_bar, 0.10)
        for k in range(4):
            root = chord[0] - 12 if k % 2 == 0 else chord[2] - 12
            add(_bass(midi(root), beat), t_bar + k * beat, 0.30)
        # percussion: shaker on 8ths, clap on 2 & 4 (from section 1 on)
        for k in range(8):
            add(_noise_hit(0.08, 0.025, rng), t_bar + k * beat / 2, 0.035 if k % 2 else 0.05, pan=0.4)
        if section >= 1:
            for k in (1, 3):
                add(_noise_hit(0.15, 0.05, rng), t_bar + k * beat, 0.08, pan=-0.2)
        # melody (sections 0,2 full; 1 sparse; 3 octave up)
        motif = motifs[(b // 2 + section) % len(motifs)]
        half = (b % 2) * 8
        for k in range(8):
            note = motif[half + k]
            if note is None or (section == 1 and k % 2):
                continue
            # keep melody consonant with the chord on strong beats
            if k % 2 == 0 and (note % 12) not in [c % 12 for c in chord]:
                note = min(chord, key=lambda c: abs(c + 12 - note)) + 12
            if section == 3:
                note += 12
            add(_marimba(midi(note), beat), t_bar + k * beat / 2, 0.20, pan=-0.3 + 0.6 * rng.random())

    st = np.stack([L, R], axis=1)[: int(seconds * SR)]
    fade = int(1.5 * SR)
    st[:fade] *= np.linspace(0, 1, fade)[:, None]
    st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return st / (np.max(np.abs(st)) + 1e-9) * 0.5


def sfx(kind: str) -> np.ndarray:
    rng = np.random.default_rng(1)
    if kind == "tick":        # countdown tick
        s = _tone(1760, 0.12, 0.03) * 0.6 + _noise_hit(0.12, 0.01, rng) * 0.2
    elif kind == "go":        # last count
        s = _tone(1318.5, 0.35, 0.12) + 0.6 * _tone(1760, 0.35, 0.12)
    elif kind == "chime":     # scene change
        s = _tone(880, 0.6, 0.22) + 0.6 * _tone(1318.5, 0.6, 0.22)
    elif kind == "tada":      # correct answer: C-E-G-C arpeggio
        s = np.zeros(int(0.9 * SR))
        for i, m in enumerate([72, 76, 79, 84]):
            n = _marimba(midi(m), 0.9 - i * 0.08)
            j = int(i * 0.08 * SR)
            s[j:j + len(n)] += n[: len(s) - j]
    elif kind == "pop":
        s = _tone(660, 0.15, 0.04, ((1, 1.0), (2, 0.3)))
    else:
        raise ValueError(kind)
    s = s / (np.max(np.abs(s)) + 1e-9) * 0.5
    return np.stack([s, s], axis=1)


def write(path: str, data: np.ndarray) -> str:
    sf.write(path, data.astype(np.float32), SR, subtype="PCM_16")
    return path
