import os
import json
import asyncio
import logging
import requests
from typing import Type, TypeVar, Optional, Any, Dict, Union
from pydantic import BaseModel, ValidationError
from utils.schema_adapter import pydantic_to_gemini_schema

# Initialize logger
logger = logging.getLogger(__name__)

# Define generic type for Pydantic models
T = TypeVar("T", bound=BaseModel)

import os
from dotenv import load_dotenv

load_dotenv()  # <-- THIS loads .env

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not found. "
        "Ensure .env exists at project root and is loaded."
    )
BASE_API_URL = "https://generativelanguage.googleapis.com/v1beta"

async def run_gemini_agent(
    instruction: Union[str, Any],
    user_input: Any,
    output_type: Optional[Type[T]] = None,
    model: str = "gemini-3-pro-preview",
    temperature: float = 0.7,
    retries: int = 2,
    initial_backoff: float = 2.0,
    campaign_id: Optional[str] = None
) -> Optional[T]:
    """
    Modular helper function to replace agent execution with direct Gemini API calls.
    
    This function mimics the logic of 'run_agent_with_retry' but bypasses the 
    intermediary Agent/Runner framework to call Gemini directly with structured outputs.
    It includes retry logic with exponential backoff.
    
    Args:
        instruction (Union[str, Any]): The system instruction used in the agent OR an Agent object.
        user_input (Any): The input data for the agent (dict, string, or Pydantic model).
        output_type (Optional[Type[T]]): The Pydantic model class defining the expected output schema. Required if instruction is str.
        model (str): The Gemini model to use (e.g., 'gemini-2.5-pro', 'gemini-3-pro-preview').
        temperature (float): Creativity control (default 0.7).
        retries (int): Number of retries on failure (default 2).
        initial_backoff (float): Initial backoff delay in seconds (default 2.0).
        campaign_id (Optional[str]): Campaign ID for logging/tracking (optional).

    Returns:
        Optional[T]: Parsed instance of output_type, or None if generation/validation fails after all retries.
    """
    
    # Handle Agent object passed as instruction
    real_instruction = instruction
    real_output_type = output_type

    if not isinstance(instruction, str) and hasattr(instruction, 'instructions') and hasattr(instruction, 'output_type'):
        # It's likely an Agent object
        real_instruction = instruction.instructions
        real_output_type = instruction.output_type
        # logger.info(f"Using Agent object: {getattr(instruction, 'name', 'Unknown')}")
    
    if real_output_type is None:
        logger.error("output_type is required when instruction is a string.")
        return None

    # 1. Convert user_input to string format
    if isinstance(user_input, BaseModel):
        input_text = user_input.model_dump_json(indent=2)
    elif isinstance(user_input, dict):
        input_text = json.dumps(user_input, indent=2)
    else:
        input_text = str(user_input)

    # 2. Generate Gemini-compatible schema from Pydantic model
    try:
        response_schema = pydantic_to_gemini_schema(real_output_type)
    except Exception as e:
        logger.error(f"Failed to generate schema for {real_output_type.__name__}: {e}")
        return None

    # 3. Construct API Endpoint and Headers
    # Using the model specified in the arguments
    generate_url = f"{BASE_API_URL}/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }

    # 4. Build Payload
    # We use 'system_instruction' for the agent prompt and 'contents' for the user input
    payload = {
        "system_instruction": {
            "parts": [{"text": real_instruction}]
        },
        "contents": [{
            "role": "user",
            "parts": [{"text": input_text}]
        }],
         "tools": [
      {
        "google_search": {}
      }
    ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": response_schema,
            "temperature": temperature
        }
    }

    # 5. Execute API Call with Retry Logic
    for attempt in range(retries + 1):
        json_content = None # To hold raw response for error logging
        try:
            # logger.info(f"Calling Gemini API model: {model} (Attempt {attempt + 1}/{retries + 1})...")
            response = await asyncio.to_thread(
                requests.post, generate_url, headers=headers, json=payload, timeout=300
            )
            response.raise_for_status()
            
            response_data = response.json()
            
            # Extract text from response
            candidates = response_data.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini API returned no candidates.")
            
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("Gemini API returned no content parts.")
            
            json_content = parts[0].get("text", "")
            
            # 6. Validate and Parse Result
            result = real_output_type.model_validate_json(json_content)
            return result

        except (requests.RequestException, ValueError, ValidationError, KeyError, IndexError) as e:
            if attempt < retries:
                wait_time = initial_backoff ** attempt
                logger.warning(f"Gemini agent execution failed (attempt {attempt+1}/{retries+1}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Gemini agent execution failed after {retries+1} attempts. Error: {e}")
                # Log detailed error info for debugging
                if isinstance(e, requests.HTTPError) and hasattr(e, 'response') and hasattr(e.response, 'text'):
                    logger.error(f"Error details: {e.response.text}")
                elif isinstance(e, ValidationError) and json_content:
                     logger.error(f"Raw content causing validation error: {json_content}")
                return None
        except Exception as e:
            # Catch-all for unexpected errors to ensure retry logic works for them too
            if attempt < retries:
                wait_time = initial_backoff ** attempt
                logger.warning(f"Unexpected error in Gemini agent (attempt {attempt+1}/{retries+1}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Unexpected error in Gemini agent execution: {e}")
                return None
                
    return None
