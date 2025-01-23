
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
from PyQt6.QtCore import pyqtSlot, Qt, QReadWriteLock

import pyqtgraph as pg
from pyqtgraph import exporters, DateAxisItem

from pytz import timezone
from datetime import datetime
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
    arrow_showing = False
    curve_points = dict()
    _lock = QReadWriteLock()

    def __init__(self, plot_type, labels=['Price'], inverted=False):
        super().__init__()

        self.labels = labels
        self.plot_type = plot_type
        self.setupGraphs(inverted)
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.addLegend()

        self.dt_axis = DateAxisItem()
        self.setAxisItems({'bottom': self.dt_axis})


    def setTimezone(self, tz_string):
        time_zone = timezone(tz_string)
        now = datetime.now(time_zone)
        utc_offset = now.utcoffset().total_seconds()
        self.dt_axis.utcOffset = -utc_offset
        

    def generateColorList(self, all_line_ids):
        line_count = len(all_line_ids)
        colors = {key: [c[0]*255, c[1]*255, c[2]*255] for key, c in zip(all_line_ids, cm.rainbow(np.linspace(0, 1, line_count)))}
        return colors


    def setupGraphs(self, inverted=False):
        self.addCrossHair()
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        # self.setMouseEnabled(y=False) 
        self.setLabels(left='Normalized Price', bottom='Time (5m/point)')


    def calculateMinMax(self, line_ids):
        line_count = len(line_ids)
        min_y_value = sys.float_info.max; max_y_value = sys.float_info.min;
        min_x_value = sys.float_info.max; max_x_value = sys.float_info.min;
        
        min_points = np.empty(line_count)
        max_points = np.empty(line_count)
        min_indices = np.empty(line_count)
        max_indices = np.empty(line_count)

        for index, key in enumerate(line_ids):
            price_data = self.processed_local[key]
            
            y_points = price_data['y_points']
            x_points = price_data['x_points']
            line_points = y_points[~np.isnan(y_points)]
            time_indices = x_points[~np.isnan(x_points)]

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

         
        values_set = (min_y_value != sys.float_info.max) and (max_y_value != sys.float_info.min) and (min_x_value != sys.float_info.max) and (max_x_value != sys.float_info.min)

        return values_set, min_y_value, max_y_value, min_x_value, max_x_value, min_indices, max_indices, min_points, max_points


    def addMouseOverElements(self):
        self.addCrossHair()
        #         # Add arrow and text (assuming these are static or not part of the band-specific setup)
        self.arrow_mid = pg.ArrowItem(angle=240, pen=(255, 255, 0), brush=(255, 0, 0))
        self.text_mid = pg.TextItem('', color=(80, 80, 80), fill=pg.mkBrush('w'), anchor=(0.5, 2.0))
        
        self.arrow_mid.setPos(0, 0)  # Replace with your desired coordinates
        self.text_mid.setPos(0, 0)     # Replace with your desired coordinates


    def addCrossHair(self):
        self.addItem(pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen(color=(170,170,170), width=2, style=Qt.PenStyle.DashLine), movable=False))
        self.hLine = pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen(color=(170,170,170), width=2, style=Qt.PenStyle.DashLine), movable=False)
        self.addItem(self.hLine,ignoreBounds=True)
        self.vLine = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen(color=(170,170,170), width=2, style=Qt.PenStyle.DashLine), movable=False)
        self.addItem(self.vLine,ignoreBounds=True)


    def resetPlot(self):

        self.clear()
        self.processed_local = dict()
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

        line_ids, line_count, all_line_ids = self.data_object.getPlotParameters(self.plot_type)
        
        self.color_list = self.generateColorList(all_line_ids)
         
        for key in line_ids:

            self.createCurve(key, self.processed_local[key]['x_points'], self.processed_local[key]['y_points'], self.processed_local[key]['label'])
            self.createBands(key, self.processed_local[key]['x_points'], self.processed_local[key]['low_points'], self.processed_local[key]['high_points'])
        
        values_set, min_y_value, max_y_value, min_x_value, max_x_value, min_indices, max_indices, min_points, max_points = self.calculateMinMax(line_ids)

        
        if values_set:
            
            self.setYRange(min_y_value, max_y_value, padding=0.5)
            self.setXRange(min_x_value, max_x_value, padding=0.5)
            
            if show_tops_bottoms:
                self.min_points = self.plot(min_indices, min_points, pen=None, symbol='d')
                self.max_points = self.plot(max_indices, max_points, pen=None, symbol='x')


    def updateCurves(self, updated_keys):
        for key in updated_keys:

            if key in self.curve_points:
                self.curves[key].setData(x=self.processed_local[key]['x_points'], y=self.processed_local[key]['y_points'], connect="finite")
                self.createBands(key, self.processed_local[key]['x_points'], self.processed_local[key]['low_points'], self.processed_local[key]['high_points'])
            else:
                self.createCurve(key, self.processed_local[key]['x_points'], self.processed_local[key]['y_points'], self.processed_local[key]['label'])
                self.createBands(key, self.processed_local[key]['x_points'], self.processed_local[key]['low_points'], self.processed_local[key]['high_points'])
            
        values_set, min_y_value, max_y_value, min_x_value, max_x_value, min_indices, max_indices, min_points, max_points = self.calculateMinMax(updated_keys)
            
        if values_set:
            
            self.setYRange(min_y_value, max_y_value, padding=0.5)
            # self.setXRange(min_x_value, max_x_value, padding=0.5)
            
            if self.min_points is not None:
                self.min_points.clear()
                self.min_points = self.plot(min_indices, min_points, pen=None, symbol='d')
            if self.max_points is not None:
                self.max_points.clear()
                self.max_points = self.plot(max_indices, max_points, pen=None, symbol='x')


    def createCurve(self, key, time_indices, line_points, label):
        if self.processed_local[key]['label'] == "Average":
            pen = pg.mkPen(color=self.color_list[key],width=6)
        else:
            pen = pg.mkPen(color=self.color_list[key],width=2)
        self.curves[key] = self.plot(time_indices, line_points, pen=pen, symbol='o', symbolPen=pen, name=label)
        self.curves[key].setSymbolSize(1)
        self.curve_points[key] = pg.CurvePoint(self.curves[key])
        self.addItem(self.curve_points[key])
        

    def createBands(self, key, index_data, low_data, high_data):

        if key in self.high_low_bands:
            for band_item in self.high_low_bands[key]:
                self.removeItem(band_item)

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


    def recalculatePlotLines(self, key_selection=None):
        
        line_ids, line_count, all_line_ids = self.data_object.getPlotParameters(self.plot_type)
        
        if key_selection is not None:
            line_ids = line_ids & key_selection

        for key in line_ids:
            graph_line = self.data_object.getLineData(key)

            if not(graph_line['bar_type'] == Constants.DAY_BAR):
                dates = np.array([dt.date() for dt in graph_line['original_dts']])
                day_change_ind = np.where(np.diff(dates) != np.timedelta64(0, 'D'))[0] + 1

                def insert_nans(arr):
                    return np.insert(np.array(arr).astype(float), day_change_ind, np.nan)
                
                time_index_wbreaks = insert_nans(graph_line['time_indices'])
                adapted_wbreaks = insert_nans(graph_line['adapted'])
                original_wbreaks = insert_nans(graph_line['original'])
                low_line_wbreaks = insert_nans(graph_line['adapted_low'])
                high_line_wbreaks = insert_nans(graph_line['adapted_high'])

                self.processed_local[key] = {'x_points': time_index_wbreaks, 'y_points': adapted_wbreaks, 'original': original_wbreaks, 'low_points': low_line_wbreaks, 'high_points': high_line_wbreaks, 'label': graph_line['label']}
            else:
                self.processed_local[key] = {'x_points': graph_line['time_indices'], 'y_points': graph_line['adapted'], 'low_points': graph_line['adapted_low'], 'high_points': graph_line['adapted_high'], 'original': graph_line['original'], 'label': graph_line['label']}


        return line_ids


    def setDataObject(self, data_object):
        self.data_object = data_object
        self.data_object.processing_updater.connect(self.dataUpdate, Qt.ConnectionType.QueuedConnection)

        if self.data_object.has_data:
            self.initialPlotting()


    def initialPlotting(self):
        self._lock.lockForWrite()
        self.resetPlot()
        self.recalculatePlotLines()
        self.setupCurves(True)
        self._lock.unlock()


    @pyqtSlot(str, dict)
    def dataUpdate(self, signal, sub_signal):
        if signal == Constants.DATA_LINES_WILL_RENEW:
            self.renewal = True
        elif signal == Constants.DATA_LINES_UPDATED:
            if self.renewal:
                self.initialPlotting()
                self.renewal = False
            else:
                self._lock.lockForWrite()
                updated_keys = self.recalculatePlotLines(sub_signal['updated_uids'])
                self.updateCurves(updated_keys)
                self._lock.unlock()

    
    def mouseMoved(self, evt):
        found_match = False
        pos = evt[0]
        if (len(self.curve_points) > 0) and self.sceneBoundingRect().contains(pos):
            mousePoint = self.plotItem.vb.mapSceneToView(pos)
            x_mouse = round(mousePoint.x())
            y_mouse = mousePoint.y()
    
            self.hLine.setPos(y_mouse)
            self.vLine.setPos(x_mouse)

            for key in self.curve_points.keys():
                for band in self.high_low_bands[key]:
                    band.hide()

            min_key, min_index = self.findClosest(x_mouse, y_mouse)

            if min_key is not None:
                self.plotHighLowBandFor(min_key, min_index)
                found_match = True
        
        if found_match:
            self.placeArrow(min_key, min_index)
            

    def plotHighLowBandFor(self, key, min_index):
        if key in self.high_low_bands:
            for band_item in self.high_low_bands[key]:
                band_item.show()

            original_line = self.processed_local[key]['original']
            min_point_count = len(original_line)
            if min_point_count == 1:
                self.curve_points[key].setPos(0)
            else:
                self.curve_points[key].setPos(min_index/(min_point_count-1))
           

    def placeArrow(self, key, min_index):
        if self.arrow_showing:
            self.removeItem(self.arrow_mid)
            self.removeItem(self.text_mid)
            self.arrow_showing = False
        original_line = self.processed_local[key]['original']
        label = self.processed_local[key]['label']
        self.addItem(self.arrow_mid)
        self.addItem(self.text_mid)
        self.arrow_mid.setParentItem(self.curve_points[key])
        self.text_mid.setParentItem(self.curve_points[key])
        self.text_mid.setText(f"{label}: {original_line[min_index]:.2f}")
        self.text_mid.setZValue(100)
        self.arrow_showing = True


    def findClosest(self, x_mouse, y_mouse):
        min_y_dist = sys.float_info.max
        min_key = None
        min_symbol = 'Not Found'
        for k, price_data in self.processed_local.items():

            data_line = price_data['y_points']
            data_index, _ = findNearest(np.array(price_data['x_points']), x_mouse)
            
            y_for_x = data_line[data_index]
            y_dist = abs(y_mouse - y_for_x)

            if y_dist < min_y_dist:
                min_y_dist = y_dist
                min_key = k
                min_index = data_index
                min_symbol = price_data['label']

        return min_key, min_index


    def capturePlotAsImage(self):
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


