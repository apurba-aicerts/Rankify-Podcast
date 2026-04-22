"""
ui/streamlit_app.py
Streamlit interface for the podcast generation pipeline.
All business logic lives in core/ and clients/; this file is UI only.
"""

import asyncio
import logging
import os
import sys

import streamlit as st

# ── Path fix so imports resolve when running `streamlit run ui/streamlit_app.py`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clients.elevenlabs_client import fetch_available_voices
from core.podcast_pipeline import run_podcast_pipeline
from config import (
    GEMINI_DEFAULT_MODEL,
    GEMINI_DEFAULT_TEMPERATURE,
    MIN_SPEAKERS,
    MAX_SPEAKERS,
    DEFAULT_NUM_SPEAKERS,
    ELEVENLABS_DEFAULT_OUTPUT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("streamlit_app")

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Podcast Generator",
    page_icon="🎙️",
    layout="wide",
)

st.title("🎙️ Text → Podcast Audio")
st.caption("Powered by Gemini + ElevenLabs")

# ── Fetch voices once per session ─────────────────────────────────────────────

if "available_voices" not in st.session_state:
    with st.spinner("Loading voices from ElevenLabs…"):
        try:
            st.session_state.available_voices = fetch_available_voices()
            logger.info(
                "Loaded %d voices into session.", len(st.session_state.available_voices)
            )
        except Exception as exc:
            st.error(f"Failed to load voices: {exc}")
            st.stop()

available_voices: list[dict] = st.session_state.available_voices

# Dropdown label → voice dict (for O(1) lookup)
voice_label_map: dict[str, dict] = {
    f"{v['name']}": v
    for v in available_voices
}
voice_labels = list(voice_label_map.keys())

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Settings")

    gemini_model = st.selectbox(
        "Gemini Model",
        [   "gemini-flash-latest",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-pro-latest",
            "gemini-3.1-pro-preview"
        ],
    )

    temperature = st.slider(
        "Creativity",
        min_value=0.0,
        max_value=1.0,
        value=GEMINI_DEFAULT_TEMPERATURE,
        step=0.05,
    )

    st.divider()
    st.header("🧩 Podcast Customisation")

    podcast_style = st.selectbox(
        "Podcast Style",
        ["Interview", "News", "Storytelling"],
        index=0,
    )

    tone = st.selectbox(
        "Tone",
        ["Formal", "Casual", "Engaging"],
        index=2,
    )

    interaction_mode = st.selectbox(
        "Multi-speaker Interaction",
        ["Q/A", "Debate", "Explanation"],
        index=0,
    )

    st.divider()
    st.header("🔊 Speakers & Voices")

    num_speakers = st.slider(
        "Number of Speakers",
        min_value=MIN_SPEAKERS,
        max_value=len(st.session_state.available_voices),
        value=DEFAULT_NUM_SPEAKERS,
    )

    selected_voice_dicts: list[dict] = []
    speaker_roles: list[str] = []
    for i in range(num_speakers):
        select_key = f"voice_select_{i}"
        previously_taken = {
            st.session_state.get(f"voice_select_{j}")
            for j in range(i)
            if st.session_state.get(f"voice_select_{j}")
        }

        current_selection = st.session_state.get(select_key)
        if current_selection and current_selection in previously_taken:
            del st.session_state[select_key]
            current_selection = None

        available_labels = [
            label for label in voice_labels if label not in previously_taken
        ]

        label = st.selectbox(
            f"Speaker {i + 1} Voice",
            available_labels,
            index=available_labels.index(current_selection)
            if current_selection in available_labels
            else 0,
            key=select_key,
        )
        voice = voice_label_map[label]
        selected_voice_dicts.append(voice)

        preview_url = voice.get("preview_url", "")
        if preview_url:
            st.audio(preview_url, format="audio/mpeg")
        else:
            st.caption("Preview unavailable for this voice.")

        role_key = f"role_select_{i}"
        default_role_index = 0 if i == 0 else (1 if i == 1 else 2)
        role = st.selectbox(
            f"Speaker {i + 1} Role",
            ["Host", "Expert", "Co-host"],
            index=default_role_index,
            key=role_key,
        )
        speaker_roles.append(role)

    if num_speakers > 0 and "Host" not in speaker_roles:
        st.warning("At least one speaker should be the Host. (Recommended)")

# ── Main: input ───────────────────────────────────────────────────────────────

st.subheader("📄 Source Content")
input_text = st.text_area(
    "Paste an article, paper, blog post, or notes here",
    height=300,
    placeholder="Paste your content here…",
)

# ── Main: generate ────────────────────────────────────────────────────────────

if st.button("🚀 Generate Podcast", type="primary"):
    if not input_text.strip():
        st.error("Please paste some content before generating.")
    else:
        # Clear previous output
        st.session_state.pop("audio_path", None)
        st.session_state.pop("script", None)

        output_path = ELEVENLABS_DEFAULT_OUTPUT

        try:
            with st.status("Generating podcast…", expanded=True) as status:
                st.write("🧠 Writing script with Gemini…")
                logger.info("Pipeline triggered from UI.")

                script, audio_path = asyncio.run(
                    run_podcast_pipeline(
                        input_text=input_text,
                        speaker_voices=selected_voice_dicts,
                        num_speakers=num_speakers,
                        speaker_roles=speaker_roles,
                        podcast_style=podcast_style,
                        tone=tone,
                        interaction_mode=interaction_mode,
                        output_path=output_path,
                        model=gemini_model,
                        temperature=temperature,
                    )
                )

                st.write("🔊 Synthesising audio with ElevenLabs…")
                status.update(label="✅ Done!", state="complete")

            st.session_state.audio_path = audio_path
            st.session_state.script = script
            logger.info("Pipeline complete — audio=%s", audio_path)

        except Exception as exc:
            logger.error("Pipeline failed: %s", exc, exc_info=True)
            st.error(
                f"Generation failed: {exc}\n\n"
                "Check your API keys and inputs, then try again."
            )

# ── Main: output ──────────────────────────────────────────────────────────────

if "audio_path" in st.session_state:
    st.subheader("▶️ Your Podcast")

    audio_path: str = st.session_state.audio_path

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    st.audio(audio_bytes, format="audio/mp3")
    st.download_button(
        label="⬇️ Download MP3",
        data=audio_bytes,
        file_name="podcast.mp3",
        mime="audio/mpeg",
    )