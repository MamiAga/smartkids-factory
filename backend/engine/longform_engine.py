"""Long-form (SKQS) audio + video assembly for one master episode and 1..10 language tracks."""
import logging
import os
import subprocess
from typing import Any, Dict, List

import numpy as np
import soundfile as sf

from backend.engine import audio_synth, tts, visuals

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


def _count_words(text: str) -> int:
    return sum(1 for w in _strip_tags(text).split() if any(ch.isalnum() for ch in w))


def narrate(segs: List[Dict[str, Any]], language: str, scratch: str, job_id: str) -> None:
    for s in segs:  # spoken "Three! Two! One!" clips, synthesised once and reused
        for _, txt in s.get("voice_parts", []):
            key = f"{language}|{txt}"
            if key not in _PART_CACHE:
                wav = os.path.join(scratch, f"{job_id}_{language}_part_{abs(hash(key)) % 10**8}.wav")
                tts.synth(txt, language, wav)
                _PART_CACHE[key] = wav
    for i, s in enumerate(segs):
        if s.get("voice_path") or not s["text"]:
            continue
        wav = os.path.join(scratch, f"{job_id}_{language}_n{i:03d}_{abs(hash(s['text'])) % 10**8}.wav")
        s["speech_sec"] = tts.synth(s["text"], language, wav)
        s["voice_path"] = wav
        s["words"] = _count_words(s["text"])
        s["language"] = language


def _durations(tracks: Dict[str, List[Dict[str, Any]]]) -> float:
    """Shared timeline: every segment lasts as long as its LONGEST narration over all language tracks,
    so one rendered video fits every dubbed audio track (single-channel multi-audio mode)."""
    langs = list(tracks)
    n = len(tracks[langs[0]])
    total = 0.0
    for i in range(n):
        base = tracks[langs[0]][i]
        if base["fixed"]:
            dur = base["fixed"]
        else:
            need = max(VOICE_LEAD_IN + t[i].get("speech_sec", 0.0) + 0.55 + (t[i].get("pad") or 0) for t in tracks.values())
            dur = round(max(HOLD.get(base["kind"], 3.0), need), 3)
        for t in tracks.values():
            t[i]["dur"], t[i]["t0"] = dur, total
        total += dur
    return total


def plan_tracks(pack, tracks: Dict[str, List[Dict[str, Any]]], scratch, job_id, seed) -> float:
    """TTS every language track, fix shared durations, add bonus rounds / trim (applied to ALL tracks
    in lockstep) until the episode length is inside the standard."""
    from backend.engine.longform import bonus_round
    for segs in tracks.values():
        for s in segs:  # move 'pad' from visual kwargs into the segment
            s["pad"] = s["visual"].pop("pad", 0) if "pad" in s["visual"] else s.get("pad", 0)
    for lang, segs in tracks.items():
        narrate(segs, lang, scratch, job_id)
    total = _durations(tracks)
    extra = 0
    while total < MIN_TARGET and extra < 3:
        extra += 1
        for lang, segs in tracks.items():
            at = next(i for i, s in enumerate(segs) if s["kind"] == "chant_intro")
            segs[at:at] = bonus_round(pack, seed + extra, lang)
            narrate(segs, lang, scratch, job_id)
        total = _durations(tracks)
        logger.info("[Long-form] added bonus round %d -> %.1fs", extra, total)
    n_items = len(pack["items"])
    ref = next(iter(tracks.values()))
    while total > MAX_TARGET:
        chants = [i for i, x in enumerate(ref) if x["kind"] == "chant"]
        reviews = [i for i, x in enumerate(ref) if x["kind"] == "review"]
        examples = [i for i, x in enumerate(ref) if x["kind"] == "example"]
        cut = None
        if len(chants) > n_items:                       # 1) sing the list once instead of twice
            cut, why = (chants[-1], chants[-1] + 1), "second chant pass"
        elif len(reviews) > 4:                          # 2) shorter review round (keep >= 4 questions)
            cut, why = (reviews[-1], reviews[-1] + 3), "review question"
        elif len(examples) > 2 * n_items:               # 3) 2 examples per item instead of 3
            per = {}
            for i in examples:
                per.setdefault(ref[i]["visual"]["item"], []).append(i)
            victim = max((v for v in per.values() if len(v) > 2), key=lambda v: v[-1])[-1]
            cut, why = (victim, victim + 1), "third example"
        elif reviews:                                   # 4) drop the remaining review questions one by one
            cut, why = (reviews[-1], reviews[-1] + 3), "review question (below 4)"
        elif any(x["kind"] == "repeat" and (x.get("pad") or 0) > 1.0 for x in ref):
            for segs in tracks.values():                # 5) shorter "repeat after me" pauses
                for x in segs:
                    if x["kind"] == "repeat":
                        x["pad"] = 1.0
            why = "repeat pauses"
        else:
            break
        if cut:
            for segs in tracks.values():
                del segs[cut[0]:cut[1]]
        total = _durations(tracks)
        logger.info("[Long-form] trimmed %s -> %.1fs", why, total)
    logger.info("[Long-form] %d segments, %.1f s (%.2f min), tracks=%s", len(ref), total, total / 60, ",".join(tracks))
    return total


def plan_audio(pack, segs, language, scratch, job_id, seed) -> float:
    """Single-language wrapper (one channel per language)."""
    return plan_tracks(pack, {language: segs}, scratch, job_id, seed)


def mix_audio(segs, total: float, scratch: str, out_wav: str, seed: int, language: str = "EN") -> Dict[str, Any]:
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
            v = _load48(_PART_CACHE[f"{s.get('language') or language}|{txt}"])
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
    raw = os.path.join(scratch, f"longform_raw_{language}.wav")
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
          # 4x oversampled limiter ~ true-peak limiter; AAC can still add a little, mux() re-checks
          "aresample=192000,alimiter=limit=0.708:attack=2:release=60:level=false,aresample=48000",
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


def _true_peak(path: str) -> float:
    import re
    out = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr.decode("utf-8", "replace")
    m = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out[out.rfind("Summary:"):])
    return float(m[-1]) if m else 0.0


def mux(video_only: str, audio_wav: str, out_mp4: str) -> None:
    """Mux + AAC encode, then verify true peak on the ENCODED file. If AAC overshoots, tighten an
    oversampled peak limiter (only peaks are touched, so loudness stays at -16 LUFS) and re-encode."""
    for limit_db in (-3.0, -4.5, -6.0, -8.0):
        lim = 10 ** (limit_db / 20)
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_only, "-i", audio_wav, "-map", "0:v", "-map", "1:a",
              "-c:v", "copy",
              "-af", f"aresample=192000,alimiter=limit={lim:.3f}:attack=1:release=50:level=false,aresample=48000",
              "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
              "-shortest", "-movflags", "+faststart", out_mp4])
        tp = _true_peak(out_mp4)
        logger.info("[Mux] limiter %.1f dBFS -> encoded true peak %.2f dBTP", limit_db, tp)
        if tp <= -1.3:
            return


def chapters(segs) -> List[Dict[str, Any]]:
    out = [{"t": s["t0"], "title": s["chapter"]} for s in segs if s.get("chapter")]
    out[0]["t"] = 0.0
    # YouTube: chapters >= 10 s apart
    clean = [out[0]]
    for c in out[1:]:
        if c["t"] - clean[-1]["t"] >= 10:
            clean.append(c)
    return clean
