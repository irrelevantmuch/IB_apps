
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


from PyQt6.QtCore import QThread, QMetaObject, Qt, pyqtSlot

from dataHandling.HistoryManagement.HistoricalDataManagement import HistoricalDataManager
from dataHandling.HistoryManagement.FinazonDataManager import FinazonDataManager
from dataHandling.HistoryManagement.IndicatorProcessor import IndicatorProcessor

from dataHandling.TradeManagement.OrderManagement import OrderManager
from dataHandling.TradeManagement.PositionDataManagement import PositionDataManager
from dataHandling.OptionManagement.OptionChainManager import OptionChainManager
from dataHandling.IBConnectivity import IBConnectivity
from dataHandling.SymbolManager import SymbolManager
from dataHandling.Constants import Constants
from pubsub import pub
import time


class ConnectionThreadManager:

    curr_id = 1
    order_manager = None
    history_manager = None
    indicator_processor = None
    connectivty_ver = None

    running_workers = dict()

    @property
    def next_id(self):
        try:
            if self.curr_id < 31:
                return self.curr_id
        finally:
            self.curr_id += 1
            

    def getNewPositionManager(self):
        position_manager = PositionDataManager(self.local_address, int(self.trading_socket), self.next_id)
        position_manager.api_updater.connect(self.apiUpdate, Qt.ConnectionType.QueuedConnection)
        self.startWorkerThread('position_manager', position_manager)
        return position_manager
        

    def getNewSymbolManager(self, identifier):
        symbol_manager = SymbolManager(self.local_address, int(self.trading_socket), self.next_id, name=identifier)
        symbol_manager.api_updater.connect(self.apiUpdate, Qt.ConnectionType.QueuedConnection)
        self.startWorkerThread(identifier, symbol_manager)
        
        return symbol_manager


    def getIndicatorManager(self, indicators, data_object, **kwargs):
        if self.indicator_processor is None:
            self.indicator_processor = IndicatorProcessor(data_object, indicators, **kwargs)
            self.startWorkerThread('general_indicator', self.indicator_processor, run_function=self.indicator_processor.run, thread_priority=QThread.Priority.HighestPriority)
            
        return self.indicator_processor


    def getHistoryManager(self, identifier='general_history'):
        if self.data_source == Constants.IB_SOURCE:
            return self.getHistoryManagerIB(identifier)
        elif self.data_source == Constants.FINAZON_SOURCE:
            return self.getHistoryManagerFZ(identifier)


    def getHistoryManagerIB(self, identifier='general_history'):
        if identifier == 'general_history' and (self.history_manager is not None):
            history_manager = self.history_manager
        else:
            history_manager = HistoricalDataManager(self.local_address, int(self.trading_socket), self.next_id, name="HistoricalDataManager")
            history_manager.api_updater.connect(self.apiUpdate, Qt.ConnectionType.QueuedConnection)

            self.startWorkerThread(identifier, history_manager)
            
            if identifier == 'general_history':
                self.history_manager = history_manager    

        return history_manager


    def getHistoryManagerFZ(self, identifier='general_history'):
        if identifier == 'general_history' and (self.history_manager is not None):
            finazon_history_manager = self.history_manager
        else:
            finazon_history_manager = FinazonDataManager()
            self.finazon_thread = QThread()
            finazon_history_manager.moveToThread(self.finazon_thread)
            self.finazon_thread.started.connect(finazon_history_manager.run) #_ib_client_slot)
            self.finazon_thread.start()
            if identifier == 'general_history':
                self.history_manager = finazon_history_manager

        return finazon_history_manager


    def startWorkerThread(self, identifier, worker, run_function=None, thread_priority=None):
        thread = QThread()
        worker.moveToThread(thread)
        if run_function is None:
            thread.started.connect(worker.startConnection)
        else:
            thread.started.connect(run_function)

        worker.finished.connect(lambda: self.cleanupWorkerThread(identifier), Qt.ConnectionType.QueuedConnection)
        self.running_workers[identifier] = (worker, thread)
        thread.start()
        if thread_priority is not None:
            thread.setPriority(thread_priority)
        

    @pyqtSlot(str)
    def cleanupWorkerThread(self, identifier):
        worker, thread = self.running_workers.pop(identifier)  # Retrieve and remove thread from dictionary

            # we don't want to clean her up if she is still in use
        if isinstance(worker, IBConnectivity):
            if worker.owner_count > 0:
                return
            else: 
                if identifier == 'general_order_manager': self.order_manager = None
                elif identifier == 'general_history': self.history_manager = None

        worker.stop()
        worker.deleteLater()
        thread.quit()
        thread.wait()


    def getOrderManager(self, identifier='general_order_manager'):

        if (self.order_manager is not None) and identifier == 'general_order_manager':
            
            order_manager = self.order_manager
        else:
            if identifier == 'general_order_manager':
                order_manager = OrderManager(self.local_address, int(self.trading_socket), 0)
            else:
                order_manager = OrderManager(self.local_address, int(self.trading_socket), self.next_id)
            order_manager.api_updater.connect(self.apiUpdate, Qt.ConnectionType.QueuedConnection)
            self.startWorkerThread(identifier, order_manager)
                
            if identifier == 'general_order_manager':
                self.order_manager = order_manager

        return order_manager


    def verifyConnection(self):
        self.local_address = self.address_line.text()
        self.trading_socket = self.socket_line.text()
        self.connectivty_ver = IBConnectivity(self.local_address, int(self.trading_socket), self.next_id, name="Connectivity.TEST")
        self.ver_id = self.connectivty_ver.registerOwner()
        self.connectivty_ver.api_updater.connect(self.apiUpdate, Qt.ConnectionType.QueuedConnection)
        self.connectivty_ver.startConnection()
        

    def getOptionManager(self):
        option_chain_manager = OptionChainManager(self.local_address, int(self.trading_socket), self.next_id)
        option_chain_manager.api_updater.connect(self.apiUpdate, Qt.ConnectionType.QueuedConnection)

        self.startWorkerThread('option_manager', option_chain_manager)
        
        return option_chain_manager