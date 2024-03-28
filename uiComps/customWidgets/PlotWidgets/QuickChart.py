from PyQt5 import QtWidgets, QtCore
from PyQt5.QtChart import QChartView
from PyQt5.QtCore import pyqtSignal

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

    def __init__(self, symbol="TEST", bar_type="5 min", bars=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Candle Sticks")
        self.bars = bars
        self.setupChart(bars, symbol, bar_type)


    def setupChart(self, bars, symbol, bar_type):

        chart = CandlePlotWidget(self.barClick)
        chart.setHistoricalData(bars)
        # self.chart = QChart()
        
        # chart_view.mouseMoved.connect(self.mouseMoved)
        # chart_view.mousePressed.connect(self.mousePressed)
        # chart_view.mouseReleased.connect(self.mouseReleased)

        
        chart.setTitle(f"{symbol}: {bar_type} bars (count:{len(self.bars)})")
        # self.chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        # self.addAxisWithData(self.chart, chart_view, bars)
        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(chart)
        # chart_view.setChart(self.chart)


    def barClick(self, high_low, price_level):
        print(f"High low {high_low}")
        print(f"High low {price_level}")

    # def addAxisWithData(self, chart, chart_view, bars):

    #         #
    #     self.candle_axis = QBarCategoryAxis()
    #     self.candlestick_series = QtChart.QCandlestickSeries()
    #     self.candlestick_series.setIncreasingColor(QColor(Qt.green))
    #     self.candlestick_series.setDecreasingColor(QColor(Qt.red))

    #         #setup y axis
    #     self.axis_y = QtChart.QValueAxis()
        
    #         #setup x axis

    #     self.axis_x = QtChart.QDateTimeAxis()
    #     self.axis_x.setTickCount(11)
    #     self.axis_x.setLabelsAngle(70)
    #     self.axis_x.setFormat("dd.MM.yy")

    #     series = QtChart.QLineSeries()
    #     candle_x_axis_label = []
    #     for index, bar in bars.iterrows():
    #         self.candlestick_series.append(QtChart.QCandlestickSet(bar[Constants.OPEN], bar[Constants.HIGH], bar[Constants.LOW], bar[Constants.CLOSE]))
    #         candle_x_axis_label.append(str(index))
    #         series.append(QDateTime.fromString(index.strftime('%Y%m%d%H%M'), "yyyyMMddhhmm").toMSecsSinceEpoch(), (bar[Constants.OPEN]+bar[Constants.CLOSE])/2)

    #     chart.addSeries(series)
    #     chart.addSeries(self.candlestick_series)
    #     chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

    #     series.setVisible(False)
    #     chart.setAxisX(self.axis_x, series)
    #     chart.setAxisY(self.axis_y, series)
    #     chart.setAxisX(self.candle_axis, self.candlestick_series)
    #     chart.setAxisY(self.axis_y, self.candlestick_series)

    #     chart.axisX(self.candlestick_series).setCategories(candle_x_axis_label)
    #     chart.axisX(self.candlestick_series).setVisible(False)


    # def wheelEvent(self, event):

    #     y_delta = event.angleDelta().y()
    #     x_delta = event.angleDelta().x()
        
        
    #     if y_delta < 0.0:
    #         self.chart.zoom(0.95)
    #     elif y_delta > 0.0:
    #         self.chart.zoom(1.05)

    #     categories = self.chart.axisX(self.candlestick_series).categories()
    #     lower_index = categories.index(self.chart.axisX(self.candlestick_series).min())
    #     higher_index = categories.index(self.chart.axisX(self.candlestick_series).max())
        
    #     self.adaptYtoNewRange(lower_index, higher_index)
            

    # def adaptYtoNewRange(self, lower_index, higher_index):
    #     offset_factor = 0.15
        
    #     lower_index = max(lower_index-3, 0)
    #     higher_index = min(higher_index+3, len(self.bars)-1)
    #     new_range = self.bars.iloc[lower_index:higher_index]

    #     if len(new_range > 0):
        
    #         time_range = new_range.index
    #         time_dif = time_range[-1] - time_range[0]
    #         if time_dif.days < 1:
    #             self.axis_x.setFormat("hh:mm")
    #         else:
    #             self.axis_x.setFormat("dd.MM.yy")

    #         min_y = new_range[Constants.LOW].min()
    #         max_y = new_range[Constants.HIGH].max()
    #         offset_y = offset_factor*(max_y - min_y)
    #         self.axis_y.setRange(min_y-offset_y, max_y+offset_y)


    # def mousePressed(self, point):
    #     self.scrolling_mouse = True
    #     self.previous_point = point


    # def mouseReleased(self, point):
    #     self.scrolling_mouse = False
    #     self.previous_point = None


    # def mouseMoved(self, point):

    #     if self.scrolling_mouse:
    #         categories = self.chart.axisX(self.candlestick_series).categories()
    #         lower_index = categories.index(self.chart.axisX(self.candlestick_series).min())
    #         higher_index = categories.index(self.chart.axisX(self.candlestick_series).max())
            
    #         shift = self.previous_point.x() - point.x()
    #         #shift = int(-0.5*x_delta)
    #         if (shift > 0 and higher_index <= len(categories)*1.25) or (shift < 0 and lower_index >= -len(categories)*0.25):
                
    #             self.chart.scroll(shift, 0)
            
    #             lower_index = lower_index + shift
    #             higher_index = higher_index + shift
            
    #         self.adaptYtoNewRange(lower_index, higher_index)
    #         self.previous_point = point

