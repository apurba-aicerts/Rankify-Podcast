"""Background script and podcast generation tasks."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from gemini_client import build_speaker_voice_mapping
from schemas import PodcastScript as PodcastScriptSchema
from script_pipeline import ScriptGenerationError, generate_podcast_script_from_text
from tts_pipeline import generate_podcast_audio

from database import Podcast, PodcastScriptRecord, Project, SessionLocal, utcnow
import storage

logger = logging.getLogger(__name__)

APP_OUTPUT_DIR = __import__("pathlib").Path(__file__).resolve().parent / "outputs"
APP_OUTPUT_DIR.mkdir(exist_ok=True)


async def run_script_generation_task(
    script_id: UUID,
    input_text: str,
    num_speakers: int,
    voice_list: list[str],
    text_model: str,
    temperature: float,
) -> None:
    db = SessionLocal()
    try:
        record = db.get(PodcastScriptRecord, script_id)
        if record is None:
            return

        try:
            script = await generate_podcast_script_from_text(
                input_text=input_text,
                num_speakers=num_speakers,
                voice_list=voice_list,
                text_model=text_model,
                temperature=temperature,
            )
        except ScriptGenerationError as exc:
            record.status = "failed"
            record.error_message = str(exc)
            record.updated_at = utcnow()
            db.commit()
            return

        record.script = script.model_dump()
        record.title = script.title
        record.description = script.description
        record.status = "ready"
        record.error_message = None
        record.updated_at = utcnow()
        db.commit()

        if record.auto_generate_podcast:
            await run_podcast_from_script_task(record.project_id, script_id, record.tts_model)
    except Exception as exc:
        logger.exception("Script generation task failed for %s", script_id)
        try:
            record = db.get(PodcastScriptRecord, script_id)
            if record:
                record.status = "failed"
                record.error_message = str(exc)
                record.updated_at = utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def run_podcast_from_script_task(
    project_id: UUID,
    script_id: UUID,
    tts_model: str,
    podcast_id: UUID | None = None,
) -> None:
    db = SessionLocal()
    temp_path = None
    try:
        record = db.get(PodcastScriptRecord, script_id)
        if record is None or record.project_id != project_id:
            return
        if not record.script:
            return
        if record.status not in ("ready", "published"):
            return

        podcast_script = PodcastScriptSchema.model_validate(record.script)
        for speaker in podcast_script.speakers:
            speaker.voice_id = speaker.voice_id.lower()

        if len(podcast_script.speakers) < 1 or len(podcast_script.speakers) > 2:
            raise RuntimeError(
                f"Gemini TTS supports 1–2 speakers (got {len(podcast_script.speakers)})"
            )

        if podcast_id is None:
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
            record.updated_at = utcnow()
            db.commit()
        else:
            podcast = db.get(Podcast, podcast_id)
            if podcast is None:
                return

        speaker_voice_map = build_speaker_voice_mapping(podcast_script)
        temp_path = APP_OUTPUT_DIR / f"temp_{podcast_id}.wav"

        # Run blocking Gemini TTS + S3 upload off the event loop so API
        # requests (dashboard, project polling) stay responsive.
        def _generate_and_upload() -> tuple[dict, str]:
            result = generate_podcast_audio(
                script=podcast_script,
                speaker_voice_map=speaker_voice_map,
                tts_model=tts_model,
                output_file=temp_path,
                work_dir=APP_OUTPUT_DIR,
            )
            if not temp_path.exists():
                raise RuntimeError("Audio generation failed — no output file")
            key = storage.upload_podcast(str(temp_path), str(project_id), str(podcast_id))
            return result, key

        tts_result, s3_key = await asyncio.to_thread(_generate_and_upload)

        podcast = db.get(Podcast, podcast_id)
        if podcast:
            podcast.s3_key = s3_key
            podcast.status = "ready"
            podcast.error_message = None
            podcast.tts_metadata = {
                "input_tokens": tts_result.get("input_tokens"),
                "output_tokens": tts_result.get("output_tokens"),
                "total_tokens": tts_result.get("total_tokens"),
                "tts_chunks": tts_result.get("tts_chunks"),
            }
            podcast.updated_at = utcnow()

            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.updated_at = datetime.now(timezone.utc)

            db.commit()
    except Exception as exc:
        logger.exception("Podcast generation task failed for script %s", script_id)
        try:
            if podcast_id:
                podcast = db.get(Podcast, podcast_id)
                if podcast:
                    podcast.status = "failed"
                    podcast.error_message = str(exc)
                    podcast.updated_at = utcnow()
                    db.commit()
        except Exception:
            pass
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        db.close()


def schedule_script_generation(
    script_id: UUID,
    input_text: str,
    num_speakers: int,
    voice_list: list[str],
    text_model: str,
    temperature: float,
) -> None:
    asyncio.create_task(
        run_script_generation_task(
            script_id, input_text, num_speakers, voice_list, text_model, temperature
        )
    )


def schedule_podcast_generation(
    project_id: UUID,
    script_id: UUID,
    tts_model: str,
    podcast_id: UUID,
) -> None:
    asyncio.create_task(
        run_podcast_from_script_task(project_id, script_id, tts_model, podcast_id)
    )
