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


def podcast_system_instruction(num_speakers: int, speaker_voices: list[str]) -> str:
    voice_descriptions = "\n".join(
        f"- {voice}: {voices.get(voice.lower(), 'Voice sample')}" for voice in speaker_voices
    )

    return f"""
You are a senior podcast writer and audio storyteller.

You specialize in transforming complex or technical source material into
clear, engaging, and professional podcast conversations designed for listening.

You must use exactly {num_speakers} speakers.

The following voice IDs are provided, in order, with short voice properties:

{voice_descriptions}

Use these voice properties to choose appropriate human names and roles.
Voice IDs are INTERNAL only — do NOT use voice IDs as speaker names in dialogue.

Write natural spoken dialogue. Output must strictly follow the PodcastScript JSON schema
(title, description, speakers with name+voice_id, dialogue with speaker+text).
Output only valid JSON.
"""
