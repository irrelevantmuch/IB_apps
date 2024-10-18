
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


from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, pyqtSlot, QTimer

from .DataStructures import DetailObject
from .Constants import Constants
# from .DataManagement import DataManager

from dataHandling.DataStructures import DetailObject
from dataHandling.Constants import Constants

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData
from ibapi.ticktype import TickTypeEnum
from ibapi.account_summary_tags import AccountSummaryTags

from queue import Queue
from pubsub import pub
from threading import Thread


class IBConnectivity(EClient, EWrapper, QObject):
    
    finished = pyqtSignal()

    api_updater = pyqtSignal(str, dict)
    run_ib_client_signal = pyqtSignal()
    _active_requests = set()

    
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
        self.owners = set()
        self.local_address = local_address
        self.trading_socket = trading_socket
        self.client_id = client_id
        self.name = name
        self.request_queue = Queue()
        
        EClient.__init__(self, self)
        QObject.__init__(self)
        


    ################ General Requests

    @pyqtSlot(DetailObject)
    def requestMarketData(self, contractDetails):
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
        self.setConnectionOptions("+PACEAPI")
        def target():
            self.connect(self.local_address, self.trading_socket, self.client_id)
            self.run()
        
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.processQueue)
        self.restart_timer.connect(self.startProcessingQueue, Qt.QueuedConnection)

        self.tws_thread = Thread(target=target, daemon=True)
        self.tws_thread.start()


    def registerOwner(self):
        if len(self.owners) == 0:
            self.owners.add(0)
            return 0
        else:
            new_owner = max(self.owners) + 1
            self.owners.add(new_owner)
            return new_owner


    def deregisterOwner(self, owner_id):
        self.stopActiveRequests(owner_id)
        self.owners.remove(owner_id)


    @property
    def owner_count(self):
        return len(self.owners)

    def error(self, message):
        pub.sendMessage('log', message=f"Error: {message}")


    def error(self, req_id, errorCode, errorString, advancedOrderRejectJson=None):
        if req_id == -1:    
            pub.sendMessage('log', message=f"Base message: {errorString}")
        else:
            pub.sendMessage('log', message=f"Error: {req_id}, code: {errorCode}, message: {errorString}, req_id: {req_id}")
        
        if errorCode == 200 or errorCode == 162:
            self._active_requests.remove(req_id)
            if self.isPriceRequest(req_id):
                pass
                #What was this for?
                #self.delegate.mktDataError(req_id)

        #if req_id in self._active_requests: self._active_requests.remove(req_id)
            
        
    def connectAck(self):
        super().connectAck()
        self._connection_status = Constants.CONNECTION_OPEN
        self.api_updater.emit(Constants.CONNECTION_STATUS_CHANGED, {'connection_status': Constants.CONNECTION_OPEN})
 

    def connectionClosed(self):
        super().connectionClosed()
        self._connection_status = Constants.CONNECTION_CLOSED
        self.api_updater.emit(Constants.CONNECTION_STATUS_CHANGED, {'connection_status': Constants.CONNECTION_CLOSED})
        pub.sendMessage('log', message=f"Connection for {self.name} ({self.client_id}) closed")
        

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

    def tickSnapshotEnd(self, req_id: int):
        super().tickSnapshotEnd(req_id)
        if req_id in self._active_requests:
            self._active_requests.remove(req_id)

    ################ Request processing


    def makeRequest(self, request):
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
        req_type = request['type']

        message = f"Process ({request['req_id'] if 'req_id' in request else '-'}): {request['type']}"

        if req_type == 'reqHistoricalData':
            message += f"for {request['contract'].symbol} ({request['bar_type']}) for {request['duration']} with end date {request['end_date'] if request['end_date'] else 'now'} and keep up {request['keep_up_to_date']}"
            self.reqHistoricalData(request['req_id'], request['contract'], request['end_date'], request['duration'], request['bar_type'], Constants.TRADES, request['regular_hours'], 2, request['keep_up_to_date'], [])
            self._active_requests.add(request['req_id'])
        elif req_type == 'cancelHistoricalData':
            self.cancelHistoricalData(request['req_id'])
        elif req_type == 'reqHeadTimeStamp':
            self.reqHeadTimeStamp(request['req_id'], request['contract'], request['data_type'], request['use_rth'], request['format_date'])
            self._active_requests.add(request['req_id'])
        elif req_type == 'reqOpenOrders':
            self.reqOpenOrders()
        elif req_type == 'reqAccountUpdates':
            self.reqAccountUpdates(request['subscribe'], request['account_number'])
        elif req_type == 'reqAutoOpenOrders':
            self.reqAutoOpenOrders(request['reqAutoOpenOrders'])
        elif req_type == 'reqAccountSummary':
            self.reqAccountSummary(Constants.ACCOUNT_SUMMARY_REQID, "All", AccountSummaryTags.AccountType)
        elif req_type == 'reqIds':
            self.reqIds(request['num_ids'])
        elif req_type == 'reqSecDefOptParams':
            message += f"for {request['symbol']}"
            self.reqSecDefOptParams(request['req_id'], request['symbol'], "", request['equity_type'], request['numeric_id'])
            self._active_requests.add(request['req_id'])
        elif req_type == 'reqRealTimeBars':
            message += f"for {request['contract'].symbol}"
            self.reqRealTimeBars(request['req_id'], request['contract'], 5, "MIDPOINT", False, [])
            self._active_requests.add(request['req_id'])
        elif req_type == 'cancelMktData':
            self.cancelMktData(request['req_id'])
        elif req_type == 'reqGlobalCancel':
            self.reqGlobalCancel()
        elif req_type == 'placeOrder':
            self.placeOrder(request['order_id'], request['contract'], request['order'])
            self.makeRequest({'type': 'reqIds', 'num_ids': -1})
        elif request['type'] == 'cancelOrder':
            self.cancelOrder(request['order_id'], "")
        elif req_type == 'reqMktData':
            message += f" {request['contract'].symbol}"
            if request['contract'].secType == "OPT":
                message += f" at strike {request['contract'].strike} with expiration {request['contract'].lastTradeDateOrContractMonth}"
            self.reqMktData(request['req_id'], request['contract'], "", request['snapshot'], request['reg_snapshot'], [])
            self._active_requests.add(request['req_id'])
        elif req_type == 'reqContractDetails':
            self.reqContractDetails(request['req_id'], request['contract'])
            self._active_requests.add(request['req_id'])
        
        pub.sendMessage('log', message=message)
        
    ############# CLEANING ACTIVE REQUESTS    

    def headTimestamp(self, req_id: int, head_time_stamp: str):
        super().headTimestamp(req_id, head_time_stamp)
        if req_id in self._active_requests: self._active_requests.remove(req_id)


    def historicalDataEnd(self, req_id: int, start: str, end: str):
        super().historicalDataEnd(req_id, start, end)
        if req_id in self._active_requests: self._active_requests.remove(req_id)


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


    def stopActiveRequests(self, owner_id):
        if self._price_req_is_active:
            self.makeRequest({'type': 'cancelMktData', 'req_id': Constants.STK_PRICE_REQID})


    def stop(self):
        self.api_updater.disconnect()
        self.disconnect()
        if self.tws_thread.is_alive():
            self.tws_thread.join()  # Ensure tws_thread has finished
        

