#!/usr/bin/env python3
"""Voice lab: measure the acoustic guard on known-good and known-bad audio, to calibrate thresholds.

Step 1 (main env):      python3 backend/tools/voice_lab.py prepare
    reference clips (EN girl/boy, ES native, TR cross-lingual) + Kokoro versions of the EN test lines
Step 2 (Chatterbox env): /tmp/cbenv/bin/python backend/tools/voice_lab.py measure
    for every config: Chatterbox takes (raw), the same takes time-stretched with Rubber Band to 0.8
    (what v2 did to fast lines) and the Kokoro lines (what v2 used as fallback) -> voice_guard metrics.
Output: /tmp/smartkids_output/voice_lab.json (+ a few mp3 examples)
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
LAB = "/tmp/voice_lab"
OUT = "/tmp/smartkids_output"
LINES = {
    "EN": ["[excited] Wow! Hello, hello, my little friends! I'm Lumi the owl!",
           "[excited] Oh! What else is red? Look! An apple! [excited] Yay! The apple is red!",
           "[excited] Yay, game time! Oh-oh, which one is the cow? [whisper] Look very, very carefully...",
           "[excited] Whee! Dance break! Wiggle your arms! Stomp your feet! Clap, clap, clap!",
           "[excited] Wow! It's a lion! [excited] The lion says roar!",
           "[whisper] I'm so proud of you. Give yourself a big hug."],
    "ES": ["[excited] ¡Guau! ¡Es rojo! [excited] ¡Yupi! ¡El rojo es brillante y cálido!",
           "[excited] ¡Oh! ¿Qué más es rojo? ¡Mira! ¡Una manzana!",
           "[whisper] Mira con mucho, mucho cuidado..."],
    "TR": ["[excited] Vay! İşte kırmızı! [excited] Yaşasın! Kırmızı, parlak ve sıcacık bir renk!",
           "[excited] Oo! Başka neler kırmızı? Bakın! İşte bir elma!",
           "[whisper] Çok, çok dikkatli bakın..."],
}
CONFIGS = [  # name, language, narrator
    ("EN_female", "EN", "female"), ("EN_male", "EN", "male"), ("ES_female", "ES", "female"), ("TR_male", "TR", "male")]


def prepare():
    from backend.engine import tts
    os.makedirs(LAB, exist_ok=True)
    refs = {}
    for name, lang, narrator in CONFIGS:
        refs[name] = tts.reference_wav(lang, narrator)
    tts.ENGINE = "kokoro"
    kok = []
    for i, t in enumerate(LINES["EN"]):
        p = os.path.join(LAB, f"kokoro_EN_{i}.wav")
        tts._synth_kokoro(t, "EN", p)
        kok.append({"text": t, "path": p})
    with open(os.path.join(LAB, "prep.json"), "w") as fh:
        json.dump({"refs": refs, "kokoro": kok}, fh, indent=1, ensure_ascii=False)
    print(json.dumps(refs, indent=1))


def measure():
    import re
    import numpy as np
    import soundfile as sf
    import torch
    import voice_guard as VG
    prep = json.load(open(os.path.join(LAB, "prep.json")))
    os.makedirs(OUT, exist_ok=True)
    results, models = [], {}
    for name, lang, narrator in CONFIGS:
        cb = lang.lower()
        key = "en" if cb == "en" else "mtl"
        if key not in models:
            if key == "en":
                from chatterbox.tts import ChatterboxTTS
                models[key] = ChatterboxTTS.from_pretrained(device="cpu")
            else:
                from chatterbox.mtl_tts import ChatterboxMultilingualTTS
                models[key] = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
        model = models[key]
        ref = prep["refs"][name]
        model.prepare_conditionals(ref["path"], exaggeration=1.0)
        spk = model.conds.t3.speaker_emb.detach().cpu().numpy().reshape(-1)
        ref_emb = spk / np.linalg.norm(spk)
        cfg = 0.0 if ref["cfg_zero"] == "1" else 0.3

        def metrics(a, sr, kind, text, extra=None):
            a16 = VG.to16k(a, sr)
            m = {"config": name, "kind": kind, "text": text[:50], "dur": round(len(a) / sr, 2)}
            if len(a) / sr >= 1.0:
                m.update(VG.speaker_drift(model.ve, a16, ref_emb))
                m.update(VG.flat_pitch(a16))
                m["guard_why"] = VG.judge({**m, "err": 0.0, "sec_per_word": 0.4}, 8, 1.0, False)
            m.update(extra or {})
            results.append(m)
            print(json.dumps(m, ensure_ascii=False), flush=True)

        for li, line in enumerate(LINES[lang]):
            for tag, body in re.findall(r"(?:\[([a-z]+)\]\s*)?([^\[]+)", line):
                body = body.strip()
                if not body:
                    continue
                exag = {"excited": 1.0, "calm": 0.55, "whisper": 0.4}.get(tag or "calm", 0.55)
                for seed in (1000, 1017):
                    torch.manual_seed(seed)
                    with torch.inference_mode():
                        if key == "en":
                            wav = model.generate(body, exaggeration=exag, cfg_weight=cfg, temperature=0.7)
                        else:
                            wav = model.generate(body, language_id=cb, exaggeration=exag, cfg_weight=cfg, temperature=0.7)
                    a = wav.squeeze(0).numpy()
                    metrics(a, model.sr, "chatterbox_raw", body, {"seed": seed, "exag": exag})
                    src = os.path.join(LAB, f"{name}_{li}_{seed}.wav")
                    dst = src.replace(".wav", "_rb.wav")
                    sf.write(src, a, model.sr)
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", "rubberband=tempo=0.8", dst], check=True)
                    b, sr2 = sf.read(dst, dtype="float32")
                    metrics(b, sr2, "rubberband_0.8", body, {"seed": seed})
                    if li < 2 and seed == 1000:
                        for p in (src, dst):
                            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", p, "-b:a", "128k",
                                            os.path.join(OUT, "lab_" + os.path.basename(p).replace(".wav", ".mp3"))])
        if name == "EN_female":
            for k in prep["kokoro"]:
                a, sr = sf.read(k["path"], dtype="float32")
                metrics(a, sr, "kokoro_fallback", k["text"])

    summary = {}
    for r in results:
        if "sim_min" not in r:
            continue
        s = summary.setdefault(f"{r['config']}:{r['kind']}", {"n": 0, "sim_min": [], "sim_drop": [], "flat_sec": [], "rejected": 0})
        s["n"] += 1
        for k in ("sim_min", "sim_drop", "flat_sec"):
            s[k].append(r[k])
        s["rejected"] += bool(r.get("guard_why"))
    for s in summary.values():
        for k in ("sim_min", "sim_drop", "flat_sec"):
            v = sorted(s[k])
            s[k] = {"min": v[0], "median": v[len(v) // 2], "max": v[-1]}
    out = {"thresholds": {"SIM_MIN": VG.SIM_MIN, "SIM_DROP": VG.SIM_DROP, "FLAT_ST": VG.FLAT_SEMITONES,
                          "FLAT_MAX_SEC": VG.FLAT_MAX_SEC}, "summary": summary, "takes": results}
    with open(os.path.join(OUT, "voice_lab.json"), "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print("SUMMARY", json.dumps(summary, indent=1))


if __name__ == "__main__":
    {"prepare": prepare, "measure": measure}[sys.argv[1]]()
