# import os
# import time
# import json
# import subprocess
# from collections import deque
# from dotenv import load_dotenv
# from elevenlabs.client import ElevenLabs

# # ==============================
# # LOAD ENV
# # ==============================
# load_dotenv()
# client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# # ==============================
# # CONFIG
# # ==============================
# OUTPUT_DIR = "podcast_output"
# TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")
# os.makedirs(TEMP_DIR, exist_ok=True)

# VOICE_MAP = {
#     "Alex": "JBFqnCBsd6RMkjVDRZzb",
#     "Jamie": "EXAVITQu4vr4xnSDxMaL"
# }

# PAUSE_BETWEEN_LINES = 0.4
# PAUSE_SPEAKER_CHANGE = 0.8

# # ==============================
# # RATE LIMITER
# # ==============================

# class RateLimiter:
#     def __init__(self, max_requests_per_min=10):
#         self.max_requests = max_requests_per_min
#         self.request_times = deque()

#     def wait_if_needed(self):
#         now = time.time()

#         while self.request_times and now - self.request_times[0] > 60:
#             self.request_times.popleft()

#         if len(self.request_times) >= self.max_requests:
#             sleep_time = 60 - (now - self.request_times[0])
#             sleep_time = max(sleep_time, 1)
#             print(f"⏳ Sleeping {sleep_time:.2f}s")
#             time.sleep(sleep_time)
#             return self.wait_if_needed()

#         self.request_times.append(now)


# limiter = RateLimiter(10)

# # ==============================
# # TTS
# # ==============================

# def generate_tts(text, voice_id):
#     audio_stream = client.text_to_speech.convert(
#         text=text,
#         voice_id=voice_id,
#         model_id="eleven_v3",
#         output_format="mp3_44100_128",
#     )
#     return b"".join(audio_stream)

# def safe_generate_tts(text, voice_id):
#     limiter.wait_if_needed()
#     return generate_tts(f"Podcast tone: {text}", voice_id)

# # ==============================
# # CREATE SILENCE USING FFMPEG
# # ==============================

# def create_silence(path, duration):
#     subprocess.run([
#         "ffmpeg",
#         "-f", "lavfi",
#         "-i", "anullsrc=r=44100:cl=mono",
#         "-t", str(duration),
#         "-q:a", "9",
#         "-acodec", "libmp3lame",
#         path
#     ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# # ==============================
# # MERGE FILES USING FFMPEG
# # ==============================

# # def merge_audio(file_list, output_path):
# #     list_file = os.path.join(TEMP_DIR, "files.txt")

# #     with open(list_file, "w") as f:
# #         for file in file_list:
# #             f.write(f"file '{file}'\n")

# #     subprocess.run([
# #         "ffmpeg",
# #         "-f", "concat",
# #         "-safe", "0",
# #         "-i", list_file,
# #         "-c", "copy",
# #         output_path
# #     ])

# def merge_audio(file_list, output_path):
#     list_file = os.path.join(TEMP_DIR, "files.txt")

#     with open(list_file, "w") as f:
#         for file in file_list:
#             f.write(f"file '{os.path.abspath(file)}'\n")

#     subprocess.run([
#         "ffmpeg",
#         "-f", "concat",
#         "-safe", "0",
#         "-i", list_file,
#         "-c", "copy",
#         output_path
#     ], check=True)

# # ==============================
# # MAIN
# # ==============================

# def generate_podcast(podcast_json):
#     dialogue = podcast_json["dialogue"]

#     all_files = []
#     speaker_files = {s: [] for s in VOICE_MAP}

#     prev_speaker = None

#     for i, line in enumerate(dialogue):
#         speaker = line["speaker"]
#         text = line["text"]
#         voice_id = VOICE_MAP.get(speaker)

#         print(f"🎤 [{i+1}/{len(dialogue)}] {speaker}")

#         # Generate speech
#         audio_bytes = safe_generate_tts(text, voice_id)

#         speech_path = os.path.join(TEMP_DIR, f"{i}_{speaker}.mp3")
#         with open(speech_path, "wb") as f:
#             f.write(audio_bytes)

#         all_files.append(speech_path)
#         speaker_files[speaker].append(speech_path)

#         # Add pause
#         if prev_speaker and prev_speaker != speaker:
#             pause_dur = PAUSE_SPEAKER_CHANGE
#         else:
#             pause_dur = PAUSE_BETWEEN_LINES

#         silence_path = os.path.join(TEMP_DIR, f"silence_{i}.mp3")
#         create_silence(silence_path, pause_dur)

#         all_files.append(silence_path)
#         speaker_files[speaker].append(silence_path)

#         prev_speaker = speaker

#     # ==============================
#     # FINAL MERGE
#     # ==============================
#     final_path = os.path.join(OUTPUT_DIR, "podcast.mp3")
#     merge_audio(all_files, final_path)

#     print(f"\n✅ Final podcast: {final_path}")

#     # ==============================
#     # PER SPEAKER
#     # ==============================
#     for speaker, files in speaker_files.items():
#         path = os.path.join(OUTPUT_DIR, f"{speaker}.mp3")
#         merge_audio(files, path)
#         print(f"✅ {speaker}: {path}")

# # ==============================
# # RUN
# # ==============================

# if __name__ == "__main__":
#     json_file = r"C:\AI Certs\Rankify-Podcast\app\netcom_podcast_script.json"

#     with open(json_file, "r", encoding="utf-8") as f:
#         podcast_json = json.load(f)

#     generate_podcast(podcast_json)

# from dotenv import load_dotenv
# import os
# from elevenlabs import ElevenLabs,DialogueInput
# import wave  # Optional for WAV handling

# load_dotenv()
# client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# dialogue = [
#     DialogueInput(
#         text= "[excited] Welcome to our tech podcast!",
#         voice_id= "hpp4J3VqNfWAUOO0d1Us"  # Speaker 1: Energetic host
#     ),
#     DialogueInput(
#         text= "[calm] Thanks for having me.",
#         voice_id= "EXAVITQu4vr4xnSDxMaL"  # Speaker 2: Guest expert
#     ),
#     DialogueInput(
#         text= "[enthusiastic] AI is changing everything!",
#         voice_id= "FGY2WhTYpPnrIDTdsKH5"   # Speaker 3: Co-host
#     ),
#     DialogueInput(
#         text= "[thoughtful] Let's dive into computer vision.",
#         voice_id= "nPczCjzI2devNBz1zQrb"   # Speaker 4: Analyst
#     )
#     # Add more entries for longer convos
# ]

# audio_stream = client.text_to_dialogue.convert(inputs=dialogue)

# output_path = "multi_speaker_podcast.mp3"
# with open(output_path, "wb") as f:
#     for chunk in audio_stream:
#         if isinstance(chunk, bytes):
#             f.write(chunk)

# print(f"Saved 4-speaker podcast to {output_path}")

# import os

# import requests
# from dotenv import load_dotenv
# load_dotenv()
# # Replace with your actual API key
# API_KEY = os.getenv("ELEVENLABS_API_KEY")
# VOICE_ID = "nPczCjzI2devNBz1zQrb"

# url = f"https://api.elevenlabs.io/v1/voices/{VOICE_ID}"

# headers = {
#     "Accept": "application/json",
#     "xi-api-key": API_KEY
# }

# response = requests.get(url, headers=headers)

# print(response)
# if response.status_code == 200:
#     voice_data = response.json()
#     print(voice_data)
#     print(f"Voice Name: {voice_data.get('name')}")
#     print(f"Category: {voice_data.get('category')}")
#     print(f"Description: {voice_data.get('description')}")
# else:
#     print(f"Error: {response.status_code} - {response.text}")

import os
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

# Load your API key from an .env file or set it directly
load_dotenv()
client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")
)

# Fetch all available voices
response = client.voices.get_all()
print(response)
for voice in response.voices:
    print(f"Name: {voice.name} |Description: {voice.description} | ID: {voice.voice_id} | Category: {voice.category}")

voice_id = "nPczCjzI2devNBz1zQrb" 
voice_metadata = client.voices.get(voice_id=voice_id)
print(f"Metadata for voice ID {voice_id}:")
print(f"Name: {voice_metadata}")