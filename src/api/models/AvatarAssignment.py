from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity
from src.api.models.Avatar import Avatar


class AvatarAssignment(AbstractEntity):
    expires_at: str | None    = Field(alias="expiresAt")
    selected:   bool

    avatar:     Avatar | None = Field(None)
