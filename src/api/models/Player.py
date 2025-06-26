from __future__ import annotations

from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity
from src.api.models.AvatarAssignment import AvatarAssignment
from src.api.models.NameRecord import NameRecord


class Player(AbstractEntity):
    login:                  str
    user_agent:             str | None                    = Field(alias="userAgent")

    avatar_assignments:     list[AvatarAssignment] | None = Field(None, alias="avatarAssignments")
    names:                  list[NameRecord] | None       = Field(None)

    # set this manually, otherwise infinite recursion -> RAM goes brrrrr -> app dies ded
    # see below how Player-Clan-ClanMembership are tangled
    custom_clan_membership: ClanMembership | None         = Field(None)


# can't move them to separate files either, because everything
# shits itself with circular imports and partial initialization
# (no, you can't throw TYPE_CHECKING at it)
class Clan(AbstractEntity):
    description:         str
    name:                str
    requires_invitation: bool                        = Field(alias="requiresInvitation")
    tag:                 str
    tag_color:           str | None                  = Field(alias="tagColor")
    website_url:         str                         = Field(alias="websiteUrl")

    founder:             Player | None               = Field(None)
    leader:              Player | None               = Field(None)
    memberships:         list[ClanMembership] | None = Field(None)


class ClanMembership(AbstractEntity):
    # set this manually for reasons explained above
    custom_clan: Clan | None = Field(None)

    player: Player | None = Field(None)
