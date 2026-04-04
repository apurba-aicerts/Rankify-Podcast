import wave
import os
import time
import json
from collections import deque
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# ==============================
# CONFIG
# ==============================

OUTPUT_DIR = "podcast_output"
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")

os.makedirs(TEMP_DIR, exist_ok=True)

VOICE_MAP = {
    "Alex": "Kore",
    "Jamie": "Puck"
}

SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2
CHANNELS = 1

PAUSE_BETWEEN_LINES = 0.4
PAUSE_SPEAKER_CHANGE = 0.8

client = genai.Client(api_key=api_key)

# ==============================
# RATE LIMITER
# ==============================

class RateLimiter:
    def __init__(self, max_requests_per_min=10, max_tokens_per_min=10000):
        self.max_requests = max_requests_per_min
        self.max_tokens = max_tokens_per_min
        self.request_times = deque()
        self.token_usage = deque()  # (timestamp, tokens)

    def estimate_tokens(self, text):
        return max(1, len(text) // 4)

    def wait_if_needed(self, text):
        now = time.time()
        tokens_needed = self.estimate_tokens(text)

        # Clean old entries
        while self.request_times and now - self.request_times[0] > 60:
            self.request_times.popleft()

        while self.token_usage and now - self.token_usage[0][0] > 60:
            self.token_usage.popleft()

        current_requests = len(self.request_times)
        current_tokens = sum(t for _, t in self.token_usage)

        if current_requests >= self.max_requests or (current_tokens + tokens_needed) > self.max_tokens:
            sleep_time = 60 - (now - self.request_times[0])
            sleep_time = max(sleep_time, 1)

            print(f"⏳ Rate limit hit. Sleeping for {sleep_time:.2f}s...")
            time.sleep(sleep_time)

            return self.wait_if_needed(text)

        # Record usage
        self.request_times.append(now)
        self.token_usage.append((now, tokens_needed))


limiter = RateLimiter(10, 10000)

# ==============================
# UTIL: SAVE WAV
# ==============================

def save_wav(filename, pcm_data):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)

# ==============================
# UTIL: SILENCE
# ==============================

def generate_silence(duration_sec):
    num_samples = int(SAMPLE_RATE * duration_sec)
    return b"\x00\x00" * num_samples

# ==============================
# TTS CALL
# ==============================

def generate_tts(text, voice):
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            ),
        )
    )

    return response.candidates[0].content.parts[0].inline_data.data

# ==============================
# SAFE TTS (RATE LIMIT + RETRY)
# ==============================

def safe_generate_tts(text, voice, max_retries=5):
    for attempt in range(max_retries):
        try:
            limiter.wait_if_needed(text)

            return generate_tts(
                f"Speak in a natural podcast conversational tone: {text}",
                voice
            )

        except Exception as e:
            print(f"⚠️ Error: {e}")

            if "429" in str(e) or "rate" in str(e).lower():
                wait_time = 2 ** attempt
                print(f"🔁 Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e

    raise Exception("❌ Max retries exceeded")

# ==============================
# MAIN PODCAST GENERATOR
# ==============================

def generate_podcast(podcast_json):
    dialogue = podcast_json["dialogue"]

    final_audio = b""
    speaker_audio_map = {speaker: b"" for speaker in VOICE_MAP}

    prev_speaker = None

    for i, line in enumerate(dialogue):
        speaker = line["speaker"]
        text = line["text"]

        voice = VOICE_MAP.get(speaker, "Kore")

        print(f"🎤 [{i+1}/{len(dialogue)}] {speaker}")

        pcm = safe_generate_tts(text, voice)

        # Save temp chunk
        temp_file = os.path.join(TEMP_DIR, f"{i}_{speaker}.wav")
        save_wav(temp_file, pcm)

        # Pause logic
        if prev_speaker and prev_speaker != speaker:
            silence = generate_silence(PAUSE_SPEAKER_CHANGE)
        else:
            silence = generate_silence(PAUSE_BETWEEN_LINES)

        # Append
        final_audio += pcm + silence
        speaker_audio_map[speaker] += pcm + silence

        prev_speaker = speaker

    # ==============================
    # SAVE FINAL
    # ==============================
    final_path = os.path.join(OUTPUT_DIR, "podcast.wav")
    save_wav(final_path, final_audio)
    print(f"\n✅ Final podcast saved: {final_path}")

    # ==============================
    # SAVE PER SPEAKER
    # ==============================
    for speaker, audio in speaker_audio_map.items():
        path = os.path.join(OUTPUT_DIR, f"{speaker}.wav")
        save_wav(path, audio)
        print(f"✅ {speaker} audio saved: {path}")

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    json_file = r"C:\AI Certs\Rankify-Podcast\app\netcom_podcast_script.json"
    with open(json_file, "r", encoding="utf-8") as f:
        podcast_json = json.load(f)

    generate_podcast(podcast_json)