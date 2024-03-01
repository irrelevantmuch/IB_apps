
from PyQt5.QtCore import QThread, QMetaObject, Qt, pyqtSlot
from dataHandling.HistoryManagement.HistoricalDataManagement import HistoricalDataManager
from dataHandling.HistoryManagement.FinazonDataManager import FinazonDataManager
from dataHandling.TradeManagement.OrderManagement import OrderManager
from dataHandling.OptionManagement.OptionChainManager import OptionChainManager
from dataHandling.TradeManagement.PositionDataManagement import PositionDataManager
from dataHandling.DataManagement import DataManager
from dataHandling.SymbolManager import SymbolDataManager
from pubsub import pub


class IBConnector:

    curr_id = 1
    data_management = None
    order_manager = None
    history_manager = None

    running_workers = dict()

    @property
    def next_id(self):
        try:
            if self.curr_id < 31:
                return self.curr_id
        finally:
            self.curr_id += 1
            

    def getNewPositionManager(self):
        return None
        # data_manager = PositionDataManager()
        # data_manager.setParameters(self.local_address, int(self.trading_socket), client_id=self.next_id)
        # data_manager.api_updater.connect(self.apiUpdate, Qt.QueuedConnection)
        # data_manager.start()
        # return data_manager
        

    def getNewSymbolManager(self, identifier):
        symbol_manager = SymbolDataManager(name=identifier)
        symbol_manager.setParameters(self.local_address, int(self.trading_socket), client_id=self.next_id)
        symbol_manager.api_updater.connect(self.apiUpdate, Qt.QueuedConnection)
        symbol_manager = symbol_manager
        symbol_thread = QThread()
        self.startWorkerThread(identifier, symbol_manager)
        
        return symbol_manager


    def getHistoryManager(self, identifier='general_history'):
        if self.data_source == "IBKR":
            return self.getHistoryManagerIB(identifier)
        elif self.data_source == "Finazon":
            return self.getFinazonManager(identifier)


    def getHistoryManagerIB(self, identifier='general_history'):
        if identifier == 'general_history' and (self.history_manager is not None):
            return self.history_manager
        else:
            history_manager = HistoricalDataManager()
            history_manager.setParameters(self.local_address, int(self.trading_socket), client_id=self.next_id)
            history_manager.api_updater.connect(self.apiUpdate, Qt.QueuedConnection)

            self.startWorkerThread(identifier, history_manager)
            
            if identifier == 'general_history':
                self.history_manager = history_manager    

            return history_manager


    def startWorkerThread(self, identifier, worker, run_function=None):
        thread = QThread()
        worker.moveToThread(thread)
        if run_function is None:
            thread.started.connect(worker.run)
        else:
            thread.started.connect(run_function)
        worker.finished.connect(lambda: self.cleanupWorkerThread(identifier), Qt.QueuedConnection)
        self.running_workers[identifier] = (worker, thread)
        thread.start()
        print("We start the thread already?")



    @pyqtSlot(str)
    def cleanupWorkerThread(self, identifier):
        print(f"Not sure how this will work.... {identifier}")
        worker, thread = self.running_workers.pop(identifier)  # Retrieve and remove thread from dictionary
        worker.deleteLater()
        thread.quit()
        thread.wait()


    def getFinazonManager(self, identifier='general_history'):
        if identifier == 'general_history' and (self.history_manager is not None):
            return self.history_manager
        else:
            finazon_manager = FinazonDataManager()
            self.finazon_thread = QThread()
            finazon_manager.moveToThread(self.finazon_thread)
            self.finazon_thread.started.connect(finazon_manager.run) #_ib_client_slot)
            self.finazon_thread.start()
            if identifier == 'general_history':
                self.history_manager = finazon_manager
            return finazon_manager


    def getOrderManager(self, identifier='general_order_manager'):
        if (self.order_manager is not None) and identifier == 'general_order_manager':
            return self.order_manager
        else:
            order_manager = OrderManager()
            if identifier == 'general_order_manager':
                order_manager.setParameters(self.local_address, int(self.trading_socket), client_id=0)
            else:
                order_manager.setParameters(self.local_address, int(self.trading_socket), client_id=self.next_id)
            order_manager.api_updater.connect(self.apiUpdate, Qt.QueuedConnection)
            self.startWorkerThread(identifier, order_manager)
                
            if identifier == 'general_order_manager':
                self.order_manager = order_manager

            return order_manager


    def getNewOptionManager(self):
        option_chain_manager = OptionChainManager()
        option_chain_manager.setParameters(self.local_address, int(self.trading_socket), client_id=self.next_id)
        option_chain_manager.api_updater.connect(self.apiUpdate, Qt.QueuedConnection)
        # self.next_id += 1

        option_thread = QThread()

        self.startWorkerThread('option_manager', option_chain_manager)
        
        return option_chain_manager


    def openConnection(self):

        if self.data_management is None:
            self.data_management = DataManager(callback=self.apiUpdate)
            self.local_address = self.address_line.text()
            self.trading_socket = self.socket_line.text()
            self.data_management.setParameters(self.local_address, int(self.trading_socket), client_id=self.next_id)
            # self.next_id += 1

            self.data_thread = QThread()
            self.data_management.moveToThread(self.data_thread)
            self.data_thread.started.connect(self.data_management.run)
            self.data_thread.finished.connect(lambda: self.cleanupWorkerThread(identifier))
            self.data_thread.start()
        else:
            pub.sendMessage('log', message=f"Connection already established")

