from PyQt5.QtCore import QThread, QObject, QMetaObject, Qt, Q_ARG, pyqtSignal, pyqtSlot, QTimer, QDateTime
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.common import BarData
from ibapi.ticktype import TickTypeEnum
from pprint import pprint
import inspect

import time

from queue import Queue

from dataHandling.DataStructures import DetailObject
from dataHandling.Constants import Constants
from pubsub import pub
from generalFunctionality.GenFunctions import dateFromString
from threading import Thread, Event
# import logging
# logging.basicConfig(level=logging.DEBUG)


class IBConnectivity(EClient, EWrapper, QObject):

    price_returned = False

    connection_signal = pyqtSignal(str)
    order_update_signal = pyqtSignal(int, dict)

    latest_price_signal = pyqtSignal(float, str)

    contract_details_signal = pyqtSignal(DetailObject)
    contract_details_finished_signal = pyqtSignal()

    historical_bar_signal = pyqtSignal(int, BarData)
    historical_data_end_signal = pyqtSignal(int, str, str)
    history_error = pyqtSignal(int)
    historical_dates_signal = pyqtSignal(int, str)


    option_error_signal = pyqtSignal(int)
    contract_detail_complete_signal = pyqtSignal(int)
    snapshot_end_signal = pyqtSignal(int)
    return_option_price_signal = pyqtSignal(int, str, float)
    report_expirations_signal = pyqtSignal(set, set)
    relay_contract_id_signal = pyqtSignal(str, float, str, int)
    

    run_ib_client_signal = pyqtSignal()

    _active_requests = set()

    restart_timer = pyqtSignal()
    next_id_event = None

    managed_accounts_initialized = False
    next_valid_initialized = False

    _connection_status = Constants.CONNECTION_CLOSED


    def __init__(self, local_address, trading_socket, client_id, name='Unidentified'):
        print(f"IBConnectivity.__init__ {client_id}")
        print(f"IBConnectivity before running {int(QThread.currentThreadId())}")
        self.local_address = local_address
        self.trading_socket = trading_socket
        self.client_id = client_id
        self.name = name
        self.request_queue = Queue()

        
        EClient.__init__(self, self)
        QObject.__init__(self)

    
    ################ General Connection

    def startConnection(self):
        # This method starts the blocking operation in a separate Python thread
        # This is the blocking call within ibapi

        self.setConnectionOptions("+PACEAPI")
        def target():
            self.connect(self.local_address, self.trading_socket, self.client_id)
            self.run()
        
        print(f"IBConnectivity.startConnection {self.name}({self.client_id}) {int(QThread.currentThreadId())}")
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.processQueue)
        self.restart_timer.connect(self.startProcessingQueue, Qt.QueuedConnection)

        self.tws_thread = Thread(target=target, daemon=True)
        self.tws_thread.start()





    def error(self, something):
        print("_____")
        print("KKKKKK")
        print("------")
        print(something)      



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
                print("REIMPLEMENT PLEASE")
                #self.delegate.mktDataError(req_id)
            elif self.isHistoryRequest(req_id):
                self.history_error.emit(req_id)

        #if req_id in self._active_requests: self._active_requests.remove(req_id)
            
        
    def connectAck(self):
        super().connectAck()
        print(f"------$$$$$$$ THE CONNECTION IS ACKNOWLEDGED {self.name}({self.client_id})")
        self._connection_status = Constants.CONNECTION_OPEN
        self.connection_signal.emit(Constants.CONNECTION_OPEN)
        print(f"IBConnectivity.connectAck {self.name}({self.client_id}) {int(QThread.currentThreadId())}")
 

    def connectionClosed(self):
        super().connectionClosed()
        print(f"IBConnectivity.connectionClosed {self.name}({self.client_id})")
        self._connection_status = Constants.CONNECTION_CLOSED
        self.connection_signal.emit(Constants.CONNECTION_CLOSED)
        pub.sendMessage('log', message=f"Connection for {self.name} ({self.client_id}) closed")
        print(f"####@@@@ ###  WE BE CLOSING, but is the thread still running? {self.thread().isRunning()}")
        

    def reqIds(self, numIds):
        print(f"IBConnectivity.reqIds {self.name}({self.client_id}) {numIds}")
        super().reqIds(numIds)


    def nextValidId(self, orderId):
        print(f"IBConnectivity.nextValidId {self.name} {self.client_id} {int(QThread.currentThreadId())}")
        super().nextValidId(orderId)

        self.next_order_ID = orderId

        if self.managed_accounts_initialized:
            if (not self.queue_timer.isActive()) and not(self.request_queue.empty()):
                self.restart_timer.emit()
        self.next_valid_initialized = True
        

    def managedAccounts(self, accountsList: str):
        print(f"IBConnectivity.managedAccounts {self.name}({self.client_id}) {accountsList}")
        if self.next_valid_initialized:
            if (not self.queue_timer.isActive()) and not(self.request_queue.empty()):
                self.restart_timer.emit()
        self.managed_accounts_initialized = True
        

    def readyForRequests(self):
        return (self._connection_status == Constants.CONNECTION_OPEN) and self.managed_accounts_initialized and self.next_valid_initialized

    def contractDetails(self, req_id, contract_details):
        contract = contract_details.contract
        
        if self.isOptionInfRequest(req_id):
            self.relay_contract_id_signal.emit(contract.right, contract.strike, contract.lastTradeDateOrContractMonth, contract.conId)
        else:
            if contract.primaryExchange == "":
                exchange = contract.exchange
            else:
                exchange = contract.primaryExchange

            detailObject = DetailObject(symbol=contract.symbol, exchange=exchange, long_name=contract_details.longName, numeric_id=contract.conId, currency=contract.currency)
            self.contract_details_signal.emit(detailObject)
        

    def contractDetailsEnd(self, req_id: int):
        super().contractDetailsEnd(req_id)
        if self.isOptionInfRequest(req_id):
            self.contract_detail_complete_signal.emit(req_id)
        else:
            self.contract_details_finished_signal.emit()


    def getActiveReqCount(self):
        return len(self._active_requests)



    ################ Request processing


    @pyqtSlot(dict)
    def makeRequest(self, request):
        # print(f"IBConnectivity.makeRequest {self.name}({self.client_id}) {int(QThread.currentThreadId())} {self.queue_timer.isActive()}")
        self.request_queue.put(request)
        # print("------- CHECK IF WE NEED TO START")
        if (not (self.queue_timer.isActive())) and self.readyForRequests():
            # print(f"------- WE START {self.name}({self.client_id}) {int(QThread.currentThreadId())}")
            self.restart_timer.emit()


    @pyqtSlot()
    def startProcessingQueue(self, interval=50):
        # print(f"IBConnectivity.startProcessingQueue {self.name}({self.client_id}) {int(QThread.currentThreadId())}")
        self.queue_timer.start(interval)


    @pyqtSlot()
    def processQueue(self):
        # print(f"IBConnectivity.processQueue {self.name}({self.client_id}) {int(QThread.currentThreadId())}")
        if not self.request_queue.empty():
            request = self.request_queue.get_nowait()
            self.processRequest(request)
            self.request_queue.task_done()
        
        if self.request_queue.empty():
            # print(f"------- WE STOP THE TIMER {self.name}({self.client_id}) {int(QThread.currentThreadId())}")
            self.queue_timer.stop()


    def processRequest(self, request):
        # print(f"IBConnectivity.processRequest {request}")
        req_type = request['type']

        if req_type == 'reqHistoricalData':
            self.reqHistoricalData(request['req_id'], request['contract'], request['end_date'], request['duration'], request['bar_type'], Constants.TRADES, False, 1, request['keep_up_to_date'], [])
        elif req_type == 'cancelHistoricalData':
            self.cancelHistoricalData(request['req_id'])
        elif req_type == 'reqHeadTimeStamp':
            self.reqHeadTimeStamp(request['req_id'], request['contract'], request['data_type'], request['use_rth'], request['format_date'])
        elif req_type == 'reqOpenOrders':
            self.reqOpenOrders()
        elif req_type == 'reqAutoOpenOrders':
            self.reqAutoOpenOrders(request['reqAutoOpenOrders'])
        elif req_type == 'reqIds':
            self.reqIds(request['num_ids'])
        elif req_type == 'reqSecDefOptParams':
            self.reqSecDefOptParams(request['req_id'], request['symbol'], "", request['equity_type'], request['numeric_id'])
            # self.ib_interface.reqSecDefOptParams(1, self.contractDetails.symbol, "", Constants.STOCK, self.contractDetails.numeric_id)
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
            self.reqMktData(request['req_id'], request['contract'], "", request['snapshot'], request['reg_snapshot'], [])
        elif req_type == 'reqContractDetails':
            self.reqContractDetails(request['req_id'], request['contract'])
        
        if 'req_id' in request:
            self._active_requests.add(request['req_id'])

        
    def reqMktData(self, req_id, contract: Contract, genericTickList: str, snapshot: bool, regulatorySnapshot: bool, mktDataOptions):
        print(f"IBConnectivity.reqMktData {self.name} {self.client_id}")
        if self.isPriceRequest(req_id):
            self.price_returned = False
        super().reqMktData(req_id, contract, "", snapshot, regulatorySnapshot, [])
        

    def reqPnL(self, req_id: int, account: str, modelCode: str):
        super().reqPnL(req_id, account, modelCode)
        self._active_requests.add(req_id)
        
    def reqPnLSingle(self, req_id: int, account: str, modelCode: str, conId: int):
        super().reqPnLSingle(req_id, account, modelCode, conId)
        self._active_requests.add(req_id)


    def reqHistoricalData(self, req_id, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate, chartOptions):
        print(f"IBConnectivity.reqHistoricalData {self.name} {self.client_id} {keepUpToDate}")
        super().reqHistoricalData(req_id, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate, chartOptions)
        

    @pyqtSlot()
    def trackAndBindOpenOrders(self):
        print(f"IBConnectivity.trackAndBindOpenOrders {self.client_id}")
        self.makeRequest({'type': 'reqOpenOrders'})
        self.makeRequest({'type': 'reqAutoOpenOrders', 'reqAutoOpenOrders': True})
    

    ################ CALLBACK HANDLING


    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice) 
        print(f"IBConnectivity.orderStatus {self.name}")
        print(f"{orderId} {status} {filled} {remaining} {avgFillPrice} {permId} {parentId} {lastFillPrice} {clientId} {whyHeld} {mktCapPrice}")
        self.order_update_signal.emit(orderId, {'status': status, 'filled': filled, 'remaining': remaining})
        

    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        print(f"########### {orderId} {orderState.status}")
        self.order_update_signal.emit(orderId, {'order': order, 'contract': contract, 'status': orderState.status})


    def securityDefinitionOptionParameter(self, req_id: int, exchange: str, underlyingConId: int, tradingClass: str, multiplier: str, expirations, strikes):
        print(f"IBConnectivity.securityDefinitionOptionParameter {req_id} {exchange}")
        super().securityDefinitionOptionParameter(req_id, exchange, underlyingConId, tradingClass, multiplier, expirations, strikes)
        if exchange == Constants.DEFAULT_OPT_EXC:
            print("We report back")
            self.report_expirations_signal.emit(expirations, strikes)



    def tickSnapshotEnd(self, req_id: int):
        super().tickSnapshotEnd(req_id)
        if req_id in self._active_requests: self._active_requests.remove(req_id)

        self.snapshot_end_signal.emit(req_id)


    def updatePortfolio(self, contract: Contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):
        super().updatePortfolio(contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName)
        for x in range(10):
            print("NOT IMPLEMENTEDEEDEDEEEDEEDEED")
        

    def accountDownloadEnd(self, accountName: str):
        super().accountDownloadEnd(accountName)
        for x in range(10):
            print("NOooooooooT IMPLEMENTED")
        

    def tickPrice(self, req_id, tickType, price, attrib):
        tick_type_str = TickTypeEnum.to_str(tickType)
        if self.isOptionRequest(req_id):
            self.return_option_price_signal.emit(req_id,tick_type_str, price)
        else:
            self.latest_price_signal.emit(price, tick_type_str)



    def historicalData(self, req_id, bar):
        super().historicalData(req_id, bar)
        if self.isHistDataRequest(req_id):
            self.historical_bar_signal.emit(req_id, bar)
                

    def historicalDataUpdate(self, req_id, bar):
        super().historicalDataUpdate(req_id, bar)
        self.historical_bar_signal.emit(req_id, bar)


    def historicalDataEnd(self, req_id: int, start: str, end: str):
        super().historicalDataEnd(req_id, start, end)
        if req_id in self._active_requests: self._active_requests.remove(req_id)

        self.historical_data_end_signal.emit(req_id, start, end)


    
    def pnl(self, req_id: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float):
        super().pnl(req_id, dailyPnL, unrealizedPnL, realizedPnL)
        # self.delegate.updatePNL(req_id, dailyPnL, unrealizedPnL)
        for x in range(10): print("MORE NOT IMPLEMENTED")
        if req_id in self._active_requests: self._active_requests.remove(req_id)
        print("Daily PnL. ReqId: ", req_id, "DailyPnL: ", str(dailyPnL), "UnrealizedPnL: ", str(unrealizedPnL), "RealizedPnL: ", str(realizedPnL))
        self.cancelPnL(req_id)


    def pnlSingle(self, req_id: int, pos: float, dailyPnL: float, unrealizedPnL: float, realizedPnL: float, value: float):
        super().pnlSingle(req_id, pos, dailyPnL, unrealizedPnL, realizedPnL, value)
        #self.delegate.updateSinglePNL(req_id, dailyPnL, unrealizedPnL)
        for x in range(10): print("AGAIN NOT IMPLEMENTED")
        if req_id in self._active_requests: self._active_requests.remove(req_id)
        print("Daily PnL Single. ReqId:", req_id, "Position:", str(pos), "DailyPnL:", str(dailyPnL), "UnrealizedPnL:", str(unrealizedPnL), "RealizedPnL:", str(realizedPnL), "Value:", str(value))
        self.cancelPnLSingle(req_id)


    def accountSummary(self, req_id: int, account: str, tag: str, value: str, currency: str):
        super().accountSummary(req_id, account, tag, value, currency)
        for x in range(10): print("ANOTHEr NOT IMPLEMENTED")
        #self.delegate.returnAccount(account)
        print("AccountSummary. ReqId:", req_id, "Account:", account, "Tag: ", tag, "Value:", value, "Currency:", currency)


    def accountSummaryEnd(self, req_id: int):
        super().accountSummaryEnd(req_id)
        if req_id in self._active_requests: self._active_requests.remove(req_id)
        print("AccountSummaryEnd. ReqId:", req_id)


    def headTimestamp(self, req_id: int, headTimestamp: str):
        super().headTimestamp(req_id, headTimestamp)
        if req_id in self._active_requests: self._active_requests.remove(req_id)
        self.cancelHeadTimeStamp(req_id)
        self.historical_dates_signal.emit(req_id, headTimestamp)

    
    def cancelOrder(self, order_id, str_arg):
        super().cancelOrder(order_id, str_arg)
        print(f"IBConnectivity.CANCELORDER ########### {order_id}")

    
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


        