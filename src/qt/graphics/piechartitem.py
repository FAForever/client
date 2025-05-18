from typing import Sequence

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QGraphicsEllipseItem
from PyQt6.QtWidgets import QGraphicsRectItem
from PyQt6.QtWidgets import QStyleOptionGraphicsItem
from PyQt6.QtWidgets import QWidget

type Color = (
        # Qt defines integers in tuples as optionals so do we
        tuple[int | None, int | None, int | None, int | None]
        | str
)


class PieChartItem(pg.GraphicsObject):
    def __init__(
        self,
        values: Sequence[float],
        labels: Sequence[str] | None = None,
        colors: Sequence[Color] | None = None,
        radius: float = 1.0,
        start_angle: int = 0,
        parent_item: pg.GraphicsObject | None = None,
    ) -> None:
        pg.GraphicsObject.__init__(self, parent_item)
        self.values = values
        self.total = sum(values) or len(values) or 1
        self.labels = labels if labels is not None else [f"Slice {i}" for i in range(len(values))]

        if colors is None:
            hues = np.linspace(0.5, 0.6, len(values))
            colors = [pg.colorTuple(pg.hsvColor(h, 1, 1)) for h in hues]
        self.colors = colors

        self.radius = radius
        self.startAngle = start_angle

        self.sectors: list[QGraphicsEllipseItem] = []
        self.create_sectors()

        self.legend_items: list[QGraphicsRectItem] = []
        self.legend_labels: list[pg.TextItem] = []
        self.create_legend()

    def create_sectors(self) -> None:
        start_angle = self.startAngle
        for i, value in enumerate(self.values):
            angle = 360 * value / self.total
            sector = QGraphicsEllipseItem(0, 0, 2*self.radius, 2*self.radius, self)
            sector.setStartAngle(int(start_angle * 16))
            sector.setSpanAngle(int(angle * 16))
            sector.setPen(pg.mkPen(self.colors[i]))
            sector.setBrush(pg.mkBrush(self.colors[i]))
            sector.setPos(-self.radius, -self.radius)
            sector.setToolTip(f"{self.labels[i]}: {value} ({value/self.total:.1%})")
            self.sectors.append(sector)
            start_angle += angle

    def create_legend(self) -> None:
        for i, label in enumerate(self.labels):
            rect = QGraphicsRectItem(-5, -5, 10, 10, self)
            rect.setPen(pg.mkPen(self.colors[i]))
            rect.setBrush(pg.mkBrush(self.colors[i]))
            rect.setPos(self.radius + 20, i * 20)
            self.legend_items.append(rect)

            text = pg.TextItem(text=f"{label}: {self.values[i]} ({self.values[i]/self.total:.1%})")
            text.setAnchor((0.0, 0.5))
            text.setParentItem(self)
            text.setPos(self.radius + 35, i * 20)
            self.legend_labels.append(text)

    def boundingRect(self) -> QRectF:
        max_label_width = 0
        for label in self.legend_labels:
            # Approximate width
            max_label_width = max(max_label_width, len(label.textItem.toPlainText()) * 7)

        legend_width = 35 + max_label_width
        legend_height = len(self.labels) * 20

        return QRectF(
            -self.radius, -self.radius,
            2*self.radius + legend_width,
            max(2*self.radius, legend_height),
        )

    def paint(
            self,
            painter: QPainter | None,
            option: QStyleOptionGraphicsItem | None,
            widget: QWidget | None = None,
    ) -> None:
        # This method is left empty because it has to be overriden
        # and the sectors are drawn as child items
        ...
