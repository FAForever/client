from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity
from src.api.models.Player import Player


class Review(AbstractEntity):
    score:  int
    text:   str

    player: Player | None = Field(None)
