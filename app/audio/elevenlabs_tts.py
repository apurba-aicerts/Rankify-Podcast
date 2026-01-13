# from dotenv import load_dotenv
# import os
# from elevenlabs.client import ElevenLabs

# load_dotenv()

# client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# dialogue = [
#     {
#         "text": "[cheerfully] Hello, how are you?",
#         "voice_id": "9BWtsMINqrJLrRacOk9x",
#     },
#     {
#         "text": "[stuttering] I'm... I'm doing well, thank you",
#         "voice_id": "IKne3meq5aSn9XLyUdCD",
#     },
# ]

# # This is a generator (stream of bytes chunks)
# audio_stream = client.text_to_dialogue.convert(inputs=dialogue)

# output_path = "dialogue.mp3"
# with open(output_path, "wb") as f:
#     for chunk in audio_stream:
#         if isinstance(chunk, bytes):
#             f.write(chunk)

# print(f"Saved multi-speaker audio to {output_path}")


from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import os

load_dotenv()

elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

audio = elevenlabs.text_to_speech.convert(
    text="The first move is what sets everything in motion.",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

# Save audio to file
output_path = "output.mp3"
with open(output_path, "wb") as f:
    if isinstance(audio, bytes):
        f.write(audio)
    else:
        # If audio is a generator/iterator of bytes
        for chunk in audio:
            f.write(chunk)

print(f"Audio saved to {output_path}")


