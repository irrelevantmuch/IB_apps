
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
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from dataHandling.Constants import Constants
from .ListManagerWindow import ListManagerWindow

from uiComps.customWidgets.ProgressDialog import ProgressBarDialog

from dataHandling.DataStructures import DetailObject
from dataHandling.HistoryManagement.BufferedManager import BufferedDataManager

from dataHandling.UserDataManagement import writeStockList, readStockList, getStockListNames

class ListManager(ListManagerWindow):

    # existing_buffers = dict()
    # existing_ranges = dict()
    fetch_stock_contracts = pyqtSignal(DetailObject, bool)
    
    option_chain_requests = []

    def __init__(self, symbol_manager, history_manager, option_manager):
        super().__init__()

        self.loadData()
        self.symbol_manager = symbol_manager
        self.buffered_manager = BufferedDataManager(history_manager)
        self.option_manager = option_manager


        self.option_manager.api_updater.connect(self.apiUpdate)
        self.buffered_manager.history_manager.api_updater.connect(self.apiUpdate)
        self.buffered_manager.history_manager.mostRecentFirst = True
        
        self.buffered_manager.setStockList(self.stock_list)
        self.fetch_stock_contracts.connect(self.option_manager.makeStockSelection, type=Qt.DirectConnection)
        self.symbol_manager.api_updater.connect(self.contractUpdate, Qt.QueuedConnection)


    def loadData(self):
        self.stock_lists = getStockListNames()

        if len(self.stock_lists) == 0:
            self.createBaseStockList()
        else:
            for _, list_name in self.stock_lists:
                self.list_selector.addItem(list_name)

            self.loadNewStockList(0)


    def loadNewStockList(self, index):
        delete_button_set = set()         
        self.stock_list = self.getStockList(index)
        self.fillOutTable()


    def getStockList(self, for_index):            
            file_name, _ = self.stock_lists[for_index]

            if file_name is not None:
                return readStockList(file_name)
            
            return dict()


    def createBaseStockList(self):
        list_name = "Watch List"
        self.stock_lists = [(None, list_name)]
        self.list_selector.addItem(list_name)
        self.stock_list = dict()


    def createNewList(self):
        new_list_name = self.list_name_field.text()
        self.list_name_field.setText("")
        if new_list_name != "":
            self.stock_lists.insert(0, (None, new_list_name))
            self.list_selector.insertItem(0, new_list_name)
            self.list_selector.setCurrentIndex(0)
            self.stock_list = dict()


    def bufferChains(self):

        self.dialog = ProgressBarDialog()
        self.dialog.show()

        self.option_chain_requests = []
        for uid in self.stock_list:
            self.option_chain_requests.append(uid)

        self.total_chain_requests = len(self.option_chain_requests)
        self.fetchNextOptionChain()


    def fetchNextOptionChain(self):

        if len(self.option_chain_requests) > 0:
            
            process_progress = (self.total_chain_requests-len(self.option_chain_requests))/self.total_chain_requests
            next_uid = self.option_chain_requests.pop()

            self.dialog.setOverallProgress(process_progress, f"Downloading chains for {self.stock_list[next_uid]['long_name']}")

            stock_inf = self.stock_list[next_uid]
            contract_details = DetailObject(numeric_id=next_uid, **stock_inf)

            self.fetch_stock_contracts.emit(contract_details, False)
        else:
            self.dialog.setOverallProgress(1.0, "All chains completed")            


    def fillOutTable(self):
        for index, (key, details) in enumerate(self.stock_list.items()):
            self.addRowAt(index, key, details) 


    def listSelection(self, value):
        self.stock_table.clearContents()
        self.stock_table.setRowCount(0)
        
        self.loadNewStockList(value)


    def saveStockList(self):
        current_index = self.list_selector.currentIndex()
        file_name, list_name = self.stock_lists[current_index]
        writeStockList(self.stock_list, list_name, file_name)


    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, sub_signal):
        
        if signal == Constants.OPTION_INFO_LOADED:
            self.fetchNextOptionChain()
        elif signal == Constants.PROGRESS_UPDATE:
            self.dialog.setProcessProgress((sub_signal['total_requests']-sub_signal['open_requests'])/sub_signal['total_requests'])



    def radioSelection(self, value):
        if value == self.stock_rb:
            self.symbol_manager.setSelectedSectype(Constants.STOCK)
        elif value == self.cfd_rb:
            self.symbol_manager.setSelectedSectype(Constants.CFD)
        elif value == self.cash_rb:
            self.symbol_manager.setSelectedSectype(Constants.CASH)
        elif value == self.commodity_rb:
            self.symbol_manager.setSelectedSectype(Constants.COMMODITY)
        elif value == self.warrant_rb:
            self.symbol_manager.setSelectedSectype(Constants.WARRANT)

        

        #TODO this should be in super
    def accepts(self, value):
        return False


    def closeEvent(self, event):
        super().closeEvent(event)
        self.symbol_manager.finished.emit()
        self.option_manager.finished.emit()
        self.buffered_manager.deregister()