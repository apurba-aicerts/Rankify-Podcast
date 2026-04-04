"""
core/podcast_pipeline.py
Orchestrates the full podcast generation pipeline:
  1. Generate PodcastScript via Gemini
  2. Build a speaker → voice_id map from the script
  3. Flatten script into dialogue turns for ElevenLabs
  4. Synthesise and write the MP3
"""

import logging

from schemas.podcast_schema import PodcastScript
from prompts.podcast_prompt import build_podcast_prompt
from clients.gemini_client import run_gemini_agent
from clients.elevenlabs_client import generate_audio
from config import (
    GEMINI_DEFAULT_MODEL,
    GEMINI_DEFAULT_TEMPERATURE,
    GEMINI_DEFAULT_RETRIES,
    ELEVENLABS_DEFAULT_OUTPUT,
)

logger = logging.getLogger(__name__)


# ── Step 1: Generate script ───────────────────────────────────────────────────

async def generate_script(
    input_text: str,
    speaker_voices: list[dict],
    num_speakers: int,
    model: str = GEMINI_DEFAULT_MODEL,
    temperature: float = GEMINI_DEFAULT_TEMPERATURE,
    retries: int = GEMINI_DEFAULT_RETRIES,
) -> PodcastScript:
    """
    Generate a PodcastScript from raw input text using the Gemini API.

    Args:
        input_text:     Raw content to convert into a podcast conversation.
        speaker_voices: List of voice dicts (voice_id, name, description)
                        — one per speaker, in the order assigned to speakers.
        num_speakers:   Number of speakers the script must contain.
        model:          Gemini model name.
        temperature:    Generation temperature.
        retries:        Number of retry attempts on LLM failure.

    Returns:
        Validated PodcastScript instance.

    Raises:
        RuntimeError: If Gemini fails after all retries.
    """
    logger.info(
        "Generating podcast script — speakers=%d  model=%s  temperature=%.2f",
        num_speakers, model, temperature,
    )

    system_instruction = build_podcast_prompt(
        num_speakers=num_speakers,
        speaker_voices=speaker_voices,
    )

    script = await run_gemini_agent(
        system_instruction=system_instruction,
        user_input=input_text,
        output_type=PodcastScript,
        model=model,
        temperature=temperature,
        retries=retries,
    )

    logger.info(
        "Script generated — title=%r  speakers=%s  turns=%d",
        script.title,
        [s.name for s in script.speakers],
        len(script.dialogue),
    )
    return script


# ── Step 2: Build speaker → voice_id map ─────────────────────────────────────

def build_speaker_voice_map(script: PodcastScript) -> dict[str, str]:
    """
    Extract a {speaker_name: voice_id} mapping directly from the script.

    The mapping is built from script.speakers, which Gemini populates with the
    voice_id values provided in the prompt. This is O(n) over the speakers list.

    Args:
        script: A validated PodcastScript.

    Returns:
        Dict mapping each speaker's name to their ElevenLabs voice_id.
    """
    mapping = {speaker.name: speaker.voice_id for speaker in script.speakers}
    logger.debug("Speaker → voice map: %s", mapping)
    return mapping


# ── Step 3: Flatten dialogue turns for ElevenLabs ────────────────────────────

def build_dialogue_turns(
    script: PodcastScript,
    speaker_voice_map: dict[str, str],
) -> list[dict]:
    """
    Flatten PodcastScript dialogue into a list of {text, voice_id} dicts
    ready for the ElevenLabs text_to_dialogue API.

    Args:
        script:             Validated PodcastScript.
        speaker_voice_map:  Output of build_speaker_voice_map().

    Returns:
        List of dicts with 'text' and 'voice_id' keys.

    Raises:
        ValueError: If a speaker in the dialogue has no voice mapping.
    """
    turns = []
    for turn in script.dialogue:
        voice_id = speaker_voice_map.get(turn.speaker)
        if not voice_id:
            raise ValueError(
                f"No voice_id found for speaker '{turn.speaker}'. "
                f"Known speakers: {list(speaker_voice_map.keys())}"
            )
        turns.append({"text": turn.text, "voice_id": voice_id})

    logger.debug("Built %d dialogue turns for ElevenLabs.", len(turns))
    return turns


# ── Step 4: Synthesise audio ──────────────────────────────────────────────────

def synthesise_audio(
    script: PodcastScript,
    speaker_voice_map: dict[str, str],
    output_path: str = ELEVENLABS_DEFAULT_OUTPUT,
) -> str:
    """
    Convert a PodcastScript into an MP3 file using ElevenLabs.

    Args:
        script:            Validated PodcastScript.
        speaker_voice_map: Output of build_speaker_voice_map().
        output_path:       Destination file path for the MP3.

    Returns:
        Absolute path to the written MP3 file.
    """
    logger.info("Starting audio synthesis — output=%s", output_path)

    dialogue_turns = build_dialogue_turns(script, speaker_voice_map)
    audio_path = generate_audio(dialogue_turns, output_path=output_path)

    logger.info("Audio synthesis complete — file=%s", audio_path)
    return audio_path


# ── Full pipeline (convenience wrapper) ──────────────────────────────────────

async def run_podcast_pipeline(
    input_text: str,
    speaker_voices: list[dict],
    num_speakers: int,
    output_path: str = ELEVENLABS_DEFAULT_OUTPUT,
    model: str = GEMINI_DEFAULT_MODEL,
    temperature: float = GEMINI_DEFAULT_TEMPERATURE,
) -> tuple[PodcastScript, str]:
    """
    Run the complete podcast pipeline end-to-end.

    Args:
        input_text:     Raw source content.
        speaker_voices: Voice dicts (voice_id, name, description) per speaker.
        num_speakers:   Number of speakers.
        output_path:    MP3 output path.
        model:          Gemini model name.
        temperature:    Generation temperature.

    Returns:
        Tuple of (PodcastScript, mp3_file_path).
    """
    logger.info("=== Podcast pipeline START ===")

    script           = await generate_script(input_text, speaker_voices, num_speakers, model, temperature)
    speaker_voice_map = build_speaker_voice_map(script)
    audio_path       = synthesise_audio(script, speaker_voice_map, output_path)

    logger.info("=== Podcast pipeline COMPLETE — audio=%s ===", audio_path)
    return script, audio_path