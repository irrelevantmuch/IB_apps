
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

from PyQt5.QtCore import QTimer
import pyqtgraph as pg
from pyqtgraph import DateAxisItem
from pyqtgraph import QtCore, QtGui

import pytz
from datetime import datetime
import pandas as pd
import numpy as np

from dataHandling.Constants import Constants

pg.setConfigOption("background", "w")

class CandlestickItem(pg.GraphicsObject):

    highlight_delay = 200
    highlight_picture = None


    def __init__(self, bar_data, call_back, w=None, alt_color=False):
        pg.GraphicsObject.__init__(self)
        self.call_back = call_back
        self.bar_data = bar_data  ## data must have fields: time, open, close, min, max
        self.w = w
        self.alt_color = alt_color
        self.generatePicture()
    

    def generatePicture(self):
        ## pre-computing a QPicture object allows paint() to run much more quickly, 
        ## rather than re-drawing the shapes every time.
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen('k'))
        if self.w is None:
            self.w = self.bar_data.index.to_series().diff().min() / 3.
        for t, bar in self.bar_data.iterrows():
            p.drawLine(QtCore.QPointF(t, bar[Constants.LOW]), QtCore.QPointF(t, bar[Constants.HIGH]))

            if bar[Constants.OPEN] > bar[Constants.CLOSE]:
                p.setBrush(pg.mkBrush('r'))
            else:
                p.setBrush(pg.mkBrush('g'))

            p.drawRect(QtCore.QRectF(t-self.w, bar[Constants.OPEN], self.w*2, bar[Constants.CLOSE]-bar[Constants.OPEN]))
        p.end()
    

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
        if self.highlight_picture is not None:
            p.drawPicture(0, 0, self.highlight_picture)
            self.highlight_picture = None

    
    def generateHighlightPicture(self, highlight_index):

        bar = self.bar_data.loc[highlight_index]

        self.highlight_picture = QtGui.QPicture()
        p = QtGui.QPainter(self.highlight_picture)
        p.setPen(pg.mkPen('k'))
        p.drawLine(QtCore.QPointF(highlight_index, bar[Constants.LOW]), QtCore.QPointF(highlight_index, bar[Constants.HIGH]))
        p.setBrush(pg.mkBrush('b'))
        p.drawRect(QtCore.QRectF(highlight_index-self.w, bar[Constants.OPEN], self.w*2, bar[Constants.CLOSE]-bar[Constants.OPEN]))
        p.end()
    
    

    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtCore.QRectF(self.picture.boundingRect())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        closest_index = self.findClosestDataFrameIndex(event.pos().x())
            
        self.generateHighlightPicture(closest_index)
        self.update()
        QTimer.singleShot(self.highlight_delay, self.update)

        open_price = self.bar_data.loc[closest_index, Constants.OPEN]
        close_price = self.bar_data.loc[closest_index, Constants.CLOSE]
        middle_price = (open_price + close_price)/2

        if event.pos().y() > middle_price:
            self.call_back(Constants.HIGH, self.bar_data.loc[closest_index, Constants.HIGH])
        else:
            self.call_back(Constants.LOW, self.bar_data.loc[closest_index, Constants.LOW])


    def findClosestDataFrameIndex(self, x_data):
        idx = self.bar_data.index

        # Find the first index which is greater than or equal to the x_data
        smaller_than = idx[idx < x_data]
        greater_than = idx[idx > x_data]

        if len(smaller_than) == 0:
            return greater_than[0]
        elif len(greater_than) == 0:
            return smaller_than[-1]

        smaller_dist = x_data - smaller_than[-1]
        greater_dist = greater_than[0] - x_data
        if smaller_dist < greater_dist:
            return smaller_than[-1]
        else:
            return greater_than[0]


class CandlePlotWidget(pg.PlotWidget):

    current_item = None

    historical_data = pd.DataFrame()
    current_data = pd.DataFrame()


    def __init__(self, call_back, labels=['Price'], inverted=False):
        super().__init__()

        self.labels = labels
        self.setupGraphs(inverted)
        self.call_back = call_back
        #self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.addLegend()
    
        self.dt_axis = DateAxisItem()
        self.setAxisItems({'bottom': self.dt_axis})

        self.plotItem.setMouseEnabled(x=True, y=False)

        self.plotItem.sigXRangeChanged.connect(self.scaleChanging)


    def setTimezone(self, tz_string):
        print(f"CandlePlotWidget.setTimezone {tz_string}")
        time_zone = pytz.timezone(tz_string)
        now = datetime.now(time_zone)
        utc_offset = now.utcoffset().total_seconds()
        self.dt_axis.utcOffset = -utc_offset
        
    # def addCrossHair(self):
    #     self.vLine = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen(color=(170,170,170), width=2, style=Qt.DashLine), movable=False)
    #     self.hLine = pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen(color=(170,170,170), width=2, style=Qt.DashLine), movable=False)
    #     self.addItem(self.vLine,ignoreBounds=True)
    #     self.addItem(self.hLine,ignoreBounds=True)


    def setupGraphs(self, inverted=False):     
        pass
        # self.addCrossHair()
        # self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        # self.setMouseEnabled(y=False) 
        # self.setLabels(left='Normalized Price', bottom='Time (5m/point)')

    
    def scaleChanging(self, value):
        [x_min, x_max] = self.viewRange()[0]

        all_data = pd.concat([self.historical_data, self.current_data], axis=0)

        mask = (all_data.index >= x_min) & (all_data.index <= x_max)
        if sum(mask) > 0:
            data_selection = all_data.loc[mask]
            y_range = [min(data_selection[Constants.LOW]), max(data_selection[Constants.HIGH])]
            self.setRange(yRange=y_range)


    def setHistoricalData(self, bar_data):
        self.current_data = pd.DataFrame()
        self.historical_data = pd.DataFrame()
        if len(bar_data) > 0:
            self.last_index = bar_data.index.max()            
            self.historical_data = bar_data

            self.redrawHistoricalData()

            if len(self.historical_data) > 30:
                min_x = self.historical_data.index[-30]
            else:
                min_x = self.historical_data.index[0]
            max_x = self.historical_data.index[-1]

            self.setRange(xRange=[min_x, max_x])


    def redrawHistoricalData(self):
        self.clear()
        self.historical_item = CandlestickItem(self.historical_data, self.call_back)        
        self.addItem(self.historical_item)


    def addNewBars(self, bar_data, start_index):

        if len(bar_data) > 0:
            
                #we want to update the variable bars.
            if self.current_data is None:
                self.current_data = bar_data
            else:
                self.current_data = bar_data.combine_first(self.current_data)
            
                #if we get a new bar, we want to relegate the completed bar(s) to the history
            if start_index > self.last_index:    
                self.historical_data = self.current_data.loc[:start_index-1].copy().combine_first(self.historical_data)
                self.redrawHistoricalData()
                self.current_data = self.current_data.loc[start_index:]
                self.last_index = self.historical_data.index.max()
            
            if len(self.current_data) > 0:
                if self.current_item is not None:
                    self.removeItem(self.current_item)

                self.current_item = CandlestickItem(self.current_data, self.call_back, self.historical_item.w, alt_color=True)
                self.addItem(self.current_item)
                
