"""MIT License

Copyright (c) 2020 fafafaf

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
from __future__ import annotations

import html
import json
import logging
import os
from collections import Counter
from collections import defaultdict
from collections.abc import Generator
from datetime import datetime
from typing import Any
from typing import NamedTuple

import zstandard
from PyQt6.QtCore import QByteArray
from PyQt6.QtCore import QDataStream
from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import qUncompress
from PyQt6.QtNetwork import QNetworkReply

from src.mapGenerator.mapgenUtils import isGeneratedMap
from src.replays.replaydetails.helpers import seconds_to_human
from src.replays.replaydetails.replayformat import LUA_TYPE
from src.replays.replaydetails.replayformat import STITARGET
from src.replays.replaydetails.replayformat import ECmdStreamOp
from src.replays.replaydetails.tabs.gamestats_types import GameStats
from src.replays.replaydetails.utils import PLAYER_COLORS
from src.util import COMMON_DIR

logger = logging.getLogger(__name__)

try:
    from zigfafreplay import parse_replaydata
except ImportError:
    logger.warning("Zig replay parser not found")
    parse_replaydata = None


def uncompress(compressed: bytes, compression: str = "base64") -> QByteArray:
    if compression == "zstd":
        decompressor = zstandard.ZstdDecompressor()
        with decompressor.stream_reader(compressed) as reader:
            return QByteArray(reader.read())
    return qUncompress(QByteArray.fromBase64(compressed))


def qdata_stream(body: bytes) -> QDataStream:
    binary = QDataStream(body)
    binary.setByteOrder(QDataStream.ByteOrder.LittleEndian)
    binary.setFloatingPointPrecision(QDataStream.FloatingPointPrecision.SinglePrecision)
    return binary


class Replay(NamedTuple):
    metadata: dict[str, str | float | int | None] = {}
    body: bytes = b""

    @classmethod
    def from_qreply(cls, reply: QNetworkReply) -> Replay:
        metadata = json.loads(reply.readLine().data())
        compression = metadata.get("compression", "")
        body = uncompress(reply.readAll().data(), compression)
        return cls(metadata, body.data())

    @classmethod
    def from_file(cls, file: str) -> Replay:
        with open(file, "rb") as replay:
            if file.endswith(".fafreplay"):
                metadata = json.loads(replay.readline())
                compression = metadata.get("compression", "")
                compressed = replay.read()
                body = uncompress(compressed, compression)
            else:
                metadata = {}
                body = QByteArray(replay.read())
        return cls(metadata, body.data())


class ReplayException(Exception):
    pass


class ReplayParser(QObject):
    replayPercentage = pyqtSignal(int)

    def __init__(self, replay: Replay = Replay()) -> None:
        QObject.__init__(self)
        self.faf_info: dict[str, Any] = replay.metadata
        self.body = replay.body
        self.binary = qdata_stream(replay.body)

        self.ticks = 0
        self.lasttick: dict[int, int] = {}
        self.army = {}
        self.pts = []

        self.CPM = Counter()
        self.chatLine = []

        self.filename = ""
        self.size = 0

        self.cpmChart = defaultdict(list)
        self.commands = defaultdict(list)
        self.game_stats: dict[str, GameStats] = {}

    def set_file(self, file: str) -> None:
        self.filename = file

    def get_country_img_path(self, country: str) -> str:
        return os.path.join(COMMON_DIR, "chat", "countries", f"{country}.png")

    def get_faction_img_path(self, fac: float) -> str:
        facs = ("uef.png", "aeon.png", "cybran.png", "seraphim.png")
        try:
            return os.path.join(COMMON_DIR, "games", "automatch", facs[int(fac) - 1])
        except IndexError:
            return str(fac)

    def return_next_string(self) -> str:
        buf = b""
        while (c := self.binary.readRawData(1)) != b"\0":
            buf += c
        try:
            return buf.decode("utf-8")
        except UnicodeDecodeError:
            return buf.decode("cp1251")

    def read_until_null(self):
        while self.binary.readRawData(1) != b"\0":
            continue

    def parse_lua(self, lua_type: int | None = None) -> Any:
        typ = self.binary.readUInt8() if lua_type is None else lua_type
        match typ:
            case LUA_TYPE.NUMBER:
                return self.binary.readFloat()
            case LUA_TYPE.STRING:
                return self.return_next_string()
            case LUA_TYPE.NIL:
                self.binary.skipRawData(1)
                return None
            case LUA_TYPE.BOOL:
                return self.binary.readUInt8() == 1
            case LUA_TYPE.LUA:
                result = {}
                while (typ := self.binary.readUInt8()) != LUA_TYPE.LUA_END:
                    key = self.parse_lua(typ)
                    value = self.parse_lua()
                    result[key] = value
                return result
        raise ReplayException("Error in parsing the lua table")

    def check_sum(self) -> str:
        return "".join((f"{i:x}" for i in self.binary.readRawData(16)))

    def map_folder_name(self) -> str:
        return self.map.split("/")[2].lower()

    def parse_header(self) -> None:
        self.replayPatchFieldId = self.return_next_string()
        self.binary.skipRawData(3)
        self.replayVersionId, self.map = self.return_next_string().split("\r\n")
        self.binary.skipRawData(4)

        self.gameModsNum = self.binary.readUInt32()
        self.gameMods = self.parse_lua()

        self.luaScenarioSize = self.binary.readUInt32()
        self.luaScenarioInfo = self.parse_lua()

        self.numOfSources = self.binary.readUInt8()

        self.players = {}
        self.observers = {}
        for i in range(self.numOfSources):
            name = self.return_next_string()
            unsigned_int = self.binary.readUInt32()
            if unsigned_int == 0:
                self.observers[i] = name
            else:
                self.players[i] = name

        self.cheatsEnabled = self.binary.readUInt8()
        self.numOfArmies = self.binary.readUInt8()

        ai_army_num = len(self.players)
        for i in range(self.numOfArmies):
            self.binary.readUInt32()
            player_data = self.parse_lua()
            player_source = self.binary.readUInt8()
            if player_source == 255 and not player_data["Civilian"]:
                self.army[ai_army_num] = player_data
                ai_army_num += 1
            else:
                self.army[player_source] = player_data

            if player_source != 255:
                self.binary.skipRawData(1)
        self.randomSeed = self.binary.readUInt32()

    def parse_ticks(self) -> None:
        device = self.binary.device()
        assert device is not None

        prev_tick = -1
        prev_digest = None

        while not self.binary.atEnd():
            message_op = self.binary.readUInt8()
            message_len = self.binary.readUInt16()
            match message_op:
                case ECmdStreamOp.CMDST_Advance:
                    self.ticks += self.binary.readUInt32()

                case ECmdStreamOp.CMDST_SetCommandSource:
                    player = self.binary.readUInt8()

                case ECmdStreamOp.CMDST_CommandSourceTerminated:
                    self.lasttick[player] = self.ticks

                case ECmdStreamOp.CMDST_VerifyChecksum:
                    digest = self.binary.readRawData(16)
                    tick_num = self.binary.readUInt32()

                    if tick_num == prev_tick and digest != prev_digest and not self.game_stats:
                        raise ReplayException("DESYNC")

                    prev_digest = digest
                    prev_tick = tick_num

                case ECmdStreamOp.CMDST_SetCommandTarget:
                    self.binary.readUInt32()
                    stitarget = self.binary.readUInt8()

                    if stitarget == STITARGET.NONE:
                        pass
                    elif stitarget == STITARGET.Entity:
                        self.binary.readUInt32()
                    elif stitarget == STITARGET.Position:
                        (x, _, z) = (self.binary.readFloat() for _ in range(3))
                        self.pts.append((self.ticks, x, z))
                    else:
                        raise ReplayException("Not valid stitarget", stitarget)

                case ECmdStreamOp.CMDST_LuaSimCallback:
                    callback_start = device.pos()

                    function = self.return_next_string()
                    lua = self.parse_lua()

                    self.process_moderator_event(function, lua)
                    self.append_chatline(function, lua)

                    callback_end = device.pos()
                    # MOST of the time it works with the default `skipRawData(readUInt32() * 4)`
                    # (default means all other faf replay parsers implement it this way)
                    # BUT there was a case with the replay 24470050, where only 3 bytes left
                    # after reading function and lua, which is not enough to read u32
                    self.binary.skipRawData(message_len - 3 - (callback_end - callback_start))

                case ECmdStreamOp.CMDST_IssueCommand | ECmdStreamOp.CMDST_IssueFactoryCommand:
                    self.CPM[player] += 1  # increase commands number
                    self.cpmChart[player].append(self.ticks)
                    unitNums = self.binary.readUInt32()
                    self.binary.skipRawData(4 * (unitNums + 2))

                    command_type = self.binary.readUInt8()
                    self.binary.skipRawData(4)  # skip
                    stitarget = self.binary.readUInt8()

                    if stitarget == STITARGET.NONE:
                        pass
                    elif stitarget == STITARGET.Entity:
                        self.binary.readUInt32()
                    elif stitarget == STITARGET.Position:
                        (x, _, z) = (self.binary.readFloat() for _ in range(3))
                        self.pts.append((self.ticks, x, z))

                    self.binary.skipRawData(1)  # 0x00
                    formation = self.binary.readInt32()
                    if formation != -1:
                        _, x, _, z = (self.binary.readFloat() for _ in range(4))
                        self.binary.readFloat()

                    bp = self.return_next_string()
                    self.binary.skipRawData(12)  # 0x0 0x0 0x0 0x0

                    upgradeLua = self.parse_lua()
                    if upgradeLua:
                        self.binary.skipRawData(1)

                    self.commands[player].append({
                        "tick": self.ticks,
                        "cmd_type": command_type,
                        "blueprint": bp,
                        "upgrades": upgradeLua,
                    })

                case _:
                    self.binary.skipRawData(message_len - 3)

        self.replayPercentage.emit(100)

    def process_moderator_event(self, function: str, lua: dict) -> None:
        if (
            function != "ModeratorEvent"
            or "Message" not in lua
            or not lua["Message"].startswith("GpgNetSend with command 'JsonStats'")
        ):
            return

        if not self.game_stats:
            try:
                self.game_stats = json.loads(lua["Message"][46:-2])
            except json.JSONDecodeError as e:
                logger.exception("Error while parsing game stats: %s, lua: %s", e, lua)

    def append_chatline(self, function: str, lua: dict) -> None:
        if function != "GiveResourcesToPlayer" or "Msg" not in lua:
            return

        sender = int(lua["From"]) - 1

        # -2 => observer talking ...
        if sender == -2 or sender not in self.army:
            return

        if self.army[sender]["PlayerName"] == lua["Sender"]:
            self.chatLine.append((
                self.ticks,
                lua["Sender"],
                lua["Msg"]["to"],
                lua["Msg"]["text"],
                sender,
            ))

    def to_readable_date(self, timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def real_time(self) -> str:
        try:
            start = self.faf_info.get("launched_at") or self.faf_info.get("game_time")
            if start is None:
                return ""
            end = self.faf_info["game_end"]
            if datetime.fromtimestamp(start).day == datetime.fromtimestamp(end).day:
                start_str = datetime.fromtimestamp(start).strftime("%Y-%m-%d (%A)<br/> %H:%M:%S")
                end_str = datetime.fromtimestamp(end).strftime("%H:%M:%S")
            else:
                start_str = self.to_readable_date(start)
                end_str = self.to_readable_date(end)
            duration = seconds_to_human(end - start, sep=" ", full=False)
            return f"{start_str} - {end_str} <br/> ({duration})"
        except Exception:  # sometimes theres no such info
            return ""

    def _coop_teams(self) -> dict[int, list[int]]:
        teams = defaultdict(list)
        for id, player in self.army.items():
            # FIXME: figure out how to determine teams more accurately
            if player["Human"] or player["StartSpot"] != 1:
                teams[1].append(id)
            elif id != 255:
                teams[2].append(id)
        return teams

    def _non_coop_teams(self) -> dict[int, list[int]]:
        teams = defaultdict(list)
        ffa_team = 1
        for id, player in self.army.items():
            if id == 255:
                continue
            team = player["Team"]
            if team == 1:
                teams[ffa_team].append(id)
                ffa_team += 1
            else:
                teams[team].append(id)
        return teams

    def get_teams(self) -> dict[int, list[int]]:
        if self.faf_info.get("featured_mod", "") == "coop":
            return self._coop_teams()
        else:
            return self._non_coop_teams()

    def _gen_info(self) -> Generator[str, None, None]:
        teams = self.get_teams()
        yield (
            f"<center><h2>{self.faf_info['title']}</h2>"
            f"<center><h3>{self.replayPatchFieldId}</h3>"
            f"<center><h4>host: {self.faf_info['host']}</h4>"
            f"<h3>{seconds_to_human(self.ticks // 10, sep=' ', full=False)}</h3>"
            f"<h4>{self.real_time()}</h4>"
            "</center>"
            "<p><table width=100%><tr>"
        )

        if self.gameMods:
            yield "<td><b>Mods</b><br/>"
            for mod in self.gameMods.values():
                yield f"{mod['name']}<br/>"
            yield "</td>"
        if self.observers:
            yield "<td><b>Observers</b><br/>"
            for observer in self.observers.values():
                yield f"{observer}<br/>"
            yield "</td>"
        yield "</table></p>"

        teamid = 0
        yield "<p><table width=100%>"
        for team in teams.items():
            teamid += 1
            yield (
                f"<tr><th bgcolor=grey colspan=5><font color=white>"
                f"team {str(teamid)}"
                f"</font></th></tr>"
            )
            for id in team[1]:
                yield "<tr>"
                color_num = int(self.army[id]["PlayerColor"])
                color = PLAYER_COLORS[color_num - 1]
                yield f"<td width=40 style='background-color:{color}'></td>"
                fac_icon = self.get_faction_img_path(self.army[id]['Faction'])
                yield f"<td align='center'><img height=24 src=\"{fac_icon}\"/></td>"
                if country := self.army[id].get("Country", ""):
                    flagfile = self.get_country_img_path(country)
                    yield f"<td><img src=\"{flagfile}\" title=\"{country}\"/></td>"
                yield f"<td><b>{self.army[id]["PlayerName"]}</b><br/>"
                if "MEAN" in self.army[id] and "DEV" in self.army[id]:
                    rating = int(self.army[id]["MEAN"] - 3*self.army[id]["DEV"])
                    yield f"Rating: {rating}"
                # Commands per minute
                if self.ticks and id in self.players:
                    yield " apm: "
                    try:
                        if id in self.lasttick:  # player dies before the game ends
                            yield f"{self.CPM[id] / (self.lasttick[id] * 1.0 / 10 / 60):.2f}"
                        else:
                            yield f"{self.CPM[id] / (self.ticks * 1.0 / 10 / 60):.2f}"
                    except ZeroDivisionError:
                        yield "0.00"
                yield "</td></tr>"
            yield "<tr><td>&nbsp;</td></tr>"
        yield "</table></p>"

    def get_info(self) -> str:
        return "".join(self._gen_info())

    def generated_map_size(self) -> str:
        desc = self.luaScenarioInfo["description"].split("\r\n")
        for line in desc:
            if "Map Size" in line:
                size = int(line.split(":")[-1])
                return f"{size/51.2:.2f}x{size/51.2:.2f}"
        return ""

    def map_display_size(self) -> str:
        (a, b) = self.luaScenarioInfo["size"][1.0], self.luaScenarioInfo["size"][2.0]
        return f"{int(a/51.2)}x{int(b/51.2)}"

    def actual_map_size(self) -> str:
        if isGeneratedMap(self.map_folder_name()):
            return self.generated_map_size()
        return self.map_display_size()

    def map_display_name(self) -> str:
        return self.luaScenarioInfo["name"]

    def _gen_chat(self) -> Generator[str, None, None]:
        yield "<table width=100%>"
        for index, line in enumerate(self.chatLine):
            bgcolor = ("#202025", "#303035")[index % 2]
            yield f"<tr bgcolor='{bgcolor}'>"
            for i, elem in enumerate(line[:-1]):
                if i == 0:
                    text = seconds_to_human(elem // 10)
                else:
                    text = elem
                yield f"<td style='color: silver;'>{text}</td>"
            yield "</tr>"
        yield "</table>"

    def get_chat(self) -> str:
        return "".join(self._gen_chat())

    def _html_escape(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return html.escape(value)

    def _gen_settings(self) -> Generator[str, None, None]:
        yield (
            f"<center><h2>{self.map_display_name()}</h2><h4>"
            f"{self.actual_map_size()}</h4></center><table>"
        )
        for k, v in sorted(self.luaScenarioInfo["Options"].items()):
            if k not in ["Ratings", "ScenarioFile", "ReplayID"]:
                if not isinstance(v, dict):
                    yield (
                        f"<tr>"
                        f"<td><b>{self._html_escape(k)}</b></td>"
                        f"<td>{self._html_escape(v)}</td>"
                        f"</tr>"
                    )
                else:
                    yield f"<tr><td><b>{self._html_escape(k)}</b></td><td>&nbsp;</td></tr>"
                    for k2, v2 in v.items():
                        yield (
                            f"<tr>"
                            f"<td><i>{self._html_escape(k2)}</i></td>"
                            f"<td>{self._html_escape(v2)}</td>"
                            f"</tr>"
                        )
        yield "</table>"

    def get_settings(self) -> str:
        return "".join(self._gen_settings())

    def get_game_id(self) -> int:
        return self.faf_info["uid"] if self.faf_info and "uid" in self.faf_info else 0

    def _parse_with_zig(self) -> bool:
        if (
            parse_replaydata is None
            or (parsed := parse_replaydata(self.body)) is None
        ):
            return False

        self.replayPatchFieldId = parsed["header"]["patch"]
        self.replayVersionId, self.map = parsed["header"]["version"].split("\r\n")

        self.gameMods = parsed["header"]["mods"]
        self.luaScenarioInfo = parsed["header"]["scenario_info"]
        self.players = parsed["header"]["players"]
        self.observers = parsed["header"]["observers"]
        self.army = parsed["header"]["armies"]
        self.randomSeed = parsed["header"]["random_seed"]

        self.ticks = parsed["body"]["ticks"]
        self.pts = parsed["body"]["points"]
        self.lasttick = parsed["body"]["lasttick"]
        self.commands = parsed["body"]["commands"]
        self.chatLine = parsed["body"]["chatlines"]
        self.cpmChart = parsed["body"]["chart_data"]
        self.game_stats = parsed["body"]["game_stats"]

        self.CPM = {id: len(comlist) for id, comlist in self.commands.items()}
        return True

    def do_stuff(self) -> None:
        if self.binary == QDataStream():
            raise ReplayException("Invalid File Format or Data")
        try:
            compiled_lib_worked = self._parse_with_zig()
        except RuntimeError:
            raise ReplayException("DESYNC")
        if not compiled_lib_worked:
            self.parse_header()
            self.parse_ticks()
