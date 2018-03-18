from enum import Enum
import time
from util.magic_dict import MagicDict


# Notices differ from messages in that notices in public channels are visible
# only to the user. Due to that, it's important to be able to tell the
# difference between the two.
class ChatLineType(Enum):
    MESSAGE = 0
    NOTICE = 1
    ACTION = 2
    INFO = 3
    ANNOUNCEMENT = 4
    RAW = 5


class ChatLine:
    def __init__(self, sender, text, type_, timestamp=None):
        self.sender = sender
        self.text = text
        if timestamp is None:
            timestamp = time.time()
        self.time = timestamp
        self.type = type_


class ChatLineMetadata:
    def __init__(self, line, meta):
        self.line = line
        self.meta = meta


class ChatLineMetadataBuilder:
    def __init__(self, me, user_relations):
        self._me = me
        self._user_relations = user_relations

    @classmethod
    def build(cls, me, user_relations, **kwargs):
        return cls(me, user_relations)

    def get_meta(self, channel, line):
        if line.sender is None:
            cc = None
        else:
            key = (channel.id_key, line.sender)
            cc = channel.chatters.get(key, None)
        chatter = None
        player = None
        if cc is not None:
            chatter = cc.chatter
            player = chatter.player

        meta = MagicDict()
        self._chatter_metadata(meta, cc)
        self._player_metadata(meta, player)
        self._relation_metadata(meta, chatter, player)
        self._mention_metadata(line, meta)
        return ChatLineMetadata(line, meta)

    def _chatter_metadata(self, meta, cc):
        if cc is None:
            return
        cmeta = meta.put("chatter")
        cmeta.is_mod = cc.is_mod()
        cmeta.name = cc.chatter.name

    def _player_metadata(self, meta, player):
        if player is None:
            return
        pmeta = meta.put("player")
        pmeta.clan = player.clan
        pmeta.id = player.id
        self._avatar_metadata(pmeta, player.avatar)

    def _relation_metadata(self, meta, chatter, player):
        me = self._me
        name = None if chatter is None else chatter.name
        id_ = None if player is None else player.id
        meta.is_friend = self._user_relations.is_friend(id_, name)
        meta.is_foe = self._user_relations.is_foe(id_, name)
        meta.is_me = me.player is not None and me.player.login == name
        meta.is_clannie = me.is_clannie(id_)

    def _mention_metadata(self, line, meta):
        meta.mentions_me = (self._me.login is not None and
                            self._me.login in line.text)

    def _avatar_metadata(self, pmeta, avatar):
        if avatar is None:
            return
        tip = avatar.get("tooltip", "")
        url = avatar.get("url", None)

        ameta = pmeta.put("avatar")
        ameta.tip = tip
        if url is not None:
            ameta.url = url
