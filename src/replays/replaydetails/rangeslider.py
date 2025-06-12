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
# from https://svn.enthought.com/enthought/browser/TraitsBackendQt/trunk/enthought/traits/ui/qt4/extra/range_slider.py  # noqa: E501

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets


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
        # based on http://qt.gitorious.org/qt/qt/blobs/master/src/gui/widgets/qslider.cpp

        painter = QtGui.QPainter(self)
        style = QtWidgets.QApplication.style()
        assert style is not None

        for i, value in enumerate([self._low, self._high]):
            opt = QtWidgets.QStyleOptionSlider()
            self.initStyleOption(opt)

            # Only draw the groove for the first slider so it doesn't get drawn
            # on top of the existing ones every time
            if i == 0:
                opt.subControls = (
                    QtWidgets.QStyle.SubControl.SC_SliderGroove
                    | QtWidgets.QStyle.SubControl.SC_SliderHandle
                )
            else:
                opt.subControls = QtWidgets.QStyle.SubControl.SC_SliderHandle

            if self.tickPosition() != self.TickPosition.NoTicks:
                opt.subControls |= QtWidgets.QStyle.SubControl.SC_SliderTickmarks

            if self.pressed_control:
                opt.activeSubControls = self.pressed_control
                opt.state |= QtWidgets.QStyle.StateFlag.State_Sunken
            else:
                opt.activeSubControls = self.hover_control

            opt.sliderPosition = value
            opt.sliderValue = value
            style.drawComplexControl(QtWidgets.QStyle.ComplexControl.CC_Slider, opt, painter, self)

    def mousePressEvent(self, ev: QtGui.QMouseEvent | None) -> None:
        if ev is None:
            return
        ev.accept()

        style = QtWidgets.QApplication.style()
        assert style is not None

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
                hit = style.hitTestComplexControl(
                    style.ComplexControl.CC_Slider, opt, ev.pos(), self,
                )
                if hit == style.SubControl.SC_SliderHandle:
                    self.active_slider = i
                    self.pressed_control = hit

                    self.triggerAction(self.SliderAction.SliderMove)
                    self.setRepeatAction(self.SliderAction.SliderNoAction)
                    self.setSliderDown(True)
                    break

            if self.active_slider < 0:
                self.pressed_control = QtWidgets.QStyle.SubControl.SC_SliderHandle
                self.click_offset = self._pixel_pos_to_range_value(self._pick(ev.pos()))
                self.triggerAction(self.SliderAction.SliderMove)
                self.setRepeatAction(self.SliderAction.SliderNoAction)
        else:
            ev.ignore()

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent | None) -> None:
        if ev is None:
            return

        if self.pressed_control != QtWidgets.QStyle.SubControl.SC_SliderHandle:
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
        style = QtWidgets.QApplication.style()
        assert style is not None

        complex_control = style.ComplexControl.CC_Slider
        gr = style.subControlRect(complex_control, opt, style.SubControl.SC_SliderGroove, self)
        sr = style.subControlRect(complex_control, opt, style.SubControl.SC_SliderHandle, self)

        if self.orientation() == QtCore.Qt.Orientation.Horizontal:
            slider_length = sr.width()
            slider_min = gr.x()
            slider_max = gr.right() - slider_length + 1
        else:
            slider_length = sr.height()
            slider_min = gr.y()
            slider_max = gr.bottom() - slider_length + 1

        return style.sliderValueFromPosition(
            self.minimum(), self.maximum(),
            pos - slider_min, slider_max - slider_min,
            opt.upsideDown,
        )
