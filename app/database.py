"""PostgreSQL connection and ORM models (projects, podcasts, voices)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rankify:rankify@localhost:5432/rankify_podcast",
)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    podcasts: Mapped[list["Podcast"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    scripts: Mapped[list["PodcastScriptRecord"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class PodcastScriptRecord(Base):
    __tablename__ = "podcast_scripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    script: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_model: Mapped[str] = mapped_column(String(100), nullable=False)
    tts_model: Mapped[str] = mapped_column(String(100), nullable=False)
    generation_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auto_generate_podcast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="scripts")


class Podcast(Base):
    __tablename__ = "podcasts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    script_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("podcast_scripts.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ready")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tts_model: Mapped[str] = mapped_column(String(100), nullable=False)
    tts_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    podcast_script_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="podcasts")


class Voice(Base):
    __tablename__ = "voices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sample_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


def seed_voices() -> None:
    """Upsert catalog voices into DB (no S3 calls)."""
    from podcast_prompts import voices as voice_catalog
    import storage

    db = SessionLocal()
    try:
        for voice_id, description in voice_catalog.items():
            s3_key = storage.voice_s3_key(voice_id)
            row = db.get(Voice, voice_id)
            if row is None:
                db.add(
                    Voice(
                        id=voice_id,
                        name=voice_id.capitalize(),
                        description=description,
                        s3_key=s3_key,
                        sample_available=False,
                    )
                )
            else:
                row.name = voice_id.capitalize()
                row.description = description
                if not row.s3_key:
                    row.s3_key = s3_key
                row.updated_at = utcnow()
        db.commit()
    finally:
        db.close()


def mark_voice_sample_available(voice_id: str, s3_key: str | None = None) -> None:
    """Record that a voice sample exists on S3 (called after upload)."""
    import storage

    db = SessionLocal()
    try:
        row = db.get(Voice, voice_id.lower())
        if row is None:
            row = Voice(
                id=voice_id.lower(),
                name=voice_id.capitalize(),
                description="",
                s3_key=s3_key or storage.voice_s3_key(voice_id),
                sample_available=True,
            )
            db.add(row)
        else:
            row.s3_key = s3_key or storage.voice_s3_key(voice_id)
            row.sample_available = True
            row.updated_at = utcnow()
        db.commit()
    finally:
        db.close()


def _ensure_database_exists() -> None:
    parsed = urlparse(DATABASE_URL)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        return

    admin_url = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _migrate_schema() -> None:
    """Add columns/tables for existing deployments (create_all does not alter)."""
    statements = [
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE podcasts ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'ready'",
        "ALTER TABLE podcasts ADD COLUMN IF NOT EXISTS script_id UUID",
        "ALTER TABLE podcasts ADD COLUMN IF NOT EXISTS error_message TEXT",
        "ALTER TABLE podcasts ALTER COLUMN s3_key DROP NOT NULL",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as exc:
                print(f"Note: migration skipped ({exc})")


def init_db() -> None:
    try:
        _ensure_database_exists()
    except Exception as exc:
        print(f"Note: could not auto-create database ({exc}). Ensure it exists manually.")
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
    seed_voices()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
