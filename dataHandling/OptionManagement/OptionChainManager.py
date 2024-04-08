
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

from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSlot, pyqtSignal

from ibapi.contract import Contract, ComboLeg

from dataHandling.Constants import Constants, OptionConstrType
import pandas as pd
from dataHandling.DataStructures import DetailObject
from math import ceil
from datetime import datetime

import sys, os, pickle
import numpy as np
import time
from pytz import timezone

from operator import attrgetter

from dataHandling.DataManagement import DataManager

from generalFunctionality.GenFunctions import isRegularTradingHours

from .ComputableOptionFrame import ComputableStrikeFrame, ComputableExpirationFrame
from .ComputableOptionFrame2D import Computable2DDataFrame, ReadOnlyFrameWrapper


class OptionChainManager(DataManager):

    constr_type = OptionConstrType.single
    _expirations = []
    _strikes = np.array([])
    _contract_ids = dict()
    _exp_selection = 0
    _selected_strike = None
    _selected_expiration = None
    _strike_option_reqs = set()
    _exp_option_reqs = set()
    _all_option_reqs = set()
    _strike_exp_for_req = dict()
    _type_strike_exp_for_req = dict()

    previous_count = 0

    min_strike = None
    max_strike = None
    min_expiration  = None
    max_expiration = None


    contract_def_ids = set()

    mostly_threshold = 0.2

    _strike_data_frame = None
    _exp_data_frame = None

    _all_prices_frame = dict()

    fetching_all = False
    strike_frame_reset = False

    request_buffer = []

    contract_detail_request = pyqtSignal(int, Contract)

    queue_cap = Constants.OPEN_REQUEST_MAX

    option_type = Constants.CALL


    def __init__(self, callback=None):
        super().__init__(callback, name="OptionChainManager")

        self.strike_comp_frame = ComputableStrikeFrame(None, self.option_type)
        self.exp_comp_frame = ComputableExpirationFrame(None, self.option_type)
        self.all_option_frame = Computable2DDataFrame(None, self.option_type)
 

    def moveToThread(self, thread):
        self.strike_comp_frame.moveToThread(thread)
        self.exp_comp_frame.moveToThread(thread)
        self.exp_comp_frame.moveToThread(thread)
        super().moveToThread(thread)


    @pyqtSlot(DetailObject)
    @pyqtSlot(DetailObject, bool)
    def makeStockSelection(self, contractDetails, active_management=True):
        print("OptionChainManager.makeStockSelection")

        self.contractDetails = contractDetails
        if isRegularTradingHours():
            self.ib_interface.reqMarketDataType(1)
            self.live_data_on = True
        else:
            self.ib_interface.reqMarketDataType(2)
            self.live_data_on = False

        uid = contractDetails.numeric_id
        if active_management: 
            
            self.option_chain = self.readOptionChainInfo(uid)
            self.resetDataAndRequests()
            if len(self.option_chain) > 0:
                self.loadPricesFromFrame(uid)
                self.getContractIdsFromChain()
            
            self.requestMarketData(self.contractDetails)
        
            if len(self.option_chain) == 0:
                self.fetchOptionContracts()
        else:
            self.option_chain = self.readOptionChainInfo(uid)
            if 'timestamp' in self.option_chain:
                current_time_stamp = datetime.now(timezone(Constants.NYC_TIMEZONE)).timestamp()
                if self.option_chain['timestamp'] < (current_time_stamp - Constants.SECONDS_IN_DAY):
                    self.fetchOptionContracts()
                else:
                    self.api_updater.emit(Constants.OPTION_INFO_LOADED, dict())
            else:
                self.fetchOptionContracts()


    def getStrikeFrame(self): 
        return ReadOnlyFrameWrapper(self.strike_comp_frame)


    def getExpirationFrame(self): 
        return ReadOnlyFrameWrapper(self.strike_comp_frame)
    

    def getBufferedFrame(self): 
        return ReadOnlyFrameWrapper(self.all_option_frame)
    

    def resetDataAndRequests(self):
        self.all_option_frame.setData(None)
        self._all_prices_frame = dict()
        index = pd.MultiIndex.from_tuples([], names=['days_till_exp', 'strike'])
        self._all_prices_frame[Constants.PUT] = pd.DataFrame({Constants.BID: pd.Series(dtype='float'), Constants.ASK: pd.Series(dtype='float'), Constants.CLOSE: pd.Series(dtype='float')}, index=index)
        self._all_prices_frame[Constants.CALL] = pd.DataFrame({Constants.BID: pd.Series(dtype='float'), Constants.ASK: pd.Series(dtype='float'), Constants.CLOSE: pd.Series(dtype='float')}, index=index)


    def loadPricesFromFrame(self, uid):
        print(f"OptionChainManager.loadPricesFromFrame {int(QThread.currentThreadId())}")
        if len(self.option_chain) > 0:
            expirations_to_remove = []
            chain_dict = self.option_chain['chains']

            for opt_type in chain_dict.keys():
                for expiration in chain_dict[opt_type].keys():
                    days_till_exp = self.getDaysTillExpiration(expiration)
                    if days_till_exp < 0:
                        expirations_to_remove.append((opt_type, expiration))
                    else:
                        for strike in chain_dict[opt_type][expiration].keys():
                            for tick_type in [Constants.BID, Constants.ASK, Constants.CLOSE]:
                                if tick_type in chain_dict[opt_type][expiration][strike]:
                                    self._all_prices_frame[opt_type].loc[(days_till_exp, strike), tick_type] = float(chain_dict[opt_type][expiration][strike][tick_type])

            for (opt_type, expiration) in expirations_to_remove:
                del self.option_chain['chains'][opt_type][expiration]


            if not(self._all_prices_frame[Constants.PUT].empty and self._all_prices_frame[Constants.CALL].empty):
                if 'underlying_price' in self.option_chain:
                    self.all_option_frame.setUnderlyingPrice(self.option_chain['underlying_price'])
                self.all_option_frame.setData(self._all_prices_frame)

                self.api_updater.emit(Constants.OPTIONS_LOADED, dict())


    def getContractIdsFromChain(self):
        self._contract_ids = dict()
        for opt_type in [Constants.CALL, Constants.PUT]:
            expiration_strings = list(self.option_chain['chains'][opt_type].keys())
            self.setExpirationsFrom(expiration_strings)
            
            strikes = set()
            for exp_str in expiration_strings:
                float_strikes = set(map(float, self.option_chain['chains'][opt_type][exp_str].keys()))
                strikes.update(float_strikes)
                for strike in self.option_chain['chains'][opt_type][exp_str].keys():
                    self._contract_ids[opt_type, strike, exp_str] = self.option_chain['chains'][opt_type][exp_str][strike]['con_id']

                self._strikes = list(strikes)
        self.api_updater.emit(Constants.OPTION_INFO_LOADED, {'expirations': expiration_strings, 'strikes': list(strikes)})


    @pyqtSlot(int, str, float)
    def returnOptionPrice(self, req_id, tick_type, option_price):
        if option_price != -1.0:
            if tick_type == Constants.BID or tick_type == Constants.ASK or tick_type == Constants.CLOSE: # or tick_type == Constants.LAST:
                if self.isBufferRequest(req_id):
                    self.addToBufferFrame(req_id, option_price, tick_type)
                elif self.isLiveRequest(req_id):
                    self.addToLiveFrame(req_id, option_price, tick_type)


    def addToBufferFrame(self, req_id, option_price, tick_type):

        (opt_type, strike, expiration, contract_id) = self._type_strike_exp_for_req[req_id]
        self.option_chain['chains'][opt_type][expiration][strike][tick_type] = option_price

        days_till_exp = self.getDaysTillExpiration(expiration)
        self._all_prices_frame[opt_type].loc[(days_till_exp, strike), tick_type] = option_price
        self._all_prices_frame[opt_type].loc[(days_till_exp, strike), 'contract_id'] = contract_id
        self._all_prices_frame[opt_type].loc[(days_till_exp, strike), Constants.EXPIRATIONS] = expiration
        self._all_prices_frame[opt_type].loc[(days_till_exp, strike), Constants.NAMES] = self.getExpirationString(expiration)
        
        # print(f"We got {len(self._all_option_reqs)} lefty")

        
    def addToLiveFrame(self, req_id, option_price, tick_type):
        (strike, expiration) = self._strike_exp_for_req[req_id]
        if (self._selected_expiration is not None) and (expiration == self._selected_expiration):
            self._strike_data_frame.loc[strike, tick_type] = option_price
            self._strike_data_frame.sort_index(inplace=True)
            self.strike_comp_frame.setData(self._strike_data_frame)
        if (self._selected_strike is not None) and (strike == self._selected_strike):
            days_till_exp = self.getDaysTillExpiration(expiration)
            self._exp_data_frame.loc[days_till_exp, tick_type] = option_price
            self._exp_data_frame.loc[days_till_exp, Constants.EXPIRATIONS] = expiration
            self._exp_data_frame.loc[days_till_exp, Constants.NAMES] = self.getExpirationString(expiration)
            self._exp_data_frame.sort_index(inplace=True)
            self.exp_comp_frame.setData(self._exp_data_frame)
 

    def isLiveRequest(self, req_id):
        return req_id >= Constants.BASE_OPTION_LIVE_REQID and (req_id < Constants.BASE_OPTION_LIVE_REQID + Constants.REQID_STEP)

    
    def isBufferRequest(self, req_id):
        return req_id >= Constants.BASE_OPTION_BUFFER_REQID and (req_id < Constants.BASE_OPTION_BUFFER_REQID + Constants.REQID_STEP)



    @pyqtSlot()
    def fetchOptionContracts(self):
        print(f"OptionChainManager.fetchOptionContracts")
        self._contract_ids = dict()

        request = dict()
        request['type'] = 'reqSecDefOptParams'
        request['req_id'] = Constants.SEC_DEF_OPTION_PARAM_REQID
        request['symbol'] = self.contractDetails.symbol
        request["equity_type"] = Constants.STOCK
        request["numeric_id"] = self.contractDetails.numeric_id
        self.ib_request_signal.emit(request)
        # self.ib_interface.reqSecDefOptParams(1, self.contractDetails.symbol, "", Constants.STOCK, self.contractDetails.numeric_id)

    
    def setExpirationsFrom(self, expirations_ib_str):
        days_till_exp = [self.getDaysTillExpiration(exp) for exp in expirations_ib_str]
        date_to_days = dict(zip(expirations_ib_str, days_till_exp))
        # Sort unique_values using the date_to_days mapping
        self._expirations = sorted(expirations_ib_str, key=lambda x: date_to_days[x])
        


    @pyqtSlot(set, set)
    def reportBackExpirations(self, expiration_set, strike_set):
            print(f"OptionChainManager.reportBackExpirations {int(QThread.currentThreadId())}")
            self.contract_def_ids = set()
            
            # self.expiration_set = []
            # for index, expiration in enumerate(expiration_set):
            #     next_id = Constants.OPTION_CONTRACT_DEF_ID + index + self.previous_count
            #     self.expiration_set.append((next_id, expiration))
            #     self.contract_def_ids.add(next_id)

            # self.total_requests = len(expiration_set)
            # self.previous_count += self.total_requests
            # self.api_updater.emit(Constants.PROGRESS_UPDATE, {'total_requests': self.total_requests, 'request_type': 'option chain', 'open_requests': self.total_requests})
            
            self.strike_set = []
            for index, strike in enumerate(strike_set):
                next_id = Constants.OPTION_CONTRACT_DEF_ID + index + self.previous_count
                self.strike_set.append((next_id, strike))
                self.contract_def_ids.add(next_id)

            self.total_requests = len(strike_set)
            self.previous_count += self.total_requests
            self.api_updater.emit(Constants.PROGRESS_UPDATE, {'total_requests': self.total_requests, 'request_type': 'option chain', 'open_requests': self.total_requests})

            self.fetchContractsIds()
            

    def fetchContractsIds(self):
        if len(self.strike_set) > 0:
            req_id, for_strike = self.strike_set.pop()
            print(f"We are requesting expirations for {for_strike} {self.contractDetails.symbol} {req_id}")
            contract = Contract()
            contract.symbol = self.contractDetails.symbol
            contract.secType = "OPT"
            contract.currency = "USD"
            contract.underlyingConId = self.contractDetails.numeric_id
            print(f"We add the following id: {self.contractDetails.numeric_id}")
            contract.multiplier = "100"
            contract.exchange = Constants.DEFAULT_OPT_EXC
                #contract.lastTradeDateOrContractMonth = for_exp
            contract.strike = for_strike
            print(f"DID THIS DIE? {req_id} {contract}")
            request = dict()
            request['type'] = 'reqContractDetails'
            request['req_id'] = req_id
            request['contract'] = contract
            self.ib_request_signal.emit(request)
            #self.contract_detail_request.emit(req_id, contract)
            

    def openRequests(self):
        return len(self._strike_option_reqs) or len(self._exp_option_reqs)


    def getExpirations(self):
        return self._expirations

    def getExpirationString(self, expiration_date):
        datetime_obj = datetime.strptime(expiration_date, '%Y%m%d')
        return datetime_obj.date().strftime("%d %B %Y")


    def getExpirationAt(self, index):
        print(f"OptionChainManager.getExpirationAt {self._expirations[index]} for {index}")
        print(self._expirations)
        return self._expirations[index]


    def expirationsLoaded(self):
        return len(self._expirations) !=0


    @pyqtSlot(int)
    def optReqError(self, req_id):
        if req_id in self._exp_option_reqs:
            self._exp_option_reqs.remove(req_id)
        if req_id in self._strike_option_reqs:
            self._strike_option_reqs.remove(req_id)
        if req_id in self._all_option_reqs:
            self._all_option_reqs.remove(req_id)
   
    
    def connectSignalsToSlots(self):
        super().connectSignalsToSlots()
        self.ib_interface.contract_detail_complete_signal.connect(self.contractDetailsCompleted, Qt.QueuedConnection)
        self.ib_interface.snapshot_end_signal.connect(self.signalSnapshotEnd, Qt.QueuedConnection)
        self.ib_interface.return_option_price_signal.connect(self.returnOptionPrice, Qt.QueuedConnection)
        self.ib_interface.report_expirations_signal.connect(self.reportBackExpirations, Qt.QueuedConnection)
        self.ib_interface.relay_contract_id_signal.connect(self.relayOptionContractID, Qt.QueuedConnection)
        self.ib_interface.option_error_signal.connect(self.optReqError, Qt.QueuedConnection)


    # @pyqtSlot(str)
    # def orderTypeChangedTo(self, order_type):
    #     print(f"We change the order_type to {order_type}")
    #     self.order_type = order_type
    #     self.all_option_frame.setOrderType(order_type)


    # @pyqtSlot(str)
    # def optionStyleChangedTo(self, option_type):
    #     self.option_type = option_type
    #     self.all_option_frame.setOptionType(option_type)
    #     # if self.expirationsLoaded():
    #     #     self.cancelOptionRequests()
    #     #     self.fetchContractsFor(self.contractDetails)


    @pyqtSlot(str, str, str, list, list)
    def structureSelectionChanged(self, option_type, order_type, constr_value, offsets, ratios):
        self.option_type = option_type
        self.order_type = order_type
        self.constr_type = OptionConstrType(constr_value)
        self.offsets = offsets
        self.ratios = ratios
        self.all_option_frame.changeConstrType(option_type, order_type, self.constr_type, offsets, ratios)



    def getDaysTillExpiration(self, expiration_date):
        #TODO This one is called an aweful lot
        datetime_obj = datetime.strptime(expiration_date, '%Y%m%d').date()
        today = datetime.now(timezone(Constants.NYC_TIMEZONE)).date()
        return (datetime_obj - today).days


    def updateExpirationSelection(self, to_value):
        if self.expirationsLoaded() and self.newExpSelection(to_value):
            self._exp_selection = to_value
            self.cancelOptionRequests()
            self.requestOptionDataByStrike(self.option_type)


    def cancelOptionRequests(self, for_type=None):
        print("TODO: FIX THIS ONCE WE HAVE SORTED WHAT WE WANTEd")
        if for_type is None or for_type == Constants.OPTION_DATA_STRIKE:
            for req_id in self._strike_option_reqs:
                self.ib_request_signal.emit({'type': 'cancelMktData', 'req_id': req_id})
            self._strike_option_reqs = set()

        if for_type is None or for_type == Constants.OPTION_DATA_EXP:
            for req_id in self._exp_option_reqs:
                self.ib_request_signal.emit({'type': 'cancelMktData', 'req_id': req_id})
            self._exp_option_reqs = set()
    

    def newExpSelection(self, value):
        return (value != self._exp_selection) and value >= 0


    def getContract(self, strike, expiration, constr_type=None):

        if constr_type is None:
            constr_type == self.constr_type

        if constr_type == OptionConstrType.single:
            return self.getSingleContract(strike, expiration)
        else:
            return self.getSpreadContract(strike, expiration)


    def getSingleContract(self, strike, expiration):
        contract = Contract()
        contract.symbol = self.contractDetails.symbol
        contract.secType = "OPT"
        contract.lastTradeDateOrContractMonth = expiration
        contract.strike = strike
        contract.multiplier = "100"
        contract.right = self.option_type
        contract.exchange = Constants.SMART
        return contract


    def getSpreadContract(self, strike, expiration):

        contract = Contract()
        contract.symbol = self.contractDetails.symbol
        contract.secType = "BAG"
        contract.currency = "USD"
        contract.exchange = Constants.SMART
        # contract.lastTradeDateOrContractMonth = expiration
        # contract.right = self.option_type
        # contract.multiplier = "100"
        
        first_id = self._contract_ids[self.option_type, strike, expiration]
        if (self.option_type, strike+self.offsets[0], expiration) in self._contract_ids:
            second_id = self._contract_ids[self.option_type, strike+self.offsets[0], expiration]

            leg1 = ComboLeg()
            leg1.conId = first_id
            leg1.ratio = int(1)
            leg1.action = Constants.BUY
            leg1.exchange = Constants.SMART #Constants.DEFAULT_OPT_EXC
            leg2 = ComboLeg()
            leg2.conId = second_id
            leg2.ratio = int(1)
            leg2.action = Constants.SELL
            leg2.exchange = Constants.SMART #Constants.DEFAULT_OPT_EXC

            contract.comboLegs = [leg1, leg2]
            
            return contract
        else:
            return None



    @pyqtSlot(str)
    @pyqtSlot(str, bool)
    def requestOptionDataForExpiration(self, for_exp, execute=True):
        # print("OptionChainManager.requestOptionDataByStrike")
        self._strike_data_frame = pd.DataFrame({Constants.BID: pd.Series(dtype='float'), Constants.ASK: pd.Series(dtype='float'), Constants.CLOSE: pd.Series(dtype='float')})
        self._selected_expiration = for_exp
        strikes = self.getStrikesFor(for_exp)
        # print(f"We check these strikes: {strikes}")
        for index, strike in enumerate(strikes):

            contract = self.getContract(strike, for_exp)
            if contract is not None:
                req_id = index + Constants.BASE_OPTION_LIVE_REQID
                self._strike_option_reqs.add(req_id)
                self._strike_exp_for_req[req_id] = (strike, for_exp)
                self.request_buffer.append(OptionRequest(req_id, contract,(not self.live_data_on)))

        if execute:
            self.iterateOptionRequests()


    @pyqtSlot(float)
    @pyqtSlot(float, bool)
    def requestOptionDataForStrike(self, for_strike, execute=True):

        # print(f"OptionChainManager.requestOptionDataForStrike {for_strike}")

        self.cancelOptionRequests(for_type=Constants.OPTION_DATA_EXP)
        self._selected_strike = for_strike

        self._exp_data_frame = pd.DataFrame( {Constants.BID: pd.Series(dtype='float'), Constants.ASK: pd.Series(dtype='float'), Constants.CLOSE: pd.Series(dtype='float'), Constants.NAMES: pd.Series(dtype="string"), Constants.EXPIRATIONS: pd.Series(dtype='datetime64[ns]')})

        expirations = self.getExpirationsFor(self._selected_strike)
        # print(f"We check these expirations: {expirations}")
        for index, expiration in enumerate(expirations):

            contract = self.getContract(self._selected_strike, expiration)
            
            if contract is not None:
                req_id = index + int(Constants.BASE_OPTION_LIVE_REQID+Constants.REQID_STEP/2)
                self._exp_option_reqs.add(req_id)
                self._strike_exp_for_req[req_id] = (for_strike, expiration)
                self.request_buffer.append(OptionRequest(req_id, contract,(not self.live_data_on)))

        if execute:
            self.iterateOptionRequests()


    def resetWholeChain(self):
        uid = self.contractDetails.numeric_id
        self.removeSavedOptionInfo(uid)
        self.option_chain = dict()
        self.all_option_frame.setData(None)
        self.fetchOptionContracts()


    def flushData(self):
        print("We flush the data")
        self.resetDataAndRequests()

        uid = self.contractDetails.numeric_id
        if len(self.option_chain) > 0:

            chain_dict = self.option_chain['chains']

            for opt_type in chain_dict.keys():
                for expiration in chain_dict[opt_type].keys():
                    for strike in chain_dict[opt_type][expiration].keys():
                        for tick_type in [Constants.BID, Constants.ASK, Constants.CLOSE]:
                            if tick_type in chain_dict[opt_type][expiration][strike]:
                                del self.option_chain['chains'][opt_type][expiration][strike][tick_type]

            self.all_option_frame.setData(None)
        self.writeOptionChain(self.contractDetails.numeric_id)



    def checkStrikeExpInRange(self, strike, expiration):
        days_till_exp = self.getDaysTillExpiration(expiration)
        
        if self.min_strike is not None and strike < self.min_strike:
            return False
        if self.max_strike is not None and strike > self.max_strike:
            return False
        if self.min_expiration is not None and days_till_exp < self.min_expiration:
            return False
        if self.max_expiration is not None and days_till_exp > self.max_expiration:
            return False

        return True


    @pyqtSlot(float)
    def setMinimumStrike(self, minimum_strike):
        print(f"We set strike minimum to: {minimum_strike}")
        self.min_strike = minimum_strike
    
    @pyqtSlot(float)
    def setMaximumStrike(self, maximum_strike):
        print(f"We set strike maximum to: {maximum_strike}")
        self.max_strike = maximum_strike

    
    @pyqtSlot(int)
    def setMinimumExpiration(self, minimum_expiration):
        print(f"We set expiration minium to: {minimum_expiration}")
        self.min_expiration = minimum_expiration

    
    @pyqtSlot(int)
    def setMaximumExpiration(self, maximum_expiration):
        print(f"We set expiration maximum to: {maximum_expiration}")
        self.max_expiration = maximum_expiration



    @pyqtSlot(list)
    def requestForAllStrikesAndExpirations(self, option_types, execute=True):
        print("OptionChainManager.requestForAllStrikesAndExpirations")
        # Create an empty DataFrame with the desired MultiIndex

        self.fetching_all = True
        counter = 0
        
        for (opt_type, strike, expiration), contract_id in self._contract_ids.items():

            if (opt_type in option_types) and self.checkStrikeExpInRange(strike, expiration):
                contract = self.getContract(strike, expiration, OptionConstrType.single)
                contract.right = opt_type
                contract.conId = contract_id
                req_id = int(counter + Constants.BASE_OPTION_BUFFER_REQID)
                self._all_option_reqs.add(req_id)
                
                self._type_strike_exp_for_req[req_id] = (opt_type, strike, expiration, contract_id)
                
                self.request_buffer.append(OptionRequest(req_id, contract,True))
                counter += 1

        if execute:
            self.iterateOptionRequests(delay=10)


    def getExpirationsFor(self, strike):
        return [key[2] for key in self._contract_ids.keys() if key[1] == strike]

    def getStrikesFor(self, expiration):
        return [key[1] for key in self._contract_ids.keys() if key[2] == expiration]



    def hasQueuedRequests(self):     
        return len(self.request_buffer) > 0


    def iterateOptionRequests(self, delay=10):

        self.total_requests = len(self.request_buffer)
        self.api_updater.emit(Constants.PROGRESS_UPDATE, {'request_type': 'price', 'open_requests': len(self._all_option_reqs), 'total_requests': self.total_requests})
        self.timer = QTimer()
        self.timer.timeout.connect(self.executeHistoryRequest)
        QTimer.singleShot(0, self.executeHistoryRequest)
        self.timer.start(delay)


    def executeHistoryRequest(self):
        if self.hasQueuedRequests():
            if self.ib_interface.getActiveReqCount() < self.queue_cap:
                opt_req = self.request_buffer.pop(0)
                #print(f"We submit {opt_req.req_id},  {opt_req.contract.symbol}, {opt_req.contract.strike}, {opt_req.contract.lastTradeDateOrContractMonth}")
                request = dict()
                request['type'] = 'reqMktData'
                request['snapshot'] = True #self.snapshot
                request['reg_snapshot'] = False
                request['req_id'] = opt_req.req_id
                request['contract'] = opt_req.contract
                request['keep_up_to_date'] = opt_req.keep_updating
                self.ib_request_signal.emit(request)
        if len(self.request_buffer) == 0:
            print("All requests have been submitted")
            self.timer.stop()



    @pyqtSlot(str, float, str, int)
    def relayOptionContractID(self, opt_type, strike, expiration, contract_id): 
        if strike != -1 and expiration != -1:
            self._contract_ids[opt_type, strike, expiration] = contract_id
        

    @pyqtSlot(int)
    def contractDetailsCompleted(self, req_id):
        print(f"OptionChainManager.contractDetailsCompleted {req_id}")
        self.contract_def_ids.remove(req_id)

        requests_left = len(self.contract_def_ids)
        self.api_updater.emit(Constants.PROGRESS_UPDATE, {'total_requests': self.total_requests, 'request_type': 'option chain', 'open_requests': requests_left})

        if requests_left == 0:

            if self.openRequests():
                self.cancelOptionRequests()

            expiration_ib_str = list({key[2] for key in self._contract_ids.keys()})
            
            self._strikes = list({key[1] for key in self._contract_ids.keys()})
            
            self.gatherOptionInfo()
            self.writeOptionChain(self.contractDetails.numeric_id)

            self.api_updater.emit(Constants.OPTION_INFO_LOADED, {'expirations': expiration_ib_str, 'strikes': self._strikes})
        else:
            self.fetchContractsIds()



    def gatherOptionInfo(self):
        
        inner_dict = dict()
        inner_dict['chains'] = dict()
        inner_dict['chains'][Constants.PUT] = dict()
        inner_dict['chains'][Constants.CALL] = dict()
        self.option_chain = inner_dict
        
        for opt_type, strike, exp in self._contract_ids:
            if not exp in self.option_chain['chains'][opt_type]:
                self.option_chain['chains'][opt_type][exp] = dict()
                
            self.option_chain['chains'][opt_type][exp][strike] = {'con_id': self._contract_ids[opt_type, strike, exp]}

        self.option_chain['timestamp'] = datetime.now(timezone(Constants.NYC_TIMEZONE)).timestamp()


    def writeOptionChain(self, uid):
        try:
            with open(f"data/option_buffers/{uid}_chain.pkl", 'wb') as outfile:
                pickle.dump(self.option_chain, outfile)
        except (IOError, OSError) as e:
            print("We couldn't wite the JSON file.... :(")
            print(e)


    def removeSavedOptionInfo(self, uid):
        os.remove(f"data/option_buffers/{uid}_chain.pkl")


    def readOptionChainInfo(self, uid):
        try:
            with open(f"data/option_buffers/{uid}_chain.pkl", 'rb') as pickle_file:
                option_inf = pickle.load(pickle_file)
                return option_inf
        except (IOError, OSError) as e:
            return dict()
    

    def findExpirationIndex(self, expiration):
        try:
            return self._expirations.index(expiration)
        except ValueError:
            return -1



    @pyqtSlot()
    def contractDetailFetchComplete(self):
        self.api_updater.emit(Constants.CONTRACT_DETAILS_FINISHED, dict())


    @pyqtSlot(int)
    def signalSnapshotEnd(self, req_id):
        if self.fetching_all: 
            self._all_option_reqs.discard(req_id)
            #self._all_option_reqs.remove(req_id)
            if (len(self._all_option_reqs) % 50) == 0:
                self.api_updater.emit(Constants.PROGRESS_UPDATE, {'request_type': 'price', 'open_requests': len(self._all_option_reqs), 'total_requests': self.total_requests})

            if (len(self._all_option_reqs) % 200) == 0:
                self.all_option_frame.setUnderlyingPrice(self.price)
                self.all_option_frame.setData(self._all_prices_frame)

            if len(self._all_option_reqs) % 200 == 0:
                self.option_chain['underlying_price'] = self.price
                self.writeOptionChain(self.contractDetails.numeric_id)

            if len(self._all_option_reqs) == 0:
                self.api_updater.emit(Constants.OPTIONS_LOADED, dict())



class OptionRequest:

    def __init__(self, req_id, contract, keep_updating=False):
        self.req_id = req_id
        self.contract = contract
        self.keep_updating = keep_updating


