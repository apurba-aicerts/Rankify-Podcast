"""
clients/elevenlabs_client.py
ElevenLabs API client — voice discovery and multi-speaker audio synthesis.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs import ElevenLabs, DialogueInput

from config import ELEVENLABS_DEFAULT_OUTPUT

load_dotenv()

logger = logging.getLogger(__name__)


# ── Internal: build client ────────────────────────────────────────────────────

def _get_client() -> ElevenLabs:
    """Create an authenticated ElevenLabs client from `ELEVENLABS_API_KEY`."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY not found. "
            "Ensure .env exists at the project root and contains ELEVENLABS_API_KEY."
        )
    return ElevenLabs(api_key=api_key)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_available_voices() -> list[dict]:
    """
    Fetch all available voices from the ElevenLabs API.

    Returns:
        List of dicts, each containing:
            - voice_id    (str)
            - name        (str)  e.g. "Brian"
            - description (str)  e.g. "Deep, Resonant and Comforting"
            - category    (str)  e.g. "premade"
            - labels      (dict) raw labels from ElevenLabs
            - preview_url (str)  URL for a voice preview clip
    """
    client = _get_client()
    logger.info("Fetching available voices from ElevenLabs…")

    response = client.voices.get_all()
    voices = []

    for voice in response.voices:
        # name_parts = voice.name.split(" - ", 1)
        # friendly_name  = name_parts[0].strip()
        # description    = name_parts[1].strip() if len(name_parts) > 1 else ""

        voices.append({
            "voice_id":    voice.voice_id,
            "name":        voice.name,
            "description": voice.description,
            "category":    voice.category or "",
            "labels":      dict(voice.labels) if voice.labels else {},
            "preview_url": voice.preview_url or "",
        })

    logger.info("Fetched %d voices from ElevenLabs.", len(voices))
    return voices


def generate_audio(
    dialogue_turns: list[dict],
    output_path: str = ELEVENLABS_DEFAULT_OUTPUT,
) -> str:
    """
    Synthesise multi-speaker audio from a list of dialogue turns.

    Args:
        dialogue_turns:  List of dicts, each with:
                           - text      (str) what the speaker says
                           - voice_id  (str) ElevenLabs voice ID for this turn
        output_path:     File path for the output MP3.

    Returns:
        Absolute path to the written MP3 file.

    Raises:
        ValueError:   If any turn is missing 'text' or 'voice_id'.
        RuntimeError: If the ElevenLabs API call fails.
    """
    client = _get_client()

    # ── Validate and build DialogueInput list ─────────────────────────────────
    inputs: list[DialogueInput] = []
    for i, turn in enumerate(dialogue_turns):
        text     = turn.get("text", "").strip()
        voice_id = turn.get("voice_id", "").strip()

        if not text:
            raise ValueError(f"Turn {i} has empty 'text'.")
        if not voice_id:
            raise ValueError(f"Turn {i} has empty 'voice_id'.")

        inputs.append(DialogueInput(text=text, voice_id=voice_id))

    logger.info(
        "Sending %d dialogue turns to ElevenLabs text_to_dialogue…", len(inputs)
    )

    # ── Call ElevenLabs ───────────────────────────────────────────────────────
    try:
        audio_stream = client.text_to_dialogue.convert(inputs=inputs)
    except Exception as exc:
        raise RuntimeError(f"ElevenLabs audio generation failed: {exc}") from exc

    # ── Write MP3 ─────────────────────────────────────────────────────────────
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    bytes_written = 0
    with open(output, "wb") as f:
        for chunk in audio_stream:
            if isinstance(chunk, bytes):
                f.write(chunk)
                bytes_written += len(chunk)

    logger.info(
        "Audio written to %s  (%.1f KB)", output.resolve(), bytes_written / 1024
    )
    return str(output.resolve())