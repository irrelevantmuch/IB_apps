
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

from PyQt5.QtCore import pyqtSignal, QObject, QReadWriteLock, QThread
from dataHandling.Constants import Constants
import numpy as np


class ComputableDataFrame(QObject):

    x_values = None
    frame_updater = pyqtSignal(str, dict)
    change_counter = 0

    def __init__(self, df, option_type, underlying_price=None):
        super(ComputableDataFrame, self).__init__()

        self._lock = QReadWriteLock()
        self._option_type = option_type
        self._underlying_price = underlying_price
        self.setData(df)
        
    @property
    def has_data(self):
        if self._price_frame is not None:
            return self._price_frame.notna().any().any()
        return False
        

    def setData(self, new_frame):
        self._lock.lockForWrite()
        try:
            self._price_frame = new_frame
            if new_frame is not None:
                if self._price_frame is not None:
                    self.recalculatePrices()
        finally:
            self._lock.unlock()
            self.change_counter += 1
            self.frame_updater.emit(Constants.DATA_DID_CHANGE, {'key': '1D_frame'})

    @property
    def data_x(self):
        self._lock.lockForRead()
        try:
            return self.x_values
        finally:
            self._lock.unlock()
        
    @property
    def data_y(self):
        self._lock.lockForRead()
        try:
            return self.prices_mid
        finally:
            self._lock.unlock()


    @property
    def data_y_lower(self):
        self._lock.lockForRead()
        try:
            return self.prices_bid
        finally:
            self._lock.unlock()
        

    
    @property
    def data_y_upper(self):
        self._lock.lockForRead()
        try:
            return self.prices_ask
        finally:
            self._lock.unlock()
    

    def getBidPrices(self):
        if (Constants.BID in self._price_frame) and not self._price_frame[Constants.BID].isnull().all():
            return self._price_frame[Constants.BID].values
        else:
            if Constants.CLOSE in self._price_frame:
                return self._price_frame[Constants.CLOSE].values
            else:
                return self._price_frame[Constants.ASK].values


    def getAskPrices(self):
        if (Constants.ASK in self._price_frame) and not self._price_frame[Constants.ASK].isnull().all():
            return self._price_frame[Constants.ASK].values
        else:
            if Constants.CLOSE in self._price_frame:
                return self._price_frame[Constants.CLOSE].values
            else:
                return self._price_frame[Constants.BID].values
   


    def getMidPrices(self):
        return (self.getBidPrices() + self.getAskPrices())/2


    def getUnderlyingPrice(self):
        return self._underlying_price

    def setUnderlyingPrice(self, new_price):
        self._underlying_price = new_price


    def recalculatePrices(self):
        # print(f"ComputableDataFrame recalculatePrices {int(QThread.currentThreadId())}")
        if self._price_frame is not None:
            ask_prices = self._price_frame[Constants.ASK]
            bid_prices = self._price_frame[Constants.BID]
            avg_prices = (ask_prices + bid_prices)/2
            close_prices = self._price_frame[Constants.CLOSE]
            
            # Where either bid or ask is NaN, replace the average with the close value
            result = np.where(avg_prices.isna(), close_prices, avg_prices)
            #result = np.where(bid_prices.isna() & (~ask_prices.isna()) & (~close_prices.isna()) & (ask_prices < close_prices), ask_prices, result)
            result = np.where(np.isnan(result) & close_prices.isna() & (~ask_prices.isna()), ask_prices, result)
            self.prices_mid = np.where(np.isnan(result) & close_prices.isna() & (~bid_prices.isna()), bid_prices, result)
            self.prices_ask = ask_prices.values
            self.prices_bid = bid_prices.values
            self.x_values = self._price_frame.index.values


 

class ComputableStrikeFrame(ComputableDataFrame):
    
    prices_bid = None
    prices_ask = None
    prices_mid = None
    _premium_prices = True


    def setPremium(self, value):
        self._premium_prices = value
        self.recalculatePrices()


    @property
    def data_x_names(self):
        self._lock.lockForRead()
        try:
            names_list = [f"[%0.2f,%0.2f]:"%(self.data_x[index], self.prices_mid[index])+"MID" for index in range(len(self.data_x))]
            return names_list
        finally:
            self._lock.unlock()


class ComputableExpirationFrame(ComputableDataFrame):
    
    prices_mid = None
    prices_bid = None
    prices_ask = None
    

    def setPremium(self, value):
        self._premium_prices = value
        self.recalculatePrices()


    @property
    def data_x_names(self):
        self._lock.lockForRead()
        try:
            if self._price_frame is not None:
                names_list = [self._price_frame[Constants.NAMES].iloc[index]  + ": %0.2f"%(self.prices_mid[index]) for index in range(len(self.data_x))]
                return names_list
        finally:
            self._lock.unlock()
   