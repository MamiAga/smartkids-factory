#!/usr/bin/env python3
"""
Downloads Piper ONNX model files from Hugging Face if not already present.
"""
import os
import sys
import argparse
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DownloadModels")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(BASE_DIR, "models", "piper")

VOICE_URLS = {
    "EN": {
        "dir": os.path.join(MODELS_DIR, "en"),
        "onnx": "en_US-libritts_r-medium.onnx",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx"
    },
    "ES": {
        "dir": os.path.join(MODELS_DIR, "es"),
        "onnx": "es_ES-sharvard-medium.onnx",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx"
    },
    "DE": {
        "dir": os.path.join(MODELS_DIR, "de"),
        "onnx": "de_DE-thorsten-medium.onnx",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx"
    },
    "FR": {
        "dir": os.path.join(MODELS_DIR, "fr"),
        "onnx": "fr_FR-siwis-medium.onnx",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx"
    },
    "PT": {
        "dir": os.path.join(MODELS_DIR, "pt"),
        "onnx": "pt_BR-edresson-low.onnx",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/edresson/low/pt_BR-edresson-low.onnx"
    }
}

def download_voice(lang: str):
    info = VOICE_URLS.get(lang.upper())
    if not info:
        logger.warning("No voice configured for language %s", lang)
        return
    os.makedirs(info["dir"], exist_ok=True)
    target = os.path.join(info["dir"], info["onnx"])
    if os.path.exists(target) and os.path.getsize(target) > 1000000:
        logger.info("Model for %s already exists (%d bytes)", lang, os.path.getsize(target))
        return
    logger.info("Downloading %s from %s...", info["onnx"], info["url"])
    urllib.request.urlretrieve(info["url"], target)
    logger.info("Downloaded %s successfully (%d bytes)", info["onnx"], os.path.getsize(target))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--languages", nargs="+", default=["EN"])
    args = parser.parse_args()
    for lang in args.languages:
        download_voice(lang)

if __name__ == "__main__":
    main()
