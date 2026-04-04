"""
config.py
Global constants and default settings for the podcast generation pipeline.
"""

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_DEFAULT_MODEL       = "gemini-pro-latest"
GEMINI_DEFAULT_TEMPERATURE = 0.7
GEMINI_DEFAULT_RETRIES     = 2
GEMINI_INITIAL_BACKOFF     = 2.0          # seconds; doubles on each retry
GEMINI_REQUEST_TIMEOUT     = 300          # seconds
GEMINI_BASE_URL            = "https://generativelanguage.googleapis.com/v1beta"

# ── ElevenLabs ────────────────────────────────────────────────────────────────
ELEVENLABS_OUTPUT_FORMAT   = "mp3_44100_128"   # native mp3, 44.1 kHz, 128 kbps
ELEVENLABS_DEFAULT_OUTPUT  = "podcast_output.mp3"

# ── Podcast pipeline ──────────────────────────────────────────────────────────
MIN_SPEAKERS               = 2
MAX_SPEAKERS               = 4
DEFAULT_NUM_SPEAKERS       = 2