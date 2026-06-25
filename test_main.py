"""
test_main.py
CLI test runner for the podcast generation pipeline.
Run with: python test_main.py

Logs every stage in detail so you can debug failures quickly.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# ── Logging setup (must come before any project imports) ──────────────────────

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("test_run.log", mode="w", encoding="utf-8"),
    ],
)

# Silence overly verbose third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger("test_main")

# ── Project imports ───────────────────────────────────────────────────────────

from clients.elevenlabs_client import fetch_available_voices
from core.podcast_pipeline import (
    generate_script,
    build_speaker_voice_map,
    build_dialogue_turns,
    synthesise_audio,
)
from config import GEMINI_DEFAULT_MODEL, GEMINI_DEFAULT_TEMPERATURE


# ── Sample input ──────────────────────────────────────────────────────────────

SAMPLE_INPUT = """
Manus AI is a general-purpose AI agent introduced in early 2025 as a breakthrough
in autonomous artificial intelligence. Developed by the Chinese startup Monica.im,
Manus is designed to bridge the gap between "mind" and "hand" — it not only thinks
and plans like a large language model, but also executes complex tasks end-to-end
to deliver tangible results.

In benchmark evaluations for general AI agents, Manus AI has reportedly achieved
state-of-the-art results. On the GAIA test — a comprehensive benchmark assessing
an AI's ability to reason, use tools, and automate real-world tasks — Manus
outperformed leading models including OpenAI's GPT-4, setting a new performance
record previously held at 65%.

Unlike traditional chatbots that strictly provide information or suggestions,
Manus can plan solutions, invoke tools, and carry out multi-step procedures on
its own. For example, rather than just giving travel advice, Manus can autonomously
plan an entire trip itinerary, gather relevant information from the web, and present
a finalized plan to the user — all without step-by-step prompts.
"""

# ── Test configuration ────────────────────────────────────────────────────────

NUM_SPEAKERS   = 2
OUTPUT_MP3     = "test_output.mp3"
SCRIPT_JSON    = "test_script.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _separator(label: str) -> None:
    width = 72
    logger.info("=" * width)
    logger.info("  %s", label)
    logger.info("=" * width)


def _print_script_summary(script) -> None:
    logger.info("TITLE:       %s", script.title)
    logger.info("DESCRIPTION: %s", script.description)
    logger.info("STYLE:       %s", getattr(script, "podcast_style", ""))
    logger.info("TONE:        %s", getattr(script, "tone", ""))
    logger.info("INTERACTION: %s", getattr(script, "interaction_mode", ""))
    logger.info("SPEAKERS (%d):", len(script.speakers))
    for spk in script.speakers:
        role = getattr(spk, "role", "")
        logger.info("  %-20s  role=%-8s  voice_id=%s", spk.name, role, spk.voice_id)
    logger.info("DIALOGUE TURNS: %d", len(script.dialogue))
    for i, turn in enumerate(script.dialogue, 1):
        preview = turn.text[:80].replace("\n", " ")
        logger.info("  [%02d] %-15s: %s…", i, turn.speaker, preview)


# ── Test stages ───────────────────────────────────────────────────────────────

def test_fetch_voices() -> list[dict]:
    _separator("STAGE 1 — Fetch ElevenLabs voices")
    t0 = time.perf_counter()

    voices = fetch_available_voices()

    elapsed = time.perf_counter() - t0
    logger.info("Fetched %d voices in %.2fs", len(voices), elapsed)

    for v in voices[:5]:
        logger.debug(
            "  voice_id=%-26s  name=%-20s  desc=%s",
            v["voice_id"], v["name"], v["description"],
        )
    if len(voices) > 5:
        logger.debug("  … (%d more)", len(voices) - 5)

    assert voices, "No voices returned — check ELEVENLABS_API_KEY"
    return voices


async def test_generate_script(speaker_voices: list[dict]) -> object:
    _separator("STAGE 2 — Generate podcast script with Gemini")
    t0 = time.perf_counter()

    speaker_roles = ["Host", "Expert"] + ["Co-host"] * max(0, NUM_SPEAKERS - 2)
    script = await generate_script(
        input_text=SAMPLE_INPUT,
        speaker_voices=speaker_voices,
        num_speakers=NUM_SPEAKERS,
        speaker_roles=speaker_roles[:NUM_SPEAKERS],
        podcast_style="Interview",
        tone="Engaging",
        interaction_mode="Q/A",
        target_duration_min=10,
        model=GEMINI_DEFAULT_MODEL,
        temperature=GEMINI_DEFAULT_TEMPERATURE,
    )

    elapsed = time.perf_counter() - t0
    logger.info("Script generated in %.2fs", elapsed)
    _print_script_summary(script)

    # Save script to JSON for inspection
    out = Path(SCRIPT_JSON)
    out.write_text(
        json.dumps(script.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Script saved to %s", out.resolve())

    return script


def test_build_speaker_voice_map(script) -> dict[str, str]:
    _separator("STAGE 3 — Build speaker → voice map")

    mapping = build_speaker_voice_map(script)
    for name, vid in mapping.items():
        logger.info("  %-20s → %s", name, vid)

    assert len(mapping) == len(script.speakers), (
        f"Expected {len(script.speakers)} entries, got {len(mapping)}"
    )
    return mapping


def test_build_dialogue_turns(script, speaker_voice_map: dict) -> list[dict]:
    _separator("STAGE 4 — Build dialogue turns for ElevenLabs")

    turns = build_dialogue_turns(script, speaker_voice_map)
    logger.info("Built %d turns", len(turns))

    for i, t in enumerate(turns[:3], 1):
        logger.debug("  [%02d] voice_id=%-26s  text=%.60s…", i, t["voice_id"], t["text"])

    assert len(turns) == len(script.dialogue)
    return turns


def test_synthesise_audio(script, speaker_voice_map: dict) -> str:
    _separator("STAGE 5 — Synthesise audio with ElevenLabs")
    t0 = time.perf_counter()

    audio_path = synthesise_audio(
        script=script,
        speaker_voice_map=speaker_voice_map,
        output_path=OUTPUT_MP3,
    )

    elapsed = time.perf_counter() - t0
    size_kb = Path(audio_path).stat().st_size / 1024
    logger.info("Audio synthesised in %.2fs  —  %.1f KB  —  %s", elapsed, size_kb, audio_path)

    assert Path(audio_path).exists(), f"MP3 not found at {audio_path}"
    assert size_kb > 0, "MP3 is empty"
    return audio_path


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    """Run a full end-to-end pipeline test with verbose logging."""
    _separator("PODCAST PIPELINE — TEST RUN")
    total_start = time.perf_counter()

    try:
        # Stage 1: voices
        all_voices = test_fetch_voices()

        # Pick the first N voices for the test
        speaker_voices = all_voices[:NUM_SPEAKERS]
        print(speaker_voices)
        logger.info(
            "Using voices for test: %s",
            [f"{v['name']} ({v['voice_id']})" for v in speaker_voices],
        )

        # Stage 2: script generation
        script = await test_generate_script(speaker_voices)

        # Stage 3: speaker → voice map
        speaker_voice_map = test_build_speaker_voice_map(script)

        # Stage 4: dialogue turns
        test_build_dialogue_turns(script, speaker_voice_map)

        # Stage 5: audio synthesis
        # audio_path = test_synthesise_audio(script, speaker_voice_map)

        total = time.perf_counter() - total_start
        _separator("ALL STAGES PASSED ✅")
        logger.info("Total time: %.2fs", total)
        # logger.info("MP3 output: %s", audio_path)
        logger.info("Script JSON: %s", Path(SCRIPT_JSON).resolve())
        logger.info("Full log: %s", Path("test_run.log").resolve())

    except AssertionError as exc:
        logger.error("ASSERTION FAILED: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("PIPELINE FAILED: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())