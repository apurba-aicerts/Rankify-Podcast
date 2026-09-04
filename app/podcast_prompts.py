"""Podcast generation prompts and voice descriptions."""

voices = {
    "zephyr": "Female, Bright and clear tone",
    "puck": "Male, Upbeat and lively",
    "charon": "Male, Informative and precise",
    "kore": "Female, Firm and authoritative",
    "fenrir": "Male, Excitable and energetic",
    "leda": "Female, Youthful and fresh",
    "orus": "Male, Firm and commanding",
    "aoede": "Female, Breezy and relaxed",
    "callirrhoe": "Female, Easy-going and casual",
    "autonoe": "Female, Bright and cheerful",
    "enceladus": "Male, Breathy and soft-spoken",
    "iapetus": "Male, Clear and articulate",
    "umbriel": "Male, Easy-going and friendly",
    "algieba": "Male, Smooth and polished",
    "despina": "Female, Smooth and elegant",
    "erinome": "Female, Clear and crisp",
    "algenib": "Male, Gravelly and rugged",
    "rasalgethi": "Male, Informative and confident",
    "laomedeia": "Female, Upbeat and positive",
    "achernar": "Female, Soft and gentle",
    "alnilam": "Male, Firm and steady",
    "schedar": "Male, Even and balanced",
    "gacrux": "Female, Mature and wise",
    "pulcherrima": "Male, Forward and assertive",
    "achird": "Male, Friendly and warm",
    "zubenelgenubi": "Male, Casual and relaxed",
    "vindemiatrix": "Female, Gentle and soothing",
    "sadachbia": "Male, Lively and spirited",
    "sadaltager": "Male, Knowledgeable and clear",
    "sulafat": "Female, Warm and inviting",
}

_FIDELITY_RULES = """
Source fidelity (mandatory):
- Use ONLY the provided source material. Do not add external facts, examples, stats, or analogies.
- Do not invent claims, stories, or "experts say" filler.
- If a detail is unclear or missing in the source, skip it — do not guess.

Coverage (mandatory):
- Do NOT write a teaser, highlight reel, or executive summary episode.
- Develop each substantive unit in the outline/source at natural spoken depth.
- Thin source → short dialogue. Dense source → longer dialogue that covers the material.
- Do not pad with welcome-to-the-show intros, banter, or fake personal anecdotes.
- Prefer natural back-and-forth turns over one compressed monologue.
"""


def _voice_block(num_speakers: int, speaker_voices: list[str]) -> str:
    voice_descriptions = "\n".join(
        f"- {voice}: {voices.get(voice.lower(), 'Voice sample')}" for voice in speaker_voices
    )
    return f"""
You must use exactly {num_speakers} speakers.

The following voice IDs are provided, in order, with short voice properties:

{voice_descriptions}

Use these voice properties to choose appropriate human names and roles.
Voice IDs are INTERNAL only — do NOT use voice IDs as speaker names in dialogue.
"""


def outline_system_instruction() -> str:
    return f"""
You extract a podcast coverage outline from source material.

{_FIDELITY_RULES}

Rules for the outline:
- Invent NOTHING. Every section and point must come from the source.
- Omit boilerplate, repeated tables of contents, headers/footers, and empty filler.
- Order sections as they appear in the source when possible.
- Each point is one claim, definition, step, finding, or argument — not a vague theme.
- source_hint must be a short heading or quote fragment that anchors the point in the source.
- If the source has little usable content, return few or zero points. Never pad.

Output must strictly follow the PodcastOutline JSON schema
(title, sections with title + points of claim+source_hint).
Output only valid JSON.
"""


def podcast_system_instruction(num_speakers: int, speaker_voices: list[str]) -> str:
    return f"""
You are a senior podcast writer and audio storyteller.

You specialize in transforming complex or technical source material into
clear, engaging, and professional podcast conversations designed for listening.

{_voice_block(num_speakers, speaker_voices)}
{_FIDELITY_RULES}

When an outline is provided, treat it as the coverage contract:
develop every point; do not add points; do not drop points.

Write natural spoken dialogue. Output must strictly follow the PodcastScript JSON schema
(title, description, speakers with name+voice_id, dialogue with speaker+text).
Output only valid JSON.
"""


def section_script_system_instruction(
    num_speakers: int,
    speaker_voices: list[str],
    *,
    continuity_note: str = "",
) -> str:
    continuity = ""
    if continuity_note.strip():
        continuity = f"""
Continuity context (do not re-explain at length; just stay consistent):
{continuity_note.strip()}
"""
    return f"""
You are a senior podcast writer producing ONE section of a longer episode.

{_voice_block(num_speakers, speaker_voices)}
{_FIDELITY_RULES}

Develop only the provided section outline using the provided section source text.
Do not summarize the whole document. Do not jump ahead to later sections.
{continuity}
Write natural spoken dialogue for this section only.
If speakers were already established, keep the same human names and voice_id assignments.
Output must strictly follow the PodcastScript JSON schema
(title, description, speakers with name+voice_id, dialogue with speaker+text).
Output only valid JSON.
"""
