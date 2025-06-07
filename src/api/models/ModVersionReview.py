from pydantic import Field

from src.api.models.ModVersion import ModVersion
from src.api.models.Review import Review


class ModVersionReview(Review):
    version:     ModVersion | None = Field(None, alias="modVersion")
