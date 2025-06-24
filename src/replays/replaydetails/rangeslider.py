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
SOFTWARE.

Copyright (c) 2021, Talley Lambert
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of superqt nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."""
# from https://svn.enthought.com/enthought/browser/TraitsBackendQt/trunk/enthought/traits/ui/qt4/extra/range_slider.py  # noqa: E501
# and https://github.com/pyapp-kit/superqt/tree/13e033e4a26170dd46c6f3b73c1f8c5c08959c59/src/superqt/sliders  # noqa: E501

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets
from PyQt6.QtCore import QRect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QStyle
from PyQt6.QtWidgets import QStyleOptionSlider
from PyQt6.QtWidgets import QStylePainter

CC_SLIDER = QtWidgets.QStyle.ComplexControl.CC_Slider
SC_GROOVE = QtWidgets.QStyle.SubControl.SC_SliderGroove
SC_HANDLE = QtWidgets.QStyle.SubControl.SC_SliderHandle
SC_NONE = QtWidgets.QStyle.SubControl.SC_None


class RangeSlider(QtWidgets.QSlider):
    sliderMoved = QtCore.pyqtSignal(int, int)

    """ A slider for ranges.

        This class provides a dual-slider for ranges, where there is a defined
        maximum and minimum, as is a normal slider, but instead of having a
        single slider value, there are 2 slider values.

        This class emits the same signals as the QSlider base class, with the
        exception of valueChanged
    """
    def __init__(self, *args):
        QtWidgets.QSlider.__init__(self, *args)

        self._low: int = self.minimum()
        self._high: int = self.maximum()

        self.pressed_control = QtWidgets.QStyle.SubControl.SC_None
        self.hover_control = QtWidgets.QStyle.SubControl.SC_None
        self.click_offset = 0

        # 0 for the low, 1 for the high, -1 for both
        self.active_slider = 0

        self._offset_accum = 0
        self._value = 0
        self._control_fraction = 0.04

        self._page_step = 10
        self._remove_subpage_style()

    @property
    def _style(self) -> QStyle:
        style = self.style()
        assert style is not None
        return style

    def _remove_subpage_style(self) -> None:
        current = self.styleSheet()
        override = """
            QSlider::sub-page:horizontal {
                background: none;
                border: none;
            }
            QSlider::add-page:horizontal {
                background: none;
                border: none;
            }
        """
        self.setStyleSheet(current + override)

    def low(self) -> int:
        return self._low

    def setLow(self, low: int) -> None:
        self._low = low
        self.update()

    def high(self) -> int:
        return self._high

    def setHigh(self, high: int) -> None:
        self._high = high
        self.update()

    def paintEvent(self, ev: QtGui.QPaintEvent | None) -> None:
        if ev is None:
            return

        painter = QtWidgets.QStylePainter(self)

        opt = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(opt)
        opt.subControls = SC_GROOVE

        grect = self._style.subControlRect(CC_SLIDER, opt, SC_GROOVE, self)
        slrect = opt.rect
        rect = QRect(slrect.left(), grect.center().y() - 2, slrect.width() - 5, 4)
        brush = QBrush(QColor("#333333"))  # FIXME: Needs to come from theme
        painter.fillRect(rect, brush)
        self._draw_bar(painter, opt)
        self._draw_handle(painter, opt)

    def _draw_handle(self, painter: QStylePainter, opt: QStyleOptionSlider) -> None:
        opt.subControls = SC_HANDLE
        for i, value in enumerate([self._low, self._high]):
            if self.tickPosition() != self.TickPosition.NoTicks:
                opt.subControls |= QtWidgets.QStyle.SubControl.SC_SliderTickmarks

            if self.pressed_control:
                opt.activeSubControls = self.pressed_control
                opt.state |= QtWidgets.QStyle.StateFlag.State_Sunken
            else:
                opt.activeSubControls = self.hover_control
                opt.state &= ~QtWidgets.QStyle.StateFlag.State_Sunken

            opt.sliderPosition = value
            opt.activeSubControls = SC_NONE
            painter.drawComplexControl(CC_SLIDER, opt)

    def _handle_rect(self, index: int, opt: QStyleOptionSlider) -> QRect:
        opt.sliderPosition = self._low if index == 0 else self._high
        return self._style.subControlRect(CC_SLIDER, opt, SC_HANDLE, self)

    def _bar_rect(self, opt: QStyleOptionSlider) -> QRect:
        """Return the QRect for the bar between the outer handles."""
        r_groove = self._style.subControlRect(CC_SLIDER, opt, SC_GROOVE, self)
        r_bar = QRect(r_groove)
        hdl_low, hdl_high = self._handle_rect(0, opt), self._handle_rect(1, opt)

        thickness = 4

        if opt.orientation == Qt.Orientation.Horizontal:
            r_bar.setTop(r_bar.center().y() - thickness // 2)
            r_bar.setHeight(thickness)
            r_bar.setLeft(hdl_low.center().x())
            r_bar.setRight(hdl_high.center().x())
        else:
            r_bar.setLeft(r_bar.center().x() - thickness // 2)
            r_bar.setWidth(thickness)
            r_bar.setBottom(hdl_low.center().y())
            r_bar.setTop(hdl_high.center().y())

        return r_bar

    def _draw_bar(self, painter: QStylePainter, opt: QStyleOptionSlider) -> None:
        r_bar = self._bar_rect(opt)
        brush = QBrush(QColor("#1A7BFF"))  # FIXME: Needs to come from theme
        painter.fillRect(r_bar, brush)

    def mousePressEvent(self, ev: QtGui.QMouseEvent | None) -> None:
        if ev is None:
            return
        ev.accept()

        button = ev.button()

        # In a normal slider control, when the user clicks on a point in the
        # slider's total range, but not on the slider part of the control the
        # control would jump the slider value to where the user clicked.
        # For this control, clicks which are not direct hits will slide both
        # slider parts

        if button:
            opt = QtWidgets.QStyleOptionSlider()
            self.initStyleOption(opt)

            self.active_slider = -1

            for i, value in enumerate([self._low, self._high]):
                opt.sliderPosition = value
                hit = self._style.hitTestComplexControl(CC_SLIDER, opt, ev.pos(), self)
                if hit == SC_HANDLE:
                    self.active_slider = i
                    self.pressed_control = hit

                    self.triggerAction(self.SliderAction.SliderMove)
                    self.setRepeatAction(self.SliderAction.SliderNoAction)
                    self.setSliderDown(True)
                    break

            if self.active_slider < 0:
                self.pressed_control = SC_HANDLE
                self.click_offset = self._pixel_pos_to_range_value(self._pick(ev.pos()))
                self.triggerAction(self.SliderAction.SliderMove)
                self.setRepeatAction(self.SliderAction.SliderNoAction)
        else:
            ev.ignore()

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent | None) -> None:
        if ev is None:
            return

        if self.pressed_control != SC_HANDLE:
            ev.ignore()
            return

        ev.accept()
        new_pos = self._pixel_pos_to_range_value(self._pick(ev.pos()))
        opt = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(opt)

        old_low = self._low
        old_high = self._high

        if self.active_slider < 0:
            offset = new_pos - self.click_offset
            self._high += offset
            self._low += offset
            if self._low < self.minimum():
                diff = self.minimum() - self._low
                self._low += diff
                self._high += diff
            if self._high > self.maximum():
                diff = self.maximum() - self._high
                self._low += diff
                self._high += diff
        elif self.active_slider == 0:
            if new_pos >= self._high:
                new_pos = self._high - 1
            self._low = new_pos
        else:
            if new_pos <= self._low:
                new_pos = self._low + 1
            self._high = new_pos

        self.click_offset = new_pos

        self.update()

        if (self._low, self._high) != (old_low, old_high):
            self.sliderMoved.emit(self._low, self._high)

    def _pick(self, pt: QtCore.QPoint) -> int:
        if self.orientation() == QtCore.Qt.Orientation.Horizontal:
            return pt.x()
        else:
            return pt.y()

    def _pixel_pos_to_range_value(self, pos: int) -> int:
        opt = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(opt)

        gr = self._style.subControlRect(CC_SLIDER, opt, SC_GROOVE, self)
        sr = self._style.subControlRect(CC_SLIDER, opt, SC_HANDLE, self)

        if self.orientation() == QtCore.Qt.Orientation.Horizontal:
            slider_length = sr.width()
            slider_min = gr.x()
            slider_max = gr.right() - slider_length + 1
        else:
            slider_length = sr.height()
            slider_min = gr.y()
            slider_max = gr.bottom() - slider_length + 1

        return self._style.sliderValueFromPosition(
            self.minimum(), self.maximum(),
            pos - slider_min, slider_max - slider_min,
            opt.upsideDown,
        )

    def wheelEvent(self, e: QtGui.QWheelEvent | None) -> None:
        if e is None:
            return

        e.ignore()
        vertical = bool(e.angleDelta().y())
        delta = e.angleDelta().y() if vertical else e.angleDelta().x()
        if e.inverted():
            delta *= -1

        orientation = Qt.Orientation.Vertical if vertical else Qt.Orientation.Horizontal
        if self._scroll_by_delta(orientation, e.modifiers(), delta):
            e.accept()
            self.sliderMoved.emit(self._low, self._high)

    def _scroll_by_delta(
            self,
            orientation: Qt.Orientation,
            modifiers: Qt.KeyboardModifier,
            delta: int,
    ) -> bool:
        steps_to_scroll = 0
        page_step = self._page_step

        # in Qt scrolling to the right gives negative values.
        if orientation == Qt.Orientation.Horizontal:
            delta *= -1
        offset = delta / 120
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Scroll one page regardless of delta:
            steps_to_scroll = max(-page_step, min(page_step, offset * page_step))
            self._offset_accum = 0
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            _range = self._high - self._low
            steps_to_scroll = offset * _range * self._control_fraction
            self._offset_accum = 0
        else:
            # Calculate how many lines to scroll. Depending on what delta is (and
            # offset), we might end up with a fraction (e.g. scroll 1.3 lines). We can
            # only scroll whole lines, so we keep the reminder until next event.
            wheel_scroll_lines = QtWidgets.QApplication.wheelScrollLines()
            steps_to_scrollF = wheel_scroll_lines * offset
            # Check if wheel changed direction since last event:
            if self._offset_accum != 0 and (offset / self._offset_accum) < 0:
                self._offset_accum = 0

            self._offset_accum += steps_to_scrollF

            # Don't scroll more than one page in any case:
            steps_to_scroll = max(-page_step, min(page_step, self._offset_accum))
            self._offset_accum -= self._offset_accum

            if steps_to_scroll == 0:
                # We moved less than a line, but might still have accumulated partial
                # scroll, unless we already are at one of the ends.
                effective_offset = self._offset_accum
                if self.invertedControls():
                    effective_offset *= -1
                if self._has_scroll_space_left(effective_offset):
                    return True
                self._offset_accum = 0
                return False

        if self.invertedControls():
            steps_to_scroll *= -1

        old_pos = (self._low, self._high)
        if modifiers & Qt.KeyboardModifier.AltModifier:
            self._spread(round(steps_to_scroll))
        else:
            self._execute_scroll(round(steps_to_scroll))
        if old_pos == (self._low, self._high):
            self._offset_accum = 0
            return False
        return True

    def _bound(self, mn: int, mx: int) -> tuple[int, int]:
        return (
            int(max(self.minimum(), min(self.maximum(), mn))),
            int(min(self.maximum(), max(self.minimum(), mx))),
        )

    def _spread(self, steps_to_scroll: int) -> None:
        if (
                self._high - steps_to_scroll > self.maximum()
                or self._low + steps_to_scroll < self.minimum()
                or self._high - steps_to_scroll < self._low + steps_to_scroll
        ):
            return
        self._low, self._high = self._bound(
            self._low + steps_to_scroll,
            self._high - steps_to_scroll,
        )
        self.update()

    def _execute_scroll(self, steps_to_scroll: int) -> None:
        if self._high + steps_to_scroll > self.maximum():
            steps_to_scroll = self.maximum() - self._high
        if self._low + steps_to_scroll < self.minimum():
            steps_to_scroll = self.minimum() - self._low
        self._low, self._high = self._bound(
            self._low + steps_to_scroll,
            self._high + steps_to_scroll,
        )
        self.update()

    def _has_scroll_space_left(self, offset: float) -> bool:
        return (
            offset > 0 and self._high < self.maximum()
        ) or (
            offset < 0 and self._low < self.minimum()
        )

    def set_position(self, low: int, high: int) -> None:
        self._low = low
        self._high = high

    def update_position(self, low: int, high: int) -> None:
        old_pos = self._low, self._high
        self.set_position(low, high)
        if old_pos != (self._low, self._high):
            self.update()

    def get_position(self) -> tuple[int, int]:
        return self._low, self._high

    def set_page_step(self, step: int) -> None:
        self._page_step = step
