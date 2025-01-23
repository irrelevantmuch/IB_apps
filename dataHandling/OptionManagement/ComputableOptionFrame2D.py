
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

from PyQt6.QtCore import pyqtSignal, pyqtSlot, QObject, QReadWriteLock, Qt, QThread, QTimer
from dataHandling.Constants import Constants, OptionConstrType
from generalFunctionality.GenFunctions import getExpirationString, getDaysTillExpiration

import numpy as np
import pandas as pd

import time


class Computable2DDataFrame(QObject):

    update_delay = 5

    _underlying_price = 0.0
    _unique_expirations = dict()
    _unique_strikes = dict()
    _price_type = "price"
    frame_updater = pyqtSignal(str, dict)

    _option_type = Constants.CALL
    _order_type = Constants.BUY
    _constr_type = OptionConstrType.single

    selected_strike = None
    selected_exp = None
    selected_cost = None

    minimum_strike = None
    maximum_strike = None
    minimum_dte = None
    maximum_dte = None

    offsets = []
    ratios = [1]

    def __init__(self, option_type):
        super().__init__()

        self._lock = QReadWriteLock()
        self.resetDataFrame()
        self.setupUpdateTimer()
        self._option_type = option_type
       

    def resetDataFrame(self):
        self._price_frames = dict()
        multi_index = pd.MultiIndex.from_tuples([], names=['expiration', 'strike'])
        self._price_frames[Constants.PUT] = pd.DataFrame({Constants.BID: pd.Series(dtype='float'), Constants.ASK: pd.Series(dtype='float'), Constants.CLOSE: pd.Series(dtype='float')}, index=multi_index)
        self._price_frames[Constants.CALL] = pd.DataFrame({Constants.BID: pd.Series(dtype='float'), Constants.ASK: pd.Series(dtype='float'), Constants.CLOSE: pd.Series(dtype='float')}, index=multi_index)


    def setupUpdateTimer(self):
        self.last_update_time = int(time.time())

        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.recalculateData)


    def changeConstrType(self, option_type, order_type, constr_type, offsets, ratios):
        self._lock.lockForWrite()

        try:
            self.selected_strike = None
            self.selected_exp = None
            self.selected_cost = None

            self._option_type = option_type
            self._order_type = order_type
            self._constr_type = constr_type
            self.ratios = ratios
            self.offsets = offsets
            self.recalculateData(structural_change=True)
        finally:
            self._lock.unlock()

        
    @property
    def has_data(self):
        return self._price_frames[self._option_type].notna().any().any()
        

    def setPriceType(self, value):
        self._lock.lockForWrite()
        try:
            self.c = value
            self.recalculateData()
        finally:
            self._lock.unlock()


    def timeForUpdate(self):
        current_time = int(time.time())
        return current_time > (self.last_update_time + self.update_delay)
        

    def setValueFor(self, opt_type, index_2D, tick_type, option_price):
        self._lock.lockForWrite()
        try:
            self._price_frames[opt_type].at[index_2D, tick_type] = option_price
            self.recalculateDataIfNeeded()
        finally:
            self._lock.unlock()
    

    def recalculateDataIfNeeded(self):        
        time_for_update = self.timeForUpdate()

        if time_for_update:
            self.recalculateData()
        elif not(self.update_timer.isActive()):
            remaining_time = max(0, 5 - (time.time() - self.last_update_time))
            print("THREAD ISSUE FROM HERE")
            self.update_timer.start(int(remaining_time * 1000))


    def recalculateData(self, structural_change=False):
            for option_type in [Constants.CALL, Constants.PUT]:
                self._unique_expirations[option_type] = self._price_frames[option_type].index.get_level_values('expiration').unique().dropna().sort_values()
                self._unique_strikes[option_type] = self._price_frames[option_type].index.get_level_values('strike').unique().dropna().sort_values()
                self.estimatePrices()
            
            self.calculateDataPoints()
    
            self.frame_updater.emit(Constants.DATA_DID_CHANGE, {'key': '2D_frame', 'structural_change': structural_change})
            self.last_update_time = int(time.time())

        #self._unique_expiration_conj = np.intersect1d(self._unique_expirations[Constants.CALL], self._unique_expirations[Constants.PUT])


    def calculateDataPoints(self):
        result_frame = self.calculatePricesForCurrentConstruction()
        
        self.data_points = {'expiration_grouped': dict(), 'strike_grouped': dict(), 'price_est': dict()}
        unique_expirations = result_frame.index.get_level_values('days_till_exp').unique().sort_values().values.astype(float)
        unique_strikes = result_frame.index.get_level_values('strike').unique().sort_values().values.astype(float)

        self.calculateExpirationGrouped(result_frame, unique_strikes, unique_expirations)
        self.calculateStrikeGrouped(result_frame, unique_strikes)
        self.calulcateHypotheticalReturns(result_frame, unique_strikes, unique_expirations)


    def calulcateHypotheticalReturns(self, result_frame, for_strikes, for_expirations):
        if (self.selected_strike is not None) and (self.selected_cost is not None):
            offsets = self.selected_strike - for_strikes
            offsets = np.linspace(offsets.min(), offsets.max(), 200)
            y_coords = np.empty((len(offsets)))
            y_details = np.empty((len(offsets)))

            for index, offset in enumerate(offsets):

                y_coords[index] = self.getExpirationPriceForStrike(self._constr_type, self.selected_strike, offset)
                y_details[index] = f"{y_coords[index]:.2f}"
                if self._order_type == Constants.SELL:
                    y_coords[index] = 0 - y_coords[index]
                y_coords[index] = y_coords[index] - self.selected_cost
                
            self.data_points['price_est'][-1] = {'display_name': "At Expiration", 'x': offsets, 'y': y_coords, 'y_detail': y_details}

            for expiration in for_expirations:
                if expiration <= self.selected_exp:
                    data_selection = result_frame.xs(expiration, level='days_till_exp')
                    data_selection = data_selection.sort_index(ascending=False)
                    reworked_indices = self.selected_strike - data_selection.index.values.astype(float)
                    profit_loss = data_selection['combo_price'].values.astype(float)
                    if self._order_type == Constants.SELL: profit_loss = 0 - profit_loss
                    profit_loss = profit_loss - self.selected_cost
                    
                    self.data_points['price_est'][expiration] = {'display_name': f"{expiration} dte", 'x': reworked_indices, 'y': profit_loss, 'y_detail': data_selection['price_detail'].values}


    def calculateStrikeGrouped(self, result_frame, for_strikes):
        strike_gen = (strike for strike in for_strikes if self.withinStrikeRange(strike))
        for strike in strike_gen:
            data_selection = result_frame.xs(strike, level='strike')
            data_selection = data_selection.sort_index()

            x_coords = np.insert(data_selection[Constants.DAYS_TILL_EXP].values.astype(float), 0, -1)
            expiration_price = self.getExpirationPriceForStrike(self._constr_type, strike)
            y_coords = np.insert(data_selection['combo_price'].values.astype(float), 0, expiration_price)
            if self._order_type == Constants.SELL:
                y_coords = 0 - y_coords

            y_details = np.insert(data_selection['price_detail'].values, 0, data_selection['price_detail'].values[0])
            self.data_points['strike_grouped'][strike] = {'display_name': f"${strike}",'x': x_coords, 'y': y_coords, 'y_detail': y_details}


    def withinStrikeRange(self, strike):
        if (self.minimum_strike is not None) and strike < self.minimum_strike:
            return False
        if (self.maximum_strike is not None) and strike > self.maximum_strike:
            return False
        return True


    def calculateExpirationGrouped(self, result_frame, for_strikes, for_expirations):
        x_coords = for_strikes
        y_coords = np.empty((len(for_strikes)))
        y_details = np.empty((len(for_strikes)))
        for index, strike in enumerate(for_strikes):
            y_coords[index] = self.getExpirationPriceForStrike(self._constr_type, strike)
            if self._order_type == Constants.SELL: y_coords[index] = 0 - y_coords[index]
            y_details[index] = f"{y_coords[index]:.2f}"
        self.data_points['expiration_grouped'][-1] = {'display_name': f"-1 dte", 'x': x_coords, 'y': y_coords, 'y_detail': y_details}

        exp_gen = [exp for exp in for_expirations if self.withinExpirationRange(exp)]
        for expiration in exp_gen:
            data_selection = result_frame.xs(expiration, level='days_till_exp')
            data_selection = data_selection.sort_index()

            y_coords = data_selection['combo_price'].values.astype(float)
            if self._order_type == Constants.SELL:
                y_coords = 0 - y_coords

            self.data_points['expiration_grouped'][expiration] = {'display_name': f"{expiration} dte", 'x': data_selection.index.values.astype(float), 'y': y_coords, 'y_detail': data_selection['price_detail'].values}
        

    def withinExpirationRange(self, expiration):
        if (self.minimum_dte is not None) and expiration < self.minimum_dte:
            return False
        if (self.maximum_dte is not None) and expiration > self.maximum_dte:
            return False
        return True
    

    def getExpirationPriceForStrike(self, constr_type, strike, offset=None):
        underlying_price = self._underlying_price

        if offset is not None:
            underlying_price += offset

        if self._constr_type == OptionConstrType.single:
            if self._option_type == Constants.CALL:
                return max(underlying_price-strike,0)
            elif self._option_type == Constants.PUT:
                return max(strike-underlying_price,0)
        elif self._constr_type == OptionConstrType.vertical_spread:
            if self._option_type == Constants.CALL:
                return self.ratios[0] * max(underlying_price-(strike-self.offsets[0]/2),0) - self.ratios[1] * max(underlying_price-(strike+self.offsets[0]/2),0)
            elif self._option_type == Constants.PUT:
                return self.ratios[0] * max((strike+self.offsets[0]/2)-underlying_price,0) - self.ratios[1] * max((strike-(self.offsets[0]/2))-underlying_price,0)
        elif self._constr_type == OptionConstrType.butterfly:
            return self.ratios[1] * max(underlying_price-(strike+self.offsets[0]),0) + self.ratios[1] * max(underlying_price-(strike-self.offsets[0]),0) - self.ratios[0] * max(underlying_price-strike,0)
        elif self._constr_type == OptionConstrType.split_butterfly:
            return self.ratios[0] * max(underlying_price-strike,0) - self.ratios[1] * max(underlying_price-(strike+self.offsets[0]),0)
        elif self._constr_type == OptionConstrType.iron_condor:
            sold_call = self.ratios[0] * max(underlying_price-(strike+self.offsets[1]/2),0)
            sold_put = self.ratios[0] * max((strike-self.offsets[1]/2)-underlying_price,0)
            bought_call = self.ratios[0] * max(underlying_price-(strike+(self.offsets[1]/2+self.offsets[1])),0)
            bought_put = self.ratios[0] * max((strike-(self.offsets[1]/2+self.offsets[1])-underlying_price),0)
            return bought_call + bought_put - sold_put - sold_call
        else:
            return 0.0


    def calculatePricesForCurrentConstruction(self):
        index = pd.MultiIndex.from_tuples([], names=['days_till_exp', 'strike'])
        result_frame = pd.DataFrame({'combo_price': pd.Series(dtype='float'), 'price_detail': pd.Series(dtype='str')}, index=index)
    
        for expiration in self._unique_expirations[self._option_type]:
            strikes, prices, label = self.getPricesByExpiration(expiration)
            strikes, prices, price_split = self.priceForConstructionType(strikes, prices)
            y_values = self.priceForPriceType(strikes, prices)

            expirations = getDaysTillExpiration(expiration)*len(y_values)

            if price_split is not None:
                price_details_str = [(', '.join(['{:.2f}'.format(flt).rstrip('0').rstrip('.') for flt in tpl])) for tpl in price_split]
            else:
                price_details_str = [f'{t:.2f}' for t in y_values]

                # Concatenate to make bigger frame
            multi_index = pd.MultiIndex.from_product([[getDaysTillExpiration(expiration)], strikes], names=['days_till_exp', 'strike'])
            df_new = pd.DataFrame({'combo_price': y_values, 'price_detail': price_details_str, Constants.DAYS_TILL_EXP: expirations}, index=multi_index)
            result_frame = pd.concat([result_frame, df_new])

        return result_frame


    def estimatePrices(self):
        
        # Calculate the average for non-NaN bid and ask values
        for option_type in self._price_frames.keys():
            ask_prices = self._price_frames[option_type][Constants.ASK]
            bid_prices = self._price_frames[option_type][Constants.BID]
            avg_prices = (ask_prices + bid_prices)/2
            close_prices = self._price_frames[option_type][Constants.CLOSE]
            
            # Where either bid or ask is NaN, replace the average with the close value
            result = np.where(avg_prices.isna(), close_prices, avg_prices)
            #result = np.where(bid_prices.isna() & (~ask_prices.isna()) & (~close_prices.isna()) & (ask_prices < close_prices), ask_prices, result)
            result = np.where(np.isnan(result) & close_prices.isna() & (~ask_prices.isna()), ask_prices, result)
            result = np.where(np.isnan(result) & close_prices.isna() & (~bid_prices.isna()), bid_prices, result)

            self._price_frames[option_type]['price_est'] = result


    def getAvailableStrikes(self):
        return self._unique_strikes[self._option_type]


    def getLinesFor(self, for_type):
        self._lock.lockForRead()
        try:
            if for_type in self.data_points:
                return self.data_points[for_type].copy()
            return None
        finally:
            self._lock.unlock()


    def priceForConstructionType(self, strikes, y_values):
        if self._constr_type == OptionConstrType.vertical_spread:
            strikes, price_diffs, strike_pairs = self.findPairs(strikes, y_values, self.offsets[0], self.ratios)
            return strikes, price_diffs, strike_pairs
        elif self._constr_type == OptionConstrType.butterfly:
            strikes, price_diffs, strike_triplets = self.findTriplets(strikes, y_values, self.offsets[0], self.ratios)
            return strikes, price_diffs, strike_triplets
        elif self._constr_type == OptionConstrType.split_butterfly:
            strikes, price_diffs, strike_quadruplets = self.findQuartets(strikes, y_values, self.offsets[0], self.ratios)
            return strikes, price_diffs, strike_quadruplets
        elif self._constr_type == OptionConstrType.iron_condor:
            strikes, price_diffs, strike_quadruplets = self.findCondors(strikes, y_values, self.offsets[0], self.offsets[1], self.ratios)
            return strikes, price_diffs, strike_quadruplets
        else:
            return strikes, y_values, None


    def findPairs(self, strikes, prices, price_diff, ratios):        
        if self._option_type == Constants.CALL:
            i, j = np.where(strikes - strikes[:, None] == price_diff)
        else:
            i, j = np.where(strikes[:, None] - strikes == price_diff)
        
        strike_pairs = list(zip(strikes[i], strikes[j]))
        valid_strikes = (strikes[i] + strikes[j])/2
        prices = ratios[0]*prices[i] - ratios[1]*prices[j]

        
        return valid_strikes, prices, strike_pairs


    def findTriplets(self, strikes, prices, price_diff, ratios):
        
        #Create difference matrices
        diff_mat1 = strikes[:, None] - strikes #forward diff
        diff_mat2 = strikes - strikes[:, None] #forward diff
        # Find indices where both differences are equal to price_diff
        i, j, k = np.where((diff_mat1[:, :, None] == price_diff) & (diff_mat2[:, None, :] == price_diff))
        # Create the triplet combinations
        strike_triplets = list(zip(strikes[i], strikes[j], strikes[k]))
        valid_strikes = strikes[i]
        triplet_prices = ratios[2]*prices[j] + ratios[1]*prices[k] -ratios[0]*prices[i]
        return valid_strikes, triplet_prices, strike_triplets


    def findCondors(self, strikes, prices, price_diff, price_spread, ratios):

        call_prices = prices[:,0]
        put_prices = prices[:,1]
        #Create difference matrices
        backward_diff = strikes[:,None] - strikes
        forward_diff = strikes - strikes[:,None]
        # Find indices where both differences are equal to price_diff
        [i,j,k,l] = np.where((forward_diff[:, :, None, None] == price_spread) & (forward_diff[:, None,None, :] == price_diff+price_spread) & (backward_diff[:, None, :, None] == price_diff))
        # Create the triplet combinations
        strike_quartets = list(zip(strikes[i], strikes[j], strikes[k], strikes[l]))
        valid_strikes = (strikes[i] + strikes[j])/2
        condor_prices =  ratios[2]*put_prices[k] + ratios[2]*call_prices[l] - ratios[0]*put_prices[i] - ratios[1]*call_prices[j]
        return valid_strikes, condor_prices, strike_quartets


    def findQuartets(self, strikes, prices, price_diff, ratios):
        n = len(strikes)
        quartets = []

        # Go through each combination of 4 strikes
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    for l in range(k + 1, n):
                        if (strikes[j] - strikes[i] == price_diff and
                            strikes[k] - strikes[j] == price_diff and
                            strikes[l] - strikes[k] == price_diff):
                            quartets.append((strikes[i], strikes[j], strikes[k], strikes[l]))

        valid_strikes = [q[0] for q in quartets]
        quartet_prices = [
            ratios[0] * prices[np.where(strikes == q[0])[0][0]]
            - ratios[1] * prices[np.where(strikes == q[1])[0][0]]  
            - ratios[2] * prices[np.where(strikes == q[2])[0][0]] 
            + ratios[3] * prices[np.where(strikes == q[3])[0][0]] 
            for q in quartets
        ]

        return valid_strikes, quartet_prices, quartets

    def priceForPriceType(self, strikes, y_values):
        
        if (self._underlying_price is not None) and self._price_type == "premium":
            selection = strikes < self._underlying_price
            y_values[selection] = y_values[selection] - (self._underlying_price - strikes[selection])
        elif (self._underlying_price is not None) and self._price_type == "relative premium":
            selection = strikes < self._underlying_price
            y_values[selection] = y_values[selection] - (self._underlying_price - strikes[selection])
            y_values = y_values/y_values.max()
        
        return y_values


    def isCallPutConstr(self):
        return (self._constr_type == OptionConstrType.iron_condor)

    
    def hasDataForExp(self, opt_type, expiration):
        if opt_type in self._price_frames:
            return self._price_frames[opt_type].index.get_level_values('expiration').isin([expiration]).any()
        return False

    def getPricesByExpiration(self, exp_value):
        
        if self.isCallPutConstr():
            
            call_selection = self._price_frames[Constants.CALL].xs(exp_value, level='expiration')
            call_selection = call_selection.sort_index()
            
            put_selection = self._price_frames[Constants.PUT].xs(exp_value, level='expiration')
            put_selection = put_selection.sort_index()
            
            strikes = np.intersect1d(call_selection.index.values.astype(float), put_selection.index.values.astype(float))
            call_prices = call_selection.loc[strikes, 'price_est'].values.astype(float)
            put_prices = put_selection.loc[strikes, 'price_est'].values.astype(float)
            prices = np.column_stack((call_prices, put_prices))
            return strikes, prices, exp_value
        else:
            data_selection = self._price_frames[self._option_type].xs(exp_value, level='expiration')
            data_selection = data_selection.sort_index()

            strikes = data_selection.index.values.astype(float)
            y_values = data_selection['price_est'].values.astype(float)
            
            return strikes, y_values, exp_value


    def getValuesByExpiration(self, option_type, exp_value, column):
        data_selection = self._price_frames[option_type].xs(exp_value, level='expiration')
        data_selection = data_selection.sort_index()

        strikes = data_selection.index.values.astype(float)
        y_values = data_selection[column].values.astype(float)
            
        return strikes, y_values


    # def getPricesByExpiration(self, exp_value):

    #     if self.isCallPutConstr():
            
    #         call_selection = self._price_frames[Constants.CALL].xs(exp_value, level='expiration')
    #         call_selection = call_selection.sort_index()
            
    #         put_selection = self._price_frames[Constants.PUT].xs(exp_value, level='expiration')
    #         put_selection = put_selection.sort_index()
            
    #         strikes = np.intersect1d(call_selection.index.values.astype(float), put_selection.index.values.astype(float))
    #         call_prices = call_selection.loc[strikes, 'price_est'].values.astype(float)
    #         put_prices = put_selection.loc[strikes, 'price_est'].values.astype(float)
    #         prices = np.column_stack((call_prices, put_prices))
    #         return strikes, prices, exp_value
    #     else:
    #         data_selection = self._price_frames[self._option_type].xs(exp_value, level='expiration')
    #         data_selection = data_selection.sort_index()

    #         strikes = data_selection.index.values.astype(float)
    #         y_values = data_selection['price_est'].values.astype(float)
            
    #         return strikes, y_values, exp_value



    def setUnderlyingPrice(self, new_price):
        self._underlying_price = new_price


    def getLineCount(self, for_type):
        if not self.has_data:
            return 0
        if for_type == 'expiration_grouped':
            return len(self._unique_expirations[self._option_type])
        elif for_type == 'strike_grouped':
            return len(self._unique_strikes[self._option_type])
        elif for_type == 'expiration_diffs':
            return len(self._unique_expirations[self._option_type]) - 1


    def getBoundaries(self):

        if (self._option_type in self._unique_expirations) and len(self._unique_expirations[self._option_type]) > 0:
            min_exp = self._unique_expirations[self._option_type].min()
            max_exp = self._unique_expirations[self._option_type].max()
        else:
            min_exp = None
            max_exp = None

        if (self._option_type in self._unique_strikes) and len(self._unique_strikes[self._option_type]) > 0:
            min_strike = self._unique_strikes[self._option_type].min()
            max_strike = self._unique_strikes[self._option_type].max()
        else:
            min_strike = None
            max_strike = None


        return min_exp, max_exp, min_strike, max_strike


    def getUnderlyingPrice(self):
        return self._underlying_price


    @pyqtSlot(float)
    def setMinimumStrike(self, minimum_strike):
        self.minimum_strike = minimum_strike
        self.recalculateData(structural_change=True)


    @pyqtSlot(float)
    def setMaximumStrike(self, maximum_strike):
        self.maximum_strike = maximum_strike
        self.recalculateData(structural_change=True)

    
    @pyqtSlot(int)
    def setMinimumExpiration(self, minimum_dte):
        self.minimum_dte = minimum_dte
        self.recalculateData(structural_change=True)

    
    @pyqtSlot(int)
    def setMaximumExpiration(self, maximum_dte):
        self.maximum_dte = maximum_dte
        self.recalculateData(structural_change=True)

