
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

from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSlot, pyqtSignal, QObject

from ibapi.contract import Contract, ComboLeg
from ibapi.ticktype import TickTypeEnum

from dataHandling.Constants import Constants, OptionConstrType
from dataHandling.IBConnectivity import IBConnectivity

from generalFunctionality.GenFunctions import isRegularTradingHours, getExpirationString, getDaysTillExpiration
from .ComputableOptionFrame import ComputableStrikeFrame, ComputableExpirationFrame
from .ComputableOptionFrame2D import Computable2DDataFrame
from .OptionChainInf import OptionChainInf

from dataHandling.DataStructures import DetailObject

import sys, os

from pytz import timezone
from datetime import datetime


class OptionChainManager(IBConnectivity):

    constr_type = OptionConstrType.single
    option_type = Constants.CALL
    
    _selected_strike = None
    _selected_expiration = None
    
    _strike_option_reqs = set()
    _exp_option_reqs = set()
    _all_option_reqs = set()
    
    _live_data_on = False

    _type_strike_exp_for_req = dict()

    previous_count = 0

    queue_cap = Constants.OPEN_REQUEST_MAX


    def __init__(self, *args):
        super().__init__(*args, name="OptionChainManager")
        self.request_buffer = []

        self._strike_comp_frame = ComputableStrikeFrame(self.option_type)
        self._exp_comp_frame = ComputableExpirationFrame(self.option_type)
        self._all_option_frame = Computable2DDataFrame(self.option_type)
 

    def moveToThread(self, thread):
        self._strike_comp_frame.moveToThread(thread)
        self._exp_comp_frame.moveToThread(thread)
        self._all_option_frame.moveToThread(thread)
        super().moveToThread(thread)


    @pyqtSlot(DetailObject)
    def makeStockSelection(self, contract_details):
        
        self.contract_details = contract_details
        if isRegularTradingHours():
            self.reqMarketDataType(1)
        else:
            self.reqMarketDataType(2)

        uid = contract_details.numeric_id
        self.chain_inf = OptionChainInf(uid)
        
        self.resetOptionBuffer()
        if not self.chain_inf.is_empty:
            self._all_option_frame = self.chain_inf.loadPricesToFrame(self._all_option_frame)
            exp_strings, strikes = self.chain_inf.getContractIdsFromChain()
            self.api_updater.emit(Constants.OPTION_INFO_LOADED, {'expirations': exp_strings, 'strikes': strikes, 'is_verified': True})
            
        self.requestMarketData(self.contract_details)
        
        if self.chain_inf.is_empty:
            self.fetchOptionContracts()
        

    @pyqtSlot(DetailObject)
    def fetchOptionChainInf(self):    
        
            #if the option definitions are too old, we want to refetch
        if self.chain_inf.last_update is not None:
            current_time_stamp = datetime.now(timezone.utc).timestamp()
            if self.chain_inf.last_update < (current_time_stamp - Constants.SECONDS_IN_DAY):
                self.fetchOptionContracts()
            # else:
            #     self.api_updater.emit(Constants.OPTION_INFO_LOADED, {'is_verified': False})
        else:
            self.fetchOptionContracts()


    def resetOptionBuffer(self):
        self._all_option_frame.resetDataFrame()


    ################ Selection interaction

    @pyqtSlot(str, str, str, list, list)
    def structureSelectionChanged(self, option_type, order_type, constr_value, offsets, ratios):
        self.option_type = option_type
        self.order_type = order_type
        self.constr_type = OptionConstrType(constr_value)
        self.offsets = offsets
        self.ratios = ratios
        self._all_option_frame.changeConstrType(option_type, order_type, self.constr_type, offsets, ratios)


    def getBufferedFrame(self): 
        return self._all_option_frame


    def strikeExpInDownloadRange(self, strike, expiration, min_strike, max_strike, min_expiration, max_expiration):
        days_till_exp = getDaysTillExpiration(expiration)
        
        if (strike < min_strike) or (strike > max_strike):
            return False
        if (days_till_exp < min_expiration) or (days_till_exp > max_expiration):
            return False

        return True

    ########Chain info fetching


    def securityDefinitionOptionParameter(self, req_id: int, exchange: str, underlyingConId: int, tradingClass: str, multiplier: str, expirations, strikes):
        super().securityDefinitionOptionParameter(req_id, exchange, underlyingConId, tradingClass, multiplier, expirations, strikes)
        if exchange == Constants.DEFAULT_OPT_EXC:
            self.contract_req_ids = set()
            
            self.exp_set = expirations
            self.strike_set = strikes

            self.api_updater.emit(Constants.OPTION_INFO_LOADED, {'expirations': self.exp_set, 'strikes': self.strike_set, 'is_verified': False})

            self.req_list_exp = []
            for index, expiration in enumerate(expirations):
                next_id = Constants.OPTION_CONTRACT_DEF_ID + index + self.previous_count
                self.req_list_exp.append((next_id, expiration))
                self.contract_req_ids.add(next_id)

            self.total_requests = len(expirations)
            self.previous_count += self.total_requests
            self.api_updater.emit(Constants.PROGRESS_UPDATE, {'total_requests': self.total_requests, 'request_type': 'option chain', 'open_requests': self.total_requests})
            
            # self.req_list_strikes = []
            # for index, strike in enumerate(strikes):
            #     next_id = Constants.OPTION_CONTRACT_DEF_ID + index + self.previous_count
            #     self.req_list_strikes.append((next_id, strike))
            #     self.contract_req_ids.add(next_id)

            # self.total_requests = len(self.req_list_strikes)
            # self.previous_count += self.total_requests
            # self.api_updater.emit(Constants.PROGRESS_UPDATE, {'total_requests': self.total_requests, 'request_type': 'option chain', 'open_requests': self.total_requests})

            self.fetchContractsIds()


    def fetchOptionContracts(self):

        self.chain_inf.resetContractIDs()

        request = dict()
        request['type'] = 'reqSecDefOptParams'
        request['req_id'] = Constants.SEC_DEF_OPTION_PARAM_REQID
        request['symbol'] = self.contract_details.symbol
        request["equity_type"] = Constants.STOCK
        request["numeric_id"] = self.contract_details.numeric_id
        self.makeRequest(request)

    
    def fetchContractsIds(self):
        if len(self.req_list_exp) > 0:
            
            req_id, for_exp = self.req_list_exp.pop()
            # req_id, for_strike = self.req_list_strikes.pop()

                #make the contract
            contract = self.getBaseOptionContract()
            contract.lastTradeDateOrContractMonth = for_exp
            # contract.strike = for_strike
            
                #make request
            request = {'type': 'reqContractDetails', 'req_id': req_id, 'contract': contract}
            self.makeRequest(request)
            

    @pyqtSlot()
    def flushData(self):
        self._all_option_frame.resetDataFrame()
        self.chain_inf.removeSavedPriceInf()


    @pyqtSlot()
    def resetWholeChain(self):
        uid = self.contract_details.numeric_id
        self.chain_inf.removeEntireOptionChain(uid)
        self._all_option_frame.resetDataFrame()
        self.fetchOptionContracts()


    def isLiveReqID(self, req_id):
        return req_id >= Constants.BASE_OPTION_LIVE_REQID and (req_id < Constants.BASE_OPTION_LIVE_REQID + Constants.REQID_STEP)

    
    def isBufferReqID(self, req_id):
        return req_id >= Constants.BASE_OPTION_BUFFER_REQID and (req_id < Constants.BASE_OPTION_BUFFER_REQID + Constants.REQID_STEP)


  ############# Request management

    @pyqtSlot(int)
    def optReqError(self, req_id):
        if req_id in self._exp_option_reqs:
            self._exp_option_reqs.remove(req_id)
        if req_id in self._strike_option_reqs:
            self._strike_option_reqs.remove(req_id)
        if req_id in self._all_option_reqs:
            self._all_option_reqs.remove(req_id)
   


    @pyqtSlot(list, float, float, int, int)
    def requestForAllStrikesAndExpirations(self, option_types, min_strike, max_strike, min_expiration, max_expiration):

        next_req_id = Constants.BASE_OPTION_BUFFER_REQID

        contract_items = self.chain_inf.getContractItems()
        for (opt_type, strike, expiration), contract_id in contract_items:
            if (opt_type in option_types) and self.strikeExpInDownloadRange(strike, expiration, min_strike, max_strike, min_expiration, max_expiration):
                contract = self.getContract(strike, expiration, OptionConstrType.single)
                contract.right = opt_type
                contract.conId = contract_id
                
                self._all_option_reqs.add(next_req_id)

                self._type_strike_exp_for_req[next_req_id] = (opt_type, strike, expiration) #, contract_id)

                self.request_buffer.append({'req_id': next_req_id, 'contract': contract, 'keep_up_to_date': False})
                next_req_id += 1

        self.total_requests = len(self.request_buffer)
        self.api_updater.emit(Constants.PROGRESS_UPDATE, {'request_type': 'price', 'open_requests': len(self._all_option_reqs), 'total_requests': self.total_requests})
        self.iterateOptionRequests(delay=10)



    @pyqtSlot(str)
    @pyqtSlot(str, bool)
    def requestOptionPricesForExpiration(self, for_exp, execute=True):
        print(f"OptionChainManager.requestOptionDataByStrike {for_exp} {execute}")
        self.cancelOptionRequests(for_type=Constants.OPTION_DATA_STRIKE)
        self._selected_expiration = for_exp
        self._strike_comp_frame.resetDataFrame()
        strikes = self.chain_inf.getStrikesFor(for_exp)
        for index, strike in enumerate(strikes):

            contract = self.getContract(strike, for_exp)
            if contract is not None:
                req_id = index + Constants.BASE_OPTION_LIVE_REQID
                self._strike_option_reqs.add(req_id)
                self._type_strike_exp_for_req[req_id] = (None, strike, for_exp)
                self.request_buffer.append({'req_id': req_id, 'contract': contract, 'keep_up_to_date': self._live_data_on})

        if execute:
            self.iterateOptionRequests()


    @pyqtSlot(float)
    @pyqtSlot(float, bool)
    def requestOptionPricesForStrike(self, for_strike, execute=True):
        print(f"OptionChainManager.requestOptionPricesForStrike {for_strike} {execute}")
        self.cancelOptionRequests(for_type=Constants.OPTION_DATA_EXP)
        self._exp_comp_frame.resetDataFrame()
        self._selected_strike = for_strike
        expirations = self.chain_inf.getExpirationsFor(self._selected_strike)

        for index, expiration in enumerate(expirations):

            contract = self.getContract(self._selected_strike, expiration)
            
            if contract is not None:
                req_id = index + int(Constants.BASE_OPTION_LIVE_REQID+Constants.REQID_STEP/2)
                self._exp_option_reqs.add(req_id)
                self._type_strike_exp_for_req[req_id] = (None, for_strike, expiration)
                
                self.request_buffer.append({'req_id': req_id, 'contract': contract, 'keep_up_to_date': self._live_data_on})

        if execute:
            self.iterateOptionRequests()


    def hasQueuedRequests(self):     
        return len(self.request_buffer) > 0


    def iterateOptionRequests(self, delay=20):
        self.timer = QTimer()
        self.timer.timeout.connect(self.executeOptionRequest)
        QTimer.singleShot(0, self.executeOptionRequest)
        self.timer.start(delay)


    def executeOptionRequest(self):
        if self.hasQueuedRequests() and self.getActiveReqCount() < self.queue_cap:
            opt_req = self.request_buffer.pop(0)
            request = dict()
            request['type'] = 'reqMktData'
            request['snapshot'] = True #self.snapshot
            request['reg_snapshot'] = False
            request['req_id'] = opt_req['req_id']
            request['contract'] = opt_req['contract']
            request['keep_up_to_date'] = opt_req['keep_up_to_date']
            self.makeRequest(request)
        if len(self.request_buffer) == 0:
            self.timer.stop()


    def isBufferedRequest(self, req_id):
        return any(req['req_id'] == req_id for req in self.request_buffer)

    def cancelOptionRequests(self, for_type=None):
        if for_type is None or for_type == Constants.OPTION_DATA_STRIKE:
            for req_id in self._strike_option_reqs:
                if req_id in self._active_requests:
                    self.makeRequest({'type': 'cancelMktData', 'req_id': req_id})
                elif self.isBufferedRequest(req_id):
                    self.request_buffer = [req for req in self.request_buffer if req['req_id'] != req_id]
            
            self._strike_option_reqs = set()

        if for_type is None or for_type == Constants.OPTION_DATA_EXP:
            for req_id in self._exp_option_reqs:
                if req_id in self._active_requests:
                    self.makeRequest({'type': 'cancelMktData', 'req_id': req_id})
                elif self.isBufferedRequest(req_id):
                    self.request_buffer = [req for req in self.request_buffer if req['req_id'] != req_id]
            
            self._exp_option_reqs = set()


    ####### Incoming api data management

    def processOptionPrice(self, req_id, tick_type, option_price):
        if option_price != -1.0:
            if tick_type == Constants.BID or tick_type == Constants.ASK or tick_type == Constants.CLOSE:
                if self.isBufferReqID(req_id):
                    self.addTo2dBufferFrame(req_id, option_price, tick_type)
                elif self.isLiveReqID(req_id):
                    self.addToSingularFrame(req_id, option_price, tick_type)


    ######### Price frame management

    def addTo2dBufferFrame(self, req_id, option_price, tick_type):

        (opt_type, strike, expiration) = self._type_strike_exp_for_req[req_id]
        self._all_option_frame.setValueFor(opt_type, (expiration, strike), tick_type, option_price)


    def addToSingularFrame(self, req_id, option_price, tick_type):
        (_, strike, expiration) = self._type_strike_exp_for_req[req_id]
        if (self._selected_expiration is not None) and (expiration == self._selected_expiration):
            self._strike_comp_frame.setValueFor(strike, tick_type, option_price)
        if (self._selected_strike is not None) and (strike == self._selected_strike):
            days_till_exp = getDaysTillExpiration(expiration)
            self._exp_comp_frame.setValueFor(days_till_exp, tick_type, option_price, expiration)
 

    def getStrikeFrame(self): 
        return self._strike_comp_frame


    def getExpirationFrame(self): 
        return self._exp_comp_frame
    

    ###############ECLIENT callbacks

    def tickPrice(self, req_id, tickType, price, attrib):
        tick_type_str = TickTypeEnum.to_str(tickType)
        if self.isOptionRequest(req_id):
            self.processOptionPrice(req_id, tick_type_str, price)
        elif tick_type_str == Constants.LAST:
            self.price = price
            super().tickPrice(req_id, tickType, price, attrib)


    def tickSnapshotEnd(self, req_id: int):
        super().tickSnapshotEnd(req_id)
        self.signalSnapshotEnd(req_id)


    @pyqtSlot(int)
    def signalSnapshotEnd(self, req_id):
        if req_id in self._all_option_reqs:
            self._all_option_reqs.discard(req_id)
            
            if (len(self._all_option_reqs) % 50) == 0:
                self.api_updater.emit(Constants.PROGRESS_UPDATE, {'request_type': 'price', 'open_requests': len(self._all_option_reqs), 'total_requests': self.total_requests})

            if (len(self._all_option_reqs) % 200) == 0:
                self._all_option_frame.setUnderlyingPrice(self.price)

            if len(self._all_option_reqs) % 200 == 0:
                self.chain_inf.updateUnderlyingPrice(self.price)

            if len(self._all_option_reqs) == 0:
                self.chain_inf.writeOptionChain(price_data=self._all_option_frame)
                self.api_updater.emit(Constants.OPTIONS_LOADED, dict())


    def error(self, req_id, errorCode, errorString, advancedOrderRejectJson=None):
        super().error(req_id, errorCode, errorString, advancedOrderRejectJson)
        if errorCode == 200 or errorCode == 162:
            if self.isOptionRequest(req_id):
                self.option_error_signal.emit(req_id)


    def contractDetails(self, req_id, contract_details):
        super().contractDetails(req_id, contract_details)
        contract = contract_details.contract
        if contract.strike != -1 and contract.lastTradeDateOrContractMonth != -1:
            self.chain_inf.addContractID(contract.right, contract.strike, contract.lastTradeDateOrContractMonth, contract.conId)
        

    def contractDetailsEnd(self, req_id: int):
        super().contractDetailsEnd(req_id)
        print("OptionChainManager.contractDetailsEnd")
        self.contract_req_ids.remove(req_id)

        requests_left = len(self.contract_req_ids)
        self.api_updater.emit(Constants.PROGRESS_UPDATE, {'total_requests': self.total_requests, 'request_type': 'option chain', 'open_requests': requests_left})

        if requests_left == 0:

            # if self.openRequests():
            #     self.cancelOptionRequests()

            exp_strings, strikes = self.chain_inf.finalizeChainGathering()

            self.api_updater.emit(Constants.OPTION_INFO_LOADED, {'expirations': exp_strings, 'strikes': strikes, 'is_verified': True})
        else:
            self.fetchContractsIds()


    #############Contract creation for fetching

    def getContract(self, strike, expiration, constr_type=None):
        if constr_type is None:
            constr_type = self.constr_type

        # if constr_type == OptionConstrType.single:
        return self.getSingleContract(strike, expiration)
        # else:
        #     print("DO WE ACTUALLY USE THIS ONE?")
        #     return self.getSpreadContract(strike, expiration)


    def getBaseOptionContract(self):
        contract = Contract()
        contract.symbol = self.contract_details.symbol
        contract.secType = "OPT"
        contract.currency = "USD"
        contract.underlyingConId = self.contract_details.numeric_id
        contract.multiplier = "100"
        contract.exchange = Constants.DEFAULT_OPT_EXC

        return contract

    def getSingleContract(self, strike, expiration):
        contract = self.getBaseOptionContract()
        contract.lastTradeDateOrContractMonth = expiration
        contract.strike = strike
        contract.right = self.option_type
        
        return contract


    # def getSpreadContract(self, strike, expiration):

    #     contract = Contract()
    #     contract.symbol = self.contract_details.symbol
    #     contract.secType = "BAG"
    #     contract.currency = "USD"
    #     contract.exchange = Constants.SMART
    #     # contract.lastTradeDateOrContractMonth = expiration
    #     # contract.right = self.option_type
    #     # contract.multiplier = "100"
        
    #     first_id = self._contract_ids[self.option_type, strike, expiration]
    #     if (self.option_type, strike+self.offsets[0], expiration) in self._contract_ids:
    #         second_id = self._contract_ids[self.option_type, strike+self.offsets[0], expiration]

    #         leg1 = ComboLeg()
    #         leg1.conId = first_id
    #         leg1.ratio = int(1)
    #         leg1.action = Constants.BUY
    #         leg1.exchange = Constants.SMART #Constants.DEFAULT_OPT_EXC
    #         leg2 = ComboLeg()
    #         leg2.conId = second_id
    #         leg2.ratio = int(1)
    #         leg2.action = Constants.SELL
    #         leg2.exchange = Constants.SMART #Constants.DEFAULT_OPT_EXC

    #         contract.comboLegs = [leg1, leg2]
            
    #         return contract
    #     else:
    #         return None



    # @pyqtSlot(str)
    # def orderTypeChangedTo(self, order_type):
    #     print(f"We change the order_type to {order_type}")
    #     self.order_type = order_type
    #     self._all_option_frame.setOrderType(order_type)


    # @pyqtSlot(str)
    # def optionStyleChangedTo(self, option_type):
    #     self.option_type = option_type
    #     self._all_option_frame.setOptionType(option_type)
    #     # if self.expirationsLoaded():
    #     #     self.cancelOptionRequests()
    #     #     self.fetchContractsFor(self.contract_details)

