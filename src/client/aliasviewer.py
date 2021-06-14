from PyQt5 import QtWidgets, QtCore

import logging
logger = logging.getLogger(__name__)

from api.player_api import PlayerApiConnector

class AliasViewer:
    def __init__(self, client, alias_formatter):
        self.client = client
        self.formatter = alias_formatter
        self.api_connector = PlayerApiConnector(self.client.lobby_dispatch)
        self.client.lobby_info.aliasInfo.connect(self.process_alias_info)
        self.name_to_find = ""
        self.searching = False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.stop_alias_search)

    def find_aliases(self, login):
        if self.searching:
            return
        self.name_to_find = login
        self.api_connector.requestDataForAliasViewer(login)
        self.searching = True
        self.timer.start(10000)

    def stop_alias_search(self):
        self.searching = False
        self.timer.stop()

    def process_alias_info(self, message):
        self.stop_alias_search()

        player_aliases, other_users = [], []
        for player in message["values"]:
            if player["login"].lower() == self.name_to_find.lower():
                player_aliases.append({"name" : player["login"], "changeTime" : None})
                for name_record in player["names"]:
                    player_aliases.append(name_record)
            else:
                for name_record in player["names"]:
                    if name_record["name"].lower() == self.name_to_find.lower():
                        other_users.append({"name" : player["login"], "changeTime" : name_record["changeTime"]})

        self.show_aliases(player_aliases, other_users)

    def show_aliases(self, player_aliases, other_users):
        QtWidgets.QMessageBox.about(
            self.client,
            "Aliases : {}".format(self.name_to_find),
            self.formatter.format_aliases(player_aliases, other_users)
        )

class AliasFormatter:
    def __init__(self):
        pass

    def nick_times(self, name_records):
        past_records = [record for record in name_records if record["changeTime"] is not None]
        current_records = [record for record in name_records if record["changeTime"] is None]

        for record in past_records:
            record["changeTime"] = QtCore.QDateTime.fromString(record["changeTime"], QtCore.Qt.ISODate).toLocalTime()

        past_records.sort(key=lambda record: record["changeTime"])

        for record in past_records:
            record["changeTime"] = QtCore.QDateTime.toString(record["changeTime"], "yyyy-MM-dd '&nbsp;' hh:mm")
        for record in current_records:
            record["changeTime"] = "now"

        return past_records + current_records

    def nick_time_table(self, nicks):
        table = '<br/><table border="0" cellpadding="0" cellspacing="1" width="220"><tbody>' \
                '{}' \
                '</tbody></table>'
        head = '<tr><th align="left"> Name</th><th align="center"> used until</th></tr>'
        line_fmt = '<tr><td>{}</td><td align="right">{}</td></tr>'
        lines = [line_fmt.format(nick["name"], nick["changeTime"]) for nick in nicks]
        return table.format(head + "".join(lines))

    def name_used_by_others(self, player_aliases, other_users):
        if len(player_aliases) == len(other_users) == 0:
            return 'The name has never been used.'
        elif len(other_users) == 0:
            return 'The name has never been used by anyone else.'

        return 'The name has previously been used by:{}'.format(
                self.nick_time_table(self.nick_times(other_users))
        )

    def names_previously_known(self, player_aliases):
        if len(player_aliases) == 0:
            return ''
        elif len(player_aliases) == 1:
            return 'The user has never changed their name.'

        return 'The player has previously been known as:{}'.format(
                self.nick_time_table(self.nick_times(player_aliases))
        )

    def format_aliases(self, player_aliases, other_users):
        alias_format = self.names_previously_known(player_aliases)
        others_format = self.name_used_by_others(player_aliases, other_users)
        result = '{}<br/><br/>{}'.format(alias_format, others_format)
        return result

class AliasWindow:
    def __init__(self, parent_widget, alias_viewer):
        self._parent_widget = parent_widget
        self._alias_viewer = alias_viewer

    @classmethod
    def build(cls, parent_widget, **kwargs):
        alias_viewer = AliasViewer(parent_widget, AliasFormatter())
        return cls(parent_widget, alias_viewer)

    def view_aliases(self, name):
        self._alias_viewer.find_aliases(name)

class AliasSearchWindow:
    def __init__(self, parent_widget, alias_window):
        self._parent_widget = parent_widget
        self._alias_window = alias_window
        self._search_window = None

    @classmethod
    def build(cls, parent_widget, **kwargs):
        alias_window = AliasWindow.build(parent_widget, **kwargs)
        return cls(alias_window)

    def search_alias(self, name):
        self._alias_window.view_aliases(name)
        self._search_window = None

    def run(self):
        self._search_window = QtWidgets.QInputDialog(self._parent_widget)
        self._search_window.setInputMode(QtWidgets.QInputDialog.TextInput)
        self._search_window.textValueSelected.connect(self.search_alias)
        self._search_window.setLabelText("User name / alias:")
        self._search_window.setWindowTitle("Alias search")
        self._search_window.open()
