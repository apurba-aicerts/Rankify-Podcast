import os
import wave
from google import genai
from google.genai import types
from dotenv import load_dotenv
from google.genai.errors import ClientError

# -------------------------------------------------
# Load environment variables
# -------------------------------------------------

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY not found in environment")

# -------------------------------------------------
# Config
# -------------------------------------------------

TTS_MODEL = "gemini-2.5-flash-preview-tts"

VOICE_IDS = [
    "achernar", "achird", "algenib", "algieba", "alnilam",
    "aoede", "autonoe", "callirrhoe", "charon", "despina",
    "enceladus", "erinome", "fenrir", "gacrux", "iapetus",
    "kore", "laomedeia", "leda", "orus", "puck",
    "pulcherrima", "rasalgethi", "sadachbia", "sadaltager",
    "schedar", "sulafat", "umbriel", "vindemiatrix",
    "zephyr", "zubenelgenubi",
]

OUTPUT_DIR = "assets/voice_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def save_wave_file(
    filename: str,
    pcm: bytes,
    channels: int = 1,
    rate: int = 24000,
    sample_width: int = 2,
):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def display_name(voice_id: str) -> str:
    return voice_id.capitalize()

# -------------------------------------------------
# Main
# -------------------------------------------------

def main():
    client = genai.Client(api_key=API_KEY)

    for voice_id in VOICE_IDS:
        output_path = os.path.join(OUTPUT_DIR, f"{voice_id}.wav")

        # ✅ SKIP IF ALREADY GENERATED
        if os.path.exists(output_path):
            print(f"⏭️  Skipping {voice_id} (already exists)")
            continue

        try:
            print(f"🔊 Generating sample for voice: {voice_id}")

            text = (
                f"Hello, this is a sample of the {display_name(voice_id)} voice "
                f"for podcast narration."
            )

            response = client.models.generate_content(
                model=TTS_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_id
                            )
                        )
                    ),
                ),
            )

            pcm = response.candidates[0].content.parts[0].inline_data.data
            save_wave_file(output_path, pcm)

            usage = response.usage_metadata
            print(
                f"   ✅ Saved {voice_id}.wav | "
                f"in={usage.prompt_token_count}, "
                f"out={usage.candidates_token_count}"
            )

        except ClientError as e:
            print(f"   ⚠️ Skipping {voice_id}: {e.message}")

    print("\n🎉 Voice sample generation completed.")

if __name__ == "__main__":
    main()
