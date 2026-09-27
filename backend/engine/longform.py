"""SKQS long-form episodes (8:15 - 10:30), one MASTER episode -> 10 languages.

A master pack (PACKS below) holds everything language-neutral: item ids, colours, pictures, structure.
All words live in backend/engine/i18n/<LANG>.json (hand-localised, never machine-translated at run time).
`localize(pack, lang)` merges both into the dict every other module uses.

Structure (every item follows the same interactive activity loop):
  intro -> for each item: [mystery + 3-2-1 countdown] -> reveal -> repeat-after-me ->
  3 examples -> "Guess!" quiz + 3-2-1 countdown -> answer
  -> dance break (middle) -> review quiz round (countdown each) -> sing-along chant -> outro
If the timeline is shorter than the target, a bonus quiz round is appended automatically.
"""
import copy
import json
import os
import random
import re
from functools import lru_cache
from typing import Any, Dict, List

TEMPLATE_VERSION = "5.0.0"  # part of the idempotent job_id -> do not bump for voice-only changes

# countdown: clock tick-tock under the spoken "3... 2... 1..."; reveal effects rotate for surprise
COUNT_SFX = [(0.0, "tick"), (0.55, "tock"), (1.1, "tick"), (1.65, "tock"), (2.2, "tick"), (2.75, "go")]
COUNT_AT = (0.05, 1.15, 2.25)
REVEAL_SFX = ["tada", "boing", "chime", "quack", "pop", "tada", "boing", "quack"]
DECOR = ["🌸", "🦋", "🐞", "🌼", "🐝", "🌷", "🐛", "🌻", "🍀", "🐌"]
I18N_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "i18n")


def _ex(e):
    return {"e": e}


# ------------------------------------------------------------------ master packs (language-neutral)
PACKS: List[Dict[str, Any]] = [
    {
        "episode_id": "EP-COLORS-MEGA-V1", "family": "colors",
        "items": [
            {"key": "red", "bg_hex": "E53935", "pic": "🍓", "examples": [_ex("🍎"), _ex("🚒"), _ex("🍓")]},
            {"key": "blue", "bg_hex": "1E88E5", "pic": "🐳", "examples": [_ex("🐳"), _ex("🫐"), _ex("💧")]},
            {"key": "yellow", "bg_hex": "FDD835", "pic": "🌞", "examples": [_ex("🍌"), _ex("🐤"), _ex("🌞")]},
            {"key": "green", "bg_hex": "43A047", "pic": "🐸", "examples": [_ex("🐸"), _ex("🥦"), _ex("🍀")]},
            {"key": "purple", "bg_hex": "8E24AA", "pic": "🍇", "examples": [_ex("🍇"), _ex("🍆"), _ex("☂")]},
            {"key": "orange", "bg_hex": "FB8C00", "pic": "🍊", "examples": [_ex("🥕"), _ex("🎃"), _ex("🍊")]},
            {"key": "pink", "bg_hex": "EC407A", "pic": "🌸", "examples": [_ex("🐷"), _ex("🦩"), _ex("🌸")]},
            {"key": "brown", "bg_hex": "6D4C41", "pic": "🧸", "examples": [_ex("🧸"), _ex("🍪"), _ex("🐻")]},
        ],
    },
    {
        "episode_id": "EP-ANIMALS-MEGA-V1", "family": "animals",
        "items": [
            {"key": "cow", "bg_hex": "6D4C41", "pic": "🐄", "examples": [_ex("🐄"), _ex("🥛"), _ex("🌾")]},
            {"key": "dog", "bg_hex": "FB8C00", "pic": "🐶", "examples": [_ex("🐶"), _ex("🦴"), _ex("🎾")]},
            {"key": "cat", "bg_hex": "8E24AA", "pic": "🐱", "examples": [_ex("🐱"), _ex("🧶"), _ex("🐟")]},
            {"key": "duck", "bg_hex": "FDD835", "pic": "🦆", "examples": [_ex("🦆"), _ex("💧"), _ex("🐤")]},
            {"key": "sheep", "bg_hex": "43A047", "pic": "🐑", "examples": [_ex("🐑"), _ex("☁"), _ex("🌾")]},
            {"key": "pig", "bg_hex": "EC407A", "pic": "🐷", "examples": [_ex("🐷"), _ex("🌰"), _ex("💦")]},
            {"key": "lion", "bg_hex": "E53935", "pic": "🦁", "examples": [_ex("🦁"), _ex("👑"), _ex("🌞")]},
            {"key": "frog", "bg_hex": "1E88E5", "pic": "🐸", "examples": [_ex("🐸"), _ex("🦗"), _ex("🍃")]},
        ],
    },
]
PACKS_BY_ID = {p["episode_id"]: p for p in PACKS}


# ------------------------------------------------------------------ localisation
@lru_cache(maxsize=None)
def load_texts(language: str) -> Dict[str, Any]:
    path = os.path.join(I18N_DIR, f"{language.upper()}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"no localisation file {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def available_languages() -> List[str]:
    return sorted(f[:-5] for f in os.listdir(I18N_DIR) if f.endswith(".json"))


def localize(pack: Dict[str, Any], language: str = "EN") -> Dict[str, Any]:
    """Master pack + i18n texts -> localized pack (the dict every other module consumes).
    i18n items may override pictures ("pic", examples[].e) for cultural fit (e.g. no pig in TR/AR)."""
    if pack.get("language"):
        return pack
    T = load_texts(language)
    P = T["packs"][pack["episode_id"]]
    out = copy.deepcopy(pack)
    out.update({k: P[k] for k in ("title", "thumb_text", "learning_objective", "tags", "intro", "mystery", "repeat",
                                  "review_q", "chant", "dance", "outro")})
    out["language"] = language.upper()
    out["ui"] = {**T["ui"], **P.get("ui", {})}
    out["praise"] = T["praise"]
    out["count_words"] = T["count_words"]
    out["chapters"] = T["chapters"]
    out["meta_tpl"] = T["meta"]
    out["interjections"] = tuple(T["interjections"])
    for it in out["items"]:
        tx = P["items"][it["key"]]
        for k, v in tx.items():
            if k != "examples":
                it[k] = v
        it["Name"] = cap(it["name"], language)
        for ex, ext in zip(it["examples"], tx["examples"]):
            ex.update(ext)
    return out


def cap(s: str, language: str = "EN") -> str:
    """First letter upper-case, language aware (Turkish i -> İ, ı -> I)."""
    if not s:
        return s
    first = s[0]
    if language.upper() in ("TR", "AZ"):
        first = {"i": "İ", "ı": "I"}.get(first, first.upper())
    else:
        first = first.upper()
    return first + s[1:]


def _fmt(tpl: str, it: Dict[str, Any]) -> str:
    return tpl.replace("{K}", it["Name"]).replace("{Name}", it["Name"]).replace("{k}", it["name"])


def count_parts(lp: Dict[str, Any]):
    return list(zip(COUNT_AT, lp["count_words"]))


def build_timeline(pack: Dict[str, Any], seed: int = 1, language: str = "EN") -> List[Dict[str, Any]]:
    """Return ordered segments. Durations for narrated segments are filled in after TTS."""
    lp = localize(pack, language)
    rng = random.Random(seed)
    items = lp["items"]
    segs: List[Dict[str, Any]] = []
    praise = lambda: rng.choice(lp["praise"])  # noqa: E731
    parts = count_parts(lp)
    ch = lp["chapters"]

    def seg(kind, text=None, fixed=None, sfx=None, chapter=None, **visual):
        segs.append({"kind": kind, "text": text, "fixed": fixed, "sfx": sfx or [], "chapter": chapter,
                     "voice_parts": parts if kind == "countdown" else [],
                     "visual": dict(kind=kind, **visual)})

    seg("title", lp["intro"], sfx=[(0.0, "chime")], chapter=ch["hello"], title=lp["thumb_text"])
    for idx, it in enumerate(items):
        others = [o for o in items if o is not it]
        seg("mystery", lp["mystery"], sfx=[(0.0, "pop")], chapter=it["Name"], index=idx, total=len(items))
        seg("countdown", None, fixed=3.3, sfx=COUNT_SFX, index=idx, total=len(items), style="mystery")
        seg("reveal", it["reveal"], sfx=[(0.0, REVEAL_SFX[idx % len(REVEAL_SFX)])], item=idx)
        seg("repeat", _fmt(lp["repeat"], it), item=idx, pad=2.0)  # kid repeats, music fills
        for ei, ex in enumerate(it["examples"]):
            seg("example", ex["line"], sfx=[(0.0, "pop")], item=idx, emoji=ex["e"], example=ei,
                caption=ex["caption"] if lp["family"] == "colors" else it["Name"])
        correct = rng.choice(it["examples"])
        wrong = [rng.choice(o["examples"]) for o in rng.sample(others, 2)]
        choices = [correct] + wrong
        rng.shuffle(choices)
        ci = choices.index(correct)
        seg("quiz", it["quiz"], item=idx, choices=[c["e"] for c in choices])
        seg("countdown", None, fixed=3.3, sfx=COUNT_SFX, item=idx, choices=[c["e"] for c in choices], style="quiz")
        seg("answer", f"{correct.get('answer') or it['answer']} {praise()}",
            sfx=[(0.0, REVEAL_SFX[(idx + 3) % len(REVEAL_SFX)])], item=idx,
            choices=[c["e"] for c in choices], correct=ci)
        if idx == len(items) // 2 - 1:
            seg("dance", lp["dance"], sfx=[(0.0, "chime")], chapter=ch["dance"], pad=6.0)

    order = list(range(len(items)))
    rng.shuffle(order)
    for n, idx in enumerate(order):
        it = items[idx]
        seg("review", lp["review_q"], sfx=[(0.0, "pop")], chapter=ch["guess"] if n == 0 else None, item=idx)
        seg("countdown", None, fixed=3.3, sfx=COUNT_SFX, item=idx, style="review")
        seg("review_answer", f"{it['review_answer']} {praise()}", sfx=[(0.0, "tada")], item=idx)
    seg("chant_intro", lp["chant"], sfx=[(0.0, "chime")], chapter=ch["sing"])
    for rep in range(2):
        for idx, it in enumerate(items):
            seg("chant", f"[excited] {it['Name']}!", item=idx, pad=0.9, sfx=[(0.0, "pop")])
    seg("outro", lp["outro"], sfx=[(0.0, "tada")], chapter=ch["bye"], pad=3.0)
    return segs


def bonus_round(pack: Dict[str, Any], seed: int, language: str = "EN") -> List[Dict[str, Any]]:
    """Extra quiz round inserted before the sing-along when the episode is under the minimum length."""
    lp = localize(pack, language)
    rng = random.Random(seed)
    items = lp["items"]
    parts = count_parts(lp)
    out = []
    order = list(range(len(items)))
    rng.shuffle(order)
    for n, idx in enumerate(order):
        it = items[idx]
        ex = rng.choice(it["examples"])
        others = [o for o in items if o is not it]
        choices = [ex] + [rng.choice(o["examples"]) for o in rng.sample(others, 2)]
        rng.shuffle(choices)
        out.append({"kind": "quiz", "text": it["quiz"], "fixed": None, "sfx": [(0.0, "pop")],
                    "chapter": lp["chapters"]["bonus"] if n == 0 else None, "voice_parts": [],
                    "visual": {"kind": "quiz", "item": idx, "choices": [c["e"] for c in choices]}})
        out.append({"kind": "countdown", "text": None, "fixed": 3.3, "voice_parts": parts,
                    "sfx": COUNT_SFX, "chapter": None,
                    "visual": {"kind": "countdown", "item": idx, "choices": [c["e"] for c in choices], "style": "quiz"}})
        out.append({"kind": "answer", "text": f"{ex.get('answer') or it['answer']} {rng.choice(lp['praise'])}",
                    "fixed": None, "sfx": [(0.0, "tada")], "chapter": None, "voice_parts": [],
                    "visual": {"kind": "answer", "item": idx, "choices": [c["e"] for c in choices],
                               "correct": choices.index(ex)}})
    return out


MAX_BONUS_ROUNDS = 3


def all_narration(pack: Dict[str, Any], seed: int, language: str) -> List[str]:
    """Every distinct line a production of (pack, seed, language) can ask the TTS for, in timeline order,
    including the bonus rounds the planner may add. Used to split narration over parallel runners."""
    segs = build_timeline(pack, seed=seed, language=language)
    for extra in range(1, MAX_BONUS_ROUNDS + 1):
        segs += bonus_round(pack, seed + extra, language)
    seen, out = set(), []
    for s in segs:
        for t in [s["text"]] + [p for _, p in s.get("voice_parts", [])]:
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out


def plain(text: str) -> str:
    """Narration without emotion tags."""
    return re.sub(r"\[[a-z]+\]\s*", "", text or "").strip()


def starts_with_interjection(text: str, interjections) -> bool:
    t = plain(text).lstrip("¡¿!?.,;:«»\"'-— ")
    return any(t.lower().startswith(i.lower()) for i in interjections)


def youtube_metadata(pack: Dict[str, Any], chapters: List[Dict[str, Any]], language: str = "EN") -> Dict[str, Any]:
    lp = localize(pack, language)

    def ts(sec):
        sec = int(sec)
        return f"{sec // 60}:{sec % 60:02d}"
    words = ", ".join(it["Name"] for it in lp["items"])
    ch = "\n".join(f"{ts(c['t'])} {c['title']}" for c in chapters)
    tpl = lp["meta_tpl"]
    description = (tpl["description"].replace("{title}", lp["title"]).replace("{words}", words)
                   .replace("{goal}", lp["learning_objective"]).replace("{chapters}", ch)
                   .replace("{credits}", tpl["credits"]))
    tags = ["SmartKids"] + lp["tags"]
    return {"title": f"{lp['title']} | SmartKids"[:100], "description": description[:4900], "tags": tags[:15],
            "language": lp["language"]}


def episode_dna_row(pack: Dict[str, Any]) -> Dict[str, Any]:
    """Row for Supabase episode_dna (FK target of pipeline_jobs). Master (language-neutral) + EN names."""
    lp = localize(pack, "EN")
    return {
        "episode_id": pack["episode_id"], "version": TEMPLATE_VERSION, "family": pack["family"],
        "title": lp["title"][:255], "age_group": "2-5", "learning_objective": lp["learning_objective"],
        "format_type": "INTERACTIVE_ACTIVITY_LONGFORM", "difficulty": "BEGINNER",
        "target_duration_sec": 560, "min_duration_sec": 495, "max_duration_sec": 630,
        "characters": [{"name": "Lumi", "type": "Friendly Owl Guide"}],
        "visual_style": "Flat colour cards, Noto emoji art, flowers & bugs decorations, animated Lumi",
        "music_profile": {"profile": "procedural cheerful bed", "bpm": 124, "ducking": "-70% under voice"},
        "scenes": [{"key": i["key"], "label": i["label"], "examples": [e["caption"] for e in i["examples"]]}
                   for i in lp["items"]],
        "safety_profile": {"flash_hazard_guard": True, "zero_violence": True, "made_for_kids": True},
    }
