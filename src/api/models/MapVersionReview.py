from pydantic import Field

from src.api.models.MapVersion import MapVersion
from src.api.models.Review import Review


class MapVersionReview(Review):
    version:     MapVersion | None = Field(None, alias="mapVersion")
