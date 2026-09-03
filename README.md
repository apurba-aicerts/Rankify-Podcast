# Rankify Podcast

Project-based podcast generation (Gemini script + TTS, S3 audio, PostgreSQL) with a React dashboard UI.

## Structure

```
Rankify-Podcast/
├── app/                    # FastAPI backend
├── frontend/               # React + Vite dashboard UI
├── experiment/             # Test scripts
└── .env                    # Secrets (not committed)
```

## Backend

```powershell
cd app
docker compose up -d postgres
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8001
```

- Swagger: http://127.0.0.1:8001/docs
- API docs: [app/API_DOCUMENTATION.md](app/API_DOCUMENTATION.md)

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (API must be running on port 8001).

Copy `frontend/.env.example` to `frontend/.env` and set:

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
VITE_API_KEY=AICERTS@123
```

## Env vars (backend)

See `app/API_DOCUMENTATION.md` for `GEMINI_API_KEY`, AWS, `DATABASE_URL`, `X_API_KEY`.
