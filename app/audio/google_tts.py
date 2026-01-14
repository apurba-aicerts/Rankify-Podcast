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

# from google import genai
# from google.genai import types
# import wave
# import os
# from dotenv import load_dotenv
# load_dotenv()

# class MultiSpeakerTTS:
#     def __init__(self):
#         """
#         Initialize the Google GenAI client with an API key.
#         """
#         api_key = os.getenv("GEMINI_API_KEY")
#         self.client = genai.Client(api_key=api_key)

#     @staticmethod
#     def save_wave_file(filename: str, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2):
#         """
#         Save raw PCM bytes to a WAV file.
#         """
#         with wave.open(filename, "wb") as wf:
#             wf.setnchannels(channels)
#             wf.setsampwidth(sample_width)
#             wf.setframerate(rate)
#             wf.writeframes(pcm)

#     def generate_tts(self, dialogue: str, speaker_voice_map: dict, output_file: str = "out.wav"):
#         """
#         Generate a multi-speaker TTS WAV file.

#         Parameters:
#             dialogue (str): Full text of the conversation.
#             speaker_voice_map (dict): Mapping of speaker names to voice names.
#                                       Example: {"Joe": "Kore", "Jane": "Puck"}
#             output_file (str): Output WAV file name.
#         """
#         # Prepare speaker voice configs
#         speaker_configs = [
#             types.SpeakerVoiceConfig(
#                 speaker=speaker,
#                 voice_config=types.VoiceConfig(
#                     prebuilt_voice_config=types.PrebuiltVoiceConfig(
#                         voice_name=voice
#                     )
#                 )
#             )
#             for speaker, voice in speaker_voice_map.items()
#         ]

#         # Call Google Gemini TTS
#         response = self.client.models.generate_content(
#             model="gemini-2.5-pro-preview-tts",#"gemini-2.5-flash-preview-tts",
#             contents=dialogue,
#             config=types.GenerateContentConfig(
#                 response_modalities=["AUDIO"],
#                 speech_config=types.SpeechConfig(
#                     multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
#                         speaker_voice_configs=speaker_configs
#                     )
#                 )
#             )
#         )

#         # Extract PCM audio and save
#         pcm_data = response.candidates[0].content.parts[0].inline_data.data
#         self.save_wave_file(output_file, pcm_data)
#         print(f"Saved {output_file} successfully!")

#         prompt_token_count = response.usage_metadata.prompt_token_count
#         candidates_token_count = response.usage_metadata.candidates_token_count
#         approx_price = (prompt_token_count * 0.0000005 + candidates_token_count*0.00001)  # Example pricing
#         print(f"Approximate TTS Cost: ${approx_price:.6f}")
#         print(f"TTS Tokens: input={response.usage_metadata.prompt_token_count}, output={response.usage_metadata.candidates_token_count}, total={response.usage_metadata.total_token_count}")
# # ---------------------------
# # Example usage
# # ---------------------------
# if __name__ == "__main__":
#     api_key = "YOUR_API_KEY_HERE"
#     dialogue_text = """TTS the following conversation between Joe and Jane:
# Joe: How's it going today Jane?
# Jane: Not too bad, how about you?"""

#     speaker_voice_mapping = {
#         "Joe": "Kore",
#         "Jane": "Puck"
#     }

#     tts = MultiSpeakerTTS()
#     tts.generate_tts(dialogue_text, speaker_voice_mapping, output_file="out.wav")


import os
import wave
from typing import Dict
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()


class MultiSpeakerTTS:
    """
    Thin execution-only wrapper over Google Gemini Multi-Speaker TTS.
    All decisions (model, voices) must be resolved by the caller.
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing")

        self.client = genai.Client(api_key=api_key)

    # ------------------------------------------------------------------
    # Audio Utils
    # ------------------------------------------------------------------

    @staticmethod
    def save_wave_file(
        filename: str,
        pcm: bytes,
        channels: int = 1,
        rate: int = 24000,
        sample_width: int = 2,
    ) -> None:
        """
        Save raw PCM audio to a WAV file.
        """
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    # ------------------------------------------------------------------
    # Main TTS API
    # ------------------------------------------------------------------

    def generate_tts(
        self,
        dialogue: str,
        speaker_voice_map: Dict[str, str],
        tts_model: str = "gemini-2.5-pro-preview-tts",
        output_file: str = "out.wav",
    ) -> dict:
        """
        Generate multi-speaker TTS audio.

        Args:
            dialogue: Full dialogue text
            speaker_voice_map: {"Speaker": "VoiceName"}
            tts_model: Gemini TTS model name
            output_file: Output WAV path

        Returns:
            Metadata dict (tokens, output file)
        """
        print(speaker_voice_map)
        speaker_voice_configs = [
            types.SpeakerVoiceConfig(
                speaker=speaker,
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                ),
            )
            for speaker, voice in speaker_voice_map.items()
        ]
        print(speaker_voice_configs)
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


# ----------------------------------------------------------------------
# Simple Manual Test (CLI)
# ----------------------------------------------------------------------

def main():
    """
    Minimal example to verify TTS works.
    """

    dialogue_text = """TTS the following conversation between Maya and Liam:
Maya: You know, for the last few years, we’ve gotten really used to AI that talks. We ask a question, it writes a poem or summarizes a document. It feels like magic.

Liam: It does. But it’s a very specific kind of magic. It’s passive. It’s waiting for you to prompt it, and its output is usually just... text.

Maya: Right. But looking at this new research on Manus AI, it feels like we’re turning a corner. We’re moving from AI that talks to AI that... acts?

Liam: Exactly. That is the core promise of Manus AI. It was introduced in early 2025 by a Chinese startup called Monica.im. And the tagline they use is really telling. They say it bridges the gap between "mind" and "hand."

Maya: Mind and hand. That’s a beautiful way to put it. So, if GPT-4 is the mind, Manus is trying to be the hand?

Liam: Precisely. Think about the difference between a consultant and an executive assistant. A consultant—like a traditional Large Language Model—gives you advice. You ask, "How do I plan a trip to Paris?" and it gives you a list of ideas.

Maya: And then I have to go open twenty tabs and actually book everything.

Liam: Right. But Manus is designed as an autonomous agent. In that same scenario, it wouldn't just give you advice. It would autonomously plan the itinerary, go out to the web, gather the specific flight and hotel details, and present you with a finalized plan ready to go. It executes the workflow.

Maya: It’s doing the clicking and the searching for me. That sounds like a massive leap in complexity.

Liam: It is. And the metrics back that up. There’s a benchmark called GAIA—it tests an AI’s ability to use tools and solve real-world problems. It’s notoriously difficult.

Maya: How did Manus do?

Liam: It reportedly crushed it. It outperformed GPT-4 and set a new record, scoring over 65%. That’s significant because it shows the system isn't just hallucinating answers; it’s reasoning through steps to get a job done.

Maya: It’s interesting you mention reasoning. The research paper calls this a glimpse into the future of "General Purpose AI Agents." It sounds like they’re positioning this as a stepping stone toward AGI—artificial general intelligence.

Liam: I think that’s a fair assessment. When you have an AI that can handle tasks across healthcare, finance, gaming, and manufacturing without needing hand-holding for every single step... you’re looking at a new paradigm of work.

Maya: It changes the human role, doesn't it? We stop being the operators and start being the... managers?

Liam: That’s the vision. Instead of micromanaging the software, you provide the high-level intention. You say "Fix this financial report," and the "hand" of the AI goes and does it. Manus is really the first credible signal that this future is arriving faster than we thought.

Maya: A world where the machine doesn't just think, but does. A fascinating, if slightly intimidating, prospect. Thanks for breaking it down, Liam.

Liam: My pleasure, Maya.
"""

    speaker_voice_map = {
        "Maya": "achernar",
        "Liam": "enceladus",
    }

    tts_model = "gemini-2.5-pro-preview-tts"
    output_file = "sample_podcast_8.wav"

    tts = MultiSpeakerTTS()

    result = tts.generate_tts(
        dialogue=dialogue_text,
        speaker_voice_map=speaker_voice_map,
        tts_model=tts_model,
        output_file=output_file,
    )

    print("✅ TTS generation successful")
    print(f"📁 Output file: {result['output_file']}")
    print(
        f"🔢 Tokens — input: {result['input_tokens']}, "
        f"output: {result['output_tokens']}, "
        f"total: {result['total_tokens']}"
    )


if __name__ == "__main__":
    main()
