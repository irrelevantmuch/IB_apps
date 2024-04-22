
# # Copyright (c) 2024 Jelmer de Vries
# #
# # This program is free software: you can redistribute it and/or modify
# # it under the terms of the GNU Affero General Public License as published by
# # the Free Software Foundation in its latest version.
# #
# # This program is distributed in the hope that it will be useful,
# # but WITHOUT ANY WARRANTY; without even the implied warranty of
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# # GNU Affero General Public License for more details.
# #
# # You should have received a copy of the GNU Affero General Public License
# # along with this program.  If not, see <https://www.gnu.org/licenses/>.

# from PyQt5.QtCore import pyqtSignal, Qt, QObject, QThread, pyqtSlot
# from ibapi.contract import Contract

# from dataHandling.DataStructures import DetailObject
# from dataHandling.Constants import Constants

# from dataHandling.IBConnectivity import IBConnectivity

# class DataManager(QObject):

#     api_updater = pyqtSignal(str, dict)
#     ib_request_signal = pyqtSignal(dict)

#     snapshot = False
#     priceReqIsActive = False

#     previous_price = 0.0
#     price = 0.0

#     run_ib_client_signal = pyqtSignal()

#     finished = pyqtSignal()
    
#     def __init__(self, callback=None, name="DataManagent"):
#         super().__init__() 

#         self.name = name

#         if callback is not None:
#             self.api_updater.connect(callback, Qt.QueuedConnection)


#     def setParameters(self, local_address, trading_socket, client_id=0):
#         self.local_address = local_address
#         self.trading_socket = trading_socket
#         self.client_id = client_id
        
    
#     @pyqtSlot()
#     def run(self):
#         print(f"Datamanagement.run  on {int(QThread.currentThreadId())}")
#         # self.run_ib_client_signal.connect(self.run_ib_client_slot, Qt.QueuedConnection)
        
#         # self.ib_thread = QThread()
#         self.ib_interface = IBConnectivity(self.local_address, self.trading_socket, self.client_id, self.name)
#         # self.ib_interface.moveToThread(self.ib_thread)
#         self.connectSignalsToSlots()
#         # self.ib_thread.started.connect(self.ib_interface.startConnection)
#         print(f"Datamanagement we start with {self.client_id}")
#         # self.run_ib_client_signal.emit()  # Emit a signal to run ib_client in worker thread cofntext
#         # self.ib_thread.start()
#         self.ib_interface.startConnection()

                
#     def printPriority(self, thread_priority):
#             # Print the priority level
#         if thread_priority == QThread.InheritPriority:
#             print("Thread priority: InheritPriority")
#         elif thread_priority == QThread.IdlePriority:
#             print("Thread priority: IdlePriority")
#         elif thread_priority == QThread.LowestPriority:
#             print("Thread priority: LowestPriority")
#         elif thread_priority == QThread.NormalPriority:
#             print("Thread priority: NormalPriority")
#         elif thread_priority == QThread.HighPriority:
#             print("Thread priority: HighPriority")
#         elif thread_priority == QThread.HighestPriority:
#             print("Thread priority: HighestPriority")
#         elif thread_priority == QThread.TimeCriticalPriority:
#             print("Thread priority: TimeCriticalPriority")


#     def connectSignalsToSlots(self):
#         print("SIGNAL CONNECTED TO SLOTS")
#         self.ib_request_signal.connect(self.ib_interface.makeRequest, Qt.QueuedConnection)
#         self.ib_interface.connection_signal.connect(self.relayConnectionStatus, Qt.QueuedConnection)
#         self.ib_interface.latest_price_signal.connect(self.returnLatestPrice, Qt.QueuedConnection)


#     @pyqtSlot(DetailObject)
#     def requestMarketData(self, contractDetails):
#         print(f"Datamanagement.requestMarketData {contractDetails.symbol}")
#         if self.priceReqIsActive:
#             self.ib_request_signal.emit({'type': 'cancelMktData', 'req_id': Constants.STK_PRICE_REQID})

#         contract = Contract()
#         contract.symbol = contractDetails.symbol
        
#         if contractDetails.numeric_id != 0:
#             contract.conId = contractDetails.numeric_id
#         else:
#             contract.currency = Constants.USD
        
#         contract.secType = Constants.STOCK
        
#         if contractDetails.exchange != "":
#             contract.primaryExchange = contractDetails.exchange
#         else:
#             contract.currency = Constants.USD
        
#         contract.exchange = Constants.SMART
#         request = dict()
#         request['type'] = 'reqMktData'
#         request['req_id'] = Constants.STK_PRICE_REQID
#         request['contract'] = contract
#         request['snapshot'] = self.snapshot
#         request['reg_snapshot'] = False
#         self.ib_request_signal.emit(request)
#         self.priceReqIsActive = True


#     @pyqtSlot(float, str)
#     def returnLatestPrice(self, latest_price, tick_type_str):
#         self.previous_price = self.price

#         self.price = latest_price
#         self.api_updater.emit(Constants.UNDERLYING_PRICE_UPDATE, {'price': latest_price, 'type': tick_type_str})


#     @pyqtSlot(str)
#     def relayConnectionStatus(self, status):
#         print(f"DataManagent.relayConnectionStatus {self.name} {status}")
#         self.api_updater.emit(Constants.CONNECTION_STATUS_CHANGED, {'connection_status': status})

