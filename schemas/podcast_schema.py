"""
schemas/podcast_schema.py
Pydantic models for the podcast generation pipeline.
"""

from pydantic import BaseModel, Field
from typing import List, Literal


PodcastStyle = Literal["Interview", "News", "Storytelling"]
PodcastTone = Literal["Formal", "Casual", "Engaging"]
InteractionMode = Literal["Q/A", "Debate", "Explanation"]
SpeakerRole = Literal["Host", "Expert", "Co-host"]


class DialogueTurn(BaseModel):
    """A single spoken turn in the podcast dialogue."""

    speaker: str = Field(
        description="Name of the speaker — must match a name defined in the speakers list."
    )
    text: str = Field(
        description="Exactly what the speaker says in this turn."
    )


class Speaker(BaseModel):
    """A participant in the podcast."""

    name: str = Field(
        description=(
            "A realistic human name for the speaker (e.g., Alex, Maya, Rahul). "
            "Never use a voice ID as a name."
        )
    )
    voice_id: str = Field(
        description="ElevenLabs voice ID assigned to this speaker."
    )
    role: SpeakerRole = Field(
        description="The speaker's assigned role in the conversation."
    )


class PodcastScript(BaseModel):
    """Complete podcast episode script produced by the LLM."""

    title: str = Field(description="Catchy, descriptive podcast episode title.")
    description: str = Field(description="One or two sentence episode summary.")
    podcast_style: PodcastStyle = Field(
        description="Overall episode format style selected by the user."
    )
    tone: PodcastTone = Field(
        description="Overall episode tone selected by the user."
    )
    interaction_mode: InteractionMode = Field(
        description="How speakers interact (e.g., Q/A, Debate, Explanation)."
    )
    speakers: List[Speaker] = Field(
        description=(
            "Unique speakers ordered by their first appearance in the dialogue. "
            "Each speaker appears exactly once in this list."
        )
    )
    dialogue: List[DialogueTurn] = Field(
        description="Ordered list of all dialogue turns for the episode."
    )