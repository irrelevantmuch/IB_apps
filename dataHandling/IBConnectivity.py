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

from dataHandling.DataStructures import DetailObject
from dataHandling.Constants import Constants
from pubsub import pub
from generalFunctionality.GenFunctions import dateFromString
from threading import Thread, Event
# import logging
# logging.basicConfig(level=logging.DEBUG)


class IBConnectivity(EClient, EWrapper, QObject):

    pacing_break = 0.02
    price_returned = False

    last_req_time = 0

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

    next_id_event = None

    connection_status = Constants.CONNECTION_CLOSED


    def __init__(self, local_address, trading_socket, client_id, name='Unidentified'):
        print(f"IBConnectivity.__init__ {client_id}")
        print(f"IBConnectivity before running {int(QThread.currentThreadId())}")
        self.local_address = local_address
        self.trading_socket = trading_socket
        self.client_id = client_id
        
        EClient.__init__(self, self)
        QObject.__init__(self)

    
    def tickPrice(self, req_id, tickType, price, attrib):
        tick_type_str = TickTypeEnum.to_str(tickType)
        if self.isOptionRequest(req_id):
            self.return_option_price_signal.emit(req_id,tick_type_str, price)
        else:
            self.latest_price_signal.emit(price, tick_type_str)


    # def tickString(self, req_id, tickType, value):
    #     super().tickString(req_id, tickType, value)
    #     tick_type_str = TickTypeEnum.to_str(tickType)
    #     print(f"WTF is this? {tick_type_str}")


    # def tickGeneric(self, req_id, tickType, value):
    #     super().tickGeneric(req_id, tickType, value)
    #     tick_type_str = TickTypeEnum.to_str(tickType)
    #     print(f"WTF is that? {tick_type_str}")

    
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
        self.connection_status = Constants.CONNECTION_OPEN
        self.connection_signal.emit(Constants.CONNECTION_OPEN)
        # QMetaObject.invokeMethod(self.delegate, 'relayConnectionStatus', Qt.QueuedConnection, Q_ARG(str, Constants.CONNECTION_OPEN))


    def connectionClosed(self):
        super().connectionClosed()
        self.connection_status = Constants.CONNECTION_CLOSED
        self.connection_signal.emit(Constants.CONNECTION_CLOSED)
        #QMetaObject.invokeMethod(self.delegate, 'relayConnectionStatus', Qt.QueuedConnection, Q_ARG(str, Constants.CONNECTION_CLOSED))


    def contractDetails(self, req_id, contract_details):
        contract = contract_details.contract
        #print(f"IBConnectivity.contractDetails {req_id} {contract.right} {contract.lastTradeDateOrContractMonth} {contract.strike}")
        
        
        if self.isOptionInfRequest(req_id):
            self.relay_contract_id_signal.emit(contract.right, contract.strike, contract.lastTradeDateOrContractMonth, contract.conId)
            #QMetaObject.invokeMethod(self.delegate, 'relayOptionContractID', Qt.QueuedConnection, Q_ARG(str, contract.right), Q_ARG(float, contract.strike), Q_ARG(str, contract.lastTradeDateOrContractMonth), Q_ARG(int, contract.conId))
        else:
            if contract.primaryExchange == "":
                exchange = contract.exchange
            else:
                exchange = contract.primaryExchange

            detailObject = DetailObject(symbol=contract.symbol, exchange=exchange, long_name=contract_details.longName, numeric_id=contract.conId, currency=contract.currency)
            self.contract_details_signal.emit(detailObject)
            #self.delegate.relayContractDetails(detailObject)
        

    def contractDetailsEnd(self, req_id: int):
        super().contractDetailsEnd(req_id)
        if self.isOptionInfRequest(req_id):

            self.contract_detail_complete_signal.emit(req_id)
        else:
            self.contract_details_finished_signal.emit()


    @pyqtSlot(int, Contract)
    def reqContractDetails(self, req_id, contract):
        super().reqContractDetails(req_id, contract)

        
    def startConnection(self):
        # This method starts the blocking operation in a separate Python thread
        # This is the blocking call within ibapi

        def target():
            self.connect(self.local_address, self.trading_socket, self.client_id)
            self.run()
            
        self.tws_thread = Thread(target=target)
        self.tws_thread.start()
    

    def addContractListener(self, listener):
        self.contractListener = listener


    @pyqtSlot(int, Contract, bool, bool)
    def reqMktData(self, req_id, contract: Contract, snapshot: bool, regulatorySnapshot: bool):
        print(f"IBConnectivity.reqMktData {self.client_id}")
        self.markNewRequest()
        if self.isPriceRequest(req_id):
            self.price_returned = False
        super().reqMktData(req_id, contract, "", snapshot, regulatorySnapshot, [])
        self._active_requests.add(req_id)
        

    def tickSnapshotEnd(self, req_id: int):
        super().tickSnapshotEnd(req_id)
        if req_id in self._active_requests: self._active_requests.remove(req_id)

        self.snapshot_end_signal.emit(req_id)
        

    pyqtSlot(int,Contract,str,str,str,str,int,int,bool,list)
    def reqHistoricalData(self, req_id, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate, chartOptions):
        print(f"IBConnectivity.reqHistoricalData {self.client_id}")
        print(contract.symbol)
        print(f"{endDateTime} {durationStr} {barSizeSetting} {whatToShow} {useRTH} {keepUpToDate}")
        self.markNewRequest()
        super().reqHistoricalData(req_id, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate, chartOptions)
        self._active_requests.add(req_id)
        

    def markNewRequest(self):
        curr_time = QDateTime.currentMSecsSinceEpoch()
        delta_time = curr_time - self.last_req_time
        print(f"****************** {delta_time} {curr_time} {self.last_req_time}")
        self.last_req_time = curr_time
        


    pyqtSlot(int)
    def cancelHistoricalData(self, req_id: int):
        print(f"IBConnectivity.cancelHistoricalData {req_id}")
        self.markNewRequest()
        super().cancelHistoricalData(req_id)
        
    
    @pyqtSlot(int, Contract, str, int, int)
    def reqHeadTimeStamp(req_id, contract, data_type, useRTH: int, formatDate: int):
        print("IBConnectivity.reqHeadTimeStamp")
        self.markNewRequest()
        super().reqHeadTimeStamp(req_id, contract, data_type, formatDate)



    @pyqtSlot()
    def trackAndBindOpenOrders(self):
        print(f"IBConnectivity.trackAndBindOpenOrders {self.client_id}")
        self.markNewRequest()
        self.reqOpenOrders()
        self.reqAutoOpenOrders(True)


    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice) 
        print(f"IBConnectivity.orderStatus")
        print(f"{orderId} {status} {filled} {remaining} {avgFillPrice} {permId} {parentId} {lastFillPrice} {clientId} {whyHeld} {mktCapPrice}")
        self.order_update_signal.emit(orderId, {'status': status, 'filled': filled, 'remaining': remaining})
        

    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        print(f"########### {orderId} {orderState.status}")
        self.order_update_signal.emit(orderId, {'order': order, 'contract': contract, 'status': orderState.status})


    def reqIds(self, numIds):
        print(f"IBConnectivity.reqIds {self.client_id}")
        self.markNewRequest()
        self.next_id_event = Event()
        super().reqIds(numIds)


    def nextValidId(self, orderId):
        print(f"IBConnectivity.nextValidId  {self.client_id}")
        super().nextValidId(orderId)

        self.next_order_ID = orderId
        if self.next_id_event is not None:
            self.next_id_event.set()
            self.next_id_event = None


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


    def securityDefinitionOptionParameter(self, req_id: int, exchange: str, underlyingConId: int, tradingClass: str, multiplier: str, expirations, strikes):
        print(f"IBConnectivity.securityDefinitionOptionParameter {req_id} {exchange}")
        super().securityDefinitionOptionParameter(req_id, exchange, underlyingConId, tradingClass, multiplier, expirations, strikes)
        if exchange == Constants.DEFAULT_OPT_EXC:
            print("We report back")
            self.report_expirations_signal.emit(expirations, strikes)


    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        super().updateAccountValue(key, val, currency, accountName)


    def updatePortfolio(self, contract: Contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):
        super().updatePortfolio(contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName)
        for x in range(10):
            print("NOT IMPLEMENTEDEEDEDEEEDEEDEED")
        

    def updateAccountTime(self, timeStamp: str):
        super().updateAccountTime(timeStamp)


    def accountDownloadEnd(self, accountName: str):
        super().accountDownloadEnd(accountName)
        for x in range(10):
            print("NOooooooooT IMPLEMENTED")
        

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


    def reqPnL(self, req_id: int, account: str, modelCode: str):
        super().reqPnL(req_id, account, modelCode)
        self._active_requests.add(req_id)
        
    def reqPnLSingle(self, req_id: int, account: str, modelCode: str, conId: int):
        super().reqPnLSingle(req_id, account, modelCode, conId)
        self._active_requests.add(req_id)


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

    def getActiveReqCount(self):
        return len(self._active_requests)

    def cancelOrder(self, order_id, str_arg):
        super().cancelOrder(order_id, str_arg)
        print(f"IBConnectivity.CANCELORDER ########### {order_id}")

        