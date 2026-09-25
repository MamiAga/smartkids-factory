"""SKQS-1 — SmartKids Quality Standard, version 1 (see docs/QUALITY_STANDARD.md).

A video that fails ANY hard rule is never uploaded (job -> FAILED_QA). Every rule is measured on
the final MP4 (ffprobe / ffmpeg filters) or on numbers recorded while rendering — nothing is assumed.
"""
import json
import re
import subprocess
from typing import Any, Dict, List

STANDARD_ID = "SKQS-1"

RULES = {
    "width": 1920, "height": 1080, "fps": 60,
    "video_codec": "h264", "video_profile": "High", "pix_fmt": "yuv420p",
    "audio_codec": "aac", "audio_rate": 48000, "audio_channels": 2,
    "min_duration": 45.0, "max_duration": 90.0,
    "loudness_target": -16.0, "loudness_tol": 1.0,       # integrated LUFS (EBU R128)
    "true_peak_max": -1.0,                                 # dBTP
    "max_silence_sec": 4.5,                                # silencedetect @ -45 dB
    "max_black_sec": 0.5,                                  # blackdetect
    "max_luma_step": 12.0,                                 # flash guard: YAVG change per frame (0-255)
    "min_text_contrast": 4.5,                              # WCAG 2.x AA
    "min_text_px": 48,                                     # at 1080p
    "scenes": 5,
    "min_pause_sec": 2.0, "max_pause_sec": 4.0,            # interaction pause after each prompt
    "max_words_per_scene": 45,
    "title_max": 100, "description_min": 200,
}


class QualityGateError(Exception):
    pass


def _ff(args: List[str]) -> str:
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")


def measure(mp4: str) -> Dict[str, Any]:
    probe = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format",
                                       "-show_streams", mp4], stdout=subprocess.PIPE).stdout.decode() or "{}")
    streams = probe.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), {})
    num, den = (v.get("r_frame_rate") or "0/1").split("/")
    m: Dict[str, Any] = {
        "duration": float(probe.get("format", {}).get("duration", 0)),
        "width": v.get("width"), "height": v.get("height"),
        "fps": round(int(num) / max(1, int(den)), 3),
        "video_codec": v.get("codec_name"), "video_profile": v.get("profile"), "pix_fmt": v.get("pix_fmt"),
        "audio_codec": a.get("codec_name"), "audio_rate": int(a.get("sample_rate") or 0),
        "audio_channels": a.get("channels"),
    }
    # loudness + true peak (EBU R128)
    out = _ff(["ffmpeg", "-nostats", "-i", mp4, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    summary = out[out.rfind("Summary:"):]
    mi = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    mp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    m["loudness_lufs"] = float(mi.group(1)) if mi else None
    m["true_peak_dbtp"] = float(mp.group(1)) if mp and mp.group(1) != "-inf" else None
    # silences
    out = _ff(["ffmpeg", "-nostats", "-i", mp4, "-vn", "-af", "silencedetect=noise=-45dB:d=1", "-f", "null", "-"])
    m["silences"] = [float(x) for x in re.findall(r"silence_duration:\s*([\d.]+)", out)]
    # black segments + flash guard (per-frame average luma)
    out = _ff(["ffmpeg", "-nostats", "-i", mp4, "-an", "-vf",
               "blackdetect=d=0.1:pix_th=0.05,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
               "-f", "null", "-"])
    m["black_segments"] = [float(x) for x in re.findall(r"black_duration:\s*([\d.]+)", out)]
    yavg = [float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", out)]
    m["max_luma_step"] = round(max((abs(b - a) for a, b in zip(yavg, yavg[1:])), default=0.0), 2)
    m["frames_analyzed"] = len(yavg)
    return m


def evaluate(m: Dict[str, Any], design: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    """Return {"passed": bool, "failures": [...], "measurements": m, ...}."""
    R = RULES
    f: List[str] = []

    def need(cond: bool, msg: str):
        if not cond:
            f.append(msg)

    need(m["width"] == R["width"] and m["height"] == R["height"], f"resolution {m['width']}x{m['height']}")
    need(abs(m["fps"] - R["fps"]) < 0.01, f"fps {m['fps']}")
    need(m["video_codec"] == R["video_codec"] and m["video_profile"] == R["video_profile"]
         and m["pix_fmt"] == R["pix_fmt"], f"video {m['video_codec']}/{m['video_profile']}/{m['pix_fmt']}")
    need(m["audio_codec"] == R["audio_codec"] and m["audio_rate"] == R["audio_rate"]
         and m["audio_channels"] == R["audio_channels"],
         f"audio {m['audio_codec']}/{m['audio_rate']}Hz/{m['audio_channels']}ch")
    need(R["min_duration"] <= m["duration"] <= R["max_duration"], f"duration {m['duration']:.2f}s")
    lufs = m.get("loudness_lufs")
    need(lufs is not None and abs(lufs - R["loudness_target"]) <= R["loudness_tol"], f"loudness {lufs} LUFS")
    tp = m.get("true_peak_dbtp")
    need(tp is not None and tp <= R["true_peak_max"], f"true peak {tp} dBTP")
    need(all(s <= R["max_silence_sec"] for s in m["silences"]), f"silence gap {max(m['silences'], default=0)}s")
    need(all(b <= R["max_black_sec"] for b in m["black_segments"]), f"black segment {max(m['black_segments'], default=0)}s")
    need(m["max_luma_step"] <= R["max_luma_step"], f"flash guard: luma step {m['max_luma_step']}")

    # design-time facts recorded by the renderer
    need(design.get("scenes") == R["scenes"], f"scenes {design.get('scenes')}")
    for t in design.get("text_checks", []):
        need(t["contrast"] >= R["min_text_contrast"], f"text contrast {t['contrast']} for '{t['text']}'")
        need(t["px"] >= R["min_text_px"], f"text size {t['px']}px for '{t['text']}'")
    need(all(design.get("pictures", [])) and len(design.get("pictures", [])) == R["scenes"], "scene without picture")
    need(design.get("character_every_scene") is True, "Lumi missing in a scene")
    pause = design.get("pause_sec", 0)
    need(R["min_pause_sec"] <= pause <= R["max_pause_sec"], f"interaction pause {pause}s")

    # metadata
    need(0 < len(meta.get("title", "")) <= R["title_max"], "title length")
    need("EP-" not in meta.get("title", ""), "internal id in title")
    need(len(meta.get("description", "")) >= R["description_min"], "description too short")
    need("Apache" in meta.get("description", "") and "CC BY" in meta.get("description", ""), "attribution missing")
    need(bool(meta.get("tags")), "no tags")

    return {"standard": STANDARD_ID, "passed": not f, "failures": f, "measurements": m,
            "design": {k: v for k, v in design.items() if k != "text_checks"},
            "min_text_contrast": min((t["contrast"] for t in design.get("text_checks", [])), default=None)}
