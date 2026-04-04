# Podcast Generator

Text → Gemini script → ElevenLabs multi-speaker MP3.

## Structure

```
podcast_app/
├── config.py                    # Constants & defaults
├── schemas/
│   └── podcast_schema.py        # PodcastScript, Speaker, DialogueTurn
├── prompts/
│   └── podcast_prompt.py        # build_podcast_prompt()
├── clients/
│   ├── gemini_client.py         # run_gemini_agent()
│   └── elevenlabs_client.py     # fetch_available_voices(), generate_audio()
├── core/
│   └── podcast_pipeline.py      # generate_script(), synthesise_audio(), run_podcast_pipeline()
├── ui/
│   └── streamlit_app.py         # Streamlit UI (no business logic)
└── test_main.py                 # CLI test runner with full logging
```

## Setup

```bash
pip install streamlit elevenlabs google-generativeai pydantic python-dotenv requests
```

Create `.env` at the project root:
```
GEMINI_API_KEY=your_gemini_key
ELEVENLABS_API_KEY=your_elevenlabs_key
```

## Run

**Streamlit UI:**
```bash
streamlit run ui/streamlit_app.py
```

**CLI test (debug all stages):**
```bash
python test_main.py
```
Outputs: `test_output.mp3`, `test_script.json`, `test_run.log`

## Naming Conventions

| Thing        | Convention       | Example                    |
|--------------|------------------|----------------------------|
| Files        | snake_case.py    | gemini_client.py           |
| Classes      | PascalCase       | PodcastScript              |
| Functions    | verb_noun        | fetch_available_voices()   |
| Constants    | UPPER_SNAKE_CASE | DEFAULT_NUM_SPEAKERS       |
| Local vars   | snake_case       | speaker_voice_map          |
| Pydantic fields | snake_case    | voice_id                   |