"""
clients/gemini_client.py
Direct Gemini API client with structured JSON output and retry logic.
"""

import asyncio
import json
import logging
import os
from typing import Any, Optional, Type, TypeVar, Union
from schemas.schema_adapter import pydantic_to_gemini_schema
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from config import (
    GEMINI_BASE_URL,
    GEMINI_DEFAULT_MODEL,
    GEMINI_DEFAULT_RETRIES,
    GEMINI_DEFAULT_TEMPERATURE,
    GEMINI_INITIAL_BACKOFF,
    GEMINI_REQUEST_TIMEOUT,
)

load_dotenv()

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ── Internal: load API key ────────────────────────────────────────────────────

def _get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not found. "
            "Ensure .env exists at the project root and contains GEMINI_API_KEY."
        )
    return key

# def _pydantic_to_gemini_schema(model_class: Type[BaseModel]) -> dict:
#     """
#     Convert a Pydantic model's JSON schema to a Gemini-compatible schema dict.
#     Recursively strips 'title' and 'default' keys that Gemini rejects.
#     """
#     raw = model_class.model_json_schema()

#     def _clean(node: Any) -> Any:
#         if isinstance(node, dict):
#             return {
#                 k: _clean(v)
#                 for k, v in node.items()
#                 if k not in ("title", "default", "$defs")
#             }
#         if isinstance(node, list):
#             return [_clean(item) for item in node]
#         return node

#     schema = _clean(raw)

#     # Gemini requires explicit type at root
#     schema.setdefault("type", "object")
#     return schema


# ── Public API ────────────────────────────────────────────────────────────────

async def run_gemini_agent(
    system_instruction: str,
    user_input: Union[str, dict, BaseModel],
    output_type: Type[T],
    model: str = GEMINI_DEFAULT_MODEL,
    temperature: float = GEMINI_DEFAULT_TEMPERATURE,
    retries: int = GEMINI_DEFAULT_RETRIES,
    initial_backoff: float = GEMINI_INITIAL_BACKOFF,
) -> T:
    """
    Call the Gemini API with a system instruction and user input, returning
    a validated Pydantic model instance.

    Args:
        system_instruction: System prompt string.
        user_input:         Input data — string, dict, or Pydantic model.
        output_type:        Pydantic model class that defines the expected schema.
        model:              Gemini model name.
        temperature:        Generation temperature (0.0–1.0).
        retries:            Number of retry attempts on failure.
        initial_backoff:    Base backoff in seconds (doubles each retry).

    Returns:
        Validated instance of output_type.

    Raises:
        RuntimeError: If all retry attempts fail.
    """
    api_key = _get_api_key()

    # ── Serialise user input ──────────────────────────────────────────────────
    if isinstance(user_input, BaseModel):
        input_text = user_input.model_dump_json(indent=2)
    elif isinstance(user_input, dict):
        input_text = json.dumps(user_input, indent=2)
    else:
        input_text = str(user_input)

    # ── Build Gemini schema ───────────────────────────────────────────────────
    try:
        response_schema = pydantic_to_gemini_schema(output_type)
        # print(f"Generated Gemini schema for {output_type.__name__}:\n{json.dumps(response_schema, indent=2)}")
        logger.debug("Generated Gemini schema for %s", output_type.__name__)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to build Gemini schema for {output_type.__name__}: {exc}"
        ) from exc

    # ── Build request ─────────────────────────────────────────────────────────
    url = f"{GEMINI_BASE_URL}/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": input_text}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": response_schema,
            "temperature": temperature,
        },
    }
    # print(f"Payload for Gemini request:\n{json.dumps(payload, indent=2)}")
    # ── Retry loop ────────────────────────────────────────────────────────────
    last_error: Exception = RuntimeError("Unknown error")

    for attempt in range(retries + 1):
        raw_text: Optional[str] = None
        try:
            logger.info(
                "Gemini request — model=%s  attempt=%d/%d",
                model, attempt + 1, retries + 1,
            )

            response = await asyncio.to_thread(
                requests.post,
                url,
                headers=headers,
                json=payload,
                timeout=GEMINI_REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()

            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini returned no candidates.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("Gemini returned no content parts.")

            raw_text = parts[0].get("text", "")

            # ── Log token usage ───────────────────────────────────────────────
            usage = data.get("usageMetadata", {})
            prompt_tokens     = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)
            thoughts_tokens   = usage.get("thoughtsTokenCount", 0)
            total_tokens      = usage.get("totalTokenCount", 0)
            model_version     = data.get("modelVersion", model)

            logger.info(
                "Gemini usage — model=%s  prompt=%d  completion=%d  "
                "thoughts=%d  total=%d",
                model_version, prompt_tokens, completion_tokens,
                thoughts_tokens, total_tokens,
            )

            # ── Validate response ─────────────────────────────────────────────
            result = output_type.model_validate_json(raw_text)
            logger.info("Gemini response validated successfully.")
            return result

        except (requests.RequestException, ValueError, ValidationError, KeyError, IndexError) as exc:
            last_error = exc
            if isinstance(exc, ValidationError) and raw_text:
                logger.warning(
                    "Validation error (attempt %d). Raw content:\n%s",
                    attempt + 1, raw_text[:500],
                )
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                logger.warning(
                    "HTTP error (attempt %d): %s — %s",
                    attempt + 1, exc, exc.response.text[:300],
                )
            else:
                logger.warning("Gemini error (attempt %d): %s", attempt + 1, exc)

        if attempt < retries:
            wait = initial_backoff * (2 ** attempt)
            logger.info("Retrying in %.1f seconds…", wait)
            await asyncio.sleep(wait)

    raise RuntimeError(
        f"Gemini agent failed after {retries + 1} attempts. "
        f"Last error: {last_error}"
    )