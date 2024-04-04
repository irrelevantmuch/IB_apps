from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot, Qt
import pyqtgraph as pg
from pyqtgraph import exporters, DateAxisItem

import numpy as np
from dataHandling.Constants import Constants
import sys
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
            price_data = self.data_object.getLineData(key)
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


    def addMouseOverElements(self):
        self.addCrossHair()
                # Add arrow and text (assuming these are static or not part of the band-specific setup)
        self.arrow_mid = pg.ArrowItem(angle=240, pen=(255, 255, 0), brush=(255, 0, 0))
        self.text_mid = pg.TextItem('', color=(80, 80, 80), fill=pg.mkBrush('w'), anchor=(0.5, 2.0))
        self.text_mid.setZValue(100)
        self.addItem(self.arrow_mid)
        self.addItem(self.text_mid)


    def resetPlot(self):
        self.clear()
        self.curve_points = dict()
        self.curves = dict()
        self.high_low_bands = dict()
        self.plotItem.legend.setColumnCount(7)
        self.plotItem.legend.setOffset((30,5))
        self.addMouseOverElements()

        # axis = DateAxisItem(orientation='bottom')
        # #axis.attachToPlotItem(self.getPlotItem())
        # axis.linkToView(self.getViewBox())


    def setupCurves(self, show_tops_bottoms):
        self.resetPlot()
        line_ids, line_count = self.data_object.getPlotParameters(self.plot_type)
        
        if line_count > 0:
            color_list = self.generateColorList(line_count)
            self.len_list = [len(data_line) for data_line in self.data_object.getLines(self.plot_type).values()]
            self.longest_array = max(self.len_list)

            line_points = [data_line['adapted'] for data_line in self.data_object.getLines(self.plot_type).values()]
            min_y_value, max_y_value, min_x_value, max_x_value, min_indices, max_indices, min_points, max_points = self.calculateMinMax()

            has_plots = False
            
            for index, key in enumerate(line_ids):
                
                time_indices, line_points, low_line, high_line = self.getPlotLines(key)

                price_data = self.data_object.getLineData(key)
                if price_data['label'] == "Average":
                    pen = pg.mkPen(color=color_list[index],width=6)
                else:
                    pen = pg.mkPen(color=color_list[index],width=2)

                if len(line_points) > 0:            
                    has_plots = True
                    self.createCurve(key, time_indices, line_points, pen, price_data['label'])
                    self.createBands(key, time_indices, low_line, high_line)
                    
            if has_plots:
                print(f"Where are these coming from {min_y_value} {max_y_value}")
                print(f"Where are these coming from {min_x_value} {max_x_value}")
                self.setYRange(min_y_value, max_y_value, padding=0.5)
                self.setXRange(min_x_value, max_x_value, padding=0.5)
            
            if show_tops_bottoms:
                print("Maybe this?")
                self.min_points = self.plot(min_indices, min_points, pen=None, symbol='d')
                self.max_points = self.plot(max_indices, max_points, pen=None, symbol='x')


    def createCurve(self, key, time_indices, line_points, pen, label):
        self.curves[key] = self.plot(time_indices, line_points, pen=pen, symbol='o', symbolPen=pen, name=label)
        self.curves[key].setSymbolSize(1)
        self.curve_points[key] = pg.CurvePoint(self.curves[key])
        self.addItem(self.curve_points[key])
        

    def createBands(self, key, index_data, low_data, high_data):
        segments = []
        current_segment = {'x': [], 'low': [], 'high': []}

        # Ensure x_data, high_data, and low_data are aligned
        for x_point, low_point, high_point in zip(index_data, low_data, high_data):
            if np.isnan(low_point) or np.isnan(high_point):
                # Avoid adding empty segments
                if current_segment['x'] and current_segment['low'] and current_segment['high']:
                    segments.append(current_segment)
                current_segment = {'x': [], 'low': [], 'high': []}  # Reset for the next segment
            else:
                current_segment['x'].append(x_point)
                current_segment['low'].append(low_point)
                current_segment['high'].append(high_point)

        # Add the last segment if it's not empty
        if current_segment['x'] and current_segment['low'] and current_segment['high']:
            segments.append(current_segment)

        self.high_low_bands[key] = []
        for segment in segments:
            curve_low = pg.PlotCurveItem(segment['x'], segment['low'])
            curve_high = pg.PlotCurveItem(segment['x'], segment['high'])
            band_item = pg.FillBetweenItem(curve_low, curve_high, brush=(75, 75, 100, 50))
            self.addItem(band_item)
            band_item.hide()
            self.high_low_bands[key].append(band_item)


    # def getPlotLines(self, key):
    #     graph_line = self.data_object.getLineData(key)
    #     day_change_ind = np.where(np.diff([dt.date() for dt in graph_line['original_dts']]))[0] + 1
    #     time_index_sel = np.insert(np.array(graph_line['time_indices']).astype(float), day_change_ind, np.nan)
    #     original_line = np.insert(np.array(graph_line['adapted']).astype(float), day_change_ind, np.nan)
    #     low_line = np.insert(np.array(graph_line['adapted_low']).astype(float), day_change_ind, np.nan)
    #     high_line = np.insert(np.array(graph_line['adapted_high']).astype(float), day_change_ind, np.nan)
    #     return time_index_sel, original_line, low_line, high_line

    def getPlotLines(self, key):
        graph_line = self.data_object.getLineData(key)
        # Ensure dt.date() conversion handles all cases correctly
        dates = np.array([dt.date() for dt in graph_line['original_dts']])
        day_change_ind = np.where(np.diff(dates) != np.timedelta64(0, 'D'))[0] + 1
        
        def insert_nans(arr):
            return np.insert(np.array(arr).astype(float), day_change_ind, np.nan)
        
        time_index_sel = insert_nans(graph_line['time_indices'])
        original_line = insert_nans(graph_line['adapted'])
        low_line = insert_nans(graph_line['adapted_low'])
        high_line = insert_nans(graph_line['adapted_high'])

        return time_index_sel, original_line, low_line, high_line


    def updateCurves(self, uids):
        for uid in uids:
            time_indices, line_points, low_points, high_points = self.getPlotLines(uid)

            self.curves[uid].setData(x=time_indices, y=line_points)
            # self.curve_points[key].setData()
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


    def addCrossHair(self):
        self.addItem(pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen(color=(170,170,170), width=2, style=QtCore.Qt.DashLine), movable=False))
        self.hLine = pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen(color=(170,170,170), width=2, style=QtCore.Qt.DashLine), movable=False)
        self.addItem(self.hLine,ignoreBounds=True)
        

    def setData(self, data_object):
        self.data_object = data_object
        self.data_object.processing_updater.connect(self.dataUpdate, Qt.QueuedConnection)
        self.setupCurves(True)


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

            for key in data_lines.keys():
                for band in self.high_low_bands[key]:
                    band.hide()

            min_key, min_index = self.findClosest(x_mouse, y_mouse, data_lines)

            if min_key is not None:
                self.plotHighLowBandFor(min_key, min_index)
                found_match = True
        
        if not found_match:
            self.arrow_mid.hide()
            self.text_mid.hide()
            

    def plotHighLowBandFor(self, key, min_index):
 
        for band_item in self.high_low_bands[key]:
            band_item.show()

        graph_line = self.data_object.getLineData(key)
        label = graph_line['label']
        original_line = graph_line['original']
        min_point_count = len(original_line)
        if min_point_count == 1:
            self.curve_points[key].setPos(0)
        else:
            self.curve_points[key].setPos(min_index/(min_point_count-1))
       
        self.arrow_mid.setParentItem(self.curve_points[key])
        self.text_mid.setParentItem(self.curve_points[key])
        self.arrow_mid.show()
        self.text_mid.show()
        self.text_mid.setText(f"{label}: {original_line[min_index]:.2f}")


    def findClosest(self, x_mouse, y_mouse, data_lines):
        min_y_dist = sys.float_info.max
        min_key = None
        min_symbol = 'Not Found'
        for k, price_data in data_lines.items():

            time_index_list = price_data['time_indices'].tolist()
            
            data_line = price_data['adapted']
            data_index, _ = findNearest(np.array(time_index_list), x_mouse)
            
            y_for_x = data_line[data_index]
            y_dist = abs(y_mouse - y_for_x)

            if y_dist < min_y_dist:
                min_y_dist = y_dist
                min_key = k
                min_index = data_index
                min_symbol = price_data['label']

        return min_key, min_index


    def capturePlotAsImage(self):
        print("ComparisonPlotWidget.capturePlotAsImage")
        # create an exporter instance, as an argument give it
        # the item you wish to export
        exporter = exporters.ImageExporter(self.plotItem)
        #exporter.parameters()['width'] = 1000
        exporter.export('./data/graphs/sharing_graph.webp')
        return './data/graphs/sharing_graph.webp'


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


