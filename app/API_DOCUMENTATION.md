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
| POST | `/generate-audio-from-script` | Yes | **NEW** - Generate audio from existing script |
| POST | `/generate-podcast` | Yes | Generate podcast, returns audio directly |
| POST | `/generate-podcast-with-script` | Yes | **Recommended** - Returns JSON with script + audio URL |
| GET | `/audio/{job_id}` | No | Download generated audio by job ID |

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

**Best endpoint for React integration** - Returns JSON with script metadata + audio download URL.

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
  "audio_url": "/audio/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "tts_metadata": {
    "output_file": "/path/to/file.wav",
    "input_tokens": 1500,
    "output_tokens": 3000,
    "total_tokens": 4500
  }
}
```

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
    setAudioUrl(`http://localhost:8000${data.audio_url}`);
  }
  
  setLoading(false);
};

// Display results
<div>
  <h1>{script.title}</h1>
  <p>{script.description}</p>
  
  <audio src={audioUrl} controls />
  
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
2. Generate audio from the (edited) script

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
  "audio_url": "/audio/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
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
    setAudioUrl(`http://localhost:8000${data.audio_url}`);
  }
};
```

---

## 6. GET /audio/{job_id} - Download Audio

### Request
```bash
curl -X GET "http://localhost:8000/audio/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  --output podcast.wav
```

Returns: `audio/wav` file

### Important Notes on Audio URLs

**MVP (Current):**
- Audio files are stored locally in `app/outputs/`
- URLs are **permanent** until server restart or manual cleanup
- Files persist indefinitely

**Production (Future with S3):**
- Will use presigned URLs with expiration
- Typical expiration: 1-24 hours
- Frontend should download/cache audio after generation

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

### 500 Internal Server Error
```json
{
  "detail": "Script generation error: ..."
}
```

---

## Running the API

### Development
```bash
cd app
pip install fastapi uvicorn python-multipart
python main.py
# or
uvicorn main:app --reload --port 8000
```

### Environment Variables
Create `.env` file:
```
GEMINI_API_KEY=your_gemini_api_key
X_API_KEY=your_custom_api_key  # Optional, defaults to dev-api-key-12345
```

### Swagger UI
Once running, visit: `http://localhost:8000/docs`

---

## Typical React Flow

```
1. On mount: GET /voices → Display voice selector with audio previews
2. On mount: GET /tts-models → Populate model dropdown
3. User inputs text, selects voices
4. On submit: POST /generate-podcast-with-script
5. Display script dialogue + play audio from audio_url
6. Optional: Download audio via GET /audio/{job_id}
```
