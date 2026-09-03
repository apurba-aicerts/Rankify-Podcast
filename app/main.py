"""
Rankify Podcast API — flat structure.

Projects, Podcasts, and Podcast Scripts persisted in PostgreSQL.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import Podcast, PodcastScriptRecord, Project, Voice, get_db, init_db
from document_parser import extract_text
from gemini_client import build_speaker_voice_mapping, run_gemini_agent
from generation_tasks import schedule_podcast_generation, schedule_script_generation
from gemini_models import (
    MODELS_LIMIT,
    get_cache_fetched_at,
    get_default_text_model,
    get_text_models,
    get_tts_models,
    refresh_models,
    validate_text_model,
    validate_tts_model,
)
from google_tts import MultiSpeakerTTS
from podcast_prompts import podcast_system_instruction, voices as VOICE_DESCRIPTIONS
from schemas import (
    GeneratePodcastFromScriptRequest,
    GeneratePodcastRequest,
    GeneratePodcastResponse,
    GeneratePodcastScriptResponse,
    ModelInfo,
    ModelsResponse,
    PodcastListResponse,
    PodcastResponse,
    PodcastScript,
    PodcastSummary,
    ProjectCreate,
    ProjectCounts,
    ProjectDetailResponse,
    ProjectItem,
    ProjectListResponse,
    ProjectResponse,
    ProjectSummary,
    ProjectUpdate,
    ScriptCreateResponse,
    ScriptListResponse,
    ScriptUpdate,
    TextModelsResponse,
    TtsModelsResponse,
    VoiceInfo,
    VoicesResponse,
)
import storage

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(APP_DIR / ".env")

API_KEY = os.getenv("X_API_KEY", "dev-api-key-12345")
VOICE_SAMPLE_DIR = APP_DIR / "voice_samples"
OUTPUT_DIR = APP_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

AVAILABLE_VOICES = list(VOICE_DESCRIPTIONS.keys())


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    refresh_models(force=True)
    text_n = len(get_text_models())
    tts_n = len(get_tts_models())
    print(f"Podcast API started — database initialized, {text_n} text + {tts_n} TTS models cached")
    yield
    print("Podcast API shutting down")


app = FastAPI(
    title="Rankify Podcast API",
    description="Project-based podcast generation with S3-backed audio storage",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_api_key(x_api_key: str = Header(..., alias="x-api-key")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_podcast_or_404(db: Session, project_id: UUID, podcast_id: UUID) -> Podcast:
    podcast = (
        db.query(Podcast)
        .filter(Podcast.id == podcast_id, Podcast.project_id == project_id)
        .first()
    )
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    return podcast


def get_script_or_404(db: Session, project_id: UUID, script_id: UUID) -> PodcastScriptRecord:
    record = (
        db.query(PodcastScriptRecord)
        .filter(PodcastScriptRecord.id == script_id, PodcastScriptRecord.project_id == project_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Script not found")
    return record


def podcast_to_summary(podcast: Podcast) -> PodcastSummary:
    return PodcastSummary(
        id=podcast.id,
        title=podcast.title,
        description=podcast.description,
        status=podcast.status,
        error_message=podcast.error_message,
        audio_url=storage.audio_url(podcast.s3_key) if podcast.s3_key else None,
        script_id=podcast.script_id,
        created_at=podcast.created_at,
    )


def podcast_to_response(podcast: Podcast) -> PodcastResponse:
    audio_url = storage.audio_url(podcast.s3_key) if podcast.s3_key else None
    return PodcastResponse(
        id=podcast.id,
        project_id=podcast.project_id,
        title=podcast.title,
        description=podcast.description,
        status=podcast.status,
        error_message=podcast.error_message,
        s3_key=podcast.s3_key,
        audio_url=audio_url,
        script_id=podcast.script_id,
        tts_model=podcast.tts_model,
        tts_metadata=podcast.tts_metadata,
        podcast_script_snapshot=podcast.podcast_script_snapshot,
        created_at=podcast.created_at,
        updated_at=podcast.updated_at,
    )


def script_to_response(record: PodcastScriptRecord) -> ScriptCreateResponse:
    script_obj = None
    if record.script:
        script_obj = PodcastScript.model_validate(record.script)
    return ScriptCreateResponse(
        id=record.id,
        project_id=record.project_id,
        title=record.title,
        description=record.description,
        status=record.status,
        error_message=record.error_message,
        script=script_obj,
        text_model=record.text_model,
        tts_model=record.tts_model,
        source_filename=record.source_filename,
        auto_generate_podcast=record.auto_generate_podcast,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def compute_project_counts(db: Session, project_id: UUID) -> ProjectCounts:
    finished_podcasts = (
        db.query(func.count(Podcast.id))
        .filter(Podcast.project_id == project_id, Podcast.status == "ready")
        .scalar()
        or 0
    )
    unfinished_scripts = (
        db.query(func.count(PodcastScriptRecord.id))
        .filter(
            PodcastScriptRecord.project_id == project_id,
            PodcastScriptRecord.status.in_(("generating", "ready", "failed")),
        )
        .scalar()
        or 0
    )
    unfinished_podcasts = (
        db.query(func.count(Podcast.id))
        .filter(
            Podcast.project_id == project_id,
            Podcast.status.in_(("generating", "failed")),
        )
        .scalar()
        or 0
    )
    unfinished = unfinished_scripts + unfinished_podcasts
    return ProjectCounts(
        finished_podcasts=finished_podcasts,
        unfinished=unfinished,
        total_items=unfinished + finished_podcasts,
    )


def _script_phase(status: str) -> str:
    if status == "generating":
        return "writing_script"
    if status == "ready":
        return "script_ready"
    return "failed"


def _podcast_phase(status: str) -> str:
    if status == "generating":
        return "generating_audio"
    if status == "ready":
        return "ready"
    return "failed"


def _parse_stored_script(raw: dict | None) -> PodcastScript | None:
    if not raw:
        return None
    return PodcastScript.model_validate(raw)


def build_project_items(db: Session, project_id: UUID) -> List[ProjectItem]:
    items: List[ProjectItem] = []

    scripts = (
        db.query(PodcastScriptRecord)
        .filter(
            PodcastScriptRecord.project_id == project_id,
            PodcastScriptRecord.status != "published",
        )
        .all()
    )
    for record in scripts:
        items.append(
            ProjectItem(
                id=record.id,
                kind="script",
                phase=_script_phase(record.status),
                title=record.title,
                description=record.description,
                error_message=record.error_message,
                audio_url=None,
                script=_parse_stored_script(record.script),
                tts_model=record.tts_model,
                text_model=record.text_model,
                script_id=record.id,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )

    podcasts = (
        db.query(Podcast)
        .filter(Podcast.project_id == project_id)
        .all()
    )
    for podcast in podcasts:
        phase = _podcast_phase(podcast.status)
        items.append(
            ProjectItem(
                id=podcast.id,
                kind="podcast",
                phase=phase,
                title=podcast.title,
                description=podcast.description,
                error_message=podcast.error_message,
                audio_url=storage.audio_url(podcast.s3_key) if podcast.s3_key else None,
                script=_parse_stored_script(podcast.podcast_script_snapshot),
                tts_model=podcast.tts_model,
                script_id=podcast.script_id,
                created_at=podcast.created_at,
                updated_at=podcast.updated_at,
            )
        )

    items.sort(key=lambda item: item.created_at, reverse=True)
    return items


def project_to_summary(db: Session, project: Project) -> ProjectSummary:
    counts = compute_project_counts(db, project.id)
    return ProjectSummary(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        counts=counts,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def project_detail_to_response(db: Session, project: Project) -> ProjectDetailResponse:
    items = build_project_items(db, project.id)
    counts = compute_project_counts(db, project.id)
    counts.total_items = len(items)
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        counts=counts,
        items=items,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def get_voice_sample_path(voice_id: str) -> Optional[Path]:
    for name in (f"{voice_id}.wav", f"{voice_id.capitalize()}.wav"):
        path = VOICE_SAMPLE_DIR / name
        if path.exists():
            return path
    return None


def parse_speaker_voices(raw: str) -> List[str]:
    """
    Accept speaker voices from Swagger/curl in several formats:
      - JSON array: ["achernar","enceladus"]
      - Comma-separated: achernar,enceladus
      - Single voice: achernar
    """
    text = raw.strip()
    if not text:
        return []

    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            pass

    return [
        part.strip().strip('"').strip("'")
        for part in text.split(",")
        if part.strip()
    ]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/", tags=["Health"])
async def root():
    return {"status": "healthy", "service": "Rankify Podcast API", "version": "2.0.0"}


@app.get("/health", tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": db_ok,
        "available_voices": len(AVAILABLE_VOICES),
        "text_models": len(get_text_models()),
        "tts_models": len(get_tts_models()),
    }


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@app.get("/projects", response_model=ProjectListResponse, tags=["Projects"])
async def list_projects(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    summaries = [project_to_summary(db, p) for p in projects]
    totals = ProjectCounts(
        finished_podcasts=sum(s.counts.finished_podcasts for s in summaries),
        unfinished=sum(s.counts.unfinished for s in summaries),
        total_items=sum(s.counts.total_items for s in summaries),
    )
    return ProjectListResponse(
        projects=summaries,
        total=len(projects),
        totals=totals,
    )


@app.post("/projects", response_model=ProjectResponse, status_code=201, tags=["Projects"])
async def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    project = Project(name=body.name, description=body.description or None)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project_to_summary(db, project)


@app.get("/projects/{project_id}", response_model=ProjectDetailResponse, tags=["Projects"])
async def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    project = get_project_or_404(db, project_id)
    return project_detail_to_response(db, project)


@app.patch("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    project = get_project_or_404(db, project_id)
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description or None
    if body.status is not None:
        project.status = body.status
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return project_to_summary(db, project)


@app.delete("/projects/{project_id}", status_code=204, tags=["Projects"])
async def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    project = get_project_or_404(db, project_id)
    storage.delete_project_podcasts(str(project_id))
    db.delete(project)
    db.commit()


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


@app.post(
    "/projects/{project_id}/generate-podcast-script",
    response_model=GeneratePodcastScriptResponse,
    tags=["Generation"],
)
async def generate_podcast_script(
    project_id: UUID,
    file: UploadFile = File(...),
    speaker_voices: str = Form(
        ...,
        description='Voice IDs as JSON array or comma-separated, e.g. ["achernar","enceladus"]',
        examples=["achernar,enceladus"],
    ),
    num_speakers: int = Form(2),
    text_model: Optional[str] = Form(
        None,
        description="Gemini text model (defaults to newest from GET /models/text)",
    ),
    temperature: float = Form(0.7),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    get_project_or_404(db, project_id)

    voice_list = parse_speaker_voices(speaker_voices)
    if not voice_list:
        raise HTTPException(
            status_code=400,
            detail='speaker_voices is required. Use ["achernar","enceladus"] or achernar,enceladus',
        )

    invalid = [v for v in voice_list if v.lower() not in AVAILABLE_VOICES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid voice IDs: {invalid}")

    if len(voice_list) != num_speakers:
        raise HTTPException(
            status_code=400,
            detail=f"num_speakers ({num_speakers}) must match speaker_voices length ({len(voice_list)})",
        )

    try:
        input_text = extract_text(file.filename or "upload.txt", file.file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if len(input_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Document text too short (min 10 chars)")

    resolved_text_model = text_model or get_default_text_model()
    try:
        validate_text_model(resolved_text_model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    script = await run_gemini_agent(
        instruction=podcast_system_instruction(num_speakers, voice_list),
        user_input=input_text,
        output_type=PodcastScript,
        model=resolved_text_model,
        temperature=temperature,
    )

    if script is None:
        return GeneratePodcastScriptResponse(
            success=False,
            message="Podcast script generation failed",
            podcast_script=None,
        )

    return GeneratePodcastScriptResponse(
        success=True,
        message="Podcast script generated successfully",
        podcast_script=script,
    )


@app.post(
    "/projects/{project_id}/generate-podcast",
    response_model=GeneratePodcastResponse,
    tags=["Generation"],
)
async def generate_podcast(
    project_id: UUID,
    body: GeneratePodcastRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    get_project_or_404(db, project_id)

    try:
        validate_tts_model(body.tts_model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    podcast_script = body.podcast_script
    for speaker in podcast_script.speakers:
        if speaker.voice_id.lower() not in AVAILABLE_VOICES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice_id '{speaker.voice_id}' for speaker '{speaker.name}'",
            )

    speaker_voice_map = build_speaker_voice_mapping(podcast_script)
    dialogue_text = "\n".join(
        f"{turn.speaker}: {turn.text}" for turn in podcast_script.dialogue
    )
    final_prompt = (
        f"TTS the following conversation between "
        f"{', '.join(speaker_voice_map.keys())}:\n{dialogue_text}"
    )

    podcast_id = uuid.uuid4()
    temp_path = OUTPUT_DIR / f"temp_{podcast_id}.wav"

    try:
        tts = MultiSpeakerTTS()
        tts_result = tts.generate_tts(
            dialogue=final_prompt,
            speaker_voice_map=speaker_voice_map,
            tts_model=body.tts_model,
            output_file=str(temp_path),
        )

        if not temp_path.exists():
            raise HTTPException(status_code=500, detail="Audio generation failed")

        s3_key = storage.upload_podcast(str(temp_path), str(project_id), str(podcast_id))

        podcast = Podcast(
            id=podcast_id,
            project_id=project_id,
            title=podcast_script.title,
            description=podcast_script.description,
            status="ready",
            s3_key=s3_key,
            tts_model=body.tts_model,
            tts_metadata={
                "input_tokens": tts_result.get("input_tokens"),
                "output_tokens": tts_result.get("output_tokens"),
                "total_tokens": tts_result.get("total_tokens"),
            },
            podcast_script_snapshot=podcast_script.model_dump(),
        )
        db.add(podcast)

        project = get_project_or_404(db, project_id)
        project.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(podcast)

        return GeneratePodcastResponse(
            success=True,
            message="Podcast generated and saved successfully",
            podcast=podcast_to_summary(podcast),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Podcast generation error: {exc}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


# ---------------------------------------------------------------------------
# Podcasts
# ---------------------------------------------------------------------------


@app.get(
    "/projects/{project_id}/podcasts",
    response_model=PodcastListResponse,
    tags=["Podcasts"],
)
async def list_podcasts(
    project_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    get_project_or_404(db, project_id)
    podcasts = (
        db.query(Podcast)
        .filter(Podcast.project_id == project_id)
        .order_by(Podcast.created_at.desc())
        .all()
    )
    summaries = [
        PodcastSummary(
            id=p.id,
            title=p.title,
            description=p.description,
            status=p.status,
            error_message=p.error_message,
            audio_url=storage.audio_url(p.s3_key) if p.s3_key else None,
            script_id=p.script_id,
            created_at=p.created_at,
        )
        for p in podcasts
    ]
    return PodcastListResponse(podcasts=summaries, total=len(summaries))


@app.get(
    "/projects/{project_id}/podcasts/{podcast_id}",
    response_model=PodcastResponse,
    tags=["Podcasts"],
)
async def get_podcast(
    project_id: UUID,
    podcast_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    podcast = get_podcast_or_404(db, project_id, podcast_id)
    return podcast_to_response(podcast)


@app.delete("/projects/{project_id}/podcasts/{podcast_id}", status_code=204, tags=["Podcasts"])
async def delete_podcast(
    project_id: UUID,
    podcast_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    podcast = get_podcast_or_404(db, project_id, podcast_id)
    if podcast.s3_key:
        try:
            storage.delete_object(podcast.s3_key)
        except Exception:
            pass
    db.delete(podcast)
    db.commit()


# ---------------------------------------------------------------------------
# Podcast scripts (DB-backed, async generation)
# ---------------------------------------------------------------------------


@app.get(
    "/projects/{project_id}/scripts",
    response_model=ScriptListResponse,
    tags=["Scripts"],
)
async def list_scripts(
    project_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    get_project_or_404(db, project_id)
    scripts = (
        db.query(PodcastScriptRecord)
        .filter(PodcastScriptRecord.project_id == project_id)
        .order_by(PodcastScriptRecord.created_at.desc())
        .all()
    )
    return ScriptListResponse(
        scripts=[script_to_response(s) for s in scripts],
        total=len(scripts),
    )


@app.post(
    "/projects/{project_id}/scripts",
    response_model=ScriptCreateResponse,
    status_code=201,
    tags=["Scripts"],
)
async def create_script(
    project_id: UUID,
    file: UploadFile = File(...),
    speaker_voices: str = Form(...),
    num_speakers: int = Form(2),
    text_model: Optional[str] = Form(None),
    temperature: float = Form(0.7),
    tts_model: str = Form("gemini-2.5-flash-preview-tts"),
    episode_title: Optional[str] = Form(None),
    auto_generate_podcast: bool = Form(False),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    get_project_or_404(db, project_id)

    voice_list = parse_speaker_voices(speaker_voices)
    if not voice_list:
        raise HTTPException(status_code=400, detail="speaker_voices is required")
    invalid = [v for v in voice_list if v.lower() not in AVAILABLE_VOICES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid voice IDs: {invalid}")
    if len(voice_list) != num_speakers:
        raise HTTPException(
            status_code=400,
            detail=f"num_speakers ({num_speakers}) must match speaker_voices length ({len(voice_list)})",
        )

    try:
        input_text = extract_text(file.filename or "upload.txt", file.file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if episode_title and episode_title.strip():
        input_text = f"Episode title: {episode_title.strip()}\n\n{input_text}"

    if len(input_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Document text too short (min 10 chars)")

    resolved_text_model = text_model or get_default_text_model()
    try:
        validate_text_model(resolved_text_model)
        validate_tts_model(tts_model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    title = (episode_title or "").strip() or "New script"
    record = PodcastScriptRecord(
        project_id=project_id,
        title=title,
        status="generating",
        text_model=resolved_text_model,
        tts_model=tts_model,
        generation_config={
            "temperature": temperature,
            "num_speakers": num_speakers,
            "speaker_voices": voice_list,
        },
        source_filename=file.filename,
        auto_generate_podcast=auto_generate_podcast,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    schedule_script_generation(
        record.id,
        input_text,
        num_speakers,
        voice_list,
        resolved_text_model,
        temperature,
    )

    return script_to_response(record)


@app.get(
    "/projects/{project_id}/scripts/{script_id}",
    response_model=ScriptCreateResponse,
    tags=["Scripts"],
)
async def get_script(
    project_id: UUID,
    script_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    record = get_script_or_404(db, project_id, script_id)
    return script_to_response(record)


@app.patch(
    "/projects/{project_id}/scripts/{script_id}",
    response_model=ScriptCreateResponse,
    tags=["Scripts"],
)
async def update_script(
    project_id: UUID,
    script_id: UUID,
    body: ScriptUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    record = get_script_or_404(db, project_id, script_id)
    if record.status == "generating":
        raise HTTPException(status_code=409, detail="Script is still generating")
    if record.status == "published":
        raise HTTPException(status_code=409, detail="Script already used for podcast generation")

    if body.title is not None:
        record.title = body.title
    if body.description is not None:
        record.description = body.description
    if body.tts_model is not None:
        try:
            validate_tts_model(body.tts_model)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        record.tts_model = body.tts_model
    if body.script is not None:
        for speaker in body.script.speakers:
            if speaker.voice_id.lower() not in AVAILABLE_VOICES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid voice_id '{speaker.voice_id}'",
                )
        record.script = body.script.model_dump()
        record.title = body.script.title
        record.description = body.script.description
        if record.status == "failed":
            record.status = "ready"
            record.error_message = None

    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return script_to_response(record)


@app.delete("/projects/{project_id}/scripts/{script_id}", status_code=204, tags=["Scripts"])
async def delete_script(
    project_id: UUID,
    script_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    record = get_script_or_404(db, project_id, script_id)
    db.delete(record)
    db.commit()


@app.post(
    "/projects/{project_id}/scripts/{script_id}/generate-podcast",
    response_model=GeneratePodcastResponse,
    tags=["Scripts"],
)
async def generate_podcast_from_script(
    project_id: UUID,
    script_id: UUID,
    body: GeneratePodcastFromScriptRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    record = get_script_or_404(db, project_id, script_id)
    if record.status == "generating":
        raise HTTPException(status_code=409, detail="Script is still generating")
    if record.status == "published":
        raise HTTPException(status_code=409, detail="Script already used for podcast generation")

    tts_model = body.tts_model or record.tts_model
    try:
        validate_tts_model(tts_model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if body.script is not None:
        for speaker in body.script.speakers:
            if speaker.voice_id.lower() not in AVAILABLE_VOICES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid voice_id '{speaker.voice_id}'",
                )
        record.script = body.script.model_dump()
        record.title = body.script.title
        record.description = body.script.description
        record.tts_model = tts_model
        record.updated_at = datetime.now(timezone.utc)
        if record.status == "failed":
            record.status = "ready"
            record.error_message = None
        db.flush()
    elif body.tts_model is not None:
        record.tts_model = tts_model
        record.updated_at = datetime.now(timezone.utc)
        db.flush()

    if record.status not in ("ready",) or not record.script:
        raise HTTPException(status_code=409, detail="Script is not ready for audio generation")

    podcast_script = PodcastScript.model_validate(record.script)
    podcast_id = uuid.uuid4()
    podcast = Podcast(
        id=podcast_id,
        project_id=project_id,
        script_id=script_id,
        title=podcast_script.title,
        description=podcast_script.description,
        status="generating",
        s3_key=None,
        tts_model=tts_model,
        podcast_script_snapshot=record.script,
    )
    db.add(podcast)
    record.status = "published"
    record.updated_at = datetime.now(timezone.utc)
    project = get_project_or_404(db, project_id)
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(podcast)

    schedule_podcast_generation(project_id, script_id, tts_model, podcast_id)

    return GeneratePodcastResponse(
        success=True,
        message="Podcast generation started",
        podcast=podcast_to_summary(podcast),
    )


# ---------------------------------------------------------------------------
# Utility — voices & models
# ---------------------------------------------------------------------------


def voice_row_to_info(voice: Voice) -> VoiceInfo:
    url: Optional[str] = None
    if voice.sample_available and voice.s3_key:
        url = storage.audio_url(voice.s3_key)
    elif get_voice_sample_path(voice.id):
        url = f"/voices/sample/{voice.id}"

    available = bool(
        (voice.sample_available and voice.s3_key) or get_voice_sample_path(voice.id)
    )
    return VoiceInfo(
        id=voice.id,
        name=voice.name,
        description=voice.description,
        s3_key=voice.s3_key if voice.sample_available else None,
        audio_url=url,
        sample_url=url,
        sample_available=available,
    )


@app.get("/voices", response_model=VoicesResponse, tags=["Voices"])
async def get_voices(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    voices = db.query(Voice).order_by(Voice.id).all()
    return VoicesResponse(
        voices=[voice_row_to_info(v) for v in voices],
        total=len(voices),
    )


@app.get("/voices/sample/{voice_id}", tags=["Voices"])
async def get_voice_sample(voice_id: str, db: Session = Depends(get_db)):
    vid = voice_id.lower()
    voice = db.get(Voice, vid)
    if voice is None and vid not in AVAILABLE_VOICES:
        raise HTTPException(status_code=404, detail=f"Unknown voice: {voice_id}")

    if voice and voice.sample_available and voice.s3_key:
        return RedirectResponse(storage.audio_url(voice.s3_key), status_code=302)

    sample_path = get_voice_sample_path(vid)
    if not sample_path:
        raise HTTPException(status_code=404, detail=f"Voice sample not found for: {voice_id}")
    return FileResponse(sample_path, media_type="audio/wav", filename=f"{vid}.wav")


# ---------------------------------------------------------------------------
# Models (Gemini text + TTS — live from API, latest 10 each)
# ---------------------------------------------------------------------------


def _cached_at() -> datetime | None:
    ts = get_cache_fetched_at()
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _build_models_response() -> ModelsResponse:
    text = get_text_models()
    tts = get_tts_models()
    return ModelsResponse(
        text_models=[ModelInfo(**m) for m in text],
        tts_models=[ModelInfo(**m) for m in tts],
        text_total=len(text),
        tts_total=len(tts),
        limit=MODELS_LIMIT,
        cached_at=_cached_at(),
    )


@app.get("/models", response_model=ModelsResponse, tags=["Models"])
async def list_all_models(_: str = Depends(verify_api_key)):
    """Latest text + TTS models available for this Gemini API key."""
    refresh_models()
    return _build_models_response()


@app.get("/models/text", response_model=TextModelsResponse, tags=["Models"])
async def list_text_models(_: str = Depends(verify_api_key)):
    """Latest text models for podcast script generation."""
    refresh_models()
    models = get_text_models()
    return TextModelsResponse(
        models=[ModelInfo(**m) for m in models],
        total=len(models),
        limit=MODELS_LIMIT,
        cached_at=_cached_at(),
    )


@app.get("/models/tts", response_model=TtsModelsResponse, tags=["Models"])
async def list_tts_models(_: str = Depends(verify_api_key)):
    """Latest TTS models for podcast audio generation."""
    refresh_models()
    models = get_tts_models()
    return TtsModelsResponse(
        models=[ModelInfo(**m) for m in models],
        total=len(models),
        limit=MODELS_LIMIT,
        cached_at=_cached_at(),
    )


@app.post("/models/refresh", response_model=ModelsResponse, tags=["Models"])
async def refresh_models_endpoint(_: str = Depends(verify_api_key)):
    """Force refresh model list from Gemini API (bypasses cache)."""
    refresh_models(force=True)
    return _build_models_response()


@app.get("/tts-models", response_model=ModelsResponse, tags=["Models"], deprecated=True)
async def get_models_legacy(_: str = Depends(verify_api_key)):
    """Legacy alias — use GET /models instead."""
    refresh_models()
    return _build_models_response()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
