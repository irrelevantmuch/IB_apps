
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


from PyQt5.QtCore import Qt, pyqtSlot
from ibapi.contract import Contract

from .DataStructures import DetailObject
from .Constants import Constants
from .DataManagement import DataManager


from dataHandling.DataStructures import DetailObject
from dataHandling.Constants import Constants


from PyQt5.QtCore import QThread, QObject, Qt, pyqtSignal, pyqtSlot, QTimer
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData
from ibapi.ticktype import TickTypeEnum
from ibapi.account_summary_tags import AccountSummaryTags

from queue import Queue

from dataHandling.DataStructures import DetailObject
from dataHandling.Constants import Constants
from pubsub import pub
from threading import Thread


class IBConnectivity(EClient, EWrapper):
        
    api_updater = pyqtSignal(str, dict)
    
    run_ib_client_signal = pyqtSignal()

    _active_requests = set()

    finished = pyqtSignal()

    _price_req_is_active = False
    snapshot = False

    queue_timer = None

    restart_timer = pyqtSignal()
    next_id_event = None
    latest_price_signal = pyqtSignal(float, str)

    managed_accounts_initialized = False
    next_valid_initialized = False

    _connection_status = Constants.CONNECTION_CLOSED


    def __init__(self, local_address, trading_socket, client_id, name='Unidentified'):
        self.local_address = local_address
        self.trading_socket = trading_socket
        self.client_id = client_id
        self.name = name
        self.request_queue = Queue()

        
        EClient.__init__(self, self)


    ################ General Requests

    @pyqtSlot(DetailObject)
    def requestMarketData(self, contractDetails):
        print(f"IBConnectivityNew.requestMarketData {contractDetails.symbol}")
        if self._price_req_is_active:
            self.makeRequest({'type': 'cancelMktData', 'req_id': Constants.STK_PRICE_REQID})

        contract = Contract()
        contract.symbol = contractDetails.symbol
        
        if contractDetails.numeric_id != 0:
            contract.conId = contractDetails.numeric_id
        else:
            contract.currency = Constants.USD
        
        contract.secType = Constants.STOCK
        
        if contractDetails.exchange != "":
            contract.primaryExchange = contractDetails.exchange
        else:
            contract.currency = Constants.USD
        
        contract.exchange = Constants.SMART
        request = dict()
        request['type'] = 'reqMktData'
        request['req_id'] = Constants.STK_PRICE_REQID
        request['contract'] = contract
        request['snapshot'] = self.snapshot
        request['reg_snapshot'] = False
        self.makeRequest(request)
        self._price_req_is_active = True

    
    ################ General Connection
        
    @pyqtSlot()
    def startConnection(self):
        print(f"{self.name}.startConnection")
        self.setConnectionOptions("+PACEAPI")
        def target():
            self.connect(self.local_address, self.trading_socket, self.client_id)
            self.run()
        
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.processQueue)
        self.restart_timer.connect(self.startProcessingQueue, Qt.QueuedConnection)

        self.tws_thread = Thread(target=target, daemon=True)
        self.tws_thread.start()


    def error(self, message):
        pub.sendMessage('log', message=f"Error: {message}")


    def error(self, req_id, errorCode, errorString, advancedOrderRejectJson=None):
        if req_id == -1:    
            pub.sendMessage('log', message=f"Base message: {errorString}")
        else:
            pub.sendMessage('log', message=f"Error: {req_id}, code: {errorCode}, message: {errorString}, req_id: {req_id}")
        
        if errorCode == 200 or errorCode == 162:
            if self.isOptionRequest(req_id):
                self.option_error_signal.emit(req_id)
            elif self.isPriceRequest(req_id):
                pass
                #What was this for?
                #self.delegate.mktDataError(req_id)

        #if req_id in self._active_requests: self._active_requests.remove(req_id)
            
        
    def connectAck(self):
        super().connectAck()
        self._connection_status = Constants.CONNECTION_OPEN
        self.api_updater.emit(Constants.CONNECTION_STATUS_CHANGED, {'connection_status': Constants.CONNECTION_OPEN})
        print(f"IBConnectivity.connectAck {self.name}({self.client_id}) {int(QThread.currentThreadId())}")
 

    def connectionClosed(self):
        super().connectionClosed()
        self._connection_status = Constants.CONNECTION_CLOSED
        self.api_updater.emit(Constants.CONNECTION_STATUS_CHANGED, {'connection_status': Constants.CONNECTION_CLOSED})
        pub.sendMessage('log', message=f"Connection for {self.name} ({self.client_id}) closed")
        print(f"####@@@@ ###  WE BE CLOSING, but is the thread still running? {self.thread().isRunning()}")
        

    def nextValidId(self, orderId):
        super().nextValidId(orderId)

        self.next_order_ID = orderId

        if self.managed_accounts_initialized:
            if (not self.queue_timer.isActive()) and not(self.request_queue.empty()):
                self.restart_timer.emit()
        self.next_valid_initialized = True
        

    def managedAccounts(self, accountsList: str):
        if self.next_valid_initialized:
            if (not self.queue_timer.isActive()) and not(self.request_queue.empty()):
                self.restart_timer.emit()
        self.managed_accounts_initialized = True
        

    def readyForRequests(self):
        return (self._connection_status == Constants.CONNECTION_OPEN) and self.managed_accounts_initialized and self.next_valid_initialized


    def getActiveReqCount(self):
        return len(self._active_requests)


    ################ Specific Callbacks

    def tickPrice(self, req_id, tickType, price, attrib):
        tick_type_str = TickTypeEnum.to_str(tickType)
        self.latest_price_signal.emit(price, tick_type_str)


    ################ Request processing


    def makeRequest(self, request):
        print(f"IBConnectivtyNew.makeRequest {request['type']}")
        self.request_queue.put(request)
        if (self.queue_timer is not None) and (not (self.queue_timer.isActive())) and self.readyForRequests():
            self.restart_timer.emit()


    @pyqtSlot()
    def startProcessingQueue(self, interval=50):
        self.queue_timer.start(interval)


    @pyqtSlot()
    def processQueue(self):
        if not self.request_queue.empty():
            request = self.request_queue.get_nowait()
            self.processRequest(request)
            self.request_queue.task_done()
        
        if self.request_queue.empty():
            self.queue_timer.stop()


    def processRequest(self, request):
        print(f"IBConnectivtyNew.processRequest {request['type']}")
        req_type = request['type']

        if req_type == 'reqHistoricalData':
            self.reqHistoricalData(request['req_id'], request['contract'], request['end_date'], request['duration'], request['bar_type'], Constants.TRADES, False, 1, request['keep_up_to_date'], [])
        elif req_type == 'cancelHistoricalData':
            self.cancelHistoricalData(request['req_id'])
        elif req_type == 'reqHeadTimeStamp':
            self.reqHeadTimeStamp(request['req_id'], request['contract'], request['data_type'], request['use_rth'], request['format_date'])
        elif req_type == 'reqOpenOrders':
            self.reqOpenOrders()
        elif req_type == 'reqAccountUpdates':
            self.reqAccountUpdates(request['subscribe'], request['account_number'])
        elif req_type == 'reqAutoOpenOrders':
            self.reqAutoOpenOrders(request['reqAutoOpenOrders'])
        elif req_type == 'reqAccountSummary':
            print("IBConnectivity.processRequest")
            self.reqAccountSummary(Constants.ACCOUNT_SUMMARY_REQID, "All", AccountSummaryTags.AccountType)
        elif req_type == 'reqIds':
            self.reqIds(request['num_ids'])
        elif req_type == 'reqSecDefOptParams':
            self.reqSecDefOptParams(request['req_id'], request['symbol'], "", request['equity_type'], request['numeric_id'])
        elif req_type == 'reqRealTimeBars':
            print("IBConnectivtyNew.reqRealTimeBars")
            self.reqRealTimeBars(request['req_id'], request['contract'], 5, "MIDPOINT", False, [])
        elif req_type == 'cancelMktData':
            self.cancelMktData(request['req_id'])
        elif req_type == 'reqGlobalCancel':
            self.reqGlobalCancel()
        elif req_type == 'placeOrder':
            print("IBConnectivtyNew.placeOrder")
            print(type(request['order_id']))
            print(type(request['contract']))
            print(type(request['order']))
            self.placeOrder(request['order_id'], request['contract'], request['order'])
            self.makeRequest({'type': 'reqIds', 'num_ids': -1})
        elif request['type'] == 'cancelOrder':
            self.cancelOrder(request['order_id'], "")
        elif req_type == 'reqMktData':
            self.reqMktData(request['req_id'], request['contract'], "", request['snapshot'], request['reg_snapshot'], [])
        elif req_type == 'reqContractDetails':
            print(type(request['contract']))
            print(request['contract'])
            self.reqContractDetails(request['req_id'], request['contract'])
        
        if 'req_id' in request:
            self._active_requests.add(request['req_id'])

        
    
    ############# REQUEST TYPING


    def isStrikeType(self, req_id):
        return (req_id >= Constants.BASE_OPTION_BUFFER_REQID and req_id < (Constants.BASE_OPTION_BUFFER_REQID + Constants.REQID_STEP))


    def isExpType(self, req_id):
        return (req_id >= Constants.BASE_OPTION_LIVE_REQID and req_id < (Constants.BASE_OPTION_LIVE_REQID + Constants.REQID_STEP))


    def isOptionInfRequest(self, req_id):
        return (req_id >= Constants.OPTION_CONTRACT_DEF_ID and req_id < (Constants.OPTION_CONTRACT_DEF_ID + Constants.REQID_STEP))

    def isOptionRequest(self, req_id):
        return self.isExpType(req_id) or self.isStrikeType(req_id)


    def isPriceRequest(self, req_id):
        return (req_id >= Constants.BASE_MKT_STOCK_REQID and req_id < (Constants.BASE_MKT_STOCK_REQID + Constants.REQID_STEP))


    def isHistDataRequest(self, req_id):
        return (req_id >= Constants.BASE_HIST_DATA_REQID and req_id < (Constants.BASE_HIST_DATA_REQID + Constants.REQID_STEP))


    def isHistBarsRequest(self, req_id):
        return (req_id >= Constants.BASE_HIST_BARS_REQID and req_id < (Constants.BASE_HIST_BARS_REQID + Constants.REQID_STEP))


    def isHistMinMaxRequest(self, req_id):
        return (req_id >= Constants.BASE_HIST_MIN_MAX_REQID and req_id < (Constants.BASE_HIST_MIN_MAX_REQID + Constants.REQID_STEP))


    def isHistoryRequest(self, req_id):
        return (self.isHistMinMaxRequest(req_id) or self.isHistDataRequest(req_id) or self.isHistBarsRequest(req_id))


