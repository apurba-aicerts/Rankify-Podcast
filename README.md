# Rankify Podcast API Documentation

## Base URL
```
Development: http://localhost:8000
```

## Authentication
All protected endpoints require `x-api-key` header:
```
x-api-key: dev-api-key-12345
```

## Audio Storage
All generated podcast audio files are stored in **AWS S3**.  
Endpoints return **presigned S3 URLs** (valid for 1 hour) instead of local file paths.  
The `/audio/{job_id}` endpoint redirects (307) to a fresh presigned S3 URL.

---

## Endpoints Overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | Health check |
| GET | `/health` | No | Detailed health status |
| GET | `/voices` | Yes | List available voices with sample URLs |
| GET | `/voices/sample/{voice_id}` | No | Get voice sample audio file |
| GET | `/tts-models` | Yes | List available TTS and text models |
| POST | `/generate-script` | Yes | Generate script only (no audio) |
| POST | `/generate-audio-from-script` | Yes | Generate audio from existing script (S3) |
| POST | `/generate-podcast` | Yes | Generate podcast, returns JSON with S3 audio URL |
| POST | `/generate-podcast-with-script` | Yes | **Recommended** - Returns JSON with script + S3 audio URL |
| GET | `/audio/{job_id}` | No | Redirects to S3 presigned URL for audio |

---

## 1. GET /voices - List Available Voices

### Request
```bash
curl -X GET "http://localhost:8000/voices" \
  -H "x-api-key: dev-api-key-12345"
```

### Response
```json
{
  "voices": [
    {
      "id": "achernar",
      "name": "Achernar",
      "description": "Female, Soft and gentle",
      "sample_url": "/voices/sample/achernar",
      "sample_available": true
    },
    {
      "id": "enceladus",
      "name": "Enceladus",
      "description": "Male, Breathy and soft-spoken",
      "sample_url": "/voices/sample/enceladus",
      "sample_available": true
    }
    // ... 30 voices total
  ],
  "total": 30
}
```

### React Usage
```jsx
const [voices, setVoices] = useState([]);

useEffect(() => {
  fetch('http://localhost:8000/voices', {
    headers: { 'x-api-key': 'dev-api-key-12345' }
  })
    .then(res => res.json())
    .then(data => setVoices(data.voices));
}, []);

// Play voice sample
<audio 
  src={`http://localhost:8000${voice.sample_url}`} 
  controls 
/>
```

---

## 2. GET /voices/sample/{voice_id} - Voice Sample Audio

### Request
```bash
curl -X GET "http://localhost:8000/voices/sample/achernar" \
  --output achernar.wav
```

Returns: `audio/wav` file (no auth required)

---

## 3. GET /tts-models - List Available Models

### Request
```bash
curl -X GET "http://localhost:8000/tts-models" \
  -H "x-api-key: dev-api-key-12345"
```

### Response
```json
{
  "tts_models": [
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
  ],
  "text_models": [
    {
      "id": "gemini-3-pro-preview",
      "name": "Gemini 3 Pro Preview",
      "description": "Latest Gemini model for script generation"
    }
  ]
}
```

---

## 4. POST /generate-podcast-with-script ⭐ RECOMMENDED

**Best endpoint for React integration** - Returns JSON with script metadata + S3 presigned audio URL.

### Request
```bash
curl -X POST "http://localhost:8000/generate-podcast-with-script" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-12345" \
  -d '{
    "input_text": "Your article or content to convert to podcast. This should be substantial text that will be transformed into an engaging conversation between speakers.",
    "speaker_voices": ["achernar", "enceladus"],
    "num_speakers": 2,
    "tts_model": "gemini-2.5-flash-preview-tts",
    "text_model": "gemini-3-pro-preview",
    "temperature": 0.7
  }'
```

### Request Body Schema
```typescript
interface GeneratePodcastRequest {
  input_text: string;      // Required, min 10 chars
  speaker_voices: string[]; // Required, 1-6 voices from /voices
  num_speakers: number;     // Default: 2, range: 1-6
  tts_model: string;        // Default: "gemini-2.5-flash-preview-tts"
  text_model: string;       // Default: "gemini-3-pro-preview"
  temperature: number;      // Default: 0.7, range: 0.0-1.0
}
```

### Response (Success)
```json
{
  "success": true,
  "message": "Podcast generated successfully",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "script": {
    "title": "Understanding AI: A Deep Dive",
    "description": "A fascinating conversation exploring the latest developments in AI",
    "speakers": [
      {"name": "Maya", "voice_id": "achernar"},
      {"name": "Liam", "voice_id": "enceladus"}
    ],
    "dialogue": [
      {"speaker": "Maya", "text": "Welcome to the show! Today we're diving into..."},
      {"speaker": "Liam", "text": "Thanks Maya. This is such an exciting topic..."},
      {"speaker": "Maya", "text": "Absolutely. Let's start with the basics..."}
    ]
  },
  "audio_url": "https://rankify-image-generator.s3.amazonaws.com/generated-podcast/podcast_a1b2c3d4-e5f6-7890-abcd-ef1234567890.wav?X-Amz-Algorithm=...",
  "tts_metadata": {
    "output_file": "/path/to/file.wav",
    "input_tokens": 1500,
    "output_tokens": 3000,
    "total_tokens": 4500
  }
}
```

> **Note:** `audio_url` is now an **S3 presigned URL** (valid for 1 hour).  
> The frontend can use it directly in an `<audio>` tag or download it.  
> The `/audio/{job_id}` endpoint still works as a fallback (redirects to S3).

### React Integration
```jsx
const generatePodcast = async (inputText, voices) => {
  setLoading(true);
  
  const response = await fetch('http://localhost:8000/generate-podcast-with-script', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': 'dev-api-key-12345'
    },
    body: JSON.stringify({
      input_text: inputText,
      speaker_voices: voices,
      num_speakers: voices.length,
      tts_model: 'gemini-2.5-flash-preview-tts',
      temperature: 0.7
    })
  });
  
  const data = await response.json();
  
  if (data.success) {
    setScript(data.script);
    // audio_url is now an S3 presigned URL - use directly
    setAudioUrl(data.audio_url);
  }
  
  setLoading(false);
};

// Display results - audio_url is a full S3 presigned URL
<div>
  <h1>{script.title}</h1>
  <p>{script.description}</p>
  
  <audio src={audioUrl} controls crossOrigin="anonymous" />
  
  {script.dialogue.map((turn, i) => (
    <p key={i}><strong>{turn.speaker}:</strong> {turn.text}</p>
  ))}
</div>
```

---

## 5. POST /generate-audio-from-script ⭐ TWO-STEP FLOW

**Use this when you want to generate script first, then audio separately.**

This enables a workflow where you can:
1. Generate script → preview/edit it
2. Generate audio from the (edited) script → get S3 presigned URL

### Request
```bash
curl -X POST "http://localhost:8000/generate-audio-from-script" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-12345" \
  -d '{
    "script": {
      "title": "Truepix AI: The Creative Orchestrator",
      "description": "Maya and David explore Truepix AI...",
      "speakers": [
        {"name": "Maya", "voice_id": "achernar"},
        {"name": "David", "voice_id": "sadaltager"}
      ],
      "dialogue": [
        {"speaker": "Maya", "text": "You know, I was looking at my browser history yesterday..."},
        {"speaker": "David", "text": "Let me guess. One for text-to-image, one for video..."}
      ]
    },
    "tts_model": "gemini-2.5-flash-preview-tts"
  }'
```

### Request Body Schema
```typescript
interface GenerateAudioFromScriptRequest {
  script: {
    title: string;
    description: string;
    speakers: Array<{
      name: string;
      voice_id: string;  // Must be a valid voice from /voices
    }>;
    dialogue: Array<{
      speaker: string;  // Must match a speaker name
      text: string;
    }>;
  };
  tts_model?: string;  // Default: "gemini-2.5-flash-preview-tts"
}
```

### Response (Success)
```json
{
  "success": true,
  "message": "Audio generated successfully from script",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "audio_url": "https://rankify-image-generator.s3.amazonaws.com/generated-podcast/podcast_a1b2c3d4-...wav?X-Amz-Algorithm=...",
  "script_title": "Truepix AI: The Creative Orchestrator",
  "tts_metadata": {
    "output_file": "/path/to/file.wav",
    "input_tokens": 1500,
    "output_tokens": 3000,
    "total_tokens": 4500
  }
}
```

### React Two-Step Flow Example
```jsx
// Step 1: Generate script only
const generateScript = async (inputText, voices) => {
  const response = await fetch('http://localhost:8000/generate-script', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': 'dev-api-key-12345'
    },
    body: JSON.stringify({
      input_text: inputText,
      speaker_voices: voices,
      num_speakers: voices.length
    })
  });
  
  const data = await response.json();
  if (data.success) {
    setScript(data.script);  // Store for editing/preview
  }
};

// Step 2: After user previews/edits, generate audio
const generateAudio = async (editedScript) => {
  const response = await fetch('http://localhost:8000/generate-audio-from-script', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': 'dev-api-key-12345'
    },
    body: JSON.stringify({
      script: editedScript,
      tts_model: 'gemini-2.5-flash-preview-tts'
    })
  });
  
  const data = await response.json();
  if (data.success) {
    // audio_url is now an S3 presigned URL - use directly
    setAudioUrl(data.audio_url);
  }
};
```

---

## 6. POST /generate-podcast - Generate Full Podcast

### Request
Same request body as `/generate-podcast-with-script`.

### Response (Success)
```json
{
  "success": true,
  "message": "Podcast generated successfully",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "script": { ... },
  "audio_url": "https://rankify-image-generator.s3.amazonaws.com/generated-podcast/podcast_a1b2c3d4-...wav?..."
}
```

> **Note:** This endpoint now returns JSON with an S3 presigned URL  
> (previously it returned a streaming audio response).

---

## 7. GET /audio/{job_id} - Get Audio by Job ID

### Request
```bash
curl -L -X GET "http://localhost:8000/audio/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  --output podcast.wav
```

**Behaviour:** Returns a **307 redirect** to the S3 presigned URL.  
Use `-L` flag with curl to follow redirects. Browsers and `<audio>` tags follow redirects automatically.

### Important Notes on Audio URLs

- Audio files are stored in **AWS S3** under the `generated-podcast/` prefix
- Presigned URLs are **valid for 1 hour** after generation
- **Audio files are automatically deleted from S3 after 1 hour** — a background cleanup task runs every 15 minutes and removes any podcast files older than 1 hour
- Both the presigned URL **and** the actual S3 object expire/get deleted at ~1 hour
- The `/audio/{job_id}` endpoint generates a **fresh** presigned URL on each request (only works while the file still exists in S3)
- Frontend should use the `audio_url` from generation responses directly (it's a full S3 presigned URL)
- The `/audio/{job_id}` endpoint is a convenience fallback that checks S3 and redirects

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid API key"
}
```

### 400 Bad Request
```json
{
  "detail": "Invalid voice IDs: ['invalid_voice']"
}
```

### 404 Not Found (Audio)
```json
{
  "detail": "Audio not found for job ID: ..."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Script generation error: ..."
}
```

```json
{
  "detail": "Failed to upload audio to S3: ..."
}
```

---

## Running the API

### Development
```bash
cd app
pip install fastapi uvicorn python-multipart boto3 python-dotenv
python main.py
# or
uvicorn main:app --reload --port 8000
```

### Environment Variables
Create `.env` file:
```
GEMINI_API_KEY=your_gemini_api_key
X_API_KEY=your_custom_api_key  # Optional, defaults to dev-api-key-12345

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET_NAME=your_s3_bucket_name
AWS_REGION=us-east-1
```

### Swagger UI
Once running, visit: `http://localhost:8000/docs`

---

## CORS Notes

The API is configured with CORS middleware that:
- Allows all origins (`*`) for MVP development
- Exposes custom headers: `X-Podcast-Title`, `X-Job-Id`, `Content-Disposition`
- S3 presigned URLs are **full external URLs** (not same-origin), so they don't trigger CORS issues from the browser — the browser fetches audio directly from S3
- If your S3 bucket requires CORS, ensure the bucket CORS policy allows GET requests from your frontend origin

### S3 Bucket CORS Policy (if needed)
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": [],
    "MaxAgeSeconds": 3600
  }
]
```

---

## Typical React Flow

```
1. On mount: GET /voices → Display voice selector with audio previews
2. On mount: GET /tts-models → Populate model dropdown
3. User inputs text, selects voices
4. On submit: POST /generate-podcast-with-script
5. Display script dialogue + play audio from S3 presigned URL (audio_url)
6. Optional: GET /audio/{job_id} → redirects to fresh S3 presigned URL
```
