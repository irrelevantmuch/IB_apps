
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

from PyQt6.QtCore import pyqtSignal, QObject, QReadWriteLock, QThread
from dataHandling.Constants import Constants
from generalFunctionality.GenFunctions import getExpirationString
import numpy as np
import pandas as pd
import time
from datetime import datetime


class ComputableDataFrame(QObject):

    prices_bid = None
    prices_ask = None
    prices_mid = None

    _data_frame = None

    last_update_time = None
    update_delay = 5

    x_values = None
    frame_updater = pyqtSignal(str, dict)

    _premium_prices = True

    def __init__(self, option_type, underlying_price=None):
        super().__init__()

        self.resetDataFrame()
        self._lock = QReadWriteLock()
        self._option_type = option_type
        self._underlying_price = underlying_price

        
    @property
    def has_data(self):
        if self.prices_mid is not None:
            return (len(self.prices_mid) > 1)
        return False
    
    
    def getLineData(self):
        self._lock.lockForRead()
        try:
            return self.x_values, self.prices_mid, self.prices_bid, self.prices_ask, self.value_names
        finally:
            self._lock.unlock()
    

    def setPremium(self, value):
        self._premium_prices = value
        self.recalculatePrices()


    def getUnderlyingPrice(self):
        return self._underlying_price

    def setUnderlyingPrice(self, new_price):
        self._underlying_price = new_price


    def applyPostProcessing(self):
        if self._data_frame is not None:
            self._data_frame.sort_index(inplace=True)
            ask_prices = self._data_frame[Constants.ASK]
            bid_prices = self._data_frame[Constants.BID]
            avg_prices = (ask_prices + bid_prices)/2
            close_prices = self._data_frame[Constants.CLOSE]
            
            # Where either bid or ask is NaN, replace the average with the close value
            result = np.where(avg_prices.isna(), close_prices, avg_prices)
            #result = np.where(bid_prices.isna() & (~ask_prices.isna()) & (~close_prices.isna()) & (ask_prices < close_prices), ask_prices, result)
            result = np.where(np.isnan(result) & close_prices.isna() & (~ask_prices.isna()), ask_prices, result)
            self.prices_mid = np.where(np.isnan(result) & close_prices.isna() & (~bid_prices.isna()), bid_prices, result)
            self.prices_ask = ask_prices.values
            self.prices_bid = bid_prices.values
            self.x_values = self._data_frame.index.values
            self.value_names = self.getDataNames(self.x_values, self.prices_mid)

 
    def timeForUpdate(self):
        if self.last_update_time is not None:
            current_time = int(time.time())
            return current_time > (self.last_update_time + self.update_delay)
        else:
            return True



class ComputableStrikeFrame(ComputableDataFrame):
    

    def resetDataFrame(self):
        self._data_frame = pd.DataFrame({Constants.BID: pd.Series(dtype='float'), Constants.ASK: pd.Series(dtype='float'), Constants.CLOSE: pd.Series(dtype='float')})
        

    def setValueFor(self, strike, tick_type, option_price):
        time_for_update = self.timeForUpdate()
        self._lock.lockForWrite()
        try:
            self._data_frame.at[strike, tick_type] = option_price
            if time_for_update:
                self.applyPostProcessing()
        finally:
            self._lock.unlock()
            
            if time_for_update:
                self.frame_updater.emit(Constants.DATA_DID_CHANGE, {'key': '1D_frame', 'x_value': strike})
                self.last_update_time = int(time.time())
        

    def getDataNames(self, x_values, prices_mid):
        names_list = [f"[%0.2f,%0.2f]:"%(x_values[index], prices_mid[index])+"MID" for index in range(len(x_values))]
        return names_list


class ComputableExpirationFrame(ComputableDataFrame):


    def resetDataFrame(self):
        self._data_frame = pd.DataFrame( {Constants.BID: pd.Series(dtype='float'), Constants.ASK: pd.Series(dtype='float'), Constants.CLOSE: pd.Series(dtype='float'), Constants.NAMES: pd.Series(dtype="string"), Constants.EXPIRATIONS: pd.Series(dtype='datetime64[ns]')})

    def setValueFor(self, days_till_exp, tick_type, option_price, expiration):
        self._lock.lockForWrite()
        try:
            self._data_frame.at[days_till_exp, tick_type] = option_price
            self._data_frame.at[days_till_exp, Constants.EXPIRATIONS] = expiration
            self._data_frame.at[days_till_exp, Constants.NAMES] = getExpirationString(expiration)
            self.applyPostProcessing()

        finally:
            self._lock.unlock()
            self.frame_updater.emit(Constants.DATA_DID_CHANGE, {'key': '1D_frame', 'x_value': days_till_exp})
                

    def getDataNames(self, x_values, prices_mid):
        names_list = [self._data_frame[Constants.NAMES].iloc[index]  + ": %0.2f"%(prices_mid[index]) for index in range(len(x_values))]
        return names_list
    