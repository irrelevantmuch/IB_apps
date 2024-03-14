# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'optionsGraph.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt, pyqtSlot
from PyQt5.QtWidgets import QMainWindow
import numpy as np
from dataHandling.Constants import Constants, MAIN_BAR_TYPES, TableType
from .ComparisonWindow import ComparisonWindow

from .ComparisonProcessor import ComparisonProcessor as DataProcessor
import sys #, threading, math


from ibapi.contract import Contract
from uiComps.TableModels import StepModel, RSIModel, LevelModel, OverviewModel, PandasDataModel, CorrModel, ListCorrModel
from uiComps.customWidgets.OrderDialog import OrderDialog
from uiComps.customWidgets.PlotWidgets.QuickChart import QuickChart
from uiComps.generalUIFunctionality import addCheckableTickersTo

import webbrowser
from dataHandling.TradeManagement.UserDataManagement import readStockList
from dataHandling.ibFTPdata import getShortDataFor


class ComparisonList(ComparisonWindow):

    time_period = "Month"
    
    fetch_data_signal = pyqtSignal()
    fetch_latest_signal = pyqtSignal()
    cancel_update_signal = pyqtSignal()
    set_stock_list_signal = pyqtSignal(dict)
    update_stock_list_signal = pyqtSignal(str, bool)
    check_list_signal = pyqtSignal(dict)
    update_property_signal = pyqtSignal(dict)
    
    bar_types = MAIN_BAR_TYPES
    selected_bar_type = Constants.FIVE_MIN_BAR
    data_processor = None
    tops_and_bottoms = True

    def __init__(self, history_manager):
        super().__init__(self.bar_types)

        self.listSetup()    
        self.setupProcessor(history_manager)
        self.fillTickerLists()
        self.resetProcessor()
        sys.setrecursionlimit(20_000)


    def listSetup(self):
        file_name, _ = self.stock_lists[0]
        self.stock_list = readStockList(file_name)
        # self.comparison_list = readStockList(file_name)
        self.check_list = self.generateCheckList(self.stock_list)
        self.focus_list = self.check_list.copy()
        # self.comp_list = self.generateCheckList(self.comparison_list) 


    def setupProcessor(self, history_manager):
        self.data_processor = DataProcessor(history_manager, MAIN_BAR_TYPES, self.stock_list)
        self.data_container = self.data_processor.getDataObject()
        self.compare_plot.setData(self.data_container)
        # self.focus_plot.setData(self.data_container)
        self.plot_tf_selector.setCurrentText(self.data_processor.selected_bar_type)
        self.processor_thread = QThread()

        self.data_processor.moveToThread(self.processor_thread)
        
        self.fetch_data_signal.connect(self.data_processor.fetchStockData, Qt.QueuedConnection)
        self.fetch_latest_signal.connect(self.data_processor.buffered_manager.fetchLatestStockData, Qt.QueuedConnection)
        self.update_stock_list_signal.connect(self.data_processor.buffered_manager.requestUpdates, Qt.QueuedConnection)
        self.data_processor.buffered_manager.api_updater.connect(self.apiUpdate, Qt.QueuedConnection)
        self.set_stock_list_signal.connect(self.data_processor.setStockList, Qt.QueuedConnection)
        self.cancel_update_signal.connect(self.data_processor.buffered_manager.cancelUpdates, Qt.QueuedConnection)
        self.check_list_signal.connect(self.data_processor.setCheckLists, Qt.QueuedConnection)
        self.update_property_signal.connect(self.data_processor.updateProperties, Qt.QueuedConnection)
        self.data_processor.data_buffers.buffer_updater.connect(self.bufferUpdate, Qt.QueuedConnection)
        
        self.processor_thread.started.connect(self.data_processor.run)
        self.processor_thread.start()


    def fillTickerLists(self):
        # print("ComparisonList.fillTickerLists")
        addCheckableTickersTo(self.visible_ticker_box, self.stock_list, self.check_list)
        
        filtered_list = {uid: value for (uid, value) in self.stock_list.items() if self.check_list[uid]}
        addCheckableTickersTo(self.focus_box, filtered_list, self.focus_list)
        self.check_list_signal.emit(self.check_list)
                
        

    def generateCheckList(self, stock_list, default_bool=True):
        return {k: default_bool for k in stock_list}


    def resetProcessor(self):
        # print("ComparisonList.resetProcessor")
        self.initDataModels()
        self.prepCurrentTable()
        self.updateDataModels()
        #self.data_processor.updateFrameForHistory(selected_tab=self.tab_widget.currentIndex(), initial_list_load=True) #self.time_period
        self.signalCurrentTable()


    def initDataModels(self):
        header_labels = [value[Constants.SYMBOL] for value in self.stock_list.values()]
        mapping = {index: Constants.PRICE for index, value in enumerate(self.stock_list.values())}
        self.auto_corr_model = ListCorrModel(self.data_container, mapping, header_labels)
        self.auto_corr_table.setModel(self.auto_corr_model)


############## DATA PROCESSING

    @pyqtSlot(str, dict)
    def bufferUpdate(self, signal, sub_signal):
        if signal == Constants.SELECTED_KEYS_CHANGED:
            print("ComparisonList.bufferUpdate SELECTED_KEYS_CHANGED")


    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, sub_signal):
        print(f"ComparisonList.apiUpdate {signal}")
        if signal == Constants.SELECTED_KEYS_CHANGED:
            print("ComparisonList.apiUpdate SELECTED_KEYS_CHANGED")
        elif ((signal == Constants.HISTORICAL_GROUP_COMPLETE) and (sub_signal['type'] == 'range_group')) or (signal == Constants.ALL_DATA_LOADED):
            self.setHistoryEnabled(True)
        elif signal == Constants.DATA_LOADED_FROM_FILE:
            self.setHistoryEnabled(True, self.data_processor.isUpdatable())
    

############## BUTTON ACTIONS

    def fetchRangeData(self):
        self.fetch_range_button.setEnabled(False)
        self.fetch_full_button.setEnabled(False)
        self.fetch_data_signal.emit()


    def fetchData(self):
        self.fetch_range_button.setEnabled(False)
        self.fetch_full_button.setEnabled(False)
        self.fetch_latest_signal.emit()


    def comparisonListSelection(self, value):
        print(f"ComparisonList.comparisonListSelection {value}")
        print("DOES NOTHING")
        # self.loadNewComparisonList(value)        
        # self.resetCorrelationTable()
        # addCheckableTickersTo(self.comp_ticker_box, self.comparison_list, self.comp_list)
        # self.updateCompSelectors(value)
        

    def loadNewComparisonList(self, index):
        pass
        # file_name, _ = self.stock_lists[index]

        # self.comparison_list = readStockList(file_name)
        # self.comparison_list_signal.emit(self.comparison_list)
        # self.comp_list = self.generateCheckList(self.comparison_list)

        # self.check_list_signal.emit(self.check_list, self.comp_list, self.focus_list)


    def resetCorrelationTable(self):
        pass
        # mapping = {index: Constants.PRICE for index, value in enumerate(self.comparison_list.values())}
        # header_labels = [value[Constants.SYMBOL] for value in self.comparison_list.values()]
        # self.auto_corr_model = ListCorrModel(self.data_container, mapping, header_labels)
        # self.auto_corr_table.setModel(self.auto_corr_model) 


    def updateCompSelectors(self, value):
        self.comparison_selector_1.blockSignals(True)
        self.comparison_selector_2.blockSignals(True)
        self.comparison_selector_1.setCurrentIndex(value)
        self.comparison_selector_2.setCurrentIndex(value)
        self.comparison_selector_1.blockSignals(False)
        self.comparison_selector_2.blockSignals(False)


    def listSelection(self, value):
        file_name, _ = self.stock_lists[value]
        self.stock_list = readStockList(file_name)
        self.set_stock_list_signal.emit(self.stock_list)
        self.check_list = self.generateCheckList(self.stock_list)
        self.check_list_signal.emit(self.check_list) #, self.comp_list, self.focus_list)
        
        # self.comparisonListSelection(self.comparison_selector_1.currentIndex())
        
        filtered_list = {uid: value for (uid, value) in self.stock_list.items() if self.check_list[uid]}
        self.focus_list = self.generateCheckList(filtered_list)
        
        self.resetProcessor()

        addCheckableTickersTo(self.visible_ticker_box, self.stock_list, self.check_list)
        addCheckableTickersTo(self.focus_box, filtered_list, self.focus_list)
        
        self.fetch_full_button.setEnabled(True)
        self.fetch_range_button.setEnabled(True)
        self.keep_up_box.setChecked(False)
        self.keep_up_box.setEnabled(False)
        

    def modeSelection(self, button, value):

        if button is self.line_comp_radio and value:
            self.update_property_signal.emit({"line_mode_type": True})
            self.data_processor.setLineMode(True)
        elif button is self.adj_comp_radio and value:
            self.update_property_signal.emit({"line_mode_type": False})


    def tickerListClicked(self, value):
        self.check_list.update(self.visible_ticker_box.itemStates())

        # filtered_list = {uid: value for (uid, value) in self.stock_list.items() if self.check_list[uid]}
        # self.focus_list = self.generateCheckList(filtered_list)
        # addCheckableTickersTo(self.focus_box, filtered_list, self.focus_list)

        print(self.check_list)
        self.check_list_signal.emit(self.check_list) #, self.comp_list, self.focus_list)

        if self.visible_ticker_box.noItemsSelected():
            self.sel_all_button.setText("Check All")
        elif self.visible_ticker_box.allItemsSelected():
            self.sel_all_button.setText("Uncheck All")
    

    def tickerCompClicked(self, value):
        pass
        # self.comp_list.update(self.comp_ticker_box.itemStates())
        # self.check_list_signal.emit(self.check_list, self.comp_list, self.focus_list)


    def tickerFocusClicked(self, value):
        pass
        # self.focus_list.update(self.focus_box.itemStates())
        # self.check_list_signal.emit(self.check_list, self.comp_list, self.focus_list)


    def graphTypeChange(self, to_type):
        self.yesterday_close_check.setEnabled(to_type == Constants.INDEXED)
        self.update_property_signal.emit({"conversion_type": to_type})
        

    def dateChange(self, new_date):
        self.update_property_signal.emit({"date_selection_type": new_date})


    def yesterdayCloseToggle(self, value):
        self.update_property_signal.emit({"yesterday_close_type": value})


    def regularHourChange(self, value):
        self.update_property_signal.emit({"regular_hours_type": value})


    def changePeriodDuration(self, new_text):
        self.update_property_signal.emit({"period_duration": new_text})

    
    def changeBarType(self, new_index):
        print("ComparisonList.changeBarType")
        self.selected_bar_type = self.bar_types[new_index]
        self.update_property_signal.emit({"bar_change_type": self.selected_bar_type})
        print(self.bar_types)
        if self.bar_types[new_index] == Constants.DAY_BAR:
            self.plot_period_selector.setCurrentText('Max')



    def toggleSelection(self):
        if self.sel_all_button.text() == f"Select {Constants.MAX_DEFAULT_LINES}":
            self.visible_ticker_box.selectAll()
            self.check_list.update(self.visible_ticker_box.itemStates())
            self.data_processor.updateFrameForHistory(selected_tab=self.tab_widget.currentIndex(), initial_list_load=True)
            self.sel_all_button.setText("Check All")
        else:
            if self.sel_all_button.text() == "Uncheck All":
                if len(self.stock_list) > Constants.MAX_DEFAULT_LINES:
                    self.sel_all_button.setText(f"Select {Constants.MAX_DEFAULT_LINES}")
                else:
                    self.sel_all_button.setText("Check All")
                self.visible_ticker_box.deselectAll()
            else:
                self.sel_all_button.setText("Uncheck All")
                self.visible_ticker_box.selectAll()
            self.check_list.update(self.visible_ticker_box.itemStates())
        
        self.check_list_signal.emit(self.check_list) #, self.comp_list, self.focus_list)
        filtered_list = {uid: value for (uid, value) in self.stock_list.items() if self.check_list[uid]}
        addCheckableTickersTo(self.focus_box, filtered_list, self.focus_list)



############## GUI SIGNALING

    def setHistoryEnabled(self, value):
        for button in self.history_interaction_group.buttons():
            button.setEnabled(value)


    def prepCurrentTable(self):
        current_index = self.tab_widget.currentIndex()
        if current_index < len(self.list_of_tables):
            self.list_of_tables[current_index].model().layoutAboutToBeChanged.emit()


    def updateDataModels(self):
        for table in self.list_of_tables:
            model = table.model()
            model.setDataFrame(self.data_container)


    def signalCurrentTable(self):
        current_index = self.tab_widget.currentIndex()
        if current_index < len(self.list_of_tables):
            current_model = self.list_of_tables[current_index].model()
            current_model.layoutChanged.emit()
            current_model.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())


    def keepUpToDate(self, value):
        if value:
            self.update_stock_list_signal.emit(self.selected_bar_type, True)
        else:
            print("WE CALL FOR CANCELATION comp")
            self.cancel_update_signal.emit()


    def showTopsAndBottoms(self, value):
        self.tops_and_bottoms = value
        # self.resetCharts()
        

############## Table interactions

    def prepOrder(self, item):

        symbol, uid = self.high_model.getStockFor(item.row())

        mycontract = Contract()
        mycontract.symbol = symbol
        mycontract.secType = Constants.STOCK
        mycontract.conId = uid
        mycontract.exchange = "SMART"

        dialog = OrderDialog(symbol, 100, True)
        if dialog.exec():
            bracket_order = dialog.getOrder()

            for order in bracket_order:
                self.data_processor.history_manager.ib_interface.placeOrder(order.orderId, mycontract, order)
                #self.buffered_manager.history_manager.ib_interface.placeOrder(order.orderId, mycontract, order)


    def showChart(self, item, vs_index=False):

        if item.column() > 1:
            symbol, uid = self.rsi_model.getStockFor(item.row())
            
            bar_type = self.bar_types[item.column()-2]
            #bars = self.buffered_manager.existing_buffers[uid, bar_type]
            bars = self.data_processor.getBarData(uid, bar_type) #buffered_manager.existing_buffers[uid, bar_type]
            
            dialog = QuickChart(symbol, bar_type, bars)
            dialog.exec()


        #TODO this should be in super
    def accepts(self, command):
        return command.lower() == "plotComp".lower()


    def process(self, command, params):
        if "l" in params:
            for index, (file, name) in enumerate(self.stock_lists):
                if name == params["l"]:
                    self.listSelection(index)
                    break
        return {"photo": self.compare_plot.capturePlotAsImage()}


    def getAvailabeCommands(self):
        print("We should return this no?")
        return {"text": "plotComp - Shows a comparison plot (default is all sectors, normalized) \n\t list=$name for specific list \n\t conv=norm or ind for normalized or indexed"}


    def closeEvent(self, *args, **kwargs):
        self.data_processor.stop()
        self.processor_thread.quit()
        self.processor_thread.wait()
        super(QMainWindow, self).closeEvent(*args, **kwargs)
        # self.close_signal.emit()
        
    

