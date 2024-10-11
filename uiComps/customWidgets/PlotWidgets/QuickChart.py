
# Copyright (c) 2024 Jelmer de Vries
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation in its latest version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtChart import QChartView
from PyQt5.QtCore import pyqtSignal

from dataHandling.Constants import Constants
from uiComps.customWidgets.PlotWidgets.CandlePlotWidget import CandlePlotWidget


class MouseChartView(QChartView):

    mouseMoved = pyqtSignal(QtCore.QPoint)
    mousePressed = pyqtSignal(QtCore.QPoint)
    mouseReleased = pyqtSignal(QtCore.QPoint)


    def mouseMoveEvent(self, event):
        self.mouseMoved.emit(event.pos())
        return super().mouseMoveEvent(event)


    def mousePressEvent(self, event):
        self.mousePressed.emit(event.pos())
        return super().mousePressEvent(event)


    def mouseReleaseEvent(self, event):
        self.mouseReleased.emit(event.pos())
        return super().mouseReleaseEvent(event)


class QuickChart(QtWidgets.QDialog):

    scrolling_mouse = False
    tz = None

    def __init__(self, symbol="TEST", bar_type="5 min", tz=None, bars=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Candle Sticks")
        self.bars = bars
        if tz is not None: self.tz = tz
        self.setupChart(bars, symbol, bar_type)


    def setupChart(self, bars, symbol, bar_type):

        self.chart = CandlePlotWidget(self.barClick)
        self.chart.setHistoricalData(bars)
        
        self.chart.setTitle(f"{symbol}: {bar_type} bars (count:{len(self.bars)})")
        # self.chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        # self.addAxisWithData(self.chart, chart_view, bars)
        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.chart)

        if self.tz is not None:
            self.chart.setTimezone(self.tz)


    def barClick(self, high_low, price_level):
        pass
