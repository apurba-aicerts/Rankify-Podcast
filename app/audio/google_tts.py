# from google import genai
# from google.genai import types
# import wave

# # Function to save PCM data to a WAV file
# def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
#     with wave.open(filename, "wb") as wf:
#         wf.setnchannels(channels)
#         wf.setsampwidth(sample_width)
#         wf.setframerate(rate)
#         wf.writeframes(pcm)

# # Initialize client with API key
# client = genai.Client(api_key="")  # <- Replace with your key

# prompt = """TTS the following conversation between Joe and Jane:
# Joe: How's it going today Jane?
# Jane: Not too bad, how about you?"""

# response = client.models.generate_content(
#     model="gemini-2.5-flash-preview-tts",
#     contents=prompt,
#     config=types.GenerateContentConfig(
#         response_modalities=["AUDIO"],
#         speech_config=types.SpeechConfig(
#             multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
#                 speaker_voice_configs=[
#                     types.SpeakerVoiceConfig(
#                         speaker='Joe',
#                         voice_config=types.VoiceConfig(
#                             prebuilt_voice_config=types.PrebuiltVoiceConfig(
#                                 voice_name='Kore',
#                             )
#                         )
#                     ),
#                     types.SpeakerVoiceConfig(
#                         speaker='Jane',
#                         voice_config=types.VoiceConfig(
#                             prebuilt_voice_config=types.PrebuiltVoiceConfig(
#                                 voice_name='Puck',
#                             )
#                         )
#                     ),
#                 ]
#             )
#         )
#     )
# )

# # Extract audio data and save
# data = response.candidates[0].content.parts[0].inline_data.data
# wave_file("out.wav", data)
# print("Saved out.wav successfully!")

from google import genai
from google.genai import types
import wave
import os
from dotenv import load_dotenv
load_dotenv()

class MultiSpeakerTTS:
    def __init__(self):
        """
        Initialize the Google GenAI client with an API key.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)

    @staticmethod
    def save_wave_file(filename: str, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2):
        """
        Save raw PCM bytes to a WAV file.
        """
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    def generate_tts(self, dialogue: str, speaker_voice_map: dict, output_file: str = "out.wav"):
        """
        Generate a multi-speaker TTS WAV file.

        Parameters:
            dialogue (str): Full text of the conversation.
            speaker_voice_map (dict): Mapping of speaker names to voice names.
                                      Example: {"Joe": "Kore", "Jane": "Puck"}
            output_file (str): Output WAV file name.
        """
        # Prepare speaker voice configs
        speaker_configs = [
            types.SpeakerVoiceConfig(
                speaker=speaker,
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            )
            for speaker, voice in speaker_voice_map.items()
        ]

        # Call Google Gemini TTS
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=dialogue,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=speaker_configs
                    )
                )
            )
        )

        # Extract PCM audio and save
        pcm_data = response.candidates[0].content.parts[0].inline_data.data
        self.save_wave_file(output_file, pcm_data)
        print(f"Saved {output_file} successfully!")


# ---------------------------
# Example usage
# ---------------------------
if __name__ == "__main__":
    api_key = "YOUR_API_KEY_HERE"
    dialogue_text = """TTS the following conversation between Joe and Jane:
Joe: How's it going today Jane?
Jane: Not too bad, how about you?"""

    speaker_voice_mapping = {
        "Joe": "Kore",
        "Jane": "Puck"
    }

    tts = MultiSpeakerTTS()
    tts.generate_tts(dialogue_text, speaker_voice_mapping, output_file="out.wav")
