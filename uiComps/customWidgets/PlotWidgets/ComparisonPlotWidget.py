from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot, Qt
import pyqtgraph as pg
from pyqtgraph import exporters, DateAxisItem

import numpy as np
from dataHandling.Constants import Constants
import random, sys
from generalFunctionality.GenFunctions import findNearest

pg.setConfigOption("background", "w")

from matplotlib.pyplot import cm

class ComparisonPlotWidget(pg.PlotWidget):    

    data_object = None
    renewal = False

    min_points = None
    max_points = None

    def __init__(self, plot_type, labels=['Price'], inverted=False):
        super().__init__()

        self.labels = labels
        self.plot_type = plot_type
        self.setupGraphs(inverted)
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.addLegend()

        axis = DateAxisItem()
        self.setAxisItems({'bottom':axis})
        #print(pg.colormap.listMaps())


    def generateColorList(self, count):
        colors = cm.rainbow(np.linspace(0, 1, count))
        rgba_tuples =[c for c in colors]
        rgb_colors = [[x[0]*255, x[1]*255, x[2]*255] for x in rgba_tuples]
        return rgb_colors


    def setupGraphs(self, inverted=False):     

        self.addCrossHair()
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.setMouseEnabled(y=False) 
        self.setLabels(left='Normalized Price', bottom='Time (5m/point)')


    def calculateMinMax(self):
        line_ids, line_count = self.data_object.getPlotParameters(self.plot_type)
        min_y_value = sys.float_info.max; max_y_value = sys.float_info.min;
        min_x_value = sys.float_info.max; max_x_value = sys.float_info.min;
        
        min_points = np.empty(line_count)
        max_points = np.empty(line_count)
        min_indices = np.empty(line_count)
        max_indices = np.empty(line_count)

        for index, key in enumerate(line_ids):
            price_data = self.data_object.getLineData(self.plot_type, key)
            line_points = price_data['adapted']
            time_indices = price_data['time_indices']

            min_points[index] = min(line_points)
            max_points[index] = max(line_points)
            min_indices[index] = time_indices[np.argmin(line_points)]
            max_indices[index] = time_indices[np.argmax(line_points)]

            if len(line_points) > 0:
                min_y_data = min(line_points); max_y_data = max(line_points)
                if min_y_data < min_y_value: min_y_value = min_y_data
                if max_y_data > max_y_value: max_y_value = max_y_data
                min_x_data = min(time_indices); max_x_data = max(time_indices)
                if min_x_data < min_x_value: min_x_value = min_x_data
                if max_x_data > max_x_value: max_x_value = max_x_data

        return min_y_value, max_y_value, min_x_value, max_x_value, min_indices, max_indices, min_points, max_points


    def setupCurves(self, show_tops_bottoms):
        self.clear()
        self.initializeBand()

        line_ids, line_count = self.data_object.getPlotParameters(self.plot_type)
        
        self.plotItem.legend.setColumnCount(7)
        self.plotItem.legend.setOffset((30,5))

        axis = DateAxisItem(orientation='bottom')
        #axis.attachToPlotItem(self.getPlotItem())
        axis.linkToView(self.getViewBox())
        self.curve_points = dict()
        self.curves = dict()
        if line_count > 0:
            color_list = self.generateColorList(line_count)
            self.len_list = [len(data_line) for data_line in self.data_object.getLines(self.plot_type).values()]
            self.longest_array = max(self.len_list)

            line_points = [data_line['adapted'] for data_line in self.data_object.getLines(self.plot_type).values()]
            min_y_value, max_y_value, min_x_value, max_x_value, min_indices, max_indices, min_points, max_points = self.calculateMinMax()

            has_plots = False
            
            for index, key in enumerate(line_ids):
                price_data = self.data_object.getLineData(self.plot_type, key)
                line_points = price_data['adapted']
                time_indices = price_data['time_indices']
                
                if price_data['label'] == "Average":
                    pen = pg.mkPen(color=color_list[index],width=6)
                else:
                    pen = pg.mkPen(color=color_list[index],width=2)

                if len(line_points) > 0:            
                    has_plots = True
                    self.createCurve(key, time_indices, line_points, pen, price_data['label'])
                    
            
            if has_plots:
                # print(f"Where are these coming from {min_y_value} {max_y_value}")
                # print(f"Where are these coming from {min_x_value} {max_x_value}")
                self.setYRange(min_y_value, max_y_value, padding=0.5)
                self.setXRange(min_x_value, max_x_value, padding=0.5)
            
            if show_tops_bottoms:
                self.min_points = self.plot(min_indices, min_points, pen=None, symbol='d')
                self.max_points = self.plot(max_indices, max_points, pen=None, symbol='x')


    def updateCurves(self, uids):
        for uid in uids:
            updated_data = self.data_object.getLineData(self.plot_type, uid)
            line_points = updated_data['adapted']
            time_indices = updated_data['time_indices']
            self.curves[uid].setData(x=time_indices, y=line_points)
            # self.curve_points[uid] = pg.CurvePoint(curve_mid)

        min_y_value, max_y_value, min_x_value, max_x_value, min_indices, max_indices, min_points, max_points = self.calculateMinMax()

        # print(f"Where are these coming from {min_y_value} {max_y_value}")
        # print(f"Where are these coming from {min_x_value} {max_x_value}")
                
        # self.setYRange(min_y_value, max_y_value, padding=0.5)
        # self.setXRange(min_x_value, max_x_value, padding=0.5)
            
        if self.min_points is not None:
            self.min_points.clear()
            self.min_points = self.plot(min_indices, min_points, pen=None, symbol='d')
        if self.max_points is not None:
            self.max_points.clear()
            self.max_points = self.plot(max_indices, max_points, pen=None, symbol='x')


    def createCurve(self, key, time_indices, line_points, pen, label):
        self.curves[key] = self.plot(time_indices, line_points, pen=pen, symbol='o', symbolPen=pen, name=label)
        self.curves[key].setSymbolSize(1)
        self.curve_points[key] = pg.CurvePoint(self.curves[key])
        self.addItem(self.curve_points[key])
        

    def addCrossHair(self):
        self.addItem(pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen(color=(170,170,170), width=2, style=QtCore.Qt.DashLine), movable=False))
        self.hLine = pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen(color=(170,170,170), width=2, style=QtCore.Qt.DashLine), movable=False)
        self.addItem(self.hLine,ignoreBounds=True)
        

    def setData(self, data_object):
        self.data_object = data_object
        self.data_object.processing_updater.connect(self.dataUpdate, Qt.QueuedConnection)
        self.setupCurves(True)


    def initializeBand(self):
        self.addCrossHair()
        self.curve_high = pg.PlotCurveItem()
        self.curve_low = pg.PlotCurveItem()
        self.high_low_band = pg.FillBetweenItem(self.curve_low, self.curve_high, brush=(75,75,100,50))
        self.addItem(self.high_low_band)
        
        self.arrow_mid = pg.ArrowItem(angle=240,pen=(255,255,0),brush=(255,0,0))
        self.text_mid = pg.TextItem('',color=(80,80,80),fill=pg.mkBrush('w'),anchor=(0.5,2.0))
        self.text_mid.setZValue(100)



    @pyqtSlot(str, dict)
    def dataUpdate(self, signal, sub_signal):
        if signal == Constants.DATA_LINES_WILL_RENEW:
            self.renewal = True
        elif signal == Constants.DATA_LINES_UPDATED:
            if self.renewal:
                self.setupCurves(True)
                self.renewal = False
            else:
                self.updateCurves(sub_signal['updated_uids'])
            


    
    def mouseMoved(self, evt):
        found_match = False
        pos = evt[0]
        data_lines = self.data_object.getLines(self.plot_type)
        if self.sceneBoundingRect().contains(pos) and (len(data_lines) > 0):
            mousePoint = self.plotItem.vb.mapSceneToView(pos)
            x_mouse = round(mousePoint.x())
            y_mouse = mousePoint.y()
    
            self.hLine.setPos(y_mouse)

            min_y_dist = sys.float_info.max
            min_key = None
            min_symbol = 'Not Found'
            for k, price_data in data_lines.items():
                time_index_list = price_data['time_indices'].tolist()
                #if x_mouse in time_index_list:
                data_line = price_data['adapted']
                original_line = price_data['original']
                data_index, _ = findNearest(np.array(time_index_list), x_mouse)

                y_for_x = data_line[data_index]
                y_dist = abs(y_mouse - y_for_x)
                if y_dist < min_y_dist:
                    min_y_dist = y_dist
                    min_key = k
                    min_symbol = price_data['label']
                    min_original_line = original_line
                    min_index = data_index
                    min_point_count = len(data_line)

                    low_data = price_data['adapted_low']
                    high_data = price_data['adapted_high']
                    index_data = time_index_list

            if min_key is not None:
                self.arrow_mid.setParentItem(self.curve_points[min_key])
                self.text_mid.setParentItem(self.curve_points[min_key])
                if min_point_count == 1:
                    self.curve_points[min_key].setPos(0)
                else:
                    self.curve_points[min_key].setPos(min_index/(min_point_count-1))

                self.arrow_mid.show()
                self.high_low_band.show()
                self.text_mid.show()
                self.text_mid.setText(f"{min_symbol}: {min_original_line[min_index]:.2f}")

                self.curve_low.setData(index_data, low_data)
                self.curve_high.setData(index_data, high_data)
                found_match = True
        
        if not found_match:
            self.arrow_mid.hide()
            self.high_low_band.hide()
            self.text_mid.hide()
        

    def findClosest(self, value, element_list):
        np_list = np.array(element_list)
        distance_list = np_list - value 
        min_distance = min(distance_list)
        min_index = distance_list.index(min_distance)
        return min_index, min_distance


    def capturePlotAsImage(self):
        # create an exporter instance, as an argument give it
        # the item you wish to export
        exporter = exporters.ImageExporter(self.plotItem)
        #exporter.parameters()['width'] = 1000
        exporter.export('fileName.png')
        return 'fileName.png'



    def updatePlot(self, strike_comp_frame):
        pass
        # self.data_frame = strike_comp_frame
        
        # if self.data_frame.has_data:
        #     pen = pg.mkPen(color=(80,80,80),width=5)
        #     self.curve_mid.setData(self.data_frame.data_x, self.data_frame.data_y, pen=pen, clickable=True)

        #     if len(self.data_frame.data_y_lower) > 0 and len(self.data_frame.data_y_upper) > 0:
        #         self.curve_ask.setData(self.data_frame.data_x, self.data_frame.data_y_lower)
        #         self.curve_bid.setData(self.data_frame.data_x, self.data_frame.data_y_upper)

        #     self.setYRange(0, self.data_frame.data_y.max()*self.range_multiplier)


