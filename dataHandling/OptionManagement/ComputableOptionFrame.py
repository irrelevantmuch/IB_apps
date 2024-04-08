
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
            print(f"How many times do we call this one? {self.change_counter}")
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
        print(f"ComputableDataFrame recalculatePrices {int(QThread.currentThreadId())}")
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


    # def filterNaNs(self):
    #     selection = np.logical_not(np.isnan(self.mid_prices))
    #     self.mid_prices = self.mid_prices[selection]
    #     self.bid_prices = self.bid_prices[selection]
    #     self.ask_prices = self.ask_prices[selection]
    #     self.x_values = self.x_values[selection]
        

class ComputableStrikeFrame(ComputableDataFrame):
    
    prices_bid = None
    prices_ask = None
    prices_mid = None
    _premium_prices = True

    # @property
    # def data_y(self):
    #     self._lock.lockForRead()
    #     try:
    #         return self.mid_prices[np.logical_not(np.isnan(self.mid_prices))]
    #     finally:
    #         self._lock.unlock()


    # @property
    # def data_y_lower(self):
    #     self._lock.lockForRead()
    #     try:
    #         return self.bid_prices
    #     finally:
    #         self._lock.unlock()
            

    
    # @property
    # def data_y_upper(self):
    #     self._lock.lockForRead()
    #     try:
    #         return self.ask_prices
    #     finally:
    #         self._lock.unlock()


    def setPremium(self, value):
        self._premium_prices = value
        self.recalculatePrices()


    # def recalculatePrices(self):
    #     print(f"ComputableDataFrame recalculatePrices {int(QThread.currentThreadId())}")
    #     if self._price_frame is not None:

    #         self.x_values = self._price_frame.index.values
    #         if self._premium_prices:
    #             if self._option_type == Constants.CALL:
    #                 differences = self._underlying_price - self._price_frame.index.values
    #             elif self._option_type == Constants.PUT_TYPE:
    #                 differences = self._price_frame.index.values - self._underlying_price

    #             differences = differences.clip(min=0)
    #             self.bid_prices = (self.getBidPrices() - differences)
    #             self.ask_prices = (self.getAskPrices() - differences)
    #             self.mid_prices = (self.getMidPrices() - differences)
    #         else:
    #             print(" *-*-*-*-* Don't we make it here?")
    #             self.bid_prices = self.getBidPrices()
    #             self.ask_prices = self.getAskPrices()
    #             self.mid_prices = self.getMidPrices()


    #         self.filterNaNs()


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
    # @property
    # def data_y(self):
    #     self._lock.lockForRead()
    #     try:
    #         return self.mid_prices
    #     finally:
    #         self._lock.unlock()


    # @property
    # def data_y_lower(self):
    #     self._lock.lockForRead()
    #     try:
    #         return self.bid_prices
    #     finally:
    #         self._lock.unlock()
        

    
    # @property
    # def data_y_upper(self):
    #     self._lock.lockForRead()
    #     try:
    #         return self.ask_prices
    #     finally:
    #         self._lock.unlock()
        

    # @property
    # def data_x_names(self):
    #     self._lock.lockForRead()
    #     try:
        
    #         if self._price_frame is not None:
    #             names_list = [self._price_frame[Constants.NAMES].iloc[index]  + ": %0.2f"%(self.mid_prices[index]) for index in range(len(self.data_x))]
    #             return names_list
    #     finally:
    #         self._lock.unlock()
        

        

        # if self._price_frame is not None:
        #     self.df[Constants.CLOSE]

        #     if self._option_type == Constants.CALL:
        #         differences = self.underlying_price - self.df.index.to_series()
        #     elif self._option_type == Constants.PUT_TYPE:
        #         differences = self.df.index.to_series() - self.underlying_price

        #     differences = differences.clip(lower=0)
        #     data_y = (self.df[Constants.BID]+self.df[Constants.ASK])/2 - differences
        #     data_y_lower = self.df[Constants.BID] - differences
        #     data_y_upper = self.df[Constants.ASK] - differences
        #     return data_y.values, data_y_lower.values, data_y_upper.values
        

        # self.text_mid.setText(self.data_x_names[self.data_x[index]] + ": %0.2f"%(self.data_mid[index]))
        # return [], [], []


        # if option_type == Constants.CALL:
        #         absolute_data = (self.data_y[:-1] - self.data_y[1:])/(self.data_x[1:]-self.data_x[:-1])
        #         relative_data = ((self.data_y[:-1] - self.data_y[1:])/(self.data_x[1:]-self.data_x[:-1])).clip(min=0.001)/(self.data_y[:-1]).clip(min=0.001)
        #         self.absolute_change_line.setData(self.data_x[:-1], absolute_data, pen=pg.mkPen(color=(0,150,0),width=5))
        #         self.relative_change_line.setData(self.data_x[:-1], relative_data, pen=pg.mkPen(color=(150,0,0),width=5))
        #     elif option_type == Constants.PUT_TYPE:
        #         absolute_data = (self.data_y[1:] - self.data_y[:-1])/(self.data_x[1:]-self.data_x[:-1])
        #         relative_data = ((self.data_y[1:] - self.data_y[:-1])/(self.data_x[1:]-self.data_x[:-1])).clip(min=0.001)/(self.data_y[1:]).clip(min=0.001)
        #         self.absolute_change_line.setData(self.data_x[1:], absolute_data, pen=pg.mkPen(color=(0,150,0),width=5))
        #         self.relative_change_line.setData(self.data_x[1:], relative_data, pen=pg.mkPen(color=(150,0,0),width=5))