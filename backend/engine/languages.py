"""The 10-language registry (single source of truth for narration, QA, visuals and YouTube).

Every language is produced from the SAME master episode (backend/engine/longform.py PACKS) with a
hand-written localisation in backend/engine/i18n/<CODE>.json. Nothing is machine-translated at run time.

Narration: Chatterbox (MIT). EN uses the original English model (validated in production);
all other languages use Chatterbox Multilingual (23 languages, same licence).
Narrator timbre: a reference clip generated with Kokoro-82M (Apache-2.0) in that language when Kokoro
has a native voice, otherwise the English narrator clip with cfg_weight=0 (Chatterbox's documented way
to stop the reference accent leaking into another language).

Distortion guard per language: Whisper (faster-whisper, MIT) transcript compared with the script.
EN: word error rate with the English-only base model. Others: character error rate with the
multilingual "small" model (word boundaries are unreliable in Hindi/Arabic transcripts).
"""
from typing import Any, Dict, List

LANGUAGES: Dict[str, Dict[str, Any]] = {
    "EN": {"name": "English", "native": "English", "cb": "en", "yt": "en", "whisper": "base.en",
           "metric": "wer", "max_err": 0.25, "kokoro_lang": "en-us",
           "kokoro_ref": {"female": "af_nicole", "male": "am_puck"}, "font": "latin", "rtl": False},
    "ES": {"name": "Spanish", "native": "Español", "cb": "es", "yt": "es", "whisper": "small",
           "metric": "cer", "max_err": 0.30, "kokoro_lang": "es",
           "kokoro_ref": {"female": "ef_dora", "male": "em_alex"}, "font": "latin", "rtl": False},
    "PT": {"name": "Portuguese", "native": "Português", "cb": "pt", "yt": "pt-BR", "whisper": "small",
           "metric": "cer", "max_err": 0.30, "kokoro_lang": "pt-br",
           "kokoro_ref": {"female": "pf_dora", "male": "pm_alex"}, "font": "latin", "rtl": False},
    "FR": {"name": "French", "native": "Français", "cb": "fr", "yt": "fr", "whisper": "small",
           "metric": "cer", "max_err": 0.30, "kokoro_lang": "fr-fr",
           "kokoro_ref": {"female": "ff_siwis", "male": None}, "font": "latin", "rtl": False},
    "DE": {"name": "German", "native": "Deutsch", "cb": "de", "yt": "de", "whisper": "small",
           "metric": "cer", "max_err": 0.30, "kokoro_lang": None,
           "kokoro_ref": {"female": None, "male": None}, "font": "latin", "rtl": False},
    "IT": {"name": "Italian", "native": "Italiano", "cb": "it", "yt": "it", "whisper": "small",
           "metric": "cer", "max_err": 0.30, "kokoro_lang": "it",
           "kokoro_ref": {"female": "if_sara", "male": "im_nicola"}, "font": "latin", "rtl": False},
    "TR": {"name": "Turkish", "native": "Türkçe", "cb": "tr", "yt": "tr", "whisper": "small",
           "metric": "cer", "max_err": 0.30, "kokoro_lang": None,
           "kokoro_ref": {"female": None, "male": None}, "font": "latin", "rtl": False},
    "RU": {"name": "Russian", "native": "Русский", "cb": "ru", "yt": "ru", "whisper": "small",
           "metric": "cer", "max_err": 0.30, "kokoro_lang": None,
           "kokoro_ref": {"female": None, "male": None}, "font": "latin", "rtl": False},
    "AR": {"name": "Arabic", "native": "العربية", "cb": "ar", "yt": "ar", "whisper": "small",
           "metric": "cer", "max_err": 0.35, "kokoro_lang": None,
           "kokoro_ref": {"female": None, "male": None}, "font": "arabic", "rtl": True},
    "HI": {"name": "Hindi", "native": "हिन्दी", "cb": "hi", "yt": "hi", "whisper": "small",
           "metric": "cer", "max_err": 0.35, "kokoro_lang": "hi",
           "kokoro_ref": {"female": "hf_alpha", "male": "hm_omega"}, "font": "devanagari", "rtl": False},
}
ALL_CODES: List[str] = list(LANGUAGES)

# Fonts (Ubuntu packages fonts-dejavu-core + fonts-noto-core). DejaVu covers Latin, Turkish, Cyrillic.
FONTS = {
    "latin": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "arabic": "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    "devanagari": "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
}

# How the same master episode reaches viewers (automation_control.distribution_mode):
#   MULTI_CHANNEL              one YouTube channel per language, one video per language (own title/labels).
#                              Fully automatic. Needs YOUTUBE_REFRESH_TOKEN_<LANG> per channel.
#   SINGLE_CHANNEL             one channel, one separate localized video per language. Fully automatic.
#   SINGLE_CHANNEL_MULTI_AUDIO one video on the main channel + a dubbed audio track per language on the
#                              SAME timeline. Localized titles/descriptions go through the API; the extra
#                              audio tracks are produced as files, because the YouTube Data API has no
#                              endpoint for audio tracks (Studio > Languages > Add language > Dub).
DISTRIBUTION_MODES = ("MULTI_CHANNEL", "SINGLE_CHANNEL", "SINGLE_CHANNEL_MULTI_AUDIO")
DEFAULT_DISTRIBUTION_MODE = "MULTI_CHANNEL"


def get(code: str) -> Dict[str, Any]:
    code = (code or "").upper()
    if code not in LANGUAGES:
        raise KeyError(f"unknown language {code!r}; known: {', '.join(ALL_CODES)}")
    return LANGUAGES[code]


def reference_voice(code: str, narrator: str) -> Dict[str, Any]:
    """Which Kokoro voice/lang makes the narrator reference clip for this language.
    Falls back to the English narrator clip (cross-lingual cloning, cfg_weight=0)."""
    L = get(code)
    kv = (L.get("kokoro_ref") or {}).get(narrator)
    if kv and L.get("kokoro_lang"):
        return {"kokoro_voice": kv, "kokoro_lang": L["kokoro_lang"], "lang": code, "native": True}
    en = LANGUAGES["EN"]
    return {"kokoro_voice": en["kokoro_ref"].get(narrator), "kokoro_lang": "en-us", "lang": "EN", "native": code == "EN"}
