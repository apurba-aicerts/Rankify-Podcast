import os
import wave
from typing import Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class MultiSpeakerTTS:
    """Google Gemini multi-speaker TTS wrapper."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing")
        self.client = genai.Client(api_key=api_key)

    @staticmethod
    def save_wave_file(
        filename: str,
        pcm: bytes,
        channels: int = 1,
        rate: int = 24000,
        sample_width: int = 2,
    ) -> None:
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    def generate_tts(
        self,
        dialogue: str,
        speaker_voice_map: Dict[str, str],
        tts_model: str = "gemini-2.5-pro-preview-tts",
        output_file: str = "out.wav",
    ) -> dict:
        speaker_voice_configs = [
            types.SpeakerVoiceConfig(
                speaker=speaker,
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                ),
            )
            for speaker, voice in speaker_voice_map.items()
        ]

        response = self.client.models.generate_content(
            model=tts_model,
            contents=dialogue,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=speaker_voice_configs
                    )
                ),
            ),
        )

        pcm_audio = response.candidates[0].content.parts[0].inline_data.data
        self.save_wave_file(output_file, pcm_audio)

        return {
            "output_file": output_file,
            "input_tokens": response.usage_metadata.prompt_token_count,
            "output_tokens": response.usage_metadata.candidates_token_count,
            "total_tokens": response.usage_metadata.total_token_count,
        }
