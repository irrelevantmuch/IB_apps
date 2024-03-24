from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot, Qt
from dataHandling.Constants import Constants, MAIN_BAR_TYPES, DT_BAR_TYPES
from datetime import datetime, timedelta
import pandas as pd
from pytz import timezone
from dataHandling.DataStructures import DetailObject
import itertools, json
from dataHandling.HistoryManagement.BufferedManager import BufferedDataManager
from dataHandling.TradeManagement.UserDataManagement import readStockList
from dataHandling.HistoryManagement.FinazonDataManager import FinazonDataManager
from dataHandling.HistoryManagement.HistoricalDataManagement import HistoricalDataManager
import time


class AlertProcessor(QObject):

    initial_fetch = False
    alerts_on = False
    alert_tracker = dict()
    update_stock_selection = pyqtSignal(dict)

    stock_count_signal = pyqtSignal(int)

    rsi_bar_types = [Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR]
    step_bar_types = [Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR]
    
    
    def __init__(self, history_manager, indicator_processor, telegram_signal):
        super().__init__()
        
        print("DataProcessor.init")
        self.buffered_manager = BufferedDataManager(history_manager, name="MoversBuffer")
        self.data_buffers = self.buffered_manager.data_buffers
        self.indicator_processor = indicator_processor
        self.indicator_processor.indicator_updater.connect(self.indicatorUpdate, Qt.QueuedConnection)
        self.update_stock_selection.connect(self.indicator_processor.setTrackingList, Qt.QueuedConnection)

        self.telegram_signal = telegram_signal
        self.history_manager = history_manager
        self.stock_lists = []
        self.full_stock_list = dict()
        self.initializeSelectionLists()


    def initializeSelectionLists(self):
        self.cross_checks = {tf: False for tf in DT_BAR_TYPES}
        self.reversal_checks = {tf: False for tf in DT_BAR_TYPES}
        self.up_checks = {tf: False for tf in DT_BAR_TYPES}
        self.down_checks = {tf: False for tf in DT_BAR_TYPES}


    # def initalizeThresholds(self):
    #     self.cross_down_thresholds = {tf: 30 for tf in DT_BAR_TYPES}
    #     self.cross_up_thresholds = {tf: 70 for tf in DT_BAR_TYPES}
    #     self.step_up_thresholds = {tf: 6 for tf in DT_BAR_TYPES}
    #     self.step_down_thresholds = {tf:  for tf in DT_BAR_TYPES}


    @pyqtSlot(str)        
    def addStockList(self, stock_list):
        self.stock_lists.append(stock_list)
        self.updateStockList()

    @pyqtSlot(str)
    def removeStockList(self, stock_list):
        print(self.stock_lists)
        print(stock_list)
        self.stock_lists.remove(stock_list)
        self.updateStockList()


    def moveToThread(self, thread):
        self.buffered_manager.moveToThread(thread)
        super().moveToThread(thread)


    @pyqtSlot(bool)
    def toggleAlerts(self, value):
        self.alerts_on = value
    
    @pyqtSlot()
    def run(self):       
        pass


    def updateStockList(self):
        self.full_stock_list = dict()
        for stock_list_name in self.stock_lists:
            stock_list = readStockList(stock_list_name)
            self.full_stock_list.update(stock_list)

        if self.indicator_processor is not None:
            self.update_stock_selection.emit(self.full_stock_list)
        self.stock_count_signal.emit(len(self.full_stock_list))


    @pyqtSlot(str, dict)
    def indicatorUpdate(self, signal, sub_signal):
        print(f"AlertProcessor.indicatorUpdate {signal}")
        if signal == Constants.HAS_NEW_VALUES:
            
            print(sub_signal)
            
            
            if 'updated_from' in sub_signal:
                updated_from = sub_signal['updated_from']
            else:
                updated_from = None

            if self.alerts_on:
                if sub_signal['update_type'] == 'rsi':
                    self.checkRsiEvents(sub_signal['uid'], sub_signal['bar_type'])
                if sub_signal['update_type'] == 'steps':
                    self.checkStepEvents(sub_signal['uid'], sub_signal['bar_type'])



    @pyqtSlot(str, dict)
    def selectionSignalChange(self, sel_type, check_list):
        if sel_type == "cross_checks":
            self.cross_checks = check_list
            self.setRsiBarTypes()
        elif sel_type == "reversal_checks":
            self.reversal_checks = check_list
            self.setRsiBarTypes()
        elif sel_type == "up_checks":
            self.up_checks = check_list
            self.setStepBarTypes()
        elif sel_type == "down_checks":
            self.down_checks = check_list
            self.setStepBarTypes()


    def thresholdChangeSignal(self, sel_type, threshold_list):
        if sel_type == "cross_down_threshold":
            self.cross_down_thresholds = threshold_list
        elif sel_type == "cross_up_threshold":
            self.cross_up_thresholds = threshold_list
        elif sel_type == "step_up_threshold":
            self.step_up_thresholds = threshold_list
        elif sel_type == "step_down_threshold":
            self.step_down_thresholds = threshold_list


    def setRsiBarTypes(self):
        cross_bars = [key for key, item in self.cross_checks.items() if item]
        reversal_bars = [key for key, item in self.reversal_checks.items() if item]
        self.rsi_bar_types = list(set(cross_bars) | set(reversal_bars))


    def setStepBarTypes(self):
        print(self.up_checks)
        print(self.down_checks)
        up_bars = [key for key, item in self.up_checks.items() if item]
        down_bars = [key for key, item in self.down_checks.items() if item]
        self.step_bar_types = list(set(up_bars) | set(down_bars))

    def checkRsiEvents(self, uid, bar_type):
        rsi_column = self.data_buffers.getColumnFor(uid, bar_type, 'rsi')
        if rsi_column is not None:
            if self.alertExistsFor(uid, bar_type, "rsi crossing down"):
                if (rsi_column.iloc[-1] > self.cross_down_thresholds[bar_type]):
                    del self.alert_tracker[uid][bar_type, "rsi crossing down"]                    
            elif (rsi_column.iloc[-2] > self.cross_down_thresholds[bar_type]) and (rsi_column.iloc[-1] < self.cross_down_thresholds[bar_type]):
                self.logAlertFor(uid, bar_type, "rsi crossing down", rsi_column.iloc[-1])
                self.sendAlert(uid)

            if self.alertExistsFor(uid, bar_type, "rsi crossing up"):
                if (rsi_column.iloc[-1] < self.cross_up_thresholds[bar_type]):
                    del self.alert_tracker[uid][bar_type, "rsi crossing up"]    
            elif (rsi_column.iloc[-2] < self.cross_up_thresholds[bar_type]) and (rsi_column.iloc[-1] > self.cross_up_thresholds[bar_type]):
                self.logAlertFor(uid, bar_type, "rsi crossing up", rsi_column.iloc[-1])
                self.sendAlert(uid)


    def alertExistsFor(self, uid, bar_type, alert_type):
        if uid in self.alert_tracker:
            return (bar_type, alert_type) in self.alert_tracker[uid]
        return False
    

    def logAlertFor(self, uid, bar_type, alert_type, value):
        if uid not in self.alert_tracker:
            self.alert_tracker[uid] = dict()
        self.alert_tracker[uid][bar_type, alert_type] = value


    def checkStepEvents(self, uid, bar_type):
        up_move = self.data_buffers.getIndicatorValues(uid, bar_type, ['UpSteps','UpMove'])

        if self.alertExistsFor(uid, bar_type, "up steps"):
            old_level = self.alert_tracker[uid][bar_type, "up steps"]
            if up_move['UpSteps'] < old_level:
                # self.sendAlert("up steps", uid, bar_type, old_level, 'broke')
                del self.alert_tracker[uid][bar_type, "up steps"]
            elif up_move['UpSteps'] > old_level:
                self.logAlertFor(uid, bar_type, "up steps", up_move['UpSteps'])
                self.sendAlert(uid)
        elif (up_move['UpSteps'] > self.step_up_thresholds[bar_type]) and (up_move['UpMove'] > 1.0):
            self.logAlertFor(uid, bar_type, "up steps", up_move['UpSteps'])
            self.sendAlert(uid)
        
        down_move = self.data_buffers.getIndicatorValues(uid, bar_type, ['DownSteps','DownMove'])
        
        if self.alertExistsFor(uid, bar_type, "down steps"):
            old_level = self.alert_tracker[uid][bar_type, "down steps"]
            if down_move['DownSteps'] < old_level:
                # self.sendAlert("down steps", uid, bar_type, old_level, 'broke')
                del self.alert_tracker[uid][bar_type, "down steps"]
            elif down_move['DownSteps'] > old_level:
                self.logAlertFor(uid, bar_type, "down steps", down_move['DownSteps'])
                self.sendAlert(uid)
        elif (down_move['DownSteps'] > self.step_down_thresholds[bar_type]) and (down_move['DownMove'] < -1.0):
            print(f"down step {down_move['DownSteps']}")
            self.logAlertFor(uid, bar_type, "down steps", down_move['DownSteps'])
            self.sendAlert(uid)
                

    def isReversal(self, values):
        if (values[0] > values[1]) and (values[2] > values[1]):
            return True
        elif (values[0] < values[1]) and (values[2] < values[1]):
            return True
        return False


    def sendAlert(self, uid):
        print(f"AlertProcessor.sendAlert {uid}")
        latest_price = self.data_buffers.getLatestPrice(uid)

        print(f"AlertProcessor.sendAlert...... {self.full_stock_list[uid][Constants.SYMBOL]}")
        symbol = self.full_stock_list[uid][Constants.SYMBOL]
        self.telegram_signal.emit(symbol, latest_price, self.alert_tracker[uid].copy())


    def stopUpdating(self):
        self.buffered_manager.cancelUpdates()
    

        
class AlertProcessorFinazon(AlertProcessor):


    # def __init__(self, history_manager):
    #     super().__init__(history_manager)
    #     history_manager.addNewListener(self, self.apiUpdate)
        

    @pyqtSlot(bool)
    def runUpdates(self, turn_on):
        if turn_on:
            self.buffered_manager.setStockList(self.full_stock_list)
            self.buffered_manager.fetchLatestStockData()
        else:
            self.stopUpdating()



            
    @pyqtSlot(str, dict)
    def bufferUpdate(self, signal, sub_signal):
        print("AlertProcessor.bufferUpdate {signal}")
        if signal == Constants.ALL_DATA_LOADED:
            if self.initial_fetch:
                print("We go for keeping things up to date")
                self.buffered_manager.requestUpdates(keep_up_to_date=True)
                self.initial_fetch = False
        


class AlertProcessorIB(AlertProcessor):

    rotating = False
    next_index = 0

    def __init__(self, history_manager, indicator_processor, telegram_signal):
        super().__init__(history_manager, indicator_processor, telegram_signal)
        self.separate_stock_lists = list()
        self.buffered_manager.api_updater.connect(self.apiUpdate, Qt.QueuedConnection)
        history_manager.addNewListener(self, self.apiUpdate)
    

    def updateStockList(self):
        super().updateStockList()
        self.separate_stock_lists = []
        for stock_list_name in self.stock_lists:
            stock_list = readStockList(stock_list_name)
            self.separate_stock_lists.append(stock_list)


    @pyqtSlot(bool)
    def runUpdates(self, turn_on):
        if turn_on:
            if len(self.full_stock_list) < 50:
                self.initial_fetch = True
                self.buffered_manager.setStockList(self.full_stock_list)
                self.buffered_manager.fetchLatestStockDataWithCancelation()
            else:
                self.runRotatingUpdates()
        else:
            self.stopUpdating()


    def runRotatingUpdates(self):
            self.rotating = True
            #check voor de lengte van de full_stock_list om te zien of alles in 1 kan.
            print("AlertProcessor.runRotatingUpdates")
            self.buffered_manager.setStockList(self.separate_stock_lists[self.next_index])
            self.buffered_manager.fetchLatestStockDataWithCancelation()
            self.next_index += 1
            if self.next_index >= len(self.separate_stock_lists): self.next_index = 0



    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, sub_signal):
        print(f"AlertProcessor.apiUpdate {signal}")
        if signal == Constants.ALL_DATA_LOADED:
            print(f"We ask for more!!!! {self.initial_fetch}")
            if self.rotating:
                print("We go for rotation")
                self.runRotatingUpdates()
            elif self.initial_fetch:
                print("Are we updating?")
                self.buffered_manager.requestUpdates(keep_up_to_date=True, propagate_updates=True)
                self.initial_fetch = False        
        

