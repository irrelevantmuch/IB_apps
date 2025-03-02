
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

from PyQt6 import QtCore
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot

# from dataHandling.HistoryManagement.BufferedManager import BufferedDataManager
# from dataHandling.HistoryManagement.FinazonBufferedManager import FinazonBufferedDataManager 
from dataHandling.HistoryManagement.HistoricalDataManagement import HistoricalDataManager
from dataHandling.HistoryManagement.FinazonDataManager import FinazonDataManager
from .AlertWindow import AlertWindow

from .AlertProcessor import AlertProcessorFinazon, AlertProcessorIB
from dataHandling.UserDataManagement import getStockListNames


class AlertManager(AlertWindow):

    selection_signal_change = pyqtSignal(str, dict)
    threshold_signal_change = pyqtSignal(str, dict)
    update_signal = pyqtSignal(bool)
    list_addition_signal = pyqtSignal(str)
    list_removal_signal = pyqtSignal(str)
    alerting_signal = pyqtSignal(bool)
    update_frequency_signal = pyqtSignal(str)

    updating = False
    message_listening = False
    last_update_id = 0
    

    def __init__(self, history_manager, indicator_processor, processor_thread):
        super().__init__()

        self.loadLists()
        file_name, _ = self.stock_lists[0]
        self.prepAlertProcessor(history_manager, indicator_processor, processor_thread)

        self.providerSpecificUiSettings(history_manager)
        self.setDefaultThresholds()

        


    def providerSpecificUiSettings(self, history_manager):

        if isinstance(history_manager, FinazonDataManager):
            self.update_frequency_box.addItems(self.finazon_frequency_choices)
            self.update_frequency_box.setCurrentIndex(self.finazon_frequency_choices.index('1m'))
        elif isinstance(history_manager, HistoricalDataManager):
            self.update_frequency_box.addItems(self.ibkr_frequency_choices)
            self.update_frequency_box.setCurrentIndex(self.ibkr_frequency_choices.index('30s'))
    


    def setDefaultThresholds(self):
        self.lower_spin_all.setValue(30)
        self.higher_spin_all.setValue(70)
        self.up_spin_all.setValue(6)
        self.down_spin_all.setValue(6)

        self.up_check_all.setChecked(True)
        self.down_check_all.setChecked(True)
        self.reversal_box_all.setChecked(True)
        self.cross_box_all.setChecked(True)


    def setTelegramListener(self, telegram_signal):
        self.telegram_signal = telegram_signal
        self.data_processor.telegram_signal = telegram_signal


    def prepAlertProcessor(self, history_manager, indicator_processor, processor_thread):
        self.data_processor = AlertProcessorIB(history_manager, indicator_processor)
        self.processor_thread = processor_thread
        self.data_processor.moveToThread(self.processor_thread)
        
        history_manager.api_updater.connect(self.apiUpdate, Qt.ConnectionType.QueuedConnection)
        self.update_signal.connect(self.data_processor.runUpdates, Qt.ConnectionType.QueuedConnection)
        self.list_addition_signal.connect(self.data_processor.addStockList, Qt.ConnectionType.QueuedConnection)
        self.list_removal_signal.connect(self.data_processor.removeStockList, Qt.ConnectionType.QueuedConnection)
        self.alerting_signal.connect(self.data_processor.toggleAlerts, Qt.ConnectionType.QueuedConnection)
        self.data_processor.stock_count_signal.connect(self.stockCountUpdated, Qt.ConnectionType.QueuedConnection)
        self.selection_signal_change.connect(self.data_processor.selectionSignalChange, Qt.ConnectionType.QueuedConnection)
        self.threshold_signal_change.connect(self.data_processor.thresholdChangeSignal, Qt.ConnectionType.QueuedConnection)
        self.update_frequency_signal.connect(history_manager.setFrequency, Qt.ConnectionType.QueuedConnection)

        self.processor_thread.started.connect(self.data_processor.run)
        self.processor_thread.start()
        self.processor_thread.setPriority(QThread.Priority.HighestPriority)

        self.signalAlertPreferences()


    def signalAlertPreferences(self):
        self.updateCheckListFor("cross_box", "cross_checks")
        self.updateCheckListFor("reversal_box", "reversal_checks")
        self.updateCheckListFor("up_check", "up_checks")
        self.updateCheckListFor("down_check", "down_checks")
        self.updateThresholds("lower_spin", "cross_down_threshold")
        self.updateThresholds("higher_spin", "cross_up_threshold")
        self.updateThresholds("down_spin", "step_down_threshold")
        self.updateThresholds("up_spin", "step_up_threshold")


    def startUpdating(self):
        if not self.updating:
            self.updating = True
            self.comp_checkable_lists.disableSelection()
            self.list_selection_button.setEnabled(False)
            self.rotation_button.setText("Stop Updates")
            self.update_signal.emit(True)
        else:
            self.update_signal.emit(False)
            self.comp_checkable_lists.enableSelection()
            self.list_selection_button.setEnabled(True)
            self.rotation_button.setText("Rotating Updates")

            self.updating = False


    def loadLists(self):
        
        self.stock_lists = getStockListNames()

        self.comp_checkable_lists.blockSignals(True)

        file_list = dict()

        for index, (file_name, list_name) in enumerate(self.stock_lists):

            file_list[index] = file_name
            self.comp_checkable_lists.key_list = file_list
            self.comp_checkable_lists.addItem(list_name)

            item = self.comp_checkable_lists.model().item(index, 0)
            item.setCheckState(Qt.CheckState.Unchecked)

        self.comp_checkable_lists.blockSignals(False)            

    
    def toggleDataListening(self, value):
        self.alerting_signal.emit(value)

    
    def stockCountUpdated(self, value):
        self.stock_count_label.setText(str(value))


    def updateCheckListFor(self, button_name, signal_type):
        check_list = dict()
        for tf in self.time_frame_names:
            if tf != 'all':
                check_list[self.bar_type_conv[tf]] = self.widgetFor(f"{button_name}_{tf}").isChecked()
        self.selection_signal_change.emit(signal_type, check_list)


    def updateThresholds(self, button_name, signal_type):
        threshold_list = dict()
        for tf in self.time_frame_names:
            if tf != 'all':
                threshold_list[self.bar_type_conv[tf]] = self.widgetFor(f"{button_name}_{tf}").value()
        self.threshold_signal_change.emit(signal_type, threshold_list)



    def listSelection(self, value):
        toggle, list_name = self.comp_checkable_lists.getSelectionAt(value)
        if toggle:
            self.list_addition_signal.emit(list_name)
        else:
            self.list_removal_signal.emit(list_name)


    def toggleSelection(self):
        if self.list_selection_button.text() == "All Off":
            self.list_selection_button.setText("All On")
            self.comp_checkable_lists.deselectAll()
        else:
            self.list_selection_button.setText("All Off")
            self.comp_checkable_lists.selectAll()


    def getStockList(self, for_index):            
        file_name, _ = self.stock_lists[for_index]


    def updateFrequencyUpdate(self, sel_value):
        self.update_frequency_signal.emit(sel_value)
        


    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, sub_signal):
        pass
        #super().apiUpdate(signal, sub_signal)
        # if signal == Constants.HISTORICAL_UPDATE_COMPLETE or signal == Constants.HISTORICAL_REQUESTS_COMPLETED:
        #     if self.rotating:
        #         self.fetchNextList()


    def accepts(self, value):
        return False


    # def sendPhoto(self, file_name):
    #     method = 'sendPhoto'
    #     params = {'chat_id': self.bot_info['chat_id']}
    #     files = {'photo': file_name}
    #     api_url = f"https://api.telegram.org/bot{self.bot_info['token']}/"
    #     resp = requests.post(api_url + method, params, files=files)
    #     return resp


    