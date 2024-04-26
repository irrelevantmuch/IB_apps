
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

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QReadWriteLock, Qt, QThread
from dataHandling.Constants import Constants, OptionConstrType

import numpy as np
import pandas as pd


class Computable2DDataFrame(QObject):

    _underlying_price = 0.0
    _unique_expirations = dict()
    _unique_strikes = dict()
    _price_type = "price"
    frame_updater = pyqtSignal(str, dict)

    _price_frames = dict()
    _option_type = Constants.CALL
    _order_type = Constants.BUY
    _constr_type = OptionConstrType.single


    selected_strike = None
    selected_exp = None
    selected_cost = None

    minimum_strike = None
    maximum_strike = None
    minimum_expiration = None
    maximum_expiration = None

    offsets = []
    ratios = [1]

    def __init__(self, dfs, option_type):
        super().__init__()

        self._lock = QReadWriteLock()
        self.setData(dfs)
        self._option_type = option_type
       

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
            self.recalculateData()
        finally:
            self._lock.unlock()

        
    @property
    def has_data(self):
        if self._price_frames is not None:
            return self._price_frames[self._option_type].notna().any().any()
        return False
        

    def setPriceType(self, value):
        self._lock.lockForWrite()
        try:
            self._price_type = value
            self.recalculateData()
        finally:
            self._lock.unlock()


    def setData(self, new_frames):
        self._lock.lockForWrite()
        try:
            self._price_frames = new_frames
            if new_frames is not None:
                self.recalculateData()
            else:
                self.frame_updater.emit(Constants.DATA_DID_CHANGE, {'key': '2D_frame'})
        finally:
            self._lock.unlock()


    def recalculateData(self):
        print(f"Computable2DDataFrame.recalculateData {int(QThread.currentThreadId())}")
        for option_type in [Constants.CALL, Constants.PUT]:
            self._unique_expirations[option_type] = self._price_frames[option_type].index.get_level_values('days_till_exp').unique().sort_values()
            self._unique_strikes[option_type] = self._price_frames[option_type].index.get_level_values('strike').unique().sort_values()
            self.addPriceColumn()
        self.calculateDataPoints()
    
        #self._unique_expiration_conj = np.intersect1d(self._unique_expirations[Constants.CALL], self._unique_expirations[Constants.PUT])
        print("This be confusing....")
        self.frame_updater.emit(Constants.DATA_DID_CHANGE, {'key': '2D_frame'})


    def calculateDataPoints(self):
        print(f"Computable2DDataFrame.calculateDataPoints {int(QThread.currentThreadId())}")
        result_frame = self.calculatePricesForCurrentConstruction()
        
        self.data_points = {'expiration_grouped': dict(), 'strike_grouped': dict(), 'price_est': dict()}
        unique_expirations = result_frame.index.get_level_values('days_till_exp').unique().sort_values()
        unique_strikes = result_frame.index.get_level_values('strike').unique().sort_values()

        self.calculateExpirationGrouped(result_frame, unique_strikes, unique_expirations)
        self.calculateStrikeGrouped(result_frame, unique_strikes)
        self.calulcateHypotheticalReturns(result_frame, unique_strikes, unique_expirations)


    def calulcateHypotheticalReturns(self, result_frame, for_strikes, for_expirations):
        print(f"Computable2DDataFrame.calulcateHypotheticalReturns {int(QThread.currentThreadId())}")
        if (self.selected_strike is not None) and (self.selected_cost is not None):
            offsets = self.selected_strike - for_strikes
            offsets = np.linspace(offsets.min(), offsets.max(), 200)
            y_coords = np.empty((len(offsets)))
            y_details = np.empty((len(offsets)))

            for index, offset in enumerate(offsets):

                y_coords[index] = self.getEndPriceForStrike(self._constr_type, self.selected_strike, offset)
                y_details[index] = f"{y_coords[index]:.2f}"
                if self._order_type == Constants.SELL:
                    y_coords[index] = 0 - y_coords[index]
                y_coords[index] = y_coords[index] - self.selected_cost
                
            self.data_points['price_est'][-1] = {'display_name': "At Expiration", 'x': offsets, 'y': y_coords, 'y_detail': y_details}

            for expiration in for_expirations:
                if expiration <= self.selected_exp:
                    data_selection = result_frame.xs(expiration, level='days_till_exp')
                    data_selection = data_selection.sort_index(ascending=False)
                    reworked_indices = self.selected_strike - data_selection.index
                    profit_loss = data_selection['combo_price'].values
                    if self._order_type == Constants.SELL: profit_loss = 0 - profit_loss
                    profit_loss = profit_loss - self.selected_cost
                    
                    self.data_points['price_est'][expiration] = {'display_name': f"{expiration} dte", 'x': reworked_indices, 'y': profit_loss, 'y_detail': data_selection['price_detail'].values}


    def calculateStrikeGrouped(self, result_frame, for_strikes):
        print("Computable2DDataFrame.calculateStrikeGrouped  {int(QThread.currentThreadId())}")
        strike_gen = (strike for strike in for_strikes if self.withinStrikeRange(strike))
        for strike in strike_gen:
            data_selection = result_frame.xs(strike, level='strike')
            data_selection = data_selection.sort_index()

            x_coords = np.insert(data_selection.index, 0, -1)
            expiration_price = self.getEndPriceForStrike(self._constr_type, strike)
            y_coords = np.insert(data_selection['combo_price'].values, 0, expiration_price)
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
        print(f"Computable2DDataFrame.calculateExpirationGrouped {int(QThread.currentThreadId())}")
        x_coords = for_strikes
        y_coords = np.empty((len(for_strikes)))
        y_details = np.empty((len(for_strikes)))
        for index, strike in enumerate(for_strikes):
            y_coords[index] = self.getEndPriceForStrike(self._constr_type, strike)
            if self._order_type == Constants.SELL: y_coords[index] = 0 - y_coords[index]
            y_details[index] = f"{y_coords[index]:.2f}"
        self.data_points['expiration_grouped'][-1] = {'display_name': f"-1 dte", 'x': x_coords, 'y': y_coords, 'y_detail': y_details}

        exp_gen = (exp for exp in for_expirations if self.withinExpirationRange(exp))
        for expiration in exp_gen:
            data_selection = result_frame.xs(expiration, level='days_till_exp')
            data_selection = data_selection.sort_index()

            y_coords = data_selection['combo_price'].values
            if self._order_type == Constants.SELL:
                y_coords = 0 - y_coords
            self.data_points['expiration_grouped'][expiration] = {'display_name': f"{expiration} dte", 'x': data_selection.index, 'y': y_coords, 'y_detail': data_selection['price_detail'].values}
        

    def withinExpirationRange(self, expiration):
        if (self.minimum_expiration is not None) and expiration < self.minimum_expiration:
            return False
        if (self.maximum_expiration is not None) and expiration > self.maximum_expiration:
            return False
        return True
    

    def getEndPriceForStrike(self, constr_type, strike, offset=None):
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

            if price_split is not None:
                price_details_str = [(', '.join(['{:.2f}'.format(flt).rstrip('0').rstrip('.') for flt in tpl])) for tpl in price_split]
            else:
                price_details_str = [f'{t:.2f}' for t in y_values]

                # Concatenate to make bigger frame
            multi_index = pd.MultiIndex.from_product([[expiration], strikes], names=['days_till_exp', 'strike'])
            df_new = pd.DataFrame({'combo_price': y_values, 'price_detail': price_details_str}, index=multi_index)
            result_frame = pd.concat([result_frame, df_new])

        return result_frame


    def addPriceColumn(self):
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

    def getPricesByExpiration(self, exp_value):
        
        if self.isCallPutConstr():
            
            call_selection = self._price_frames[Constants.CALL].xs(exp_value, level='days_till_exp')
            call_selection = call_selection.sort_index()
            
            put_selection = self._price_frames[Constants.PUT].xs(exp_value, level='days_till_exp')
            put_selection = put_selection.sort_index()
            
            strikes = np.intersect1d(call_selection.index.values, put_selection.index.values)
            call_prices = call_selection.loc[strikes, 'price_est'].values
            put_prices = put_selection.loc[strikes, 'price_est'].values
            prices = np.column_stack((call_prices, put_prices))
            return strikes, prices, exp_value
        else:
            data_selection = self._price_frames[self._option_type].xs(exp_value, level='days_till_exp')
            data_selection = data_selection.sort_index()

            strikes = data_selection.index.values
            y_values = data_selection['price_est'].values
            
            return strikes, y_values, exp_value


    def getPricesByExpiration(self, exp_value):

        if self.isCallPutConstr():
            
            call_selection = self._price_frames[Constants.CALL].xs(exp_value, level='days_till_exp')
            call_selection = call_selection.sort_index()
            
            put_selection = self._price_frames[Constants.PUT].xs(exp_value, level='days_till_exp')
            put_selection = put_selection.sort_index()
            
            strikes = np.intersect1d(call_selection.index.values, put_selection.index.values)
            call_prices = call_selection.loc[strikes, 'price_est'].values
            put_prices = put_selection.loc[strikes, 'price_est'].values
            prices = np.column_stack((call_prices, put_prices))
            return strikes, prices, exp_value
        else:
            data_selection = self._price_frames[self._option_type].xs(exp_value, level='days_till_exp')
            data_selection = data_selection.sort_index()

            strikes = data_selection.index.values
            y_values = data_selection['price_est'].values
            
            return strikes, y_values, exp_value



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
        min_exp = self._unique_expirations[self._option_type].min()
        max_exp = self._unique_expirations[self._option_type].max()
        min_strike = self._unique_strikes[self._option_type].min()
        max_strike = self._unique_strikes[self._option_type].max()

        return min_exp, max_exp, min_strike, max_strike


    def getUnderlyingPrice(self):
        return self._underlying_price


    @pyqtSlot(float)
    def setMinimumStrike(self, minimum_strike):
        self.minimum_strike = minimum_strike
        self.recalculateData()


    @pyqtSlot(float)
    def setMaximumStrike(self, maximum_strike):
        self.maximum_strike = maximum_strike
        self.recalculateData()

    
    @pyqtSlot(int)
    def setMinimumExpiration(self, minimum_expiration):
        self.minimum_expiration = minimum_expiration
        self.recalculateData()

    
    @pyqtSlot(int)
    def setMaximumExpiration(self, maximum_expiration):
        self.maximum_expiration = maximum_expiration
        self.recalculateData()


# class ReadOnlyFrameWrapper:

#     def __init__(self, computable_frame):
#         self._computable_frame = computable_frame

#     def connectCallback(self, callback_function):
#         self._computable_frame.frame_updater.connect(callback_function, Qt.QueuedConnection)

#     @property
#     def has_data(self):
#         return self._computable_frame.has_data
        
#     def getLinesFor(self, for_type):
#         return self._computable_frame.getLinesFor(for_type)


#     def getBoundaries(self):
#         return self._computable_frame.getBoundaries()

#     def getAvailableStrikes(self):
#         return self._computable_frame.getAvailableStrikes()

#     def setSelectedStrike(self, strike, expiration, cost):
#         self._computable_frame.selected_strike = strike
#         self._computable_frame.selected_exp = expiration
#         self._computable_frame.selected_cost = cost
#         self._computable_frame.recalculateData()

#     def getUnderlyingPrice(self):
#         return self._computable_frame._underlying_price


