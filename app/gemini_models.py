"""Fetch and cache latest Gemini text/TTS models from the live API."""

from __future__ import annotations

import os
import re
import time
from typing import TypedDict

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BASE_API_URL = "https://generativelanguage.googleapis.com/v1beta"
MODELS_LIMIT = int(os.getenv("GEMINI_MODELS_LIMIT", "10"))
CACHE_TTL_SECONDS = int(os.getenv("GEMINI_MODELS_CACHE_TTL", "3600"))

TEXT_EXCLUDE = (
    "tts",
    "embedding",
    "image",
    "computer-use",
    "deep-research",
    "robotics",
    "lyria",
    "gemma",
    "antigravity",
    "nano-banana",
    "transcribe",
    "omni",
    "aqa",
    "clip",
    "customtools",
    "lite",
    "-latest",
)

TEXT_FALLBACK: list[dict[str, str]] = [
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "description": "Stable high-quality script generation",
    },
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "description": "Fast script generation",
    },
]

TTS_FALLBACK: list[dict[str, str]] = [
    {
        "id": "gemini-2.5-flash-preview-tts",
        "name": "Gemini 2.5 Flash TTS",
        "description": "Fast multi-speaker TTS",
    },
    {
        "id": "gemini-2.5-pro-preview-tts",
        "name": "Gemini 2.5 Pro TTS",
        "description": "High quality multi-speaker TTS",
    },
]


class ModelEntry(TypedDict):
    id: str
    name: str
    description: str


_cache: dict[str, object] = {
    "text": TEXT_FALLBACK,
    "tts": TTS_FALLBACK,
    "fetched_at": 0.0,
}


def _version_sort_key(model_id: str) -> tuple:
    """Numbered gemini-X.Y first (newest highest)."""
    m = re.search(r"gemini-(\d+)\.(\d+)", model_id)
    if m:
        major, minor = int(m.group(1)), int(m.group(2))
        tier = 2 if "pro" in model_id else (1 if "flash" in model_id else 0)
        return (1, major, minor, tier, model_id)
    m = re.search(r"gemini-(\d+)", model_id)
    if m:
        return (1, int(m.group(1)), 0, 0, model_id)
    return (0, 0, 0, 0, model_id)


def _is_podcast_text_model(model_id: str) -> bool:
    low = model_id.lower()
    if not low.startswith("gemini-"):
        return False
    return not any(token in low for token in TEXT_EXCLUDE)


def _is_tts_model(model_id: str) -> bool:
    return "tts" in model_id.lower()


def _to_model_info(raw: dict) -> ModelEntry:
    model_id = raw.get("name", "").split("/")[-1]
    display = raw.get("displayName") or model_id
    desc = raw.get("description") or f"Gemini model — {model_id}"
    if len(desc) > 200:
        desc = desc[:197] + "..."
    return {"id": model_id, "name": display, "description": desc}


def _fetch_from_api() -> tuple[list[ModelEntry], list[ModelEntry]]:
    if not GEMINI_API_KEY:
        return TEXT_FALLBACK[:MODELS_LIMIT], TTS_FALLBACK[:MODELS_LIMIT]

    url = f"{BASE_API_URL}/models"
    headers = {"x-goog-api-key": GEMINI_API_KEY}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    text_raw: list[dict] = []
    tts_raw: list[dict] = []

    for item in resp.json().get("models", []):
        methods = item.get("supportedGenerationMethods", [])
        if "generateContent" not in methods:
            continue
        model_id = item.get("name", "").split("/")[-1]
        if _is_tts_model(model_id):
            tts_raw.append(item)
        elif _is_podcast_text_model(model_id):
            text_raw.append(item)

    text_raw.sort(key=lambda m: _version_sort_key(m.get("name", "").split("/")[-1]), reverse=True)
    tts_raw.sort(key=lambda m: _version_sort_key(m.get("name", "").split("/")[-1]), reverse=True)

    text_models = [_to_model_info(m) for m in text_raw[:MODELS_LIMIT]]
    tts_models = [_to_model_info(m) for m in tts_raw[:MODELS_LIMIT]]

    if not text_models:
        text_models = TEXT_FALLBACK[:MODELS_LIMIT]
    if not tts_models:
        tts_models = TTS_FALLBACK[:MODELS_LIMIT]

    return text_models, tts_models


def refresh_models(force: bool = False) -> None:
    now = time.time()
    fetched_at = float(_cache.get("fetched_at", 0))
    if not force and now - fetched_at < CACHE_TTL_SECONDS:
        return

    try:
        text_models, tts_models = _fetch_from_api()
        _cache["text"] = text_models
        _cache["tts"] = tts_models
        _cache["fetched_at"] = now
    except Exception:
        if not _cache.get("text"):
            _cache["text"] = TEXT_FALLBACK[:MODELS_LIMIT]
        if not _cache.get("tts"):
            _cache["tts"] = TTS_FALLBACK[:MODELS_LIMIT]


def get_cache_fetched_at() -> float | None:
    fetched = _cache.get("fetched_at")
    if fetched and float(fetched) > 0:
        return float(fetched)
    return None


def get_text_models() -> list[ModelEntry]:
    refresh_models()
    return list(_cache["text"])  # type: ignore[arg-type]


def get_tts_models() -> list[ModelEntry]:
    refresh_models()
    return list(_cache["tts"])  # type: ignore[arg-type]


def get_default_text_model() -> str:
    models = get_text_models()
    return models[0]["id"] if models else "gemini-2.5-pro"


def get_default_tts_model() -> str:
    models = get_tts_models()
    return models[0]["id"] if models else "gemini-2.5-flash-preview-tts"


def validate_text_model(model_id: str) -> None:
    allowed = {m["id"] for m in get_text_models()}
    if model_id not in allowed:
        raise ValueError(f"Invalid text model '{model_id}'. Choose from: {sorted(allowed)}")


def validate_tts_model(model_id: str) -> None:
    allowed = {m["id"] for m in get_tts_models()}
    if model_id not in allowed:
        raise ValueError(f"Invalid TTS model '{model_id}'. Choose from: {sorted(allowed)}")
