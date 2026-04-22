"""
ui/streamlit_app.py
Streamlit interface for the podcast generation pipeline.
All business logic lives in core/ and clients/; this file is UI only.
"""

import asyncio
import json
import logging
import os
import sys

import streamlit as st
import streamlit.components.v1 as components

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

st.markdown(
    """
<style>
/* Clean, friendly layout */
.block-container { padding-top: 1.25rem; padding-bottom: 2.5rem; max-width: 1080px; }
h1, h2, h3 { letter-spacing: 0.2px; }
/* Calmer typography */
p, li { line-height: 1.55; }
/* De-clutter Streamlit chrome */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
/* Buttons */
div.stButton > button { width: 100%; border-radius: 8px; }
/* Inputs */
textarea { border-radius: 8px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Podcast Generator")
st.caption("Paste content, pick speakers, and generate a script + MP3.")

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

# ── Main: simple, guided form ────────────────────────────────────────────────

# Tracks which speaker preview (if any) is currently shown
if "preview_speaker_idx" not in st.session_state:
    st.session_state.preview_speaker_idx = None
if "preview_nonce" not in st.session_state:
    st.session_state.preview_nonce = 0

with st.form("podcast_form", border=False):
    left, right = st.columns([1.35, 0.65], gap="large")

    with left:
        st.subheader("Source")
        input_text = st.text_area(
            "Content",
            height=320,
            placeholder="Paste an article, paper, blog post, or notes here…",
            label_visibility="collapsed",
        )

    with right:
        st.subheader("Settings")
        podcast_style = st.selectbox("Style", ["Interview", "News", "Storytelling"], index=0)
        tone = st.selectbox("Tone", ["Formal", "Casual", "Engaging"], index=2)
        interaction_mode = st.selectbox("Interaction", ["Q/A", "Debate", "Explanation"], index=0)
        num_speakers = st.slider(
            "Speakers",
            min_value=MIN_SPEAKERS,
            max_value=min(len(st.session_state.available_voices), MAX_SPEAKERS),
            value=DEFAULT_NUM_SPEAKERS,
        )
        gemini_model = st.selectbox(
            "Gemini model",
            [
                "gemini-flash-latest",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-pro-latest",
                "gemini-3.1-pro-preview",
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
    st.subheader("Speakers")

    selected_voice_dicts: list[dict] = []
    speaker_roles: list[str] = []

    for i in range(num_speakers):
        col1, col2, col3 = st.columns([0.60, 0.30, 0.10], gap="small")

        previously_taken = {
            st.session_state.get(f"voice_select_{j}")
            for j in range(i)
            if st.session_state.get(f"voice_select_{j}")
        }
        available_labels = [label for label in voice_labels if label not in previously_taken]

        with col1:
            label = st.selectbox(
                f"Speaker {i + 1} voice",
                available_labels,
                key=f"voice_select_{i}",
            )
        with col2:
            default_role_index = 0 if i == 0 else (1 if i == 1 else 2)
            role = st.selectbox(
                f"Speaker {i + 1} role",
                ["Host", "Expert", "Co-host"],
                index=default_role_index,
                key=f"role_select_{i}",
            )
        with col3:
            st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
            play_clicked = st.form_submit_button(
                "▶",
                help="Play voice preview",
                key=f"preview_btn_{i}",
            )

        voice = voice_label_map[label]
        selected_voice_dicts.append(voice)
        speaker_roles.append(role)

        # Record which speaker preview should be shown after submit
        # (Streamlit forms only react on submit; this keeps UI minimal per speaker row)
        if play_clicked:
            st.session_state.preview_speaker_idx = i
            st.session_state.preview_nonce += 1

    if num_speakers > 0 and "Host" not in speaker_roles:
        st.info("Tip: It usually sounds best if one speaker is the Host.")

    st.divider()
    generate_clicked = st.form_submit_button("Generate podcast", type="primary")

# Inline preview area (kept close to speaker selection)
if st.session_state.get("preview_speaker_idx") is not None:
    idx = int(st.session_state.preview_speaker_idx)
    if 0 <= idx < len(selected_voice_dicts):
        voice = selected_voice_dicts[idx]
        preview_url = voice.get("preview_url", "")
        if preview_url:
            # Attempt immediate playback (browser may still block autoplay).
            components.html(
                f"""
                <!-- nonce={st.session_state.preview_nonce} -->
                <audio src="{preview_url}" autoplay style="display:none"></audio>
                """,
                height=0,
            )
        # If preview_url is missing, stay silent (no UI noise).

# ── Main: generate ────────────────────────────────────────────────────────────

if generate_clicked:
    if not input_text.strip():
        st.error("Please paste some content before generating.")
    else:
        # Clear previous output
        st.session_state.pop("audio_path", None)
        st.session_state.pop("script", None)

        output_path = ELEVENLABS_DEFAULT_OUTPUT

        try:
            with st.status("Generating podcast…", expanded=True) as status:
                st.write("Writing script with Gemini…")
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

                st.write("Synthesising audio with ElevenLabs…")
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

st.subheader("Results")
tabs = st.tabs(["Audio", "Script", "JSON"])

with tabs[0]:
    if "audio_path" not in st.session_state:
        st.info("Generate a podcast to preview the MP3 here.")
    else:
        audio_path: str = st.session_state.audio_path

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        st.audio(audio_bytes, format="audio/mp3")
        st.download_button(
            label="Download MP3",
            data=audio_bytes,
            file_name="podcast.mp3",
            mime="audio/mpeg",
        )

with tabs[1]:
    if "script" not in st.session_state:
        st.info("Generate a podcast to view the script here.")
    else:
        script = st.session_state.script
        script_dict = script.model_dump() if hasattr(script, "model_dump") else script

        st.markdown(f"**{script_dict.get('title', '')}**")
        st.caption(script_dict.get("description", ""))

        chips = [
            script_dict.get("podcast_style", ""),
            script_dict.get("tone", ""),
            script_dict.get("interaction_mode", ""),
        ]
        st.caption(" • ".join([c for c in chips if c]))

        st.divider()
        st.markdown("**Speakers**")
        for spk in script_dict.get("speakers", []):
            st.write(f"- {spk.get('name','')} • {spk.get('role','')}")

        with st.expander("Dialogue", expanded=True):
            for turn in script_dict.get("dialogue", []):
                st.markdown(f"**{turn.get('speaker','')}:** {turn.get('text','')}")

with tabs[2]:
    if "script" not in st.session_state:
        st.info("Generate a podcast to download/view the JSON here.")
    else:
        script = st.session_state.script
        script_dict = script.model_dump() if hasattr(script, "model_dump") else script
        st.code(json.dumps(script_dict, indent=2, ensure_ascii=False), language="json")
        st.download_button(
            label="Download Script (JSON)",
            data=json.dumps(script_dict, indent=2, ensure_ascii=False),
            file_name="podcast_script.json",
            mime="application/json",
        )