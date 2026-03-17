"""
FastAPI backend for Podcast Generation MVP

Endpoints:
- GET /voices - Available voices with sample URLs
- GET /tts-models - Available TTS models
- POST /generate-podcast - Generate podcast from text

Authentication: x-api-key header

Audio Storage: AWS S3 with presigned URLs
"""

import os
import sys
import io
import uuid
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from schemas.podcast import PodcastScript
from prompts.podcast import podcast_system_instruction, voices as VOICE_DESCRIPTIONS
from core.gemini_client import run_gemini_agent, build_speaker_voice_mapping
from audio.google_tts import MultiSpeakerTTS

# Add parent directory to path so we can import helpers
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from helpers.s3_helper import (
    upload_file as s3_upload_file,
    generate_presigned_url as s3_presigned_url,
    delete_objects_older_than as s3_cleanup_old,
)

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

API_KEY = os.getenv("X_API_KEY", "dev-api-key-12345")  # Set in production

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_SAMPLE_DIR = os.path.join(BASE_DIR, "audio", "assets", "voice_samples")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# Ensure output directory exists (still used as temp dir before S3 upload)
os.makedirs(OUTPUT_DIR, exist_ok=True)

AVAILABLE_VOICES = [
    "achernar", "achird", "algenib", "algieba", "alnilam",
    "aoede", "autonoe", "callirrhoe", "charon", "despina",
    "enceladus", "erinome", "fenrir", "gacrux", "iapetus",
    "kore", "laomedeia", "leda", "orus", "puck",
    "pulcherrima", "rasalgethi", "sadachbia", "sadaltager",
    "schedar", "sulafat", "umbriel", "vindemiatrix",
    "zephyr", "zubenelgenubi",
]

TTS_MODELS = [
    {
        "id": "gemini-2.5-flash-preview-tts",
        "name": "Gemini 2.5 Flash TTS",
        "description": "Fast TTS model, good for quick generation"
    },
    {
        "id": "gemini-2.5-pro-preview-tts",
        "name": "Gemini 2.5 Pro TTS",
        "description": "High quality TTS model, better for production"
    }
]

TEXT_MODELS = [
    {
        "id": "gemini-3-pro-preview",
        "name": "Gemini 3 Pro Preview",
        "description": "Latest Gemini model for script generation"
    }
]


# ------------------------------------------------------------------
# S3 Cleanup Configuration
# ------------------------------------------------------------------
S3_CLEANUP_INTERVAL_MINUTES = 30  # Run cleanup every 15 minutes
S3_OBJECT_TTL_HOURS = 1           # Delete podcast files older than 1 hour


# ------------------------------------------------------------------
# Lifespan & App Setup
# ------------------------------------------------------------------

async def _periodic_s3_cleanup():
    """
    Background coroutine that periodically deletes S3 podcast objects
    older than S3_OBJECT_TTL_HOURS. Runs every S3_CLEANUP_INTERVAL_MINUTES.
    """
    while True:
        await asyncio.sleep(S3_CLEANUP_INTERVAL_MINUTES * 60)
        try:
            deleted = await asyncio.to_thread(
                s3_cleanup_old, S3_OBJECT_TTL_HOURS
            )
            if deleted:
                print(f"🧹 S3 cleanup: deleted {deleted} podcast file(s) older than {S3_OBJECT_TTL_HOURS}h")
        except Exception as e:
            print(f"⚠️  S3 cleanup error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Podcast API starting up...")
    # Launch periodic S3 cleanup task
    cleanup_task = asyncio.create_task(_periodic_s3_cleanup())
    print(f"🧹 S3 cleanup scheduled: every {S3_CLEANUP_INTERVAL_MINUTES}min, TTL {S3_OBJECT_TTL_HOURS}h")
    yield
    # Shutdown – cancel the background cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    print("🛑 Podcast API shutting down...")


app = FastAPI(
    title="Rankify Podcast API",
    description="API for generating multi-speaker podcast audio from text (S3-backed storage)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration for React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # Allow all for MVP - restrict in production
    ],
    allow_credentials=False,  # Must be False when allow_origins includes "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Podcast-Title",
        "X-Job-Id",
        "Content-Disposition",
    ],
)


# ------------------------------------------------------------------
# Authentication Dependency
# ------------------------------------------------------------------

async def verify_api_key(x_api_key: str = Header(..., alias="x-api-key")):
    """
    Simple API key verification for MVP.
    Replace with JWT or proper auth in production.
    """
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return x_api_key


# ------------------------------------------------------------------
# Pydantic Models for API
# ------------------------------------------------------------------

class VoiceInfo(BaseModel):
    id: str = Field(description="Voice identifier")
    name: str = Field(description="Display name (capitalized)")
    description: str = Field(description="Voice characteristics")
    sample_url: str = Field(description="URL to voice sample audio")
    sample_available: bool = Field(description="Whether sample file exists")


class VoicesResponse(BaseModel):
    voices: List[VoiceInfo]
    total: int


class TTSModelInfo(BaseModel):
    id: str
    name: str
    description: str


class ModelsResponse(BaseModel):
    tts_models: List[TTSModelInfo]
    text_models: List[TTSModelInfo]


class GeneratePodcastRequest(BaseModel):
    input_text: str = Field(
        ...,
        description="The text content to convert into a podcast",
        min_length=10
    )
    speaker_voices: List[str] = Field(
        ...,
        description="List of voice IDs for each speaker",
        min_length=1,
        max_length=6
    )
    num_speakers: int = Field(
        default=2,
        ge=1,
        le=6,
        description="Number of speakers in the podcast"
    )
    tts_model: str = Field(
        default="gemini-2.5-flash-preview-tts",
        description="TTS model to use"
    )
    text_model: str = Field(
        default="gemini-3-pro-preview",
        description="Text generation model for script"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Creativity/temperature for script generation"
    )


class GeneratePodcastResponse(BaseModel):
    success: bool
    message: str
    script: Optional[PodcastScript] = None
    audio_url: Optional[str] = None
    job_id: Optional[str] = None


class ScriptOnlyResponse(BaseModel):
    success: bool
    message: str
    script: Optional[PodcastScript] = None


class GenerateAudioFromScriptRequest(BaseModel):
    """Request body for generating audio from an existing script."""
    script: PodcastScript = Field(
        ...,
        description="The podcast script object (from /generate-script response)"
    )
    tts_model: str = Field(
        default="gemini-2.5-flash-preview-tts",
        description="TTS model to use"
    )


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------

def get_voice_sample_url(voice_id: str) -> str:
    """Generate URL for voice sample (relative path for API serving)."""
    return f"/voices/sample/{voice_id}"


def check_voice_sample_exists(voice_id: str) -> bool:
    """Check if voice sample file exists."""
    # Handle case sensitivity - check both lowercase and capitalized
    sample_path = os.path.join(VOICE_SAMPLE_DIR, f"{voice_id}.wav")
    sample_path_cap = os.path.join(VOICE_SAMPLE_DIR, f"{voice_id.capitalize()}.wav")
    return os.path.exists(sample_path) or os.path.exists(sample_path_cap)


def get_voice_sample_path(voice_id: str) -> Optional[str]:
    """Get actual path to voice sample file."""
    sample_path = os.path.join(VOICE_SAMPLE_DIR, f"{voice_id}.wav")
    sample_path_cap = os.path.join(VOICE_SAMPLE_DIR, f"{voice_id.capitalize()}.wav")
    
    if os.path.exists(sample_path):
        return sample_path
    elif os.path.exists(sample_path_cap):
        return sample_path_cap
    return None


async def generate_script_async(
    input_text: str,
    speaker_voices: List[str],
    num_speakers: int,
    model: str,
    temperature: float,
) -> Optional[PodcastScript]:
    """Generate podcast script using Gemini."""
    return await run_gemini_agent(
        instruction=podcast_system_instruction(num_speakers, speaker_voices),
        user_input=input_text,
        output_type=PodcastScript,
        model=model,
        temperature=temperature,
        retries=2,
    )


def upload_to_s3_and_cleanup(local_path: str, filename: str) -> str:
    """
    Upload the generated podcast audio to S3 and delete the local temp file.
    Returns the S3 presigned URL for the uploaded file.
    """
    try:
        # Upload to S3
        s3_upload_file(local_path, filename)
        # Generate presigned URL (1 hour expiry)
        presigned_url = s3_presigned_url(filename)
        return presigned_url
    finally:
        # Always clean up the local temp file
        cleanup_temp_file(local_path)


def cleanup_temp_file(filepath: str):
    """Clean up temporary local files after S3 upload."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error cleaning up {filepath}: {e}")


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Rankify Podcast API",
        "version": "1.0.0",
        "storage": "S3"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "voice_samples_dir": os.path.exists(VOICE_SAMPLE_DIR),
        "available_voices": len(AVAILABLE_VOICES),
        "tts_models": len(TTS_MODELS),
        "storage": "S3"
    }


@app.get(
    "/voices",
    response_model=VoicesResponse,
    tags=["Voices"],
    summary="Get available voices"
)
async def get_voices(api_key: str = Depends(verify_api_key)):
    """
    Get list of all available voices with their descriptions and sample URLs.
    """
    voices = []
    
    for voice_id in AVAILABLE_VOICES:
        description = VOICE_DESCRIPTIONS.get(
            voice_id.lower(), 
            "Voice sample"
        )
        
        voices.append(VoiceInfo(
            id=voice_id,
            name=voice_id.capitalize(),
            description=description,
            sample_url=get_voice_sample_url(voice_id),
            sample_available=check_voice_sample_exists(voice_id)
        ))
    
    return VoicesResponse(
        voices=voices,
        total=len(voices)
    )


@app.get(
    "/voices/sample/{voice_id}",
    tags=["Voices"],
    summary="Get voice sample audio"
)
async def get_voice_sample(voice_id: str):
    """
    Stream voice sample audio file for a given voice ID.
    No authentication required for voice samples (public resource).
    """
    sample_path = get_voice_sample_path(voice_id)
    
    if not sample_path:
        raise HTTPException(
            status_code=404,
            detail=f"Voice sample not found for: {voice_id}"
        )
    
    return FileResponse(
        sample_path,
        media_type="audio/wav",
        filename=f"{voice_id}.wav"
    )


@app.get(
    "/tts-models",
    response_model=ModelsResponse,
    tags=["Models"],
    summary="Get available models"
)
async def get_models(api_key: str = Depends(verify_api_key)):
    """
    Get list of available TTS and text generation models.
    """
    return ModelsResponse(
        tts_models=[TTSModelInfo(**m) for m in TTS_MODELS],
        text_models=[TTSModelInfo(**m) for m in TEXT_MODELS]
    )


@app.post(
    "/generate-script",
    response_model=ScriptOnlyResponse,
    tags=["Generation"],
    summary="Generate podcast script only"
)
async def generate_script_only(
    request: GeneratePodcastRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Generate just the podcast script without audio.
    Useful for previewing/editing before TTS generation.
    """
    # Validate voices
    invalid_voices = [v for v in request.speaker_voices if v.lower() not in [av.lower() for av in AVAILABLE_VOICES]]
    if invalid_voices:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid voice IDs: {invalid_voices}"
        )
    
    # Ensure num_speakers matches speaker_voices length
    if len(request.speaker_voices) != request.num_speakers:
        raise HTTPException(
            status_code=400,
            detail=f"Number of speakers ({request.num_speakers}) must match speaker_voices length ({len(request.speaker_voices)})"
        )
    
    try:
        script = await generate_script_async(
            input_text=request.input_text,
            speaker_voices=request.speaker_voices,
            num_speakers=request.num_speakers,
            model=request.text_model,
            temperature=request.temperature,
        )
        
        if script is None:
            return ScriptOnlyResponse(
                success=False,
                message="Script generation failed. Please try again.",
                script=None
            )
        
        return ScriptOnlyResponse(
            success=True,
            message="Script generated successfully",
            script=script
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Script generation error: {str(e)}"
        )


@app.post(
    "/generate-podcast",
    tags=["Generation"],
    summary="Generate full podcast with audio"
)
async def generate_podcast(
    request: GeneratePodcastRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Generate complete podcast: script + TTS audio.
    
    Audio is generated locally, uploaded to S3, and a presigned URL
    is returned. The local temp file is cleaned up after upload.
    """
    # Validate voices
    invalid_voices = [v for v in request.speaker_voices if v.lower() not in [av.lower() for av in AVAILABLE_VOICES]]
    if invalid_voices:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid voice IDs: {invalid_voices}"
        )
    
    # Ensure num_speakers matches speaker_voices length
    if len(request.speaker_voices) != request.num_speakers:
        raise HTTPException(
            status_code=400,
            detail=f"Number of speakers ({request.num_speakers}) must match speaker_voices length ({len(request.speaker_voices)})"
        )
    
    # Validate TTS model
    valid_tts_models = [m["id"] for m in TTS_MODELS]
    if request.tts_model not in valid_tts_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid TTS model. Choose from: {valid_tts_models}"
        )
    
    try:
        # Step 1: Generate Script
        script = await generate_script_async(
            input_text=request.input_text,
            speaker_voices=request.speaker_voices,
            num_speakers=request.num_speakers,
            model=request.text_model,
            temperature=request.temperature,
        )
        
        if script is None:
            raise HTTPException(
                status_code=500,
                detail="Script generation failed. Please try again."
            )
        
        # Step 2: Build speaker-voice mapping
        speaker_voice_map = build_speaker_voice_mapping(script)
        
        # Step 3: Prepare dialogue text for TTS
        dialogue_text = "\n".join(
            f"{turn.speaker}: {turn.text}"
            for turn in script.dialogue
        )
        
        final_prompt = (
            f"TTS the following conversation between "
            f"{', '.join(speaker_voice_map.keys())}:\n{dialogue_text}"
        )
        
        # Step 4: Generate TTS audio locally (temp file)
        job_id = str(uuid.uuid4())
        audio_filename = f"podcast_{job_id}.wav"
        output_file = os.path.join(OUTPUT_DIR, audio_filename)
        
        tts = MultiSpeakerTTS()
        tts_result = tts.generate_tts(
            dialogue=final_prompt,
            speaker_voice_map=speaker_voice_map,
            tts_model=request.tts_model,
            output_file=output_file,
        )
        
        if not os.path.exists(output_file):
            raise HTTPException(
                status_code=500,
                detail="Audio generation failed - output file not created"
            )
        
        # Step 5: Upload to S3 and get presigned URL
        try:
            presigned_url = upload_to_s3_and_cleanup(output_file, audio_filename)
        except Exception as e:
            # Clean up local file even on S3 upload failure
            cleanup_temp_file(output_file)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload audio to S3: {str(e)}"
            )
        
        # Step 6: Return JSON with S3 presigned URL
        return {
            "success": True,
            "message": "Podcast generated successfully",
            "job_id": job_id,
            "script": script.model_dump(),
            "audio_url": presigned_url,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Podcast generation error: {str(e)}"
        )


@app.post(
    "/generate-podcast-with-script",
    tags=["Generation"],
    summary="Generate podcast and return script + audio URL"
)
async def generate_podcast_with_metadata(
    request: GeneratePodcastRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Generate complete podcast and return both the script metadata and audio.
    
    Returns JSON with script details and a presigned S3 URL for the audio.
    The presigned URL is valid for 1 hour.
    """
    # Validate voices
    invalid_voices = [v for v in request.speaker_voices if v.lower() not in [av.lower() for av in AVAILABLE_VOICES]]
    if invalid_voices:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid voice IDs: {invalid_voices}"
        )
    
    if len(request.speaker_voices) != request.num_speakers:
        raise HTTPException(
            status_code=400,
            detail=f"Number of speakers ({request.num_speakers}) must match speaker_voices length ({len(request.speaker_voices)})"
        )
    
    valid_tts_models = [m["id"] for m in TTS_MODELS]
    if request.tts_model not in valid_tts_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid TTS model. Choose from: {valid_tts_models}"
        )
    
    try:
        # Generate Script
        script = await generate_script_async(
            input_text=request.input_text,
            speaker_voices=request.speaker_voices,
            num_speakers=request.num_speakers,
            model=request.text_model,
            temperature=request.temperature,
        )
        
        if script is None:
            return {
                "success": False,
                "message": "Script generation failed",
                "script": None,
                "audio_url": None
            }
        
        # Build speaker-voice mapping and generate TTS
        speaker_voice_map = build_speaker_voice_mapping(script)
        
        dialogue_text = "\n".join(
            f"{turn.speaker}: {turn.text}"
            for turn in script.dialogue
        )
        
        final_prompt = (
            f"TTS the following conversation between "
            f"{', '.join(speaker_voice_map.keys())}:\n{dialogue_text}"
        )
        
        job_id = str(uuid.uuid4())
        audio_filename = f"podcast_{job_id}.wav"
        output_file = os.path.join(OUTPUT_DIR, audio_filename)
        
        tts = MultiSpeakerTTS()
        tts_result = tts.generate_tts(
            dialogue=final_prompt,
            speaker_voice_map=speaker_voice_map,
            tts_model=request.tts_model,
            output_file=output_file,
        )
        
        if not os.path.exists(output_file):
            raise HTTPException(
                status_code=500,
                detail="Audio generation failed - output file not created"
            )
        
        # Upload to S3 and get presigned URL, clean up local file
        try:
            presigned_url = upload_to_s3_and_cleanup(output_file, audio_filename)
        except Exception as e:
            cleanup_temp_file(output_file)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload audio to S3: {str(e)}"
            )
        
        return {
            "success": True,
            "message": "Podcast generated successfully",
            "job_id": job_id,
            "script": script.model_dump(),
            "audio_url": presigned_url,
            "tts_metadata": tts_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Podcast generation error: {str(e)}"
        )


@app.post(
    "/generate-audio-from-script",
    tags=["Generation"],
    summary="Generate audio from existing script"
)
async def generate_audio_from_script(
    request: GenerateAudioFromScriptRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Generate TTS audio from an existing podcast script.
    
    Use this endpoint when you have already generated a script via /generate-script
    and want to convert it to audio (possibly after editing).
    
    The audio is uploaded to S3 and a presigned URL (valid 1 hour) is returned.
    
    Flow:
    1. POST /generate-script → get script JSON
    2. (Optional) Edit the script in your UI
    3. POST /generate-audio-from-script with the script → get S3 audio URL
    """
    script = request.script
    
    # Validate TTS model
    valid_tts_models = [m["id"] for m in TTS_MODELS]
    if request.tts_model not in valid_tts_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid TTS model. Choose from: {valid_tts_models}"
        )
    
    # Validate that speakers have voice_ids
    for speaker in script.speakers:
        if not speaker.voice_id:
            raise HTTPException(
                status_code=400,
                detail=f"Speaker '{speaker.name}' is missing voice_id"
            )
        if speaker.voice_id.lower() not in [v.lower() for v in AVAILABLE_VOICES]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice_id '{speaker.voice_id}' for speaker '{speaker.name}'"
            )
    
    try:
        # Build speaker-voice mapping from the script
        speaker_voice_map = build_speaker_voice_mapping(script)
        
        # Prepare dialogue text for TTS
        dialogue_text = "\n".join(
            f"{turn.speaker}: {turn.text}"
            for turn in script.dialogue
        )
        
        final_prompt = (
            f"TTS the following conversation between "
            f"{', '.join(speaker_voice_map.keys())}:\n{dialogue_text}"
        )
        
        # Generate TTS audio locally (temp file)
        job_id = str(uuid.uuid4())
        audio_filename = f"podcast_{job_id}.wav"
        output_file = os.path.join(OUTPUT_DIR, audio_filename)
        
        tts = MultiSpeakerTTS()
        tts_result = tts.generate_tts(
            dialogue=final_prompt,
            speaker_voice_map=speaker_voice_map,
            tts_model=request.tts_model,
            output_file=output_file,
        )
        
        if not os.path.exists(output_file):
            raise HTTPException(
                status_code=500,
                detail="Audio generation failed - output file not created"
            )
        
        # Upload to S3 and get presigned URL, clean up local file
        try:
            presigned_url = upload_to_s3_and_cleanup(output_file, audio_filename)
        except Exception as e:
            cleanup_temp_file(output_file)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload audio to S3: {str(e)}"
            )
        
        return {
            "success": True,
            "message": "Audio generated successfully from script",
            "job_id": job_id,
            "audio_url": presigned_url,
            "script_title": script.title,
            "tts_metadata": tts_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Audio generation error: {str(e)}"
        )


@app.get(
    "/audio/{job_id}",
    tags=["Audio"],
    summary="Get audio presigned URL by job ID"
)
async def get_audio(job_id: str):
    """
    Get a presigned S3 URL for previously generated podcast audio by job ID.
    
    Redirects the client to the S3 presigned URL. If the audio file
    does not exist in S3, a 404 error is returned.
    """
    audio_filename = f"podcast_{job_id}.wav"
    
    try:
        # Verify the object exists in S3 before generating URL
        from helpers.s3_helper import head_object as s3_head_object
        s3_head_object(audio_filename)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Audio not found for job ID: {job_id}"
        )
    
    # Generate a fresh presigned URL and redirect
    presigned_url = s3_presigned_url(audio_filename)
    return RedirectResponse(url=presigned_url, status_code=307)


# ------------------------------------------------------------------
# Run with Uvicorn (for development)
# ------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
