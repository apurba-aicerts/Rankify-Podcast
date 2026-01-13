from google import genai
from google.genai import types
import wave
import os
from dotenv import load_dotenv

load_dotenv()

class SingleSpeakerTTS:
    def __init__(self):
        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

    @staticmethod
    def save_wave_file(
        filename: str,
        pcm: bytes,
        channels: int = 1,
        rate: int = 24000,
        sample_width: int = 2
    ):
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    def synthesize(
        self,
        text: str,
        voice_name: str,
        output_file: str
    ):
        response = self.client.models.generate_content(
            model="gemini-2.5-pro-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                )
            )
        )

        pcm = response.candidates[0].content.parts[0].inline_data.data
        self.save_wave_file(output_file, pcm)

import json
import wave
import os

class PodcastTTSBuilder:
    def __init__(self, speaker_voice_map: dict):
        self.tts = SingleSpeakerTTS()
        self.speaker_voice_map = speaker_voice_map
        self.temp_files = []

    def generate_from_script(self, script: dict, output_file="podcast.wav"):
        for i, turn in enumerate(script["dialogue"]):
            speaker = turn["speaker"]
            text = turn["text"]

            voice = self.speaker_voice_map[speaker]
            temp_wav = f"temp_{i:03d}_{speaker}.wav"

            prompt = f"""
Convert the following text into natural podcast speech.

Speaker: {speaker}
Text: {text}
"""
            self.tts.synthesize(prompt, voice, temp_wav)
            self.temp_files.append(temp_wav)

        self._merge_wavs(output_file)
        self._cleanup()

    def _merge_wavs(self, output_file):
        with wave.open(self.temp_files[0], "rb") as wf:
            params = wf.getparams()

        with wave.open(output_file, "wb") as out:
            out.setparams(params)
            for wav_file in self.temp_files:
                with wave.open(wav_file, "rb") as wf:
                    out.writeframes(wf.readframes(wf.getnframes()))

    def _cleanup(self):
        for f in self.temp_files:
            os.remove(f)

if __name__ == "__main__":
    scripts_path = r"C:\AI Certs\Rankify-Podcast\app\netcom_podcast_script.json"
    with open(scripts_path) as f:
        script = json.load(f)

    SPEAKER_VOICE_MAP = {
        "Alex": "Kore",
        "Jamie": "Puck"
    }

    builder = PodcastTTSBuilder(SPEAKER_VOICE_MAP)
    builder.generate_from_script(script, output_file="final_podcast.wav")
