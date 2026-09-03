# Rankify Podcast API — Documentation

**Version:** 2.0.0  
**Base URL (local):** `http://127.0.0.1:8001`  
**Interactive docs:** [Swagger UI](http://127.0.0.1:8001/docs) · [OpenAPI JSON](http://127.0.0.1:8001/openapi.json)

---

## Table of contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Environment variables](#environment-variables)
4. [Quick start](#quick-start)
5. [Architecture](#architecture)
6. [Database schema](#database-schema)
7. [S3 storage layout](#s3-storage-layout)
8. [End-to-end workflow](#end-to-end-workflow)
9. [Data models](#data-models)
10. [API reference](#api-reference)
    - [Health](#health)
    - [Projects](#projects)
    - [Generation](#generation)
    - [Podcasts](#podcasts)
    - [Voices](#voices)
    - [Models](#models)
11. [Voice catalog](#voice-catalog)
12. [Error responses](#error-responses)
13. [cURL examples](#curl-examples)

---

## Overview

Rankify Podcast API turns uploaded documents into multi-speaker podcast audio.

| Layer | Technology |
|-------|------------|
| API | FastAPI 2.0 |
| Script generation | Google Gemini (text models) |
| Audio synthesis | Google Gemini TTS |
| Persistence | PostgreSQL (`projects`, `podcasts`, `voices`) |
| File storage | AWS S3 (podcast audio + voice samples) |

**Design principles**

- **Projects** and **podcasts** are persisted in PostgreSQL with S3 audio links.
- **Documents** and **podcast scripts** are ephemeral — passed in requests and returned in responses; they are not stored as separate DB entities.
- **Voices** are a static catalog of 30 Gemini TTS voice IDs, with metadata in PostgreSQL and sample audio on S3.
- **Gemini models** (text + TTS) are fetched live from the Gemini API and cached for 1 hour.

---

## Authentication

Most endpoints require an API key in the request header:

```http
x-api-key: your-api-key
```

| Endpoint group | Auth required |
|----------------|---------------|
| `GET /`, `GET /health` | No |
| `GET /voices/sample/{voice_id}` | No |
| All other endpoints | **Yes** |

**401 Unauthorized** — missing or invalid `x-api-key`.

Set the key in `.env`:

```env
X_API_KEY=AICERTS@123
```

---

## Environment variables

Create `.env` at the **repository root** (`Rankify-Podcast/.env`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `X_API_KEY` | Yes | `dev-api-key-12345` | API authentication key |
| `DATABASE_URL` | Yes | `postgresql://rankify:rankify@localhost:5432/rankify_podcast` | PostgreSQL connection string |
| `AWS_ACCESS_KEY_ID` | Yes* | — | AWS credentials for S3 |
| `AWS_SECRET_ACCESS_KEY` | Yes* | — | AWS credentials for S3 |
| `AWS_S3_BUCKET_NAME` | No | `rankify-image-generator` | S3 bucket name |
| `AWS_REGION` | No | `us-east-1` | AWS region |
| `PRESIGNED_URL_EXPIRY` | No | `3600` | Presigned URL lifetime (seconds) |
| `S3_USE_PUBLIC_URLS` | No | `false` | If `true`, return clean public S3 URLs instead of presigned |
| `VOICE_S3_PREFIX` | No | `voices` | S3 prefix for voice sample files |

\* Required for podcast generation and voice sample URLs.

**Local PostgreSQL (Docker):**

```env
DATABASE_URL=postgresql://rankify:rankify@localhost:5433/rankify_podcast
```

---

## Quick start

```powershell
# 1. Start PostgreSQL
cd "C:\AI Certs\Rankify-Podcast\app"
docker compose up -d postgres

# 2. Activate virtual environment & install dependencies
cd ..
.\podcast_env\Scripts\Activate.ps1
pip install -r app\requirements.txt

# 3. Run API server
cd app
python -m uvicorn main:app --reload --port 8001
```

Open Swagger: **http://127.0.0.1:8001/docs**

**Upload voice samples to S3 (one-time):**

```powershell
python experiment\s3_voice_samples_upload.py
python experiment\s3_voice_samples_upload.py --sync-db   # mark DB available without re-upload
```

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│  FastAPI     │────▶│ PostgreSQL  │
│  (Frontend) │     │  main.py     │     │ projects    │
└─────────────┘     └──────┬───────┘     │ podcasts    │
                           │             │ voices      │
                           ▼             └─────────────┘
                    ┌──────────────┐
                    │  AWS S3      │
                    │  podcasts    │
                    │  voice samples│
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Gemini API   │
                    │ text + TTS   │
                    └──────────────┘
```

### Generation pipeline (2 API calls)

```
Document upload  →  POST .../generate-podcast-script  →  PodcastScript JSON
PodcastScript    →  POST .../generate-podcast           →  Saved podcast + audio_url
```

---

## Database schema

### `projects`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `name` | VARCHAR(255) | Project display name |
| `status` | VARCHAR(20) | `active` or `archived` |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

### `podcasts`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated on generation |
| `project_id` | UUID (FK) | Parent project |
| `title` | VARCHAR(255) | From podcast script |
| `description` | TEXT | From podcast script |
| `s3_key` | VARCHAR(512) | S3 object key for WAV |
| `tts_model` | VARCHAR(100) | Gemini TTS model used |
| `tts_metadata` | JSONB | Token usage stats |
| `podcast_script_snapshot` | JSONB | Full script at generation time |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

### `voices`

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(64) (PK) | Voice ID, e.g. `achernar` |
| `name` | VARCHAR(128) | Display name |
| `description` | TEXT | Voice characteristics |
| `s3_key` | VARCHAR(512) | e.g. `voices/achernar.wav` |
| `sample_available` | BOOLEAN | `true` after S3 upload / sync |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

Voices are seeded from `podcast_prompts.py` on application startup.

---

## S3 storage layout

| Resource | S3 key pattern | Example |
|----------|----------------|---------|
| Podcast audio | `projects/{project_id}/podcasts/{podcast_id}.wav` | `projects/a1b2.../podcasts/c3d4....wav` |
| Voice sample | `voices/{voice_id}.wav` | `voices/achernar.wav` |

**Audio URLs** in API responses are either:

- **Presigned URLs** (default) — expire after `PRESIGNED_URL_EXPIRY` seconds
- **Public URLs** — when `S3_USE_PUBLIC_URLS=true` and bucket policy allows public read

---

## End-to-end workflow

### Step 1 — Create a project

```http
POST /projects
Content-Type: application/json
x-api-key: {key}

{ "name": "Bengali Short Stories" }
```

Save the returned `id` as `{project_id}`.

### Step 2 — List available voices (optional)

```http
GET /voices
x-api-key: {key}
```

Pick voice IDs for your speakers (e.g. `achernar`, `enceladus`).

### Step 3 — Generate podcast script from document

```http
POST /projects/{project_id}/generate-podcast-script
Content-Type: multipart/form-data
x-api-key: {key}

file: <document.pdf>
speaker_voices: achernar,enceladus
num_speakers: 2
text_model: gemini-2.5-pro        (optional)
temperature: 0.7                   (optional)
```

Response contains `podcast_script` — use it in the next step.

### Step 4 — Generate podcast audio

```http
POST /projects/{project_id}/generate-podcast
Content-Type: application/json
x-api-key: {key}

{
  "podcast_script": { ... },
  "tts_model": "gemini-2.5-flash-preview-tts"
}
```

Response contains `podcast.audio_url` — play or download the WAV.

### Step 5 — List / retrieve podcasts

```http
GET /projects/{project_id}/podcasts
GET /projects/{project_id}/podcasts/{podcast_id}
```

---

## Data models

### PodcastScript (ephemeral)

Returned by script generation; sent back for audio generation.

```json
{
  "title": "Episode Title",
  "description": "Short episode summary",
  "speakers": [
    { "name": "Alex", "voice_id": "achernar" },
    { "name": "Jordan", "voice_id": "enceladus" }
  ],
  "dialogue": [
    { "speaker": "Alex", "text": "Welcome to the show." },
    { "speaker": "Jordan", "text": "Thanks for having me." }
  ]
}
```

| Field | Type | Rules |
|-------|------|-------|
| `title` | string | Required |
| `description` | string | Required |
| `speakers` | array | Each speaker has `name` + `voice_id` |
| `dialogue` | array | Each turn has `speaker` (name) + `text` |
| `voice_id` | string | Must be one of the [30 voice IDs](#voice-catalog) |

### speaker_voices formats

The `speaker_voices` form field accepts:

| Format | Example |
|--------|---------|
| Comma-separated | `achernar,enceladus` |
| JSON array | `["achernar","enceladus"]` |
| Single voice | `achernar` |

`num_speakers` must equal the number of voices provided.

---

## API reference

**Endpoint summary (19 routes)**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Service info |
| GET | `/health` | No | Health + DB status |
| GET | `/projects` | Yes | List all projects |
| POST | `/projects` | Yes | Create project |
| GET | `/projects/{project_id}` | Yes | Get project |
| PATCH | `/projects/{project_id}` | Yes | Update project |
| DELETE | `/projects/{project_id}` | Yes | Delete project + S3 podcasts |
| POST | `/projects/{project_id}/generate-podcast-script` | Yes | Document → script |
| POST | `/projects/{project_id}/generate-podcast` | Yes | Script → audio |
| GET | `/projects/{project_id}/podcasts` | Yes | List podcasts |
| GET | `/projects/{project_id}/podcasts/{podcast_id}` | Yes | Get podcast |
| DELETE | `/projects/{project_id}/podcasts/{podcast_id}` | Yes | Delete podcast |
| GET | `/voices` | Yes | List voices + sample URLs |
| GET | `/voices/sample/{voice_id}` | No | Redirect/serve sample audio |
| GET | `/models` | Yes | Text + TTS models |
| GET | `/models/text` | Yes | Text models only |
| GET | `/models/tts` | Yes | TTS models only |
| POST | `/models/refresh` | Yes | Force refresh model cache |
| GET | `/tts-models` | Yes | **Deprecated** — use `/models` |

---

### Health

#### `GET /`

Service metadata. No authentication.

**Response 200**

```json
{
  "status": "healthy",
  "service": "Rankify Podcast API",
  "version": "2.0.0"
}
```

---

#### `GET /health`

Database connectivity and catalog counts. No authentication.

**Response 200**

```json
{
  "status": "healthy",
  "database": true,
  "available_voices": 30,
  "text_models": 7,
  "tts_models": 3
}
```

`status` is `"degraded"` when the database is unreachable.

---

### Projects

#### `GET /projects`

List all projects, newest activity first. Includes `podcast_count` and `recent_podcast`.

**Headers:** `x-api-key`

**Response 200**

```json
{
  "projects": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Bengali Short Stories",
      "status": "active",
      "podcast_count": 2,
      "recent_podcast": {
        "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "title": "Episode One",
        "created_at": "2026-09-01T12:00:00Z",
        "audio_url": "https://bucket.s3.amazonaws.com/projects/.../podcasts/....wav?..."
      },
      "created_at": "2026-09-01T10:00:00Z",
      "updated_at": "2026-09-01T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

#### `POST /projects`

Create a new project.

**Headers:** `x-api-key`  
**Body:** `application/json`

```json
{ "name": "My Podcast Project" }
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | 1–255 characters |

**Response 201** — `ProjectResponse` (same shape as list item, `podcast_count: 0`).

---

#### `GET /projects/{project_id}`

Get a single project by UUID.

**Response 200** — `ProjectResponse`  
**Response 404** — Project not found

---

#### `PATCH /projects/{project_id}`

Partial update.

**Body:** `application/json` (all fields optional)

```json
{
  "name": "Renamed Project",
  "status": "archived"
}
```

| Field | Type | Values |
|-------|------|--------|
| `name` | string | 1–255 characters |
| `status` | string | `active` \| `archived` |

**Response 200** — Updated `ProjectResponse`

---

#### `DELETE /projects/{project_id}`

Delete project, all associated podcast DB rows, and all S3 objects under `projects/{project_id}/`.

**Response 204** — No content  
**Response 404** — Project not found

---

### Generation

#### `POST /projects/{project_id}/generate-podcast-script`

Upload a document and generate a structured podcast script via Gemini.

**Headers:** `x-api-key`  
**Content-Type:** `multipart/form-data`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | file | Yes | — | Source document |
| `speaker_voices` | string | Yes | — | Voice IDs (see [formats](#speaker_voices-formats)) |
| `num_speakers` | integer | No | `2` | Must match voice count |
| `text_model` | string | No | Newest from `/models/text` | Gemini text model |
| `temperature` | float | No | `0.7` | Generation temperature |

**Supported file types:** `.txt`, `.md`, `.pdf`, `.docx`

**Response 200**

```json
{
  "success": true,
  "message": "Podcast script generated successfully",
  "podcast_script": {
    "title": "...",
    "description": "...",
    "speakers": [...],
    "dialogue": [...]
  }
}
```

**Errors**

| Status | Cause |
|--------|-------|
| 400 | Invalid voices, voice count mismatch, unsupported file, text too short (<10 chars), invalid model |
| 404 | Project not found |
| 401 | Invalid API key |

On Gemini failure: `success: false`, `podcast_script: null`.

---

#### `POST /projects/{project_id}/generate-podcast`

Synthesize audio from a `PodcastScript`, upload to S3, and persist a podcast record.

**Headers:** `x-api-key`  
**Body:** `application/json`

```json
{
  "podcast_script": {
    "title": "Episode Title",
    "description": "Summary",
    "speakers": [
      { "name": "Alex", "voice_id": "achernar" },
      { "name": "Jordan", "voice_id": "enceladus" }
    ],
    "dialogue": [
      { "speaker": "Alex", "text": "Hello and welcome." },
      { "speaker": "Jordan", "text": "Great to be here." }
    ]
  },
  "tts_model": "gemini-2.5-flash-preview-tts"
}
```

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `podcast_script` | PodcastScript | Yes | — |
| `tts_model` | string | No | `gemini-2.5-flash-preview-tts` |

**Response 200**

```json
{
  "success": true,
  "message": "Podcast generated and saved successfully",
  "podcast": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "Episode Title",
    "description": "Summary",
    "s3_key": "projects/3fa85f64.../podcasts/7c9e6679....wav",
    "audio_url": "https://bucket.s3.amazonaws.com/...",
    "tts_model": "gemini-2.5-flash-preview-tts",
    "tts_metadata": {
      "input_tokens": 120,
      "output_tokens": 80,
      "total_tokens": 200
    },
    "podcast_script_snapshot": { "...": "..." },
    "created_at": "2026-09-01T12:00:00Z",
    "updated_at": "2026-09-01T12:00:00Z"
  }
}
```

**Errors**

| Status | Cause |
|--------|-------|
| 400 | Invalid `voice_id`, invalid TTS model |
| 404 | Project not found |
| 500 | TTS or upload failure |

---

### Podcasts

#### `GET /projects/{project_id}/podcasts`

List podcasts for a project, newest first.

**Response 200**

```json
{
  "podcasts": [
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "title": "Episode Title",
      "description": "Summary",
      "audio_url": "https://bucket.s3.amazonaws.com/...",
      "created_at": "2026-09-01T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

#### `GET /projects/{project_id}/podcasts/{podcast_id}`

Full podcast details including `podcast_script_snapshot` and `tts_metadata`.

**Response 200** — `PodcastResponse`  
**Response 404** — Project or podcast not found

---

#### `DELETE /projects/{project_id}/podcasts/{podcast_id}`

Delete podcast record and S3 audio object.

**Response 204** — No content

---

### Voices

Voice metadata is read from PostgreSQL (one query, no S3 HEAD checks). Presigned `audio_url` values are generated from stored `s3_key`.

#### `GET /voices`

List all 30 Gemini TTS voices with sample URLs.

**Headers:** `x-api-key`

**Response 200**

```json
{
  "voices": [
    {
      "id": "achernar",
      "name": "Achernar",
      "description": "Female, Soft and gentle",
      "s3_key": "voices/achernar.wav",
      "audio_url": "https://rankify-image-generator.s3.amazonaws.com/voices/achernar.wav?AWSAccessKeyId=...",
      "sample_available": true,
      "sample_url": "https://rankify-image-generator.s3.amazonaws.com/voices/achernar.wav?..."
    }
  ],
  "total": 30
}
```

| Field | Description |
|-------|-------------|
| `audio_url` | Use this to play the sample (S3 presigned or public URL) |
| `sample_url` | Deprecated alias of `audio_url` |
| `sample_available` | `true` when S3 sample exists (or local fallback) |
| `s3_key` | S3 object path; `null` if sample not on S3 |

---

#### `GET /voices/sample/{voice_id}`

Play a voice sample. **No API key required.**

| Condition | Behavior |
|-----------|----------|
| Sample on S3 | `302 Redirect` to presigned/public URL |
| Local fallback only | `200` — streams `app/voice_samples/{voice_id}.wav` |
| Not found | `404` |

---

### Models

Gemini models are fetched from `GET https://generativelanguage.googleapis.com/v1beta/models` and cached for **1 hour**. Up to **10** models per category (text / TTS) are returned, sorted newest first.

#### `GET /models`

Returns both text and TTS model lists.

**Response 200**

```json
{
  "text_models": [
    {
      "id": "gemini-2.5-pro",
      "name": "gemini-2.5-pro",
      "description": "..."
    }
  ],
  "tts_models": [
    {
      "id": "gemini-2.5-flash-preview-tts",
      "name": "gemini-2.5-flash-preview-tts",
      "description": "..."
    }
  ],
  "text_total": 7,
  "tts_total": 3,
  "limit": 10,
  "cached_at": "2026-09-01T17:00:00Z"
}
```

---

#### `GET /models/text`

Text models for script generation (`generate-podcast-script`).

**Response 200**

```json
{
  "models": [{ "id": "gemini-2.5-pro", "name": "gemini-2.5-pro", "description": "..." }],
  "total": 7,
  "limit": 10,
  "cached_at": "2026-09-01T17:00:00Z"
}
```

When `text_model` is omitted on script generation, the **first model** in this list is used as default.

---

#### `GET /models/tts`

TTS models for audio generation (`generate-podcast`).

**Response 200** — Same shape as `/models/text` with `models` array of TTS models.

---

#### `POST /models/refresh`

Force-refresh the model cache from Gemini (bypasses 1-hour TTL).

**Response 200** — Same as `GET /models`.

---

#### `GET /tts-models` *(deprecated)*

Legacy alias for `GET /models`. Prefer `/models`.

---

## Voice catalog

30 fixed Gemini TTS voice IDs. There is **no Google API** to list these dynamically — this catalog is the source of truth.

| ID | Description |
|----|-------------|
| `zephyr` | Female, Bright and clear tone |
| `puck` | Male, Upbeat and lively |
| `charon` | Male, Informative and precise |
| `kore` | Female, Firm and authoritative |
| `fenrir` | Male, Excitable and energetic |
| `leda` | Female, Youthful and fresh |
| `orus` | Male, Firm and commanding |
| `aoede` | Female, Breezy and relaxed |
| `callirrhoe` | Female, Easy-going and casual |
| `autonoe` | Female, Bright and cheerful |
| `enceladus` | Male, Breathy and soft-spoken |
| `iapetus` | Male, Clear and articulate |
| `umbriel` | Male, Easy-going and friendly |
| `algieba` | Male, Smooth and polished |
| `despina` | Female, Smooth and elegant |
| `erinome` | Female, Clear and crisp |
| `algenib` | Male, Gravelly and rugged |
| `rasalgethi` | Male, Informative and confident |
| `laomedeia` | Female, Upbeat and positive |
| `achernar` | Female, Soft and gentle |
| `alnilam` | Male, Firm and steady |
| `schedar` | Male, Even and balanced |
| `gacrux` | Female, Mature and wise |
| `pulcherrima` | Male, Forward and assertive |
| `achird` | Male, Friendly and warm |
| `zubenelgenubi` | Male, Casual and relaxed |
| `vindemiatrix` | Female, Gentle and soothing |
| `sadachbia` | Male, Lively and spirited |
| `sadaltager` | Male, Knowledgeable and clear |
| `sulafat` | Female, Warm and inviting |

Voice IDs are **case-insensitive** in API validation.

---

## Error responses

All errors use FastAPI's standard format:

```json
{
  "detail": "Human-readable error message"
}
```

| HTTP status | Meaning |
|-------------|---------|
| 400 | Bad request — validation, invalid voices, unsupported file |
| 401 | Missing or invalid `x-api-key` |
| 404 | Project, podcast, or voice not found |
| 500 | Internal error (TTS failure, unexpected exception) |

---

## cURL examples

Replace `{KEY}` and `{PROJECT_ID}` with your values.

**Health check**

```bash
curl http://127.0.0.1:8001/health
```

**Create project**

```bash
curl -X POST http://127.0.0.1:8001/projects \
  -H "x-api-key: {KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"My Project\"}"
```

**List voices**

```bash
curl http://127.0.0.1:8001/voices \
  -H "x-api-key: {KEY}"
```

**Generate script from PDF**

```bash
curl -X POST "http://127.0.0.1:8001/projects/{PROJECT_ID}/generate-podcast-script" \
  -H "x-api-key: {KEY}" \
  -F "file=@document.pdf" \
  -F "speaker_voices=achernar,enceladus" \
  -F "num_speakers=2" \
  -F "text_model=gemini-2.5-pro"
```

**Generate podcast audio**

```bash
curl -X POST "http://127.0.0.1:8001/projects/{PROJECT_ID}/generate-podcast" \
  -H "x-api-key: {KEY}" \
  -H "Content-Type: application/json" \
  -d @podcast_request.json
```

**List Gemini models**

```bash
curl http://127.0.0.1:8001/models/text \
  -H "x-api-key: {KEY}"
```

---

## Project structure

```
app/
├── main.py              # FastAPI routes
├── database.py          # PostgreSQL ORM (projects, podcasts, voices)
├── schemas.py           # Pydantic request/response models
├── storage.py           # S3 upload, presigned URLs
├── document_parser.py   # txt, md, pdf, docx extraction
├── gemini_client.py     # Script generation
├── gemini_models.py     # Dynamic model discovery + cache
├── google_tts.py        # Multi-speaker TTS
├── podcast_prompts.py   # Prompts + voice catalog
├── schema_adapter.py    # Gemini JSON schema helper
├── voice_samples/       # Local WAV fallbacks (30 files)
├── docker-compose.yml   # PostgreSQL service
└── requirements.txt
```

---

*Last updated: September 2026 — API v2.0.0*
