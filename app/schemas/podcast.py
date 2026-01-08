from pydantic import BaseModel, Field
from typing import List


class DialogueTurn(BaseModel):
    speaker: str = Field(description="Name of the speaker, e.g., Host or Guest")
    text: str = Field(description="What the speaker says in this turn")


class PodcastScript(BaseModel):
    title: str = Field(description="Catchy podcast episode title")
    description: str = Field(description="Short episode description")
    dialogue: List[DialogueTurn] = Field(
        description="Ordered list of dialogue turns between speakers"
    )
