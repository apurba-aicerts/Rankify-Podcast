
import asyncio
import streamlit as st
from typing import Dict

from schemas.podcast import PodcastScript
from prompts.podcast import podcast_system_instruction
from core.gemini_client import run_gemini_agent
from audio.google_tts import MultiSpeakerTTS

# ------------------------------------------------------------------
# Async Script Generator Wrapper (Streamlit-safe)
# ------------------------------------------------------------------

async def generate_script_async(
    input_text: str,
    num_speakers: int,
    model: str,
    temperature: float
) -> PodcastScript | None:
    return await run_gemini_agent(
        instruction=podcast_system_instruction(num_speakers),
        user_input=input_text,
        output_type=PodcastScript,
        model=model,
        temperature=temperature,
        retries=2,
    )


def generate_script(*args, **kwargs):
    return asyncio.run(generate_script_async(*args, **kwargs))

# ------------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------------

st.set_page_config(page_title="Podcast Generator", layout="wide")

st.title("🎧 Text → Podcast → Multi-Speaker Audio")

# ------------------------------------------------------------------
# Sidebar – Model Controls
# ------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Generation Settings")

    text_model = st.selectbox(
        "Gemini Text Model",
        [
            "gemini-3-pro-preview",
            "gemini-2.5-pro-preview",
            "gemini-2.0-flash",
        ],
    )

    tts_model = st.selectbox(
        "Gemini TTS Model",
        [
            "gemini-2.5-pro-preview-tts",
            "gemini-2.5-flash-preview-tts",
        ],
    )

    num_speakers = st.slider("Number of Speakers", 2, 6, 2)
    temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7)

# ------------------------------------------------------------------
# Input Text
# ------------------------------------------------------------------

input_text = st.text_area(
    "📄 Input Content",
    height=300,
    placeholder="Paste article, paper, or notes here…",
)

# ------------------------------------------------------------------
# Script Generation
# ------------------------------------------------------------------

if st.button("🧠 Generate Podcast Script"):
    if not input_text.strip():
        st.error("Please provide input text")
    else:
        with st.spinner("Generating podcast script…"):
            script = generate_script(
                input_text=input_text,
                num_speakers=num_speakers,
                model=text_model,
                temperature=temperature,
            )

        if script is None:
            st.error("Script generation failed")
        else:
            st.session_state.script = script
            st.success("Podcast script generated")

# ------------------------------------------------------------------
# Display Script
# ------------------------------------------------------------------

if "script" in st.session_state:
    script: PodcastScript = st.session_state.script

    st.subheader("🎙️ Podcast Script")
    st.markdown(f"### {script.title}")
    st.write(script.description)

    for turn in script.dialogue:
        st.markdown(f"**{turn.speaker}:** {turn.text}")

    # ------------------------------------------------------------------
    # Voice Selection
    # ------------------------------------------------------------------

    st.subheader("🔊 Speaker Voice Assignment")

    AVAILABLE_VOICES = [
        "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda",
        "Orus", "Aoede", "Callirhoe", "Autonoe", "Enceladus",
        "Iapetus", "Umbriel", "Achernar", "Alnilam",
    ]

    speaker_voice_map: Dict[str, str] = {}

    for speaker in script.speakers:
        speaker_voice_map[speaker.name] = st.selectbox(
            f"Voice for {speaker.name}",
            AVAILABLE_VOICES,
            key=speaker.name,
        )

    # ------------------------------------------------------------------
    # TTS Generation
    # ------------------------------------------------------------------

    if st.button("🔊 Generate Audio"):
        with st.spinner("Generating multi-speaker audio…"):
            tts = MultiSpeakerTTS()

            dialogue_lines = "\n".join(
                f"{turn.speaker}: {turn.text}" for turn in script.dialogue
            )

            dialogue_text = (
                f"TTS the following conversation between "
                f"{', '.join(speaker_voice_map.keys())}:\n{dialogue_lines}"
            )

            output_file = "podcast_output.wav"

            tts.generate_tts(
                dialogue=dialogue_text,
                speaker_voice_map=speaker_voice_map,
                tts_model=tts_model,
                output_file=output_file,
            )

        st.success("Audio generated")

        with open(output_file, "rb") as f:
            st.audio(f.read(), format="audio/wav")
            st.download_button(
                "⬇️ Download WAV",
                f,
                file_name="podcast.wav",
            )