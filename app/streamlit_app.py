
# import asyncio
# import streamlit as st
# from typing import Dict

# from schemas.podcast import PodcastScript
# from prompts.podcast import podcast_system_instruction
# from core.gemini_client import run_gemini_agent
# from audio.google_tts import MultiSpeakerTTS

# # ------------------------------------------------------------------
# # Async Script Generator Wrapper (Streamlit-safe)
# # ------------------------------------------------------------------

# async def generate_script_async(
#     input_text: str,
#     num_speakers: int,
#     model: str,
#     temperature: float
# ) -> PodcastScript | None:
#     return await run_gemini_agent(
#         instruction=podcast_system_instruction(num_speakers),
#         user_input=input_text,
#         output_type=PodcastScript,
#         model=model,
#         temperature=temperature,
#         retries=2,
#     )


# def generate_script(*args, **kwargs):
#     return asyncio.run(generate_script_async(*args, **kwargs))

# # ------------------------------------------------------------------
# # Streamlit UI
# # ------------------------------------------------------------------

# st.set_page_config(page_title="Podcast Generator", layout="wide")

# st.title("🎧 Text → Podcast → Multi-Speaker Audio")

# # ------------------------------------------------------------------
# # Sidebar – Model Controls
# # ------------------------------------------------------------------

# with st.sidebar:
#     st.header("⚙️ Generation Settings")

#     text_model = st.selectbox(
#         "Gemini Text Model",
#         [
#             "gemini-3-pro-preview",
#             "gemini-2.5-pro-preview",
#             "gemini-2.0-flash",
#         ],
#     )

#     tts_model = st.selectbox(
#         "Gemini TTS Model",
#         [
#             "gemini-2.5-pro-preview-tts",
#             "gemini-2.5-flash-preview-tts",
#         ],
#     )

#     num_speakers = st.slider("Number of Speakers", 2, 6, 2)
#     temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7)

# # ------------------------------------------------------------------
# # Input Text
# # ------------------------------------------------------------------

# input_text = st.text_area(
#     "📄 Input Content",
#     height=300,
#     placeholder="Paste article, paper, or notes here…",
# )

# # ------------------------------------------------------------------
# # Script Generation
# # ------------------------------------------------------------------

# if st.button("🧠 Generate Podcast Script"):
#     if not input_text.strip():
#         st.error("Please provide input text")
#     else:
#         with st.spinner("Generating podcast script…"):
#             script = generate_script(
#                 input_text=input_text,
#                 num_speakers=num_speakers,
#                 model=text_model,
#                 temperature=temperature,
#             )

#         if script is None:
#             st.error("Script generation failed")
#         else:
#             st.session_state.script = script
#             st.success("Podcast script generated")

# # ------------------------------------------------------------------
# # Display Script
# # ------------------------------------------------------------------

# if "script" in st.session_state:
#     script: PodcastScript = st.session_state.script

#     st.subheader("🎙️ Podcast Script")
#     st.markdown(f"### {script.title}")
#     st.write(script.description)

#     for turn in script.dialogue:
#         st.markdown(f"**{turn.speaker}:** {turn.text}")

#     # ------------------------------------------------------------------
#     # Voice Selection
#     # ------------------------------------------------------------------

#     st.subheader("🔊 Speaker Voice Assignment")

#     AVAILABLE_VOICES = [
#         "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda",
#         "Orus", "Aoede", "Callirhoe", "Autonoe", "Enceladus",
#         "Iapetus", "Umbriel", "Achernar", "Alnilam",
#     ]

#     speaker_voice_map: Dict[str, str] = {}

#     for speaker in script.speakers:
#         speaker_voice_map[speaker.name] = st.selectbox(
#             f"Voice for {speaker.name}",
#             AVAILABLE_VOICES,
#             key=speaker.name,
#         )

#     # ------------------------------------------------------------------
#     # TTS Generation
#     # ------------------------------------------------------------------

#     if st.button("🔊 Generate Audio"):
#         with st.spinner("Generating multi-speaker audio…"):
#             tts = MultiSpeakerTTS()

#             dialogue_lines = "\n".join(
#                 f"{turn.speaker}: {turn.text}" for turn in script.dialogue
#             )

#             dialogue_text = (
#                 f"TTS the following conversation between "
#                 f"{', '.join(speaker_voice_map.keys())}:\n{dialogue_lines}"
#             )

#             output_file = "podcast_output.wav"

#             tts.generate_tts(
#                 dialogue=dialogue_text,
#                 speaker_voice_map=speaker_voice_map,
#                 tts_model=tts_model,
#                 output_file=output_file,
#             )

#         st.success("Audio generated")

#         with open(output_file, "rb") as f:
#             st.audio(f.read(), format="audio/wav")
#             st.download_button(
#                 "⬇️ Download WAV",
#                 f,
#                 file_name="podcast.wav",
#             )


# import asyncio
# import streamlit as st
# from typing import Dict

# from schemas.podcast import PodcastScript
# from prompts.podcast import podcast_system_instruction
# from core.gemini_client import run_gemini_agent
# from audio.google_tts import MultiSpeakerTTS

# # ------------------------------------------------------------------
# # Async Script Generator Wrapper (Streamlit-safe)
# # ------------------------------------------------------------------

# async def generate_script_async(
#     input_text: str,
#     num_speakers: int,
#     model: str,
#     temperature: float
# ) -> PodcastScript | None:
#     return await run_gemini_agent(
#         instruction=podcast_system_instruction(num_speakers),
#         user_input=input_text,
#         output_type=PodcastScript,
#         model=model,
#         temperature=temperature,
#         retries=2,
#     )


# def generate_script(*args, **kwargs):
#     return asyncio.run(generate_script_async(*args, **kwargs))

# # ------------------------------------------------------------------
# # Streamlit Page Config
# # ------------------------------------------------------------------

# st.set_page_config(page_title="Podcast Generator", layout="wide")

# st.title("🎧 Text → Podcast → Multi-Speaker Audio")

# # ------------------------------------------------------------------
# # Sidebar – Global Controls (chosen BEFORE generation)
# # ------------------------------------------------------------------

# with st.sidebar:
#     st.header("⚙️ Generation Settings")

#     text_model = st.selectbox(
#         "Gemini Text Model",
#         [
#             "gemini-3-pro-preview",
#             "gemini-2.5-pro-preview",
#             "gemini-2.0-flash",
#         ],
#     )

#     tts_model = st.selectbox(
#         "Gemini TTS Model",
#         [
#             "gemini-2.5-pro-preview-tts",
#             "gemini-2.5-flash-preview-tts",
#         ],
#     )

#     num_speakers = st.slider("Number of Speakers", 2, 6, 2)
#     temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7)

#     st.divider()
#     st.header("🔊 Voice Selection")

#     AVAILABLE_VOICES = [
#         "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda",
#         "Orus", "Aoede", "Callirhoe", "Autonoe", "Enceladus",
#         "Iapetus", "Umbriel", "Achernar", "Alnilam",
#     ]

#     st.caption("Select one voice per speaker (based on number of speakers)")

#     selected_voices = []
#     for i in range(num_speakers):
#         voice = st.selectbox(
#             f"Voice for Speaker {i+1}",
#             AVAILABLE_VOICES,
#             key=f"voice_{i}",
#         )
#         selected_voices.append(voice)

# # ------------------------------------------------------------------
# # Input Text
# # ------------------------------------------------------------------

# st.subheader("📄 Input Content")

# input_text = st.text_area(
#     "Paste article, paper, or notes here",
#     height=280,
# )

# # ------------------------------------------------------------------
# # Generate Script + Audio (single flow)
# # ------------------------------------------------------------------

# if st.button("🚀 Generate Podcast Audio"):
#     if not input_text.strip():
#         st.error("Please provide input text")
#     else:
#         with st.spinner("Generating podcast script…"):
#             script = generate_script(
#                 input_text=input_text,
#                 num_speakers=num_speakers,
#                 model=text_model,
#                 temperature=temperature,
#             )

#         if script is None:
#             st.error("Script generation failed")
#         else:
#             # Store script
#             st.session_state.script = script

#             # Auto voice assignment (can be refined later)
#             speaker_voice_map = {
#                 speaker.name: selected_voices[i]
#                 for i, speaker in enumerate(script.speakers)
#             }


#             with st.spinner("Generating multi-speaker audio…"):
#                 tts = MultiSpeakerTTS()

#                 dialogue_lines = "\n".join(
#                     f"{turn.speaker}: {turn.text}" for turn in script.dialogue
#                 )

#                 dialogue_text = (
#                     f"TTS the following conversation between "
#                     f"{', '.join(speaker_voice_map.keys())}:\n{dialogue_lines}"
#                 )

#                 output_file = "podcast_output.wav"

#                 tts.generate_tts(
#                     dialogue=dialogue_text,
#                     speaker_voice_map=speaker_voice_map,
#                     tts_model=tts_model,
#                     output_file=output_file,
#                 )

#             st.session_state.audio_file = output_file
#             st.success("Podcast audio generated")

# # ------------------------------------------------------------------
# # OUTPUT SECTION (Audio FIRST, then Script)
# # ------------------------------------------------------------------

# if "audio_file" in st.session_state:
#     st.subheader("▶️ Podcast Audio")

#     with open(st.session_state.audio_file, "rb") as f:
#         st.audio(f.read(), format="audio/wav")
#         st.download_button(
#             "⬇️ Download WAV",
#             f,
#             file_name="podcast.wav",
#         )

# if "script" in st.session_state:
#     script: PodcastScript = st.session_state.script

#     st.subheader("📝 Podcast Transcription")
#     st.markdown(f"### {script.title}")
#     st.write(script.description)

#     for turn in script.dialogue:
#         st.markdown(f"**{turn.speaker}:** {turn.text}")


import asyncio
import os
import streamlit as st
from typing import Dict

from schemas.podcast import PodcastScript
from prompts.podcast import podcast_system_instruction
from core.gemini_client import run_gemini_agent, build_speaker_voice_mapping
from audio.google_tts import MultiSpeakerTTS

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

# VOICE_SAMPLE_DIR = "app/audio/assets/voice_samples"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VOICE_SAMPLE_DIR = os.path.join(
    BASE_DIR,
    "audio",
    "assets",
    "voice_samples",
)


AVAILABLE_VOICES = [
    "achernar", "achird", "algenib", "algieba", "alnilam",
    "aoede", "autonoe", "callirrhoe", "charon", "despina",
    "enceladus", "erinome", "fenrir", "gacrux", "iapetus",
    "kore", "laomedeia", "leda", "orus", "puck",
    "pulcherrima", "rasalgethi", "sadachbia", "sadaltager",
    "schedar", "sulafat", "umbriel", "vindemiatrix",
    "zephyr", "zubenelgenubi",
]


# ------------------------------------------------------------------
# Async Script Generator Wrapper
# ------------------------------------------------------------------

async def generate_script_async(
    input_text: str,
    speaker_voices:list[str],
    num_speakers: int,
    model: str,
    temperature: float,
) -> PodcastScript | None:
    return await run_gemini_agent(
        instruction=podcast_system_instruction(num_speakers,speaker_voices),
        user_input=input_text,
        output_type=PodcastScript,
        model=model,
        temperature=temperature,
        retries=2,
    )


def generate_script(*args, **kwargs):
    return asyncio.run(generate_script_async(*args, **kwargs))

# ------------------------------------------------------------------
# Streamlit Page Config
# ------------------------------------------------------------------

st.set_page_config(page_title="Podcast Generator", layout="wide")
st.title("🎧 Text → Podcast → Multi-Speaker Audio")

# ------------------------------------------------------------------
# Sidebar – Controls
# ------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Generation Settings")

    text_model = st.selectbox(
        "Gemini Text Model",
        [
            "gemini-3-pro-preview",
            # "gemini-2.5",
            # "gemini-2.0-flash",
        ],
    )

    tts_model = st.selectbox(
        "Gemini TTS Model",
        [
            "gemini-2.5-flash-preview-tts",
            "gemini-2.5-pro-preview-tts",

        ],
    )

    # num_speakers = st.slider("Number of Speakers", 2, 6, 2)
    num_speakers = 2  # Fixed number of speakers
    temperature = st.slider("Creativity", 0.0, 1.0, 0.7)

    st.divider()
    st.header("🔊 Voice Selection")

    selected_voices = []

    for i in range(num_speakers):
        voice = st.selectbox(
            f"Speaker {i + 1} Voice",
            AVAILABLE_VOICES,
            format_func=lambda v: v.capitalize(),
            key=f"voice_{i}",
        )
        selected_voices.append(voice)

        # 🔊 Voice sample preview
        sample_path = os.path.join(VOICE_SAMPLE_DIR, f"{voice}.wav")
        print(sample_path)
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                st.audio(f.read(), format="audio/wav")
        else:
            st.caption("⚠️ Sample not found")

# ------------------------------------------------------------------
# Input Text
# ------------------------------------------------------------------

st.subheader("📄 Input Content")

input_text = st.text_area(
    "Paste article, paper, or notes here",
    height=280,
)

# ------------------------------------------------------------------
# Generate Script + Audio
# ------------------------------------------------------------------

if st.button("🚀 Generate Podcast Audio"):
    if not input_text.strip():
        st.error("Please provide input text")
    else:
        with st.spinner("🧠 Generating podcast script…"):
            script = generate_script(
                input_text=input_text,
                speaker_voices=selected_voices,
                num_speakers=num_speakers,
                model=text_model,
                temperature=temperature,
            )

        if script is None:
            st.error("Script generation failed")
        else:
            st.session_state.script = script

            # speaker_voice_map = {
            #     speaker.name: selected_voices[i]
            #     for i, speaker in enumerate(script.speakers)
            # }
            speaker_voice_map = build_speaker_voice_mapping(script)
            with st.spinner("🔊 Generating multi-speaker audio…"):
                tts = MultiSpeakerTTS()

                dialogue_text = "\n".join(
                    f"{turn.speaker}: {turn.text}"
                    for turn in script.dialogue
                )

                final_prompt = (
                    f"TTS the following conversation between "
                    f"{', '.join(speaker_voice_map.keys())}:\n{dialogue_text}"
                )

                output_file = "podcast_output.wav"

                tts.generate_tts(
                    dialogue=final_prompt,
                    speaker_voice_map=speaker_voice_map,
                    tts_model=tts_model,
                    output_file=output_file,
                )

            st.session_state.audio_file = output_file
            st.success("🎉 Podcast audio generated")

# ------------------------------------------------------------------
# OUTPUT – Audio FIRST, then Script
# ------------------------------------------------------------------

if "audio_file" in st.session_state:
    st.subheader("▶️ Podcast Audio")

    with open(st.session_state.audio_file, "rb") as f:
        st.audio(f.read(), format="audio/wav")
        st.download_button(
            "⬇️ Download WAV",
            f,
            file_name="podcast.wav",
        )

if "script" in st.session_state:
    script: PodcastScript = st.session_state.script

    st.subheader("📝 Podcast Transcription")
    st.markdown(f"### {script.title}")
    st.write(script.description)

    for turn in script.dialogue:
        st.markdown(f"**{turn.speaker}:** {turn.text}")
