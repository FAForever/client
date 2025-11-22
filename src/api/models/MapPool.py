from __future__ import annotations

from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity
from src.api.models.MapPoolAssignment import MapPoolAssignment
from src.api.models.MapVersion import MapVersion


class MapPool(AbstractEntity):
    name: str

    assignments:  list[MapPoolAssignment] | None = Field(None, alias="mapPoolAssignments")
    map_versions: list[MapVersion] | None        = Field(None, alias="mapVersions")
