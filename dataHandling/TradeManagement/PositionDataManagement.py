from ibapi.account_summary_tags import AccountSummaryTags

from dataHandling.Constants import Constants

import numpy as np
import pandas as pd

from dataHandling.DataManagement import DataManager


class PositionDataManager(DataManager):

    _option_positions = None
    _stock_positions = None
    daily_pnl = 0.0
    unrealized_pnl = 0.0
    _pnl_requests = dict()
    _pnl_data_reqs = set()

    account_number = None
    

    def run(self):
        super().run()
        self.ib_interface.reqAccountSummary(Constants.ACCOUNT_SUMMARY_REQID, "All", AccountSummaryTags.AccountType)

    def returnAccount(self, account):
        print("What do we get back for account?")
        print(account)
        self.account_number = account

    def updatePNL(self, req_id, daily_pnl, unrealized_pnl):
        self.daily_pnl = daily_pnl
        self.unrealized_pnl = unrealized_pnl
        self.api_updater.emit(Constants.PNL_RETRIEVED, dict())

    def updateSinglePNL(self, req_id, daily_pnl, unrealized_pnl):        
        numeric_id = self._pnl_requests[req_id]
        if numeric_id in self._option_positions['ID'].values:
            self._option_positions.loc[self._option_positions['ID'] == numeric_id, 'DPNL'] = daily_pnl
            self._option_positions.loc[self._option_positions['ID'] == numeric_id, 'UPNL'] = unrealized_pnl
        elif numeric_id in self._stock_positions['ID'].values:
            self._stock_positions.loc[self._stock_positions['ID'] == numeric_id, 'DPNL'] = daily_pnl
            self._stock_positions.loc[self._stock_positions['ID'] == numeric_id, 'UPNL'] = unrealized_pnl
        
        if req_id in self._pnl_data_reqs:
            self._pnl_data_reqs.remove(req_id)

            if len(self._pnl_data_reqs) < 4:
                for item in self._pnl_data_reqs:
                    numeric_id = self._pnl_requests[item]
            if len(self._pnl_data_reqs) == 0: self.api_updater.emit(Constants.IND_PNL_COMPLETED, dict())
        

    def retrievePositions(self):
        self._stock_positions = pd.DataFrame( {'ID': pd.Series(dtype='int'), 'INSTRUMENT': pd.Series(dtype='string'), 'PRICE': pd.Series(dtype='float'), 'COUNT': pd.Series(dtype='float'), 'UNREALIZED_PNL': pd.Series(dtype='float')} )
        self._option_positions = pd.DataFrame( {'ID': pd.Series(dtype='int'), 'INSTRUMENT': pd.Series(dtype='string'), 'STRIKE': pd.Series(dtype='float'), 'EXPIRATION': pd.Series(dtype='string'), 'TYPE': pd.Series(dtype='string'), 'PRICE': pd.Series(dtype='float'), 'COUNT': pd.Series(dtype='float'), 'MULTIPLIER': pd.Series(dtype='float'), 'UNREALIZED_PNL': pd.Series(dtype='float'), 'EXCHANGE': pd.Series(dtype='string')} )

        print("Do we make it here?")
        self.ib_interface.reqAccountUpdates(True, self.account_number)


    def stopPositionRequest(self):
        print("Are we properly calling it quits?")
        self.ib_interface.reqAccountUpdates(False, self.account_number)


    def getOptionPositions(self):
        return self._option_positions


    def getOptionPositionForIndex(self, index):
        return self._option_positions[index]


    def getStockPositionForIndex(self, index):
        return self._stock_positions[index]


    def getStockPositions(self):
        return self._stock_positions


    def returnPosition(self, contract, position, marketPrice, unrealizedPNL):
        if contract.secType == Constants.STOCK:
            new_position = {'ID': str(contract.conId), 'INSTRUMENT': contract.symbol, 'PRICE': marketPrice, 'COUNT': position, 'UNREALIZED_PNL': unrealizedPNL}
            self._stock_positions = self._stock_positions.append(new_position, ignore_index = True)
        elif contract.secType == "OPT":
            new_position = {'ID': str(contract.conId), 'INSTRUMENT': contract.symbol, 'TYPE': contract.right, 'STRIKE': contract.strike, 'EXPIRATION': contract.lastTradeDateOrContractMonth, 'PRICE': marketPrice, 'COUNT': position, 'MULTIPLIER': float(contract.multiplier), 'UNREALIZED_PNL': unrealizedPNL, "EXCHANGE": contract.primaryExchange}
            self._option_positions = self._option_positions.append(new_position, ignore_index = True)

    
    def positionsFetched(self):
        self.stopPositionRequest()
        self.api_updater.emit(Constants.POSITIONS_RETRIEVED, dict())

        self._stock_positions["UPNL"] = np.nan
        self._stock_positions["DPNL"] = np.nan
        self._option_positions["UPNL"] = np.nan
        self._option_positions["DPNL"] = np.nan

        self.ib_interface.reqPnL(Constants.PNL_REQID, str(self.account_number), "")

        index = 0        
        for id in pd.concat([self._stock_positions['ID'], self._option_positions['ID']]):
            
            if self.getCountFor(id) != 0:
            
                req_id = Constants.BASE_PNL_REQID+index
                self._pnl_data_reqs.add(req_id)
                self.ib_interface.reqPnLSingle(req_id, str(self.account_number), "", int(id))
                self._pnl_requests[req_id] = id
                index += 1

        
        
    def getCountFor(self, numeric_id):
        if self._stock_positions.loc[numeric_id == self._stock_positions['ID']].COUNT.count() == 1:
            return self._stock_positions.loc[numeric_id == self._stock_positions['ID']].COUNT.item()

        if self._option_positions.loc[numeric_id == self._option_positions['ID']].COUNT.count() == 1:
            return self._option_positions.loc[numeric_id == self._option_positions['ID']].COUNT.item()

        return 0

