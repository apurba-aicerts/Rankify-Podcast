import asyncio
import json
import logging
import os
from typing import Any, Optional, Type, TypeVar, Union

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from schema_adapter import pydantic_to_gemini_schema
from schemas import PodcastScript

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not found. Ensure .env exists and is loaded."
    )

BASE_API_URL = "https://generativelanguage.googleapis.com/v1beta"


async def run_gemini_agent(
    instruction: Union[str, Any],
    user_input: Any,
    output_type: Optional[Type[T]] = None,
    model: str = "gemini-2.5-pro",
    temperature: float = 0.7,
    retries: int = 2,
    initial_backoff: float = 2.0,
) -> Optional[T]:
    real_instruction = instruction
    real_output_type = output_type

    if (
        not isinstance(instruction, str)
        and hasattr(instruction, "instructions")
        and hasattr(instruction, "output_type")
    ):
        real_instruction = instruction.instructions
        real_output_type = instruction.output_type

    if real_output_type is None:
        logger.error("output_type is required when instruction is a string.")
        return None

    if isinstance(user_input, BaseModel):
        input_text = user_input.model_dump_json(indent=2)
    elif isinstance(user_input, dict):
        input_text = json.dumps(user_input, indent=2)
    else:
        input_text = str(user_input)

    try:
        response_schema = pydantic_to_gemini_schema(real_output_type)
    except Exception as exc:
        logger.error("Failed to generate schema for %s: %s", real_output_type.__name__, exc)
        return None

    generate_url = f"{BASE_API_URL}/models/{model}:generateContent"
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    payload = {
        "system_instruction": {"parts": [{"text": real_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": input_text}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": response_schema,
            "temperature": temperature,
            "maxOutputTokens": 65536,
        },
    }

    json_content = None
    for attempt in range(retries + 1):
        try:
            response = await asyncio.to_thread(
                requests.post, generate_url, headers=headers, json=payload, timeout=300
            )
            response.raise_for_status()
            response_data = response.json()

            candidates = response_data.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini API returned no candidates.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("Gemini API returned no content parts.")

            json_content = parts[0].get("text", "")
            return real_output_type.model_validate_json(json_content)

        except (requests.RequestException, ValueError, ValidationError, KeyError, IndexError) as exc:
            if attempt < retries:
                wait_time = initial_backoff**attempt
                logger.warning(
                    "Gemini call failed (attempt %s/%s): %s. Retrying in %ss...",
                    attempt + 1,
                    retries + 1,
                    exc,
                    wait_time,
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error("Gemini call failed after %s attempts: %s", retries + 1, exc)
                if isinstance(exc, ValidationError) and json_content:
                    logger.error("Raw content: %s", json_content)
                return None
        except Exception as exc:
            if attempt < retries:
                await asyncio.sleep(initial_backoff**attempt)
            else:
                logger.error("Unexpected Gemini error: %s", exc)
                return None

    return None


def build_speaker_voice_mapping(script: PodcastScript) -> dict[str, str]:
    speaker_voice_mapping: dict[str, str] = {}
    voice_index = 0
    num_speakers = len(script.speakers)

    for turn in script.dialogue:
        speaker = turn.speaker
        if speaker not in speaker_voice_mapping:
            speaker_voice_mapping[speaker] = script.speakers[voice_index].voice_id
            voice_index += 1
            if voice_index == num_speakers:
                break

    return speaker_voice_mapping
