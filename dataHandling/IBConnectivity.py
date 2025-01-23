# 
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


from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, pyqtSlot, QTimer


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


class ReqIDManager:

    
    def __init__(self):
        self._open_requests = set()
        self._hist_req_ids = set()       #general log of open history requests, allows for creating unique id's
        self._price_req_ids = set()
        self._option_live_ids = set()
        self._option_buffer_ids = set()
        self._option_contract_ids = set()

        

    def getNextPriceReqID(self):
        if len(self._price_req_ids) == 0:
            next_id = Constants.BASE_PRICE_REQID
        else:
            next_id = max(self._price_req_ids)+1

        self._price_req_ids.add(next_id)
        return next_id


    def getNextOptionLiveID(self):
        if len(self._option_live_ids) == 0:
            next_id = Constants.BASE_OPTION_LIVE_REQID
        else:
            next_id = max(self._option_live_ids)+1

        self._option_live_ids.add(next_id)
        return next_id


    def getNextOptionBufferID(self):
        if len(self._option_buffer_ids) == 0:
            next_id = Constants.BASE_OPTION_BUFFER_REQID
        else:
            next_id = max(self._option_buffer_ids)+1

        self._option_buffer_ids.add(next_id)
        return next_id


    def getNextHistID(self, cancelling_req_ids=set()):
        req_ids_in_use = self._hist_req_ids.union(cancelling_req_ids)
        if len(req_ids_in_use) == 0:
            new_id = Constants.BASE_HIST_DATA_REQID
        else:
            new_id = max(req_ids_in_use) + 1
        
        self._hist_req_ids.add(new_id)     #keep a trace requested but not yet used requests
        return new_id

    
    def getNextOptionContractID(self):
        if len(self._option_contract_ids) == 0:
            next_id = Constants.OPTION_CONTRACT_DEF_ID
        else:
            next_id = max(self._option_contract_ids) + 1

        self._option_contract_ids.add(next_id)
        return next_id
            

    def clearPriceReqID(self, req_id):
        if req_id in self._price_req_ids: self._price_req_ids.remove(req_id)


    def clearHistReqID(self, req_id):
        if req_id in self._hist_req_ids: self._hist_req_ids.remove(req_id)


    def clearHistReqIDs(self, req_ids):
        self._open_requests = self._open_requests - req_ids

    def getAllHistIDs(self):
        return self._hist_req_ids.copy()


    def isActiveHistID(self, req_id):
        return (req_id in self._hist_req_ids)


    def isStrikeType(self, req_id):
        return (req_id >= Constants.BASE_OPTION_BUFFER_REQID and req_id < (Constants.BASE_OPTION_BUFFER_REQID + Constants.REQID_STEP))


    def isExpType(self, req_id):
        return (req_id >= Constants.BASE_OPTION_LIVE_REQID and req_id < (Constants.BASE_OPTION_LIVE_REQID + Constants.REQID_STEP))


    def isOptionRequest(self, req_id):
        return self.isExpType(req_id) or self.isStrikeType(req_id)


    def isLiveReqID(self, req_id):
        return req_id >= Constants.BASE_OPTION_LIVE_REQID and (req_id < Constants.BASE_OPTION_LIVE_REQID + Constants.REQID_STEP)

    
    def isBufferReqID(self, req_id):
        return req_id >= Constants.BASE_OPTION_BUFFER_REQID and (req_id < Constants.BASE_OPTION_BUFFER_REQID + Constants.REQID_STEP)


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


    def addOpenReq(self, req_id):
        self._open_requests.add(req_id)


    def isOpenReqID(self, req_id):
        return (req_id in self._open_requests)


    def clearOpenReqID(self, req_id):
        if req_id in self._open_requests:
            self._open_requests.remove(req_id)

    def getActiveReqCount(self):
        return len(self._open_requests)


    def cleanIfActive(self, req_id):
        if req_id in self._open_requests:
            self._open_requests.remove(req_id)



class IBConnectivity(EClient, EWrapper, QObject):
    
    finished = pyqtSignal()

    api_updater = pyqtSignal(str, dict)
    run_ib_client_signal = pyqtSignal()

    _cont_hist = set()

    req_id_manager = ReqIDManager()

    _active_price_req_id = None
    snapshot = False

    queue_timer = None
    restart_timer_signal = pyqtSignal()
    latest_price_signal = pyqtSignal(float, str)

    _managed_accounts_initialized = False
    _next_valid_initialized = False

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
        if self._active_price_req_id is not None:
            self.makeRequest({'type': 'cancelMktData', 'req_id': self._active_price_req_id})
            self.req_id_manager.clearPriceReqID(self._active_price_req_id)
            self._active_price_req_id = None

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
        
        self._active_price_req_id = self.req_id_manager.getNextPriceReqID()
        contract.exchange = Constants.SMART
        request = dict()
        request['type'] = 'reqMktData'
        request['req_id'] = self._active_price_req_id
        request['contract'] = contract
        request['snapshot'] = self.snapshot
        request['reg_snapshot'] = False
        self.makeRequest(request)

    
    ################ General Connection
        
    @pyqtSlot()
    def startConnection(self):
        # self.setConnectionOptions("+PACEAPI")
        def target():
            print(f"We start the connection on: {int(QThread.currentThreadId())}")
            self.connect(self.local_address, self.trading_socket, self.client_id)
            self.run()
        
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.processQueue)
        self.restart_timer_signal.connect(self.startProcessingQueue, Qt.ConnectionType.QueuedConnection)

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
        print(f"IBConnectivity.error {message}")
        pub.sendMessage('log', message=f"Error: {message}")


    def error(self, req_id, errorCode, errorString, advancedOrderRejectJson=None):
        if req_id == -1:    
            pub.sendMessage('log', message=f"Base message: {errorString}")
        else:
            pub.sendMessage('log', message=f"Error: {req_id}, code: {errorCode}, message: {errorString}, req_id: {req_id}")
        
        if errorCode == 200 or errorCode == 162:
            if self.req_id_manager.isOpenReqID(req_id):
                self.req_id_manager.clearHistReqID(req_id)
            if self.req_id_manager.isPriceRequest(req_id):
                pass
                #What was this for?
                #self.delegate.mktDataError(req_id)
            
        
    def connectAck(self):
        super().connectAck()
        self._connection_status = Constants.CONNECTION_OPEN
        self.api_updater.emit(Constants.CONNECTION_STATUS_CHANGED, {'connection_status': Constants.CONNECTION_OPEN, 'owners': self.owners})
 

    def connectionClosed(self):
        super().connectionClosed()
        self._connection_status = Constants.CONNECTION_CLOSED
        self.api_updater.emit(Constants.CONNECTION_STATUS_CHANGED, {'connection_status': Constants.CONNECTION_CLOSED, 'owners': self.owners})
        pub.sendMessage('log', message=f"Connection for {self.name} ({self.client_id}) closed")
        

    def nextValidId(self, orderId):
        super().nextValidId(orderId)

        self.next_order_ID = orderId

        if self._managed_accounts_initialized:
            if (not self.queue_timer.isActive()) and not(self.request_queue.empty()):
                self.restart_timer_signal.emit()
        self._next_valid_initialized = True
        

    def managedAccounts(self, accountsList: str):
        if self._next_valid_initialized:
            if (not self.queue_timer.isActive()) and not(self.request_queue.empty()):
                self.restart_timer_signal.emit()
        self._managed_accounts_initialized = True
        self.api_updater.emit(Constants.MANAGED_ACCOUNT_LIST, {'account_list': accountsList, 'owners': self.owners})
        

    def readyForRequests(self):
        return (self._connection_status == Constants.CONNECTION_OPEN) and self._managed_accounts_initialized and self._next_valid_initialized


    ################ Specific Callbacks

    def tickPrice(self, req_id, tickType, price, attrib):
        tick_type_str = TickTypeEnum.toStr(tickType)
        self.latest_price_signal.emit(price, tick_type_str)

    def tickSnapshotEnd(self, req_id: int):
        super().tickSnapshotEnd(req_id)
        self.req_id_manager.cleanIfActive(req_id)
        
    ################ Request processing


    def makeRequest(self, request):
        self.request_queue.put(request)
        if (self.queue_timer is not None) and (not (self.queue_timer.isActive())) and self.readyForRequests():
            self.restart_timer_signal.emit()


    @pyqtSlot()
    def startProcessingQueue(self, interval=50):
        self.queue_timer.start(interval)


    @pyqtSlot()
    def processQueue(self):
        print(f"IBConnectivity.processQueue {self.request_queue.qsize()}")
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
            message += f" for {request['contract'].symbol} ({request['bar_type']}) for {request['duration']} with end date {request['end_date'] if request['end_date'] else 'now'} and keep up {request['keep_up_to_date']}"
            self.reqHistoricalData(request['req_id'], request['contract'], request['end_date'], request['duration'], request['bar_type'], Constants.TRADES, request['regular_hours'], 2, request['keep_up_to_date'], [])
            if request['keep_up_to_date']: self._cont_hist.add(request['req_id'])
            self.req_id_manager.addOpenReq(request['req_id'])
        elif req_type == 'cancelHistoricalData':
            if request['req_id'] in self._cont_hist:
                self._cont_hist.remove(request['req_id'])
                self.req_id_manager.clearOpenReqID(request['req_id'])
            self.cancelHistoricalData(request['req_id'])
        elif req_type == 'reqHeadTimeStamp':
            self.reqHeadTimeStamp(request['req_id'], request['contract'], request['data_type'], request['use_rth'], request['format_date'])
            self.req_id_manager.addOpenReq(request['req_id'])
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
            message += f" for {request['symbol']}"
            self.reqSecDefOptParams(request['req_id'], request['symbol'], "", request['equity_type'], request['numeric_id'])
            self.req_id_manager.addOpenReq(request['req_id'])
        elif req_type == 'reqRealTimeBars':
            message += f" for {request['contract'].symbol}"
            self.reqRealTimeBars(request['req_id'], request['contract'], 5, "MIDPOINT", False, [])
            self.req_id_manager.addOpenReq(request['req_id'])
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
            self.req_id_manager.addOpenReq(request['req_id'])
        elif req_type == 'reqContractDetails':
            self.reqContractDetails(request['req_id'], request['contract'])
            self.req_id_manager.addOpenReq(request['req_id'])
        
        pub.sendMessage('log', message=message)
        
    ############# CLEANING ACTIVE REQUESTS    

    def headTimestamp(self, req_id: int, head_time_stamp: str):
        super().headTimestamp(req_id, head_time_stamp)
        self.req_id_manager.cleanIfActive(req_id)


    def historicalDataEnd(self, req_id: int, start: str, end: str):
        super().historicalDataEnd(req_id, start, end)
        if self.req_id_manager.isOpenReqID(req_id) and not(req_id in self._cont_hist): self.req_id_manager.clearOpenReqID(req_id)



    def stopActiveRequests(self, owner_id):
        if self._active_price_req_id is not None:
            self.makeRequest({'type': 'cancelMktData', 'req_id': self._active_price_req_id})
            self.clearPriceReqID(self._active_price_req_id)
            self._active_price_req_id = None


    def stop(self):
        self.api_updater.disconnect()
        self.disconnect()
        if self.tws_thread.is_alive():
            self.tws_thread.join()  # Ensure tws_thread has finished
        

