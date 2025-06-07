from __future__ import annotations

import math

from PyQt6.QtCore import QPointF
from PyQt6.QtCore import QRectF
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QPainter
from PyQt6.QtGui import QPaintEvent
from PyQt6.QtGui import QPen
from PyQt6.QtGui import QPolygonF
from PyQt6.QtWidgets import QWidget


class StarRatingWidget(QWidget):
    def __init__(
            self,
            rating: float = 0.0,
            max_rating: int = 5,
            star_size: int = 30,
            star_color_filled: QColor = QColor(255, 215, 0),
            parent: QWidget | None = None,
    ) -> None:
        QWidget.__init__(self, parent)

        self.rating = rating
        self.max_rating = max_rating
        self.star_size = star_size

        self.star_color_filled = star_color_filled
        self.star_color_empty = Qt.GlobalColor.black

        self.setFixedSize(self.max_rating * self.star_size, self.star_size)

    def paintEvent(self, event: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i in range(self.max_rating):
            x = i * self.star_size
            if self.rating > i:
                fill_fration = min(1.0, self.rating - i)
                self.draw_star(painter, x, 0, fill_fration)
            else:
                self.draw_star(painter, x, 0, 0)

    def create_star_polygon(self, x: float, y: float, size: int) -> QPolygonF:
        points = []
        for i in range(10):
            angle = math.pi / 10 * (3 + 2 * i)
            radius = size * (0.5 if i % 2 == 0 else 0.2)
            points.append(
                QPointF(
                    x + size * 0.5 + radius * math.cos(angle),
                    y + size * 0.5 + radius * math.sin(angle),
                ),
            )
        return QPolygonF(points)

    def draw_star(self, painter: QPainter, x: float, y: float, fill_fraction: float) -> None:
        star_polygon = self.create_star_polygon(x, y, self.star_size)

        painter.setPen(QPen(self.star_color_empty, 1))
        painter.setBrush(self.star_color_empty)
        painter.drawPolygon(star_polygon)

        if fill_fraction > 0:
            painter.setPen(QPen(self.star_color_filled, 1))
            painter.setBrush(self.star_color_filled)

            clip_rect = QRectF(
                x, y,
                self.star_size * fill_fraction,
                self.star_size,
            )
            painter.setClipRect(clip_rect)
            painter.drawPolygon(star_polygon)
            painter.setClipping(False)

    def set_rating(self, rating: float) -> None:
        self.rating = max(0, min(rating, self.max_rating))
        self.update()
