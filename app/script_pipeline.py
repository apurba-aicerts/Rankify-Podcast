"""Outline-then-script generation: length follows source information density."""

from __future__ import annotations

import json
import logging
from typing import Optional

from gemini_client import run_gemini_agent
from podcast_prompts import (
    outline_system_instruction,
    podcast_system_instruction,
    section_script_system_instruction,
)
from schemas import (
    OutlineSection,
    PodcastOutline,
    PodcastScript,
    Speaker,
)

logger = logging.getLogger(__name__)

MAX_ONE_SHOT_POINTS = 12
MAX_ONE_SHOT_SECTIONS = 6
MAX_ONE_SHOT_SOURCE_CHARS = 24_000
OUTLINE_TEMPERATURE = 0.3
SECTION_WINDOW_CHARS = 12_000


class ScriptGenerationError(Exception):
    """Raised when script generation cannot produce a usable result."""


def outline_point_count(outline: PodcastOutline) -> int:
    return sum(len(section.points) for section in outline.sections)


def should_generate_sectionally(outline: PodcastOutline, source_text: str) -> bool:
    """Engineering routing: one call vs per-section (not a duration target)."""
    points = outline_point_count(outline)
    if points > MAX_ONE_SHOT_POINTS:
        return True
    if len(outline.sections) > MAX_ONE_SHOT_SECTIONS:
        return True
    if len(source_text) > MAX_ONE_SHOT_SOURCE_CHARS:
        return True
    return False


def _extract_section_window(source_text: str, section: OutlineSection) -> str:
    """Best-effort slice of source around section title / point hints."""
    text = source_text
    lower = text.lower()
    anchors: list[str] = []
    if section.title.strip():
        anchors.append(section.title.strip())
    for point in section.points:
        hint = (point.source_hint or "").strip()
        if hint and hint.lower() not in {a.lower() for a in anchors}:
            anchors.append(hint)

    best_idx: Optional[int] = None
    for anchor in anchors:
        idx = lower.find(anchor.lower())
        if idx >= 0 and (best_idx is None or idx < best_idx):
            best_idx = idx

    if best_idx is None:
        return text

    start = max(0, best_idx - 500)
    end = min(len(text), start + SECTION_WINDOW_CHARS)
    # Prefer extending forward from the anchor when near the end.
    if end - best_idx < SECTION_WINDOW_CHARS // 2:
        start = max(0, end - SECTION_WINDOW_CHARS)
    return text[start:end]


def _merge_scripts(
    outline: PodcastOutline,
    parts: list[PodcastScript],
    speakers: list[Speaker],
) -> PodcastScript:
    dialogue = []
    for part in parts:
        dialogue.extend(part.dialogue)
    description = ""
    if parts:
        description = parts[0].description or ""
    if not description and outline.sections:
        description = f"Coverage of: {', '.join(s.title for s in outline.sections[:5])}"
    return PodcastScript(
        title=outline.title,
        description=description,
        speakers=speakers,
        dialogue=dialogue,
    )


async def generate_podcast_script_from_text(
    input_text: str,
    num_speakers: int,
    voice_list: list[str],
    text_model: str,
    temperature: float,
) -> PodcastScript:
    """
    Outline → one-shot or sectional script writing.
    Raises ScriptGenerationError on failure / empty outline.
    """
    outline = await run_gemini_agent(
        instruction=outline_system_instruction(),
        user_input=input_text,
        output_type=PodcastOutline,
        model=text_model,
        temperature=OUTLINE_TEMPERATURE,
    )
    if outline is None:
        raise ScriptGenerationError("Outline generation failed")

    points = outline_point_count(outline)
    if points == 0:
        raise ScriptGenerationError("No usable content in source")

    logger.info(
        "Outline ready: %s sections, %s points, source_chars=%s, sectional=%s",
        len(outline.sections),
        points,
        len(input_text),
        should_generate_sectionally(outline, input_text),
    )

    if not should_generate_sectionally(outline, input_text):
        user_payload = {
            "coverage_outline": outline.model_dump(),
            "source_material": input_text,
        }
        script = await run_gemini_agent(
            instruction=podcast_system_instruction(num_speakers, voice_list),
            user_input=user_payload,
            output_type=PodcastScript,
            model=text_model,
            temperature=temperature,
        )
        if script is None:
            raise ScriptGenerationError("Podcast script generation failed")
        return script

    # Sectional path
    established_speakers: list[Speaker] | None = None
    parts: list[PodcastScript] = []
    for index, section in enumerate(outline.sections):
        if not section.points:
            continue
        window = _extract_section_window(input_text, section)
        continuity = ""
        if established_speakers:
            continuity = (
                "Established speakers (keep names and voice_ids): "
                + json.dumps([s.model_dump() for s in established_speakers])
            )
            if parts:
                last_lines = parts[-1].dialogue[-2:]
                if last_lines:
                    continuity += "\nRecent turns:\n" + "\n".join(
                        f"{t.speaker}: {t.text}" for t in last_lines
                    )

        payload = {
            "section_index": index + 1,
            "section_count": len(outline.sections),
            "episode_title": outline.title,
            "section_outline": section.model_dump(),
            "section_source": window,
        }
        part = await run_gemini_agent(
            instruction=section_script_system_instruction(
                num_speakers, voice_list, continuity_note=continuity
            ),
            user_input=payload,
            output_type=PodcastScript,
            model=text_model,
            temperature=temperature,
        )
        if part is None:
            raise ScriptGenerationError(
                f"Podcast script generation failed for section '{section.title}'"
            )
        if established_speakers is None:
            established_speakers = part.speakers
        else:
            # Normalize to first section's speakers for TTS consistency.
            name_map = {
                part.speakers[i].name: established_speakers[i].name
                for i in range(min(len(part.speakers), len(established_speakers)))
            }
            for turn in part.dialogue:
                turn.speaker = name_map.get(turn.speaker, turn.speaker)
            part.speakers = established_speakers
        parts.append(part)

    if not parts or established_speakers is None:
        raise ScriptGenerationError("Podcast script generation failed")

    return _merge_scripts(outline, parts, established_speakers)
