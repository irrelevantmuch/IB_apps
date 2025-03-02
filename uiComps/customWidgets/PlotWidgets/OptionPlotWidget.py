
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

from PyQt6 import QtCore
from PyQt6.QtCore import Qt, pyqtSlot

import pyqtgraph as pg
import numpy as np
from generalFunctionality.GenFunctions import findNearest
from .StrikeLineObject import StrikeLineObject


pg.setConfigOption("background", "w")

class OptionPlotWidget(pg.PlotWidget):

    range_multiplier = 1.4
    comp_frame = None
    data_x = None


    def __init__(self, delegate, labels=['Price'], x_label="Strike", inverted=False):
        super().__init__()

        self.x_label = x_label
        self.labels = labels
        self.delegate = delegate
        self.setupGraphs(inverted)


    def setupGraphs(self, inverted=False):     

        self.addCrossHair()
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.setMouseEnabled(y=False) 
        self.setupCurves()
        self.setupCurveHooks()
        if inverted: self.getViewBox().invertX(True)


    def setupCurves(self):
        self.curve_bid = pg.PlotCurveItem()
        self.curve_ask = pg.PlotCurveItem()
        self.bid_ask_band = pg.FillBetweenItem(self.curve_ask, self.curve_bid, brush=(50,50,200,50))
        self.addItem(self.bid_ask_band)
        self.curve_mid = self.plot(np.array([0]), np.array([0]), color='r', symbol='o')
        self.curve_mid.setSymbolSize(5)


    def setupCurveHooks(self):
        self.curvePoints = pg.CurvePoint(self.curve_mid)
        self.addItem(self.curvePoints)
        self.arrow_mid = pg.ArrowItem(angle=240,pen=(255,255,0),brush=(255,0,0))
        self.arrow_mid.setParentItem(self.curvePoints)
        self.text_mid = pg.TextItem('',color=(80,80,80),anchor=(0.5,2.0))
        self.text_mid.setParentItem(self.curvePoints)


    def addCrossHair(self):
        self.hLine = pg.InfiniteLine(angle=0,movable=False)
        self.addItem(self.hLine,ignoreBounds=True)
        self.vLine = pg.InfiniteLine(angle=90,movable=False)
        self.addItem(self.vLine,ignoreBounds=True)


    def mouseMoved(self, evt): 
        pos = evt[0]
        if self.sceneBoundingRect().contains(pos):
            mousePoint = self.plotItem.vb.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

        if self.data_x is not None:
            pos = evt[0] 
            if self.sceneBoundingRect().contains(pos):
                mousePoint = self.plotItem.vb.mapSceneToView(pos)
                index, value = findNearest(self.data_x, mousePoint.x())
                if len(self.data_y) == 1:
                    self.curvePoints.setPos(0)
                else:
                    self.curvePoints.setPos(float(index)/float(len(self.data_y)-1))
                self.text_mid.setText(self.data_x_names[index])


    def setDataObject(self, comp_frame):
        self.comp_frame = comp_frame
        self.comp_frame.frame_updater.connect(self.updatePlot, Qt.ConnectionType.QueuedConnection)
        self.updatePlot("", dict())


    @pyqtSlot(str, dict)
    def updatePlot(self, signal, details):
        if self.comp_frame.has_data:

            self.data_x, self.data_y, self.data_y_lower, self.data_y_upper, self.data_x_names = self.comp_frame.getLineData()

            if len(self.data_x) > 1:
                pen = pg.mkPen(color=(80,80,80),width=5)

                self.curve_mid.setData(self.data_x, self.data_y, pen=pen, clickable=True)

                if len(self.data_y_lower) > 0 and len(self.data_y_upper) > 0:
                    self.curve_ask.setData(self.data_x, self.data_y_upper)
                    self.curve_bid.setData(self.data_x, self.data_y_lower)

                self.setXRange(self.data_x.min()/self.range_multiplier, self.data_x.max()*self.range_multiplier)
                self.setYRange(0, self.data_y.max()*self.range_multiplier)
            

class PremiumPlotWidget(OptionPlotWidget):

    no_strike_set = True
    selected_strike = None
    price = None

    def setupGraphs(self, inverted):     
    
        if len(self.labels) > 1:
            self.addRightAxis(self.labels[1])
        
        super().setupGraphs(inverted)

        self.setLabels(left=self.labels[0], bottom=self.x_label)
        
        pg.setConfigOption("background", "w")
        self.plotItem.vb.sigResized.connect(self.updateViews)
        self.updateViews()


    def setupCurves(self):
        super().setupCurves()

        if len(self.labels) > 1:
            self.absolute_change_line = pg.PlotCurveItem()
            self.changePlot.addItem(self.absolute_change_line)
            self.relative_change_line = pg.PlotCurveItem()
            self.changePlot.addItem(self.relative_change_line)


    def addPriceLine(self):
        self.price_line = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen(color=(200,200,200), width=3, style=Qt.PenStyle.DashLine),movable=False)
        self.addItem(self.price_line)


    def addRightAxis(self, right_label):
        ## create a new ViewBox, link the right axis to its coordinate system
        self.changePlot = pg.ViewBox()
        self.plotItem.showAxis('right')
        self.plotItem.scene().addItem(self.changePlot)
        self.plotItem.getAxis('right').linkToView(self.changePlot)
        self.changePlot.setXLink(self.plotItem)
        self.plotItem.getAxis('right').setLabel(right_label, color='#0000ff', angle=180)


    ## Handle view resizing 
    def updateViews(self):

        if len(self.labels) > 1:
            ## view has resized; update auxiliary views to match
            self.changePlot.setGeometry(self.plotItem.vb.sceneBoundingRect())
            
            ## need to re-update linked axes since this was called
            ## incorrectly while views had different shapes.
            ## (probably this should be handled in ViewBox.resizeEvent)
            self.changePlot.linkedViewChanged(self.plotItem.vb, self.changePlot.XAxis)


    # def setStrikeLine(self, to_price):
    #     if self.no_strike_set:
    #         self.no_strike_set = False

    #         self.strike_object = StrikeLineObject(self, self.delegate)
            
    #     if (self.comp_frame is not None) and self.comp_frame.has_data:
    #         data_x, data_y, _, _, _ = self.comp_frame.getLineData()
    #         index = findNearest(data_x, to_price)
    #         self.selected_strike = data_x[index]
    #         self.strike_object.updatePosition(data_x[index])
    #         self.delegate.updateStrikeSelection(self.selected_strike)


    def updatePrice(self, price):
        self.price = price
        self.price_line.setPos(price)


    def updatePlotPrice(self, price):
        self.price = price
        self.price_line.setPos(price)


