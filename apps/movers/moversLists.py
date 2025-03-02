
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

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'optionsGraph.ui'
#
# Created by: PyQt6 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot


from dataHandling.Constants import Constants, DT_BAR_TYPES, TableType
from .MoversWindow import MoversWindow

from .MoversProcessor import MoversProcessor
import sys

from datetime import datetime

from ibapi.contract import Contract
from uiComps.TableModels import StepModel, RSIModel, LevelModel, OverviewModel, CorrModel
from uiComps.customWidgets.OrderDialog import StepOrderDialog
from uiComps.customWidgets.PlotWidgets.QuickChart import QuickChart

import webbrowser
from dataHandling.UserDataManagement import readStockList

class MoversList(MoversWindow):

    time_period = "Month"

    gui_change_signal = pyqtSignal(TableType)
    fetch_latest_signal = pyqtSignal(bool)
    set_stock_list_signal = pyqtSignal(dict)
    update_stock_list_signal = pyqtSignal(str, bool, bool)
    period_update_signal = pyqtSignal(str)
    cancel_update_signal = pyqtSignal()
    index_selection_signal = pyqtSignal(str)
    continuous_updating_on = False
    bar_types = DT_BAR_TYPES
    counter = 0

    table_data = None
    data_processor = None


    def __init__(self, history_manager, processor_thread):
        super().__init__(self.bar_types)
        print(f"We initiate MoversList from: {int(QThread.currentThreadId())}")
        file_name, _ = self.stock_lists[0]
        self.stock_list = readStockList(file_name)
        self.attemptIndexLoading(self.findIndexList())

        self.setupProcessor(history_manager, processor_thread)

        self.initTableModels()
        #self.fetchShortRates()
        self.period_selector.blockSignals(True)
        self.period_selector.setCurrentText(self.time_period)
        self.period_selector.blockSignals(False)
        sys.setrecursionlimit(20_000)


    def setupProcessor(self, history_manager, processor_thread):
        #print(f"MoversList
        self.data_processor = MoversProcessor(history_manager, DT_BAR_TYPES, self.stock_list) #, self.index_list)
        self.table_data = self.data_processor.getDataObject()
        self.processor_thread = processor_thread
        self.data_processor.moveToThread(self.processor_thread)
        self.data_processor.buffered_manager.api_updater.connect(self.apiUpdate, Qt.ConnectionType.QueuedConnection)
        self.connectSignalToSlots()
 
        self.processor_thread.started.connect(self.data_processor.run)
        self.processor_thread.start()
        self.processor_thread.setPriority(QThread.Priority.HighestPriority)


    def connectSignalToSlots(self):
        self.fetch_latest_signal.connect(self.data_processor.buffered_manager.fetchLatestStockData, Qt.ConnectionType.QueuedConnection)
        self.set_stock_list_signal.connect(self.data_processor.setStockList, Qt.ConnectionType.QueuedConnection)
        self.cancel_update_signal.connect(self.data_processor.buffered_manager.cancelUpdates, Qt.ConnectionType.QueuedConnection)
        self.data_processor.buffered_manager.api_updater.connect(self.apiUpdate, Qt.ConnectionType.QueuedConnection)
        self.update_stock_list_signal.connect(self.data_processor.buffered_manager.requestUpdates, Qt.ConnectionType.QueuedConnection)
        self.period_update_signal.connect(self.data_processor.updatePeriodSelection, Qt.ConnectionType.QueuedConnection)
        self.index_selection_signal.connect(self.data_processor.compSelection, Qt.ConnectionType.QueuedConnection)
        self.gui_change_signal.connect(self.data_processor.guiSelectionChange, Qt.ConnectionType.QueuedConnection)
        self.data_processor.data_buffers.buffer_updater.connect(self.bufferUpdate, Qt.ConnectionType.QueuedConnection)

        
    def initTableModels(self):
        print(f"We initiate the models from: {int(QThread.currentThreadId())}")
        mapping = {0: Constants.PRICE, 1: Constants.DAY_MOVE, 2: 'Day_HIGH', 3: 'Day_LOW', 4: "MIN_FROM", 5: "MAX_FROM"}
        header_labels = ['Price', 'Day %', 'HOD', 'LOD', 'From Low', 'From High']
        function_labels = [lambda x: f"{x:.2f}", lambda x: f"{x:.2f}%", lambda x: f"{x:.2f}", lambda x: f"{x:.2f}", lambda x: f"{x:.2f}%", lambda x: f"{x:.2f}%"]
        self.overview_model = OverviewModel(self.table_data, mapping, header_labels, function_labels)
        self.overview_table.setModel(self.overview_model)
        self.setupVerticalHeaderInteraction(self.overview_table, self.overview_model)

        mapping = {0: Constants.PRICE, 1: 'Day_LOW', 2: 'Week_LOW', 3: "2 Weeks_LOW", 4: "Month_LOW", 5: "2 Months_LOW", 6: "6 Months_LOW", 7: "1 Year_LOW"}
        header_labels = ['Price', 'Day', 'Week', '2 Weeks', '1 Month', '2 Months', '6 Months', 'Year']
        self.low_model = LevelModel(self.table_data, mapping, header_labels)
        self.low_table.setModel(self.low_model)
        self.setupVerticalHeaderInteraction(self.low_table, self.low_model)

        mapping = {0: Constants.PRICE, 1: 'Day_HIGH', 2: 'Week_HIGH', 3: "2 Weeks_HIGH", 4: "Month_HIGH", 5: "2 Months_HIGH", 6: "6 Months_HIGH", 7: "1 Year_HIGH"}
        header_labels = ['Price', 'Day', 'Week', '2 Weeks', '1 Month', '2 Months', '6 Months', 'Year']
        self.high_model = LevelModel(self.table_data, mapping, header_labels)
        self.high_table.setModel(self.high_model)
        self.setupVerticalHeaderInteraction(self.high_table, self.high_model)

        mapping = {0: Constants.PRICE, 1: '1 min_UpSteps', 2: '2 mins_UpSteps', 3: '3 mins_UpSteps', 4: '5 mins_UpSteps', 5: '15 mins_UpSteps', 6: '1 hour_UpSteps', 7: '4 hours_UpSteps', 8: '1 day_UpSteps'}
        header_labels = ['Price', '1m Up', '2m Up', '3m Up', '5m Up', '15m Up', '1H Up', '4H Up', 'Day Up']
        self.step_up_model = StepModel(self.table_data, mapping, header_labels)
        self.step_up_table.setModel(self.step_up_model)
        self.setupVerticalHeaderInteraction(self.step_up_table, self.step_up_model)

        mapping = {0: Constants.PRICE, 1: '1 min_DownSteps', 2: '2 mins_DownSteps', 3: '3 mins_DownSteps', 4: '5 mins_DownSteps', 5: '15 mins_DownSteps', 6: '1 hour_DownSteps', 7: '4 hours_DownSteps', 8: '1 day_DownSteps'}
        header_labels = ['Price', '1m Down', '2m Down', '3m Down', '5m Down', '15m Down', '1H Down', '4H Down', 'Day Down']
        self.step_down_model = StepModel(self.table_data, mapping, header_labels)
        self.step_down_table.setModel(self.step_down_model)
        self.setupVerticalHeaderInteraction(self.step_down_table, self.overview_model)

        mapping = {0: Constants.PRICE, 1: '1 min_InnerCount', 2: '2 mins_InnerCount', 3: '3 mins_InnerCount', 4: '5 mins_InnerCount', 5: '15 mins_InnerCount', 6: '1 hour_InnerCount', 7: '4 hours_InnerCount', 8: '1 day_InnerCount'}
        header_labels = ['Price', '1m', '2m', '3m', '5m', '15m', '1H', '4H', 'Day']
        function_labels = [lambda x: f"{x:.2f}", lambda x: str(x), lambda x: str(x), lambda x: str(x), lambda x: str(x), lambda x: str(x), lambda x: str(x), lambda x: str(x), lambda x: str(x)]
        self.inside_bar_model = StepModel(self.table_data, mapping, header_labels, function_labels)
        self.inside_bar_table.setModel(self.inside_bar_model)
        self.setupVerticalHeaderInteraction(self.inside_bar_table, self.inside_bar_model)

        mapping = {0: Constants.PRICE, 1: '1 min_RSI', 2: '2 mins_RSI', 3: '3 mins_RSI', 4: '5 mins_RSI', 5: '15 mins_RSI', 6: "1 hour_RSI", 7: "4 hours_RSI", 8: "1 day_RSI", 9: "Difference_RSI"} #, 9: "3 days_RSI", 10: "1 week_RSI"
        header_labels = ['Price', Constants.ONE_MIN_BAR, Constants.TWO_MIN_BAR, Constants.THREE_MIN_BAR, Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR, Constants.HOUR_BAR, Constants.FOUR_HOUR_BAR, Constants.DAY_BAR, 'Long v Short'] #, Constants.THREE_DAY_BAR, Constants.WEEK_BAR
        function_labels = [lambda x: f"{x:.2f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}"] #, lambda x: f"{x:.1f}", lambda x: f"{x:.1f}"
        self.rsi_model = RSIModel(self.table_data, mapping, header_labels, function_labels)
        self.rsi_table.setModel(self.rsi_model)
        self.setupVerticalHeaderInteraction(self.rsi_table, self.rsi_model)

        mapping = {0: Constants.PRICE, 1: '1 min_REL_RSI', 2: '2 mins_REL_RSI', 3: "3 mins_REL_RSI", 4: '5 mins_REL_RSI', 5: '15 mins_REL_RSI', 6: "1 hour_REL_RSI", 7: "4 hours_REL_RSI", 8: "1 day_REL_RSI", 9: "Difference_REL_RSI"}
        header_labels = ['Price', Constants.ONE_MIN_BAR, Constants.TWO_MIN_BAR, Constants.THREE_MIN_BAR, Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR, Constants.HOUR_BAR, Constants.FOUR_HOUR_BAR, Constants.DAY_BAR, 'Long v Short']
        function_labels = [lambda x: f"{x:.2f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}", lambda x: f"{x:.1f}"]
        self.rel_rsi_model = RSIModel(self.table_data, mapping, header_labels, function_labels)
        self.rel_rsi_table.setModel(self.rel_rsi_model)
        self.setupVerticalHeaderInteraction(self.rel_rsi_table, self.rel_rsi_model)

        mapping = {0: Constants.PRICE, 1: 'SPY_CORR', 2: 'QQQ_CORR', 3: 'IWM_CORR'}
        header_labels = ['Price', 'SPY', 'QQQ', 'IWM']
        function_labels = [lambda x: f"{x:.2f}", lambda x: f"{x:.2f}", lambda x: f"{x:.2f}", lambda x: f"{x:.2f}"]
        self.index_corr_model = CorrModel(self.table_data, mapping, header_labels, function_labels)
        self.index_correlation_table.setModel(self.index_corr_model)
        self.setupVerticalHeaderInteraction(self.index_correlation_table, self.index_corr_model)

        self.models = [self.overview_model, self.low_model, self.high_model, self.step_up_model, self.step_down_model, self.rsi_model, self.rel_rsi_model, self.index_corr_model]
        for model in self.models: model.greyout_stale = self.use_stale_box.isChecked()

    
    def setupVerticalHeaderInteraction(self, table_view, table_model):        
        # table_view.setCornerButtonEnabled(False)
        table_view.verticalHeader().sectionClicked.connect(self.onRowHeaderClicked)
        corner_button = table_view.findChild(QtWidgets.QAbstractButton)
        corner_button.clicked.disconnect()
        corner_button.clicked.connect(table_model.onVerticalHeaderClicked)

    
    def onRowHeaderClicked(self, row_index):
        symbol = self.table_data.getValueForColRow(Constants.SYMBOL, row_index)
        webbrowser.open(f"https://www.tradingview.com/chart/?symbol={symbol}", new=2)


############## Callbacks

    @pyqtSlot(str)
    def processingUpdate(self, signal):
        if signal == Constants.ALL_DATA_LOADED:
            self.setHistoryEnabled(True)


    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, sub_signal):
        if signal == Constants.ALL_DATA_LOADED:
            self.setHistoryEnabled(True)
        elif signal == Constants.DATA_LOADED_FROM_FILE:
            self.setHistoryEnabled(True, self.data_processor.isUpdatable())
    

    @pyqtSlot(str, dict)
    def bufferUpdate(self, signal, sub_signal):
        pass
        # if signal == Constants.ALL_DATA_LOADED:
        #     self.setHistoryEnabled(True)
        # elif signal == Constants.DATA_LOADED_FROM_FILE:
        #     self.setHistoryEnabled(True, self.data_processor.isUpdatable())
        
        

############## Index lists

    def getIndexUI(self):
        current_index = self.index_selector.currentIndex()
        index_uid = list(self.index_list.keys())[current_index]
        return index_uid


    def findIndexList(self):
        for (file_name, list_name) in self.stock_lists:
            if list_name == 'Indices':
                return file_name

        return None


    def attemptIndexLoading(self, index_file_name):
        if index_file_name is not None:
            self.index_list = readStockList(index_file_name)

            for key, item in self.index_list.items():
                self.index_selector.addItem(item[Constants.SYMBOL])


############## BUTTON ACTIONS

    def updateData(self):
        self.update_button.setEnabled(False)
        self.full_fetch_button.setEnabled(False)
        self.keep_up_button.setEnabled(False)
        self.fetch_latest_signal.emit(False)


    def refreshData(self):
        self.update_button.setEnabled(False)
        self.keep_up_button.setEnabled(False)
        self.full_fetch_button.setEnabled(False)
        self.fetch_latest_signal.emit(True)


    def indexSelection(self, value):
        if self.data_processor is not None:
            self.index_selection_signal.emit(self.getIndexUI())


    def periodSelection(self, value):
        self.time_period = value
        self.period_update_signal.emit(value)
        

    def listSelection(self, value):
        file_name, _ = self.stock_lists[value]
        self.stock_list = readStockList(file_name)
        self.set_stock_list_signal.emit(self.stock_list)

        self.initTableModels()
        #self.fetchShortRates()
        
        self.update_button.setEnabled(True)
        self.full_fetch_button.setEnabled(True)
        self.keep_up_button.setEnabled(False)

        self.setHistoryEnabled(True, self.data_processor.isUpdatable())
        

    
    def correlationTimeFrameUpdate(self, bar_type):
        pass
        # if bar_type != self.data_processor.corr_bar_type:
        #     self.data_processor.corr_bar_type = bar_type

    def updateCorrBarCount(self, count):
        pass
        # bar_count = int(count)
        # if bar_count != self.data_processor.corr_bar_count:
        #     self.data_processor.corr_bar_count = bar_count


    def greyoutStale(self, value):
        for model in self.models: model.greyout_stale = value


    def setHistoryEnabled(self, fetch_enabled, keep_up_enabled=None):
        if keep_up_enabled is None:
            keep_up_enabled = fetch_enabled
        self.update_button.setEnabled(fetch_enabled)
        self.full_fetch_button.setEnabled(fetch_enabled)
        self.keep_up_button.setEnabled(keep_up_enabled)
        


############## GUI SIGNALING
    
    def onTabChange(self, value):
        super().onTabChange(value)
        table_type = self.tab_widget.currentWidget().table_type
        self.gui_change_signal.emit(table_type)


    def keepUpToDate(self, button):
        if self.continuous_updating_on:
            self.cancel_update_signal.emit()
            self.keep_up_button.setText("Continuous")
        else:
            self.update_stock_list_signal.emit(Constants.ONE_MIN_BAR, True, True)
            self.keep_up_button.setText("Stop Cont.")
        

############## Table interactions

    def prepOrder(self, item, direction_str):
        row = item.row()
        column = item.column()
        
        if direction_str == 'Up':
            table = self.step_up_table
        elif direction_str == 'Down':
            table = self.step_down_table

        if column >= 2:
            symbol, uid = self.overview_model.getStockFor(item.row())

            r = table.visualRect(item)
            p = table.viewport().mapToGlobal(QtCore.QPoint(r.center().x(), r.top()))

            level_value = self.table_data.getValueFor(uid, self.bar_types[column-2] + '_' + direction_str + 'Steps_Level')
            apex_value = self.table_data.getValueFor(uid, self.bar_types[column-2] + '_' + direction_str + 'Steps_Apex')
                
            symbol, uid = self.high_model.getStockFor(item.row())

            mycontract = Contract()
            mycontract.symbol = symbol
            mycontract.secType = Constants.STOCK
            mycontract.conId = uid
            mycontract.exchange = "SMART"

            dialog = StepOrderDialog(symbol, direction_str)
            if dialog.exec():
                order_params = dialog.getOrder()

                for order in bracket_order:
                    pass
                    # self.data_processor.history_manager.ib_interface.placeOrder(order.orderId, mycontract, order)
                #     #self.buffered_manager.history_manager.ib_interface.placeOrder(order.orderId, mycontract, order)


    def showChart(self, item, vs_index=False):

        if item.column() > 0:
            symbol, uid = self.rsi_model.getStockFor(item.row())

            bar_type = self.bar_types[item.column()-1]

            if vs_index:
                bars = self.data_processor.getCompBarData(uid, bar_type).copy()
                index_uid = self.getIndexUI()
                index_name = self.index_list[index_uid][Constants.SYMBOL]
                symbol = f"{symbol}/{index_name}"
            else:
                bars = self.data_processor.getBarData(uid, bar_type).copy()
            
            dialog = QuickChart(symbol, bar_type, tz=self.stock_list[uid]['time_zone'], bars=bars)
            dialog.exec()


    def overviewClicked(self, item):
        row = item.row()
        column = item.column()
        
        symbol, uid = self.overview_model.getStockFor(item.row())
        
        QtWidgets.QToolTip.hideText()
        r = self.overview_table.visualRect(item)
        p = self.overview_table.viewport().mapToGlobal(QtCore.QPoint(r.center().x(), r.top()))

        if column == 1:
            value = self.table_data.getValueFor(uid, 'YESTERDAY_CLOSE')
            QtWidgets.QToolTip.showText(p, f"Yest close: {value}")
        elif column == 4:
            min_value = self.table_data.getValueFor(uid, 'MIN')
            unix_timestamp = self.table_data.getValueFor(uid, 'MIN_DATE')
            min_date = datetime.utcfromtimestamp(unix_timestamp).strftime('%Y.%m.%d')
            QtWidgets.QToolTip.showText(p, f"{min_value} on {min_date}")
        elif column == 5:
            max_value = self.table_data.getValueFor(uid, 'MAX')
            unix_timestamp = self.table_data.getValueFor(uid, 'MAX_DATE')
            max_date = datetime.utcfromtimestamp(unix_timestamp).strftime('%Y.%m.%d')
            QtWidgets.QToolTip.showText(p, f"{max_value} on {max_date}")



        #TODO this should be in super
    def accepts(self, value):
        return False


    # def fetchShortRates(self):
    #     self.fee_rates = np.ones((len(self.stock_list))) * 500
    #     self.short_availability = [""] * len(self.stock_list)
    #     for index, stock in enumerate(self.stock_list):
    #         short_data = getShortDataFor(stock)
    #         if len(short_data) != 0:
    #             self.fee_rates[index] = float(short_data[6])
    #             self.short_availability[index] = short_data[7]


