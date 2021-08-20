import re

from PyQt5 import QtCore


class LeaderboardFilterModel(QtCore.QSortFilterProxyModel):
    def lessThan(self, leftIndex, rightIndex):
        column = leftIndex.column()
        leftData = self.sourceModel().data(leftIndex)
        rightData = self.sourceModel().data(rightIndex)

        if column == 0:  # Name
            return leftData < rightData
        elif column == 1:  # Rating
            return int(leftData) < int(rightData)
        elif column == 2:  # Mean
            return float(leftData) < float(rightData)
        elif column == 3:  # Deviation
            return float(leftData) < float(rightData)
        elif column == 4:  # Total Games
            return int(leftData) < int(rightData)
        elif column == 5:  # Won Games
            return int(leftData) < int(rightData)
        elif column == 6:  # Win rate
            percentageLeft = float(re.sub(r"[^\d.]", "", str(leftData)))
            percentageRight = float(re.sub(r"[^\d.]", "", str(rightData)))
            return percentageLeft < percentageRight
        elif column == 7:  # Updated
            return leftData < rightData

    def headerData(self, section, orientation, role):
        return self.sourceModel().headerData(section, orientation, role)
