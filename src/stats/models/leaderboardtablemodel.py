from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QDateTime, QDate, QTime
from PyQt5.QtGui import QColor, QFont, QBrush

class LeaderboardTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        QAbstractTableModel.__init__(self)
        self.load_data(data)

    def load_data(self, data):
        self.values = data["values"]
        self.meta = data["meta"]
        self.logins = []
        for value in self.values:
            self.logins.append(value["player"]["login"])
        self.column_count = 9
        self.row_count = len(data["values"])

    def rowCount(self, parent=QModelIndex()):
        return self.row_count

    def columnCount(self, parent=QModelIndex()):
        return self.column_count

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return ("Name", "Rating", "Mean", "Deviation", "Games", "Won", "Win rate", "Updated", "Player Id")[section]
            else:
                return "{}".format(int(self.meta["page"]["number"] - 1) * int(self.meta["page"]["limit"]) + section + 1)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        row = index.row()

        if role == Qt.DisplayRole:
            if column == 0:
                return "{}".format(self.values[row]["player"]["login"])
            elif column == 1:
                return "{}".format(int(self.values[row]["rating"]))
            elif column == 2:
                return "{:.2f}".format(round(self.values[row]["mean"], 2))
            elif column == 3:
                return "{:.2f}".format(round(self.values[row]["deviation"], 2))
            elif column == 4:
                return "{}".format(self.values[row]["totalGames"])
            elif column == 5:
                return "{}".format(self.values[row]["wonGames"])
            elif column == 6:
                if self.values[row]["totalGames"] == 0:
                    return "{:.2f}%".format(0)
                else:
                    return "{:.2f}%".format(100 * self.values[row]["wonGames"]/self.values[row]["totalGames"])
            elif column == 7:
                dateUTC = QDateTime.fromString(self.values[row]["updateTime"], Qt.ISODate)
                dateLocal = dateUTC.toLocalTime().toString("yyyy-MM-dd")
                return "{}".format(dateLocal)
            elif column == 8:
                return "{}".format(self.values[row]["player"]["id"])

        return None
