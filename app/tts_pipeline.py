"""Chunked multi-speaker TTS and WAV concatenation."""

from __future__ import annotations

import logging
import wave
from pathlib import Path
from typing import Dict, Sequence

from google_tts import MultiSpeakerTTS
from schemas import DialogueTurn, PodcastScript

logger = logging.getLogger(__name__)

# Soft budget for spoken dialogue text per TTS request (chars of "Speaker: text" lines).
TTS_CHUNK_CHAR_BUDGET = 3500


def split_dialogue_into_chunks(
    dialogue: Sequence[DialogueTurn],
    *,
    max_chars: int = TTS_CHUNK_CHAR_BUDGET,
) -> list[list[DialogueTurn]]:
    """Split turns into chunks under a char budget; never split mid-turn."""
    if not dialogue:
        return []

    chunks: list[list[DialogueTurn]] = []
    current: list[DialogueTurn] = []
    current_len = 0

    for turn in dialogue:
        line = f"{turn.speaker}: {turn.text}"
        line_len = len(line) + (1 if current else 0)  # newline between turns
        if current and current_len + line_len > max_chars:
            chunks.append(current)
            current = [turn]
            current_len = len(line)
        else:
            current.append(turn)
            current_len += line_len

    if current:
        chunks.append(current)
    return chunks


def build_tts_prompt(speaker_names: Sequence[str], turns: Sequence[DialogueTurn]) -> str:
    dialogue_text = "\n".join(f"{turn.speaker}: {turn.text}" for turn in turns)
    return (
        f"TTS the following conversation between "
        f"{', '.join(speaker_names)}:\n{dialogue_text}"
    )


def concat_wav_files(input_paths: Sequence[Path], output_path: Path) -> None:
    """Concatenate PCM WAV files with identical format into one file."""
    if not input_paths:
        raise ValueError("No WAV files to concatenate")

    params = None
    frames: list[bytes] = []
    for path in input_paths:
        with wave.open(str(path), "rb") as wf:
            p = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
            if params is None:
                params = p
            elif p != params:
                raise ValueError(
                    f"WAV format mismatch: {path} has {p}, expected {params}"
                )
            frames.append(wf.readframes(wf.getnframes()))

    assert params is not None
    channels, sample_width, rate = params
    with wave.open(str(output_path), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(sample_width)
        out.setframerate(rate)
        for chunk in frames:
            out.writeframes(chunk)


def generate_podcast_audio(
    script: PodcastScript,
    speaker_voice_map: Dict[str, str],
    tts_model: str,
    output_file: str | Path,
    *,
    work_dir: str | Path | None = None,
) -> dict:
    """
    Generate TTS for the full script, chunking when needed, and write one WAV.
    Returns aggregated token metadata.
    """
    output_path = Path(output_file)
    work = Path(work_dir) if work_dir else output_path.parent
    work.mkdir(parents=True, exist_ok=True)

    chunks = split_dialogue_into_chunks(script.dialogue)
    if not chunks:
        raise RuntimeError("Script has no dialogue to synthesize")

    speaker_names = list(speaker_voice_map.keys())
    tts = MultiSpeakerTTS()
    chunk_paths: list[Path] = []
    total_in = 0
    total_out = 0
    total_all = 0

    try:
        for i, turns in enumerate(chunks):
            chunk_path = work / f"{output_path.stem}_chunk_{i}.wav"
            prompt = build_tts_prompt(speaker_names, turns)
            logger.info(
                "TTS chunk %s/%s (%s turns, %s chars)",
                i + 1,
                len(chunks),
                len(turns),
                len(prompt),
            )
            result = tts.generate_tts(
                dialogue=prompt,
                speaker_voice_map=speaker_voice_map,
                tts_model=tts_model,
                output_file=str(chunk_path),
            )
            if not chunk_path.exists():
                raise RuntimeError(f"Audio generation failed for chunk {i + 1}")
            chunk_paths.append(chunk_path)
            total_in += result.get("input_tokens") or 0
            total_out += result.get("output_tokens") or 0
            total_all += result.get("total_tokens") or 0

        if len(chunk_paths) == 1:
            chunk_paths[0].replace(output_path)
        else:
            concat_wav_files(chunk_paths, output_path)

        if not output_path.exists():
            raise RuntimeError("Audio generation failed — no output file")

        return {
            "output_file": str(output_path),
            "input_tokens": total_in,
            "output_tokens": total_out,
            "total_tokens": total_all,
            "tts_chunks": len(chunks),
        }
    finally:
        for path in chunk_paths:
            if path.exists() and path.resolve() != output_path.resolve():
                path.unlink(missing_ok=True)
