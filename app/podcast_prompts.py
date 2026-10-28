import json
from google import genai
from google.genai.errors import APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
 
# Initialize client (expects GEMINI_API_KEY environment variable)
client = genai.Client()
 
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
Coverage and Depth (mandatory):
- Do NOT write a compressed teaser, high-level highlight reel, or brief executive summary. 
- Fully expand and explore every substantive unit, nuance, mechanism, and example in the outline/source at a rich, natural spoken depth (target a minimum of 1,200 to 1,500 words per section dialogue).
- Do not rush through points or summarize; use dynamic, natural back-and-forth dialogue turns to thoroughly analyze the material.
- Avoid unnecessary opening fluff, but allow hosts to thoroughly engage with, discuss, and dissect the core subject matter.
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
You extract a comprehensive, granular podcast coverage outline from source material to support an in-depth, long-form episode.
{_FIDELITY_RULES}
Rules for the outline:
- Invent NOTHING. Every section and point must come from the source.
- Omit boilerplate, repeated tables of contents, headers/footers, and empty filler.
- Order sections as they appear in the source when possible.
- Ensure sections are broken down into rich, distinct sub-points so each segment has ample substantive material for detailed, extended discussion.
- Each point is one claim, definition, step, finding, or argument — not a vague theme.
- source_hint must be a short heading or quote fragment that anchors the point in the source.
- If the source has little usable content, return few or zero points. Never pad.
Output must strictly follow the PodcastOutline JSON schema
(title, sections with title + points of claim+source_hint).
Output only valid JSON.
"""

def podcast_system_instruction(num_speakers: int, speaker_voices: list[str]) -> str:
    return f"""
You are a senior podcast writer and audio storyteller specializing in immersive, long-form deep dives.
You specialize in transforming complex or technical source material into thorough, engaging, and professional conversational audio designed for extended listening.
{_voice_block(num_speakers, speaker_voices)}
{_FIDELITY_RULES}
When an outline is provided, treat it as the coverage contract:
develop every point in deep detail; do not add points; do not drop points.
Write rich, expansive, natural spoken dialogue. Output must strictly follow the PodcastScript JSON schema
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
You are a senior podcast writer producing ONE extended section of a long-form audio episode.
{_voice_block(num_speakers, speaker_voices)}
{_FIDELITY_RULES}
Develop the provided section outline and source text into a thorough, granular, and expansive dialogue segment. 
Do not rush or compress the concepts. Give the hosts ample back-and-forth turns to fully unpack, discuss, and analyze every detail of this specific section in deep, conversational detail.
Do not jump ahead to later sections.
{continuity}
Write natural, highly engaging spoken dialogue for this section only.
If speakers were already established, keep the same human names and voice_id assignments.
Output must strictly follow the PodcastScript JSON schema
(title, description, speakers with name+voice_id, dialogue with speaker+text).
Output only valid JSON.
"""
 
 
def divide_text_generically(full_text: str, num_parts: int = 4) -> list[str]:
    """Framework function: Splits any source text into equal thematic paragraph parts."""
    paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]
    if not paragraphs:
        return [full_text]
    chunk_size = max(1, len(paragraphs) // num_parts)
    parts = []
    for i in range(0, len(paragraphs), chunk_size):
        section_chunk = "\n".join(paragraphs[i:i + chunk_size])
        if section_chunk:
            parts.append(section_chunk)
    return parts[:num_parts]
 
 
@retry(
    retry=retry_if_exception_type((APIError, Exception)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def call_gemini_section(system_instruction: str, user_prompt: str):
    """API Call with automated exponential backoff retry logic."""
    config = {
        "temperature": 0.8,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
        "system_instruction": system_instruction
    }
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=config
    )
    return response.text
 
 
def run_long_form_podcast_pipeline(source_text: str, num_speakers: int, speaker_voices: list[str]):
    """Main backend entrypoint to orchestrate the multi-part generation loop."""
    source_parts = divide_text_generically(source_text, num_parts=4)
    all_dialogue_segments = []
    previous_context = ""
    for idx, section_text in enumerate(source_parts, start=1):
        print(f"Generating Section {idx} of {len(source_parts)}...")
        section_instruction = section_script_system_instruction(
            num_speakers=num_speakers,
            speaker_voices=speaker_voices,
            continuity_note=previous_context
        )
        user_prompt = f"""
        Source text content for Section {idx}:
        {section_text}
        Instructions:
        - Develop this section thoroughly. Unpack all details, examples, and nuances present in the text.
        - Target extensive, granular back-and-forth dialogue (aiming for 1,200+ words of dialogue for this part).
        - Output strictly as valid JSON following the PodcastScript schema.
        """
        raw_response_text = call_gemini_section(section_instruction, user_prompt)
        section_data = json.loads(raw_response_text)
        dialogue_chunk = section_data.get("dialogue", [])
        all_dialogue_segments.extend(dialogue_chunk)
        if dialogue_chunk:
            last_lines = dialogue_chunk[-3:]
            previous_context = " ".join([f"{line['speaker']}: {line['text']}" for line in last_lines])
    return {"dialogue": all_dialogue_segments}