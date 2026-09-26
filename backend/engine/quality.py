"""SKQS-3 — SmartKids Quality Standard, version 3 (acting rule) (see docs/QUALITY_STANDARD.md).

A video that fails ANY hard rule is never uploaded (job -> FAILED_QA). Every rule is measured on
the final MP4 (ffprobe / ffmpeg filters) or on numbers recorded while rendering — nothing is assumed.
"""
import json
import re
import subprocess
from typing import Any, Dict, List

STANDARD_ID = "SKQS-3"

RULES = {
    "width": 1920, "height": 1080, "fps": 60,
    "video_codec": "h264", "video_profile": "High", "pix_fmt": "yuv420p",
    "audio_codec": "aac", "audio_rate": 48000, "audio_channels": 2,
    "min_duration": 495.0, "max_duration": 630.0,          # 8:15 - 10:30 (mid-roll eligible)
    "loudness_target": -16.0, "loudness_tol": 1.0,       # integrated LUFS (EBU R128)
    "true_peak_max": -1.0,                                 # dBTP
    "max_silence_sec": 1.0,                                # zero-silence rule: music bed never stops
    "max_black_sec": 0.5,                                  # blackdetect
    "flash_delta": 25.0,                                   # a frame-to-frame YAVG jump above this counts as a flash
    "max_flashes_per_sec": 2,                              # WCAG 2.3.1 / Harding: fewer than 3 flashes in any second
    "min_text_contrast": 4.5,                              # WCAG 2.x AA
    "min_text_px": 48,                                     # at 1080p
    "min_items": 6,
    "wpm_min": 90, "wpm_max": 150,                         # energetic but understandable for preschoolers
    "min_interjection_ratio": 0.8,                         # acting rule: >= 80 % of lines start with Wow/Oh/Yay...
    "min_tagged_ratio": 0.95,                              # every line carries an emotion tag
    "min_whisper_lines": 5,                                # dynamic range: not only shouting
    "approved_voices": ["af_heart", "ef_dora", "ff_siwis", "pf_dora", "chatterbox_female_nicole", "chatterbox_male_puck"],
    "title_max": 100, "description_min": 400,
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
               "scale=320:180,blackdetect=d=0.1:pix_th=0.05,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
               "-f", "null", "-"])
    m["black_segments"] = [float(x) for x in re.findall(r"black_duration:\s*([\d.]+)", out)]
    yavg = [float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", out)]
    steps = [abs(b - a) for a, b in zip(yavg, yavg[1:])]
    m["max_luma_step"] = round(max(steps, default=0.0), 2)
    flash_frames = [i for i, d in enumerate(steps) if d > RULES["flash_delta"]]
    worst, j = 0, 0
    for i, f in enumerate(flash_frames):          # sliding 1-second window (60 frames)
        while f - flash_frames[j] >= 60:
            j += 1
        worst = max(worst, i - j + 1)
    m["max_flashes_per_sec"] = worst
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
    need(m.get("max_flashes_per_sec", 99) <= R["max_flashes_per_sec"],
         f"flash guard: {m.get('max_flashes_per_sec')} flashes within one second")

    # design-time facts recorded by the renderer / mixer
    items = design.get("items", 0)
    need(items >= R["min_items"], f"only {items} learning items")
    for t in design.get("text_checks", []):
        need(t["contrast"] >= R["min_text_contrast"], f"text contrast {t['contrast']} for '{t['text']}'")
        need(t["px"] >= R["min_text_px"], f"text size {t['px']}px for '{t['text']}'")
    need(bool(design.get("pictures")) and all(design["pictures"]), "segment without picture")
    need(design.get("character_every_scene") is True, "Lumi missing in a segment")
    need(design.get("decorations") is True, "no flower/bug decorations")
    need(design.get("music_bed") is True, "no continuous music bed")
    need(design.get("countdowns", 0) >= items, f"countdowns {design.get('countdowns')} < items {items}")
    wpm = design.get("wpm", 0)
    need(R["wpm_min"] <= wpm <= R["wpm_max"], f"narration pace {wpm} wpm")
    need(design.get("voice") in R["approved_voices"], f"voice {design.get('voice')} not approved")
    need(design.get("interjection_ratio", 0) >= R["min_interjection_ratio"],
         f"monotony: only {design.get('interjection_ratio')} of lines have an interjection")
    need(design.get("tagged_ratio", 0) >= R["min_tagged_ratio"], f"untagged lines: {design.get('tagged_ratio')}")
    need(design.get("whisper_lines", 0) >= R["min_whisper_lines"], "no whisper contrast")
    need(design.get("countdown_sfx") is True, "countdown without tick-tock/reveal effects")

    # metadata
    need(0 < len(meta.get("title", "")) <= R["title_max"], "title length")
    need("EP-" not in meta.get("title", ""), "internal id in title")
    need(len(meta.get("description", "")) >= R["description_min"], "description too short")
    need("0:00" in meta.get("description", ""), "no chapters")
    need("Apache" in meta.get("description", ""), "attribution missing")
    need(bool(meta.get("tags")), "no tags")
    need(meta.get("made_for_kids") is True, "must be declared made for kids (COPPA)")

    return {"standard": STANDARD_ID, "passed": not f, "failures": f, "measurements": m,
            "design": {k: v for k, v in design.items() if k != "text_checks"},
            "min_text_contrast": min((t["contrast"] for t in design.get("text_checks", [])), default=None)}
