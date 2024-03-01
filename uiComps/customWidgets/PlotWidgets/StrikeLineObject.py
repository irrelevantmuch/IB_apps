from PyQt5 import QtCore
import pyqtgraph as pg

from generalFunctionality.GenFunctions import findNearest


class StrikeLineObject:

    delegate = None
    upper_offset = 1.0
    lower_offset = -1.0

    def __init__(self, plotItem, delegate):

        self.delegate = delegate
        self.plotItem = plotItem

        self.strike_line = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen(color=(0,170,0),width=5, style=QtCore.Qt.DashLine),movable=True)
        self.proxy_strike_line_changed = pg.SignalProxy(self.strike_line.sigPositionChanged, rateLimit=5, slot=self.strikeLineDragging)
        self.proxy_strike_line_finished = pg.SignalProxy(self.strike_line.sigPositionChangeFinished, slot=self.strikeLineDraggingEnded)
        plotItem.addItem(self.strike_line)

        # self.upper_line = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen(color=(0,120,0),width=5, style=QtCore.Qt.DashLine),movable=False)
        # self.lower_line = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen(color=(0,120,0),width=5, style=QtCore.Qt.DashLine),movable=False)
        # plotItem.addItem(self.upper_line)
        # plotItem.addItem(self.lower_line)


    def strikeLineDragging(self, evt):
        pos = evt[0].value()  
        index = findNearest(self.plotItem.data_frame.data_x, pos)    
        print('Position ', str(pos), ', ', str(index))
        self.strike_line.setPos(self.plotItem.data_frame.data_x[index])
        self.delegate.selected_strike = self.plotItem.data_frame.data_x[index]


    def strikeLineDraggingEnded(self, evt):
        pos = evt[0].value()
        index = findNearest(self.plotItem.data_frame.data_x, pos)    
        self.strike_line.setPos(self.plotItem.data_frame.data_x[index])
        print('Position ', str(pos), ', ', str(index))
        print(f"Who be my delegate {self.delegate}")
        self.delegate.selected_strike = self.plotItem.data_frame.data_x[index]
        self.delegate.updateStrikeSelection(self.delegate.selected_strike)


    def updatePosition(self, pos):
        self.strike_line.setPos(pos)