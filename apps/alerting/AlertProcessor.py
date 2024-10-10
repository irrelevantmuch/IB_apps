
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

from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, Qt
from dataHandling.Constants import Constants, DT_BAR_TYPES
from dataHandling.HistoryManagement.BufferedManager import BufferedDataManager
from dataHandling.UserDataManagement import readStockList


class AlertProcessor(QObject):

    initial_fetch = False
    alerts_on = False
    alert_tracker = dict()
    update_stock_selection = pyqtSignal(dict)

    stock_count_signal = pyqtSignal(int)

    rsi_bar_types = [Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR]
    step_bar_types = [Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR]
    
    
    def __init__(self, buffered_manager, indicator_processor):
        super().__init__()
        
        print("DataProcessor.init")
        self.buffered_manager = buffered_manager
        self.buffered_manager.api_updater.connect(self.apiUpdate, Qt.QueuedConnection)

        self.data_buffers = self.buffered_manager.data_buffers
        self.indicator_processor = indicator_processor
        self.indicator_processor.indicator_updater.connect(self.indicatorUpdate, Qt.QueuedConnection)
        self.update_stock_selection.connect(self.indicator_processor.setTrackingList, Qt.QueuedConnection)
        self.stock_lists = []
        self.full_stock_list = dict()
        self.initializeSelectionLists()


    def initializeSelectionLists(self):
        self.cross_checks = {tf: False for tf in DT_BAR_TYPES}
        self.reversal_checks = {tf: False for tf in DT_BAR_TYPES}
        self.up_checks = {tf: False for tf in DT_BAR_TYPES}
        self.down_checks = {tf: False for tf in DT_BAR_TYPES}


    @pyqtSlot(str)        
    def addStockList(self, stock_list):
        self.stock_lists.append(stock_list)
        self.updateStockList()

    @pyqtSlot(str)
    def removeStockList(self, stock_list):
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


    @pyqtSlot(str)
    def updateFrequencyChange(self, freq_type):
        print("THIS IS ONLY IMPLEMENTED FOR FINAZON!!!!!!")
        print("THIS IS ONLY IMPLEMENTED FOR FINAZON!!!!!!")
        print("THIS IS ONLY IMPLEMENTED FOR FINAZON!!!!!!")
        print("THIS IS ONLY IMPLEMENTED FOR FINAZON!!!!!!")



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
        if signal == Constants.HAS_NEW_VALUES:
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


    @pyqtSlot(str, dict)
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

        if self.alertExistsFor(uid, bar_type, 'up steps'):
            old_steps_object = self.alert_tracker[uid][bar_type, 'up steps']
            if up_move['UpSteps'] < old_steps_object['UpSteps']:
                self.logAlertFor(uid, bar_type, 'up steps broken', old_steps_object)
                del self.alert_tracker[uid][bar_type, 'up steps']
                self.sendAlert(uid)
                del self.alert_tracker[uid][bar_type, 'up steps broken']
            elif up_move['UpSteps'] > old_steps_object['UpSteps']:
                self.logAlertFor(uid, bar_type, 'up steps', up_move)
                self.sendAlert(uid)
        elif (up_move['UpSteps'] > self.step_up_thresholds[bar_type]) and (up_move['UpMove'] > 1.0):
            self.logAlertFor(uid, bar_type, 'up steps', up_move)
            self.sendAlert(uid)
        
        down_move = self.data_buffers.getIndicatorValues(uid, bar_type, ['DownSteps','DownMove'])
        
        if self.alertExistsFor(uid, bar_type, 'down steps'):
            old_steps_object = self.alert_tracker[uid][bar_type, 'down steps']
            if down_move['DownSteps'] < old_steps_object['DownSteps']:
                self.logAlertFor(uid, bar_type, 'down steps broken', down_move)
                del self.alert_tracker[uid][bar_type, 'down steps']
                self.sendAlert(uid)
                del self.alert_tracker[uid][bar_type, 'down steps broken']
            elif down_move['DownSteps'] > old_steps_object['DownSteps']:
                self.logAlertFor(uid, bar_type, 'down steps', down_move)
                self.sendAlert(uid)
        elif (down_move['DownSteps'] > self.step_down_thresholds[bar_type]) and (down_move['DownMove'] < -1.0):
            self.logAlertFor(uid, bar_type, 'down steps', down_move)
            self.sendAlert(uid)
                

    def isReversal(self, values):
        if (values[0] > values[1]) and (values[2] > values[1]):
            return True
        elif (values[0] < values[1]) and (values[2] < values[1]):
            return True
        return False


    def sendAlert(self, uid):
        
        latest_price = self.data_buffers.getLatestPrice(uid)
        symbol = self.full_stock_list[uid][Constants.SYMBOL]
        print(f"AlertProcessor.sendAlert {symbol}")

        message_props = {'symbol': symbol, 'latest_price': latest_price, 'alert_lines': self.alert_tracker[uid].copy()}

            #in the beginning a daily RSI may not have been downloaded yet
        if self.data_buffers.bufferExists(uid, Constants.DAY_BAR):
            daily_rows = self.data_buffers.getBarsFromIntIndex(uid, Constants.DAY_BAR, -2)
            previous_close = daily_rows.iloc[0][Constants.CLOSE]
            if 'rsi' in daily_rows:
                message_props['daily_rsi'] = daily_rows.iloc[1]['rsi']
            message_props['daily_move'] = 100*((latest_price-previous_close)/previous_close)
        
        self.telegram_signal.emit('alert_message', message_props)


    def stopUpdating(self):
        self.buffered_manager.cancelUpdates()
    
    
    @pyqtSlot()
    def stop(self):
        self.buffered_manager.deregister()
        

        
class AlertProcessorFinazon(AlertProcessor):


    @pyqtSlot(bool)
    def runUpdates(self, turn_on):
        if turn_on:
            self.buffered_manager.setStockList(self.full_stock_list)
            self.buffered_manager.fetchLatestStockData()
            self.initial_fetch = True
        else:
            self.stopUpdating()


    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, sub_signal):
        print(f"AlertProcessor.apiUpdate {signal}")
        if signal == Constants.ALL_DATA_LOADED:
            if self.initial_fetch:
                self.buffered_manager.requestUpdates(keep_up_to_date=True, propagate_updates=True)
                self.initial_fetch = False        
        

class AlertProcessorIB(AlertProcessor):

    rotating = False
    next_index = 0

    def __init__(self, buffered_manager, indicator_processor):
        super().__init__(buffered_manager, indicator_processor)
        self.separate_stock_lists = list()
        buffered_manager.history_manager.addNewListener(self, self.apiUpdate)
    

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
            if self.rotating:
                self.runRotatingUpdates()
            elif self.initial_fetch:
                self.buffered_manager.requestUpdates(keep_up_to_date=True, propagate_updates=True)
                self.initial_fetch = False        
        

