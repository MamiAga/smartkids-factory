"""Long-form (SKQS-2) audio + video assembly. Used by ProductionEngine for PACKS episodes."""
import logging
import os
import subprocess
from typing import Any, Dict, List

import numpy as np
import soundfile as sf

from backend.engine import audio_synth, tts, visuals
from backend.engine.longform import bonus_round

logger = logging.getLogger("smartkids.longform")
SR = 48000
MIN_TARGET = 525.0   # aim a little above the 495 s hard floor
MAX_TARGET = 615.0
HOLD = {"title": 6.0, "mystery": 3.0, "reveal": 4.0, "repeat": 3.5, "example": 4.2, "quiz": 3.5, "answer": 3.8,
        "review": 2.8, "review_answer": 3.0, "chant_intro": 3.0, "chant": 1.9, "dance": 14.0, "outro": 9.0}
VOICE_LEAD_IN = 0.25


def _run(cmd: List[str]):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {p.stderr.decode('utf-8', 'replace')[-600:]}")
    return p


def _load48(path: str) -> np.ndarray:
    out = path.replace(".wav", "_48k.wav")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ar", str(SR), "-ac", "2", out])
    data, _ = sf.read(out, dtype="float32", always_2d=True)
    return data


_PART_CACHE: Dict[str, str] = {}


def _strip_tags(text: str) -> str:
    import re
    return re.sub(r"\[[a-z]+\]\s*", "", text)


def narrate(segs: List[Dict[str, Any]], language: str, scratch: str, job_id: str, start: int = 0) -> None:
    for s in segs:  # spoken "Three! Two! One!" clips, synthesised once and reused
        for _, txt in s.get("voice_parts", []):
            if txt not in _PART_CACHE:
                wav = os.path.join(scratch, f"{job_id}_part_{abs(hash(txt)) % 10**6}.wav")
                tts.synth(txt, language, wav)
                _PART_CACHE[txt] = wav
    for i, s in enumerate(segs[start:], start=start):
        if s.get("voice_path") or not s["text"]:
            continue
        wav = os.path.join(scratch, f"{job_id}_n{i:03d}_{abs(hash(s['text'])) % 10**6}.wav")
        s["speech_sec"] = tts.synth(s["text"], language, wav)
        s["voice_path"] = wav
        s["words"] = len(_strip_tags(s["text"]).split())


def _durations(segs: List[Dict[str, Any]]) -> float:
    total = 0.0
    for s in segs:
        if s["fixed"]:
            s["dur"] = s["fixed"]
        else:
            need = VOICE_LEAD_IN + s.get("speech_sec", 0.0) + 0.55 + (s.get("pad") or 0)
            s["dur"] = round(max(HOLD.get(s["kind"], 3.0), need), 3)
        s["t0"] = total
        total += s["dur"]
    return total


def plan_audio(pack, segs, language, scratch, job_id, seed) -> float:
    """TTS everything, fix durations, add bonus rounds until the minimum length is reached."""
    for s in segs:  # move 'pad' from visual kwargs into the segment
        s["pad"] = s["visual"].pop("pad", 0) if "pad" in s["visual"] else s.get("pad", 0)
    narrate(segs, language, scratch, job_id)
    total = _durations(segs)
    extra = 0
    while total < MIN_TARGET and extra < 3:
        extra += 1
        at = next(i for i, s in enumerate(segs) if s["kind"] == "chant_intro")
        bonus = bonus_round(pack, seed + extra)
        segs[at:at] = bonus
        narrate(segs, language, scratch, job_id)
        total = _durations(segs)
        logger.info("[Long-form] added bonus round %d -> %.1fs", extra, total)
    n_items = len(pack["items"])
    while total > MAX_TARGET:
        chants = [i for i, x in enumerate(segs) if x["kind"] == "chant"]
        reviews = [i for i, x in enumerate(segs) if x["kind"] == "review"]
        examples = [i for i, x in enumerate(segs) if x["kind"] == "example"]
        if len(chants) > n_items:                       # 1) sing the list once instead of twice
            del segs[chants[-1]]
            why = "second chant pass"
        elif len(reviews) > 4:                          # 2) shorter review round (keep >= 4 questions)
            del segs[reviews[-1]:reviews[-1] + 3]
            why = "review question"
        elif len(examples) > 2 * n_items:               # 3) 2 examples per item instead of 3
            per = {}
            for i in examples:
                per.setdefault(segs[i]["visual"]["item"], []).append(i)
            victim = max((v for v in per.values() if len(v) > 2), key=lambda v: v[-1])[-1]
            del segs[victim]
            why = "third example"
        else:
            break
        total = _durations(segs)
        logger.info("[Long-form] trimmed %s -> %.1fs", why, total)
    logger.info("[Long-form] %d segments, %.1f s (%.2f min)", len(segs), total, total / 60)
    return total


def mix_audio(segs, total: float, scratch: str, out_wav: str, seed: int) -> Dict[str, Any]:
    n = int((total + 0.5) * SR)
    voice = np.zeros((n, 2), dtype=np.float32)
    fx = np.zeros((n, 2), dtype=np.float32)
    cache: Dict[str, np.ndarray] = {}
    for s in segs:
        if s.get("voice_path"):
            v = _load48(s["voice_path"])
            i = int((s["t0"] + VOICE_LEAD_IN) * SR)
            voice[i:i + len(v)] += v[: n - i]
        for off, txt in s.get("voice_parts", []):
            v = _load48(_PART_CACHE[txt])
            i = int((s["t0"] + off) * SR)
            voice[i:i + len(v)] += v[: n - i]
        for off, kind in s["sfx"]:
            if kind not in cache:
                cache[kind] = audio_synth.sfx(kind).astype(np.float32)
            e = cache[kind]
            i = int((s["t0"] + off) * SR)
            fx[i:i + len(e)] += e[: n - i]
    music = audio_synth.music_bed(total + 0.5, seed=seed).astype(np.float32)[:n]
    if len(music) < n:
        music = np.pad(music, ((0, n - len(music)), (0, 0)))
    # sidechain ducking: music -70 % while Lumi talks, smooth 150 ms attack/400 ms release
    env = np.abs(voice).max(axis=1)
    hop = int(0.05 * SR)
    frames = env[: len(env) // hop * hop].reshape(-1, hop).max(axis=1)
    active = (frames > 0.02).astype(np.float32)
    k = np.ones(8) / 8
    active = np.clip(np.convolve(active, k, mode="same") * 2, 0, 1)
    gain = 1.0 - 0.70 * np.repeat(active, hop)   # music drops 70 % while Lumi speaks
    gain = np.pad(gain, (0, n - len(gain)), constant_values=1.0)
    mix = voice * 1.0 + fx * 0.45 + music * 0.55 * gain[:, None]
    mix /= max(1.0, float(np.max(np.abs(mix))) / 0.95)
    raw = os.path.join(scratch, "longform_raw.wav")
    sf.write(raw, mix, SR, subtype="PCM_16")
    # 2-pass EBU R128 -> -16 LUFS / -1.5 dBTP
    import json
    p1 = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", "loudnorm=I=-16:TP=-2:LRA=11:print_format=json",
                         "-f", "null", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr.decode()
    st = json.loads(p1[p1.rfind("{"):p1.rfind("}") + 1])
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
          "loudnorm=I=-16:TP=-2:LRA=11:linear=true:"
          f"measured_I={st['input_i']}:measured_TP={st['input_tp']}:measured_LRA={st['input_lra']}:"
          f"measured_thresh={st['input_thresh']}:offset={st['target_offset']},"
          # brick-wall safety limiter at -3 dBFS: AAC encoding can add ~1-2 dB of inter-sample peaks
          "alimiter=limit=0.708:attack=5:release=50:level=false,aresample=48000",
          "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", out_wav])
    speech_sec = sum(s.get("speech_sec", 0) for s in segs)
    words = sum(s.get("words", 0) for s in segs)
    return {"path": out_wav, "speech_sec": round(speech_sec, 1), "words": words,
            "wpm": round(words / (speech_sec / 60), 1) if speech_sec else 0.0, "music_bed": True}


def render(pack, segs, scratch: str, out_mp4: str, job_id: str) -> Dict[str, Any]:
    lumi = visuals.render_lumi(scratch, job_id)
    clips, checks, pictures = [], [], []
    bgs = [(pack["items"][s["visual"]["item"]]["bg_hex"] if "item" in s["visual"] else visuals.NEUTRAL_BG) for s in segs]
    decor_all = visuals.DECOR
    countdowns = 0
    for i, s in enumerate(segs):
        decor = decor_all[i % len(decor_all):] + decor_all[:i % len(decor_all)]
        r = visuals.render_segment(pack, s["visual"], scratch, job_id, i, decor)
        checks += r["text_checks"]
        pictures.append(r["has_picture"])
        if s["kind"] == "countdown":
            countdowns += 1
        frames = r["frames"]
        fade_in = i > 0 and bgs[i - 1] != bgs[i]
        fade_out = i < len(segs) - 1 and bgs[i + 1] != bgs[i]
        part = s["dur"] / len(frames)
        for j, fr in enumerate(frames):
            d = part if j < len(frames) - 1 else s["dur"] - part * (len(frames) - 1)
            fx = []
            if fade_in and j == 0:
                fx.append("fade=t=in:st=0:d=0.3")
            if fade_out and j == len(frames) - 1:
                fx.append(f"fade=t=out:st={max(0, d - 0.3):.3f}:d=0.3")
            filt = ("[1:v]format=rgba[p];[2:v]format=rgba[l];"
                    # pop-in: object drops in with a bounce during the first 0.45 s, then bobs gently
                    f"[0:v][p]overlay=x=(W-w)/2:y={fr['hero_y']}-h/2+12*sin(2*PI*t/1.8)"
                    "+if(lt(t\\,0.45)\\,-260*cos(PI*t/0.9)*exp(-t*4)\\,0):eval=frame[a];"
                    "[a][l]overlay=x=40:y=H-h-10+6*sin(2*PI*t/1.3+1):eval=frame"
                    + ("," + ",".join(fx) if fx else "") + ",format=yuv420p[v]")
            clip = os.path.join(scratch, f"{job_id}_c{i:03d}_{j}.mp4")
            _run(["ffmpeg", "-y", "-loglevel", "error",
                  "-loop", "1", "-framerate", "60", "-i", fr["bg"],
                  "-loop", "1", "-framerate", "60", "-i", fr["hero"],
                  "-loop", "1", "-framerate", "60", "-i", lumi,
                  "-filter_complex", filt, "-map", "[v]", "-t", f"{d:.3f}", "-r", "60",
                  "-c:v", "libx264", "-profile:v", "high", "-preset", "fast", "-crf", "18", "-g", "120",
                  "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", clip])
            clips.append(clip)
        if i % 20 == 0:
            logger.info("[Render] %d/%d segments", i + 1, len(segs))
    concat = os.path.join(scratch, f"{job_id}_concat.txt")
    with open(concat, "w") as fh:
        fh.writelines(f"file '{c}'\n" for c in clips)
    video_only = os.path.join(scratch, f"{job_id}_video.mp4")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat, "-c", "copy", video_only])
    return {"video_only": video_only, "text_checks": checks, "pictures": pictures, "countdowns": countdowns,
            "decorations": True}


def mux(video_only: str, audio_wav: str, out_mp4: str) -> None:
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_only, "-i", audio_wav, "-map", "0:v", "-map", "1:a",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest",
          "-movflags", "+faststart", out_mp4])


def chapters(segs) -> List[Dict[str, Any]]:
    out = [{"t": s["t0"], "title": s["chapter"]} for s in segs if s.get("chapter")]
    out[0]["t"] = 0.0
    # YouTube: chapters >= 10 s apart
    clean = [out[0]]
    for c in out[1:]:
        if c["t"] - clean[-1]["t"] >= 10:
            clean.append(c)
    return clean
