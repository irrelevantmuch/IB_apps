
from dataHandling.Constants import Constants, TableType
from dataHandling.DataProcessor import DataProcessor

from datetime import datetime, timedelta
from pytz import timezone
from dateutil.relativedelta import relativedelta
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5 import QtCore

from scipy.stats import linregress

import numpy as np
import pandas as pd

import itertools


class AnalysisProcessor(DataProcessor):

    data_dict = None

    def setStockList(self, stock_list):
        super().setStockList(stock_list)
        self.data_dict = None

    def createAbstractRepresentation(self):
        self.data_dict = dict()

        for (uid, bar_type), buffer in self.buffered_manager.existing_buffers.items():

            symbol_name = self._stock_list[uid][Constants.SYMBOL]
            result_df = pd.DataFrame(columns=['GAP UP','GAP DOWN', 'PM UP', 'PM DOWN'])

            trades = self.evaluateStrategy(buffer)
            # total_profit = np.sum(trades)
            # print(f'Total profit: {total_profit}')

            if bar_type == Constants.FIFTEEN_MIN_BAR:
                
                pre_market_daily, regular_daily, after_hours_daily = self.splitFrame(buffer)

                # Create a list of datetime indices from each DataFrame
                indices = [df.index for df in [pre_market_daily, regular_daily, after_hours_daily]]
                # Find the common indices that are present in all DataFrames
                common_indices = sorted(set(indices[0]).intersection(*indices[1:]))

                # Iterate through the common indices
                for index in range(1, len(common_indices)):
                    today_index = common_indices[index]
                    yest_index = common_indices[index-1]

                    regular_bar_today = regular_daily.loc[today_index]
                    regular_bar_yest = regular_daily.loc[yest_index]
                    
                    pre_market_today = pre_market_daily.loc[today_index]

                    result_df.loc[today_index, 'GAP UP'] = (regular_bar_today[Constants.OPEN] > regular_bar_yest[Constants.CLOSE]) and (regular_bar_yest[Constants.CLOSE] > regular_bar_yest[Constants.OPEN])
                    result_df.loc[today_index, 'PM UP'] = (regular_bar_today[Constants.HIGH] > pre_market_today[Constants.HIGH])
                    result_df.loc[today_index, 'GAP DOWN'] = (regular_bar_today[Constants.OPEN] < regular_bar_yest[Constants.CLOSE]) and (regular_bar_yest[Constants.CLOSE] < regular_bar_yest[Constants.OPEN])
                    result_df.loc[today_index, 'PM DOWN'] = (regular_bar_today[Constants.LOW] < pre_market_today[Constants.LOW])

                self.data_dict[symbol_name] = result_df


    def getHeatmapData(self):

        if self.data_dict is None:
            self.createAbstractRepresentation()

        symbols = list(self.data_dict.keys())
        rows = len(symbols)
        columns = max([len(df) for df in self.data_dict.values()])

        heatmap_data = np.zeros((columns, rows), dtype=np.uint8)

        all_indices = sorted(set(itertools.chain(*[list(df.index) for df in self.data_dict.values()])))
        
        for row_h_index, df in enumerate(self.data_dict.values()):
                # Assign colors based on the values in the DataFrame
            for i, row in df.iterrows():
                col_h_index = all_indices.index(i) #if specific_date in indices else -
                if not row['GAP UP'] and not row['GAP DOWN']:
                    heatmap_data[col_h_index, row_h_index] = 0
                elif row['GAP UP'] and row['PM UP']:
                    heatmap_data[col_h_index, row_h_index] = 1
                elif row['GAP UP'] and not row['PM UP']:
                    heatmap_data[col_h_index, row_h_index] = 2
                elif row['GAP DOWN'] and row['PM DOWN']:
                    heatmap_data[col_h_index, row_h_index] = 1
                elif row['GAP DOWN'] and not row['PM DOWN']:
                    heatmap_data[col_h_index, row_h_index] = 2

        success_count = heatmap_data.sum(axis=0)
        sort_indices = np.argsort(success_count)
        sorted_heatmap = heatmap_data.T[sort_indices].T
        sorted_symbol_list = [symbols[i] for i in sort_indices]

        return sorted_heatmap, all_indices, sorted_symbol_list

    def splitFrame(self, buffer):

        # create new dataframes based on the desired time intervals
        pre_market_df = buffer.between_time('04:00', '09:30')
        regular_df = buffer.between_time('09:30', '16:00')
        after_hours_df = buffer.between_time('16:00', '20:00')

        pre_market_daily = pre_market_df.resample('D').agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last'})
        regular_daily = regular_df.resample('D').agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last'})
        after_hours_daily = after_hours_df.resample('D').agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last'})

        return pre_market_daily, regular_daily, after_hours_daily


    def evaluateStategy2(self, df):

        # Assuming premarket_df and market_df are your dataframes

        # Filter rows where price goes above the premarket high in the first 30 mins
        premarket_high = premarket_df['high'].max()
        first_30_mins = market_df.between_time('9:30', '10:00')

        over_premarket = first_30_mins[first_30_mins['high'] > premarket_high]

        # Define a function to calculate gain/loss
        def calculate_gain_loss(row):
            sell_price = premarket_high
            stop_price = row['high']
            profit_take = sell_price + 2*(sell_price - stop_price)
            return profit_take - sell_price

        # Apply the function to the rows
        over_premarket['gain_loss'] = over_premarket.apply(calculate_gain_loss, axis=1)

# # Assume df is your DataFrame, with columns: Constants.OPEN, Constants.CLOSE, Constants.HIGH, Constants.LOW, Constants.VOLUME
# df.index = pd.to_datetime(df.index)

    def evaluateStrategy(self, df, pre_open='04:00:00', open_time='09:30:00', close_time='10:30:00', stop_loss=0.05, balance=10_000):
        trades = []
        current_balance = balance
        
        # Loop over each trading day in the data
        for date in pd.date_range(df.index.min().date(), df.index.max().date(), tz=df.index.tz):
            
            # Define time intervals
            pre_open_time = pd.Timestamp(date.date().strftime('%Y-%m-%d') + ' ' + pre_open).tz_localize(df.index.tz)
            open_time_stamp = pd.Timestamp(date.date().strftime('%Y-%m-%d') + ' ' + open_time).tz_localize(df.index.tz)
            close_time_stamp = pd.Timestamp(date.date().strftime('%Y-%m-%d') + ' ' + close_time).tz_localize(df.index.tz)

            # Determine the high during the premarket period
            premarket_data = df.loc[pre_open_time:open_time_stamp-pd.Timedelta(minutes=1)]
            
            # If there is no premarket data for the day, skip to the next day
            if premarket_data.empty: 
                continue
            
            premarket_high = premarket_data[Constants.HIGH].max()

            # Check if the stock price exceeds the premarket high between 9:30 and 10:30
            open_data = df.loc[open_time_stamp:close_time_stamp]
            
            # If there is no data for the 9:30-10:30 period, skip to the next day
            if open_data.empty: 
                continue

            # If the premarket high is exceeded, place a stop sell order at this price
            if (open_data[Constants.HIGH] > premarket_high).any():
                stop_sell = premarket_high
                stop_loss_price = stop_sell + stop_loss
                profit_take_price = stop_sell - 2 * stop_loss  # Adjust the profit take price relative to the stop sell price
                
                # Determine the number of shares to trade based on available balance
                shares_to_trade = current_balance / stop_sell

                # Tracking the performance of the strategy after the stop sell
                after_sell_data = df.loc[close_time_stamp:]
                
                # If there is no data after the stop sell, skip to the next day
                if after_sell_data.empty: 
                    continue
                
                # Find the indices where the stop loss and profit take prices are hit
                stop_loss_hit = np.where(after_sell_data[Constants.LOW] < stop_loss_price)[0]
                profit_take_hit = np.where(after_sell_data[Constants.HIGH] > profit_take_price)[0]
                trade = 0
                # If the stock price hits the stop loss before hitting the profit take, record a loss
                if stop_loss_hit.size > 0 and (profit_take_hit.size == 0 or stop_loss_hit[0] < profit_take_hit[0]):
                    trade = -stop_loss * shares_to_trade  # Record the loss in dollars
                
                # If the stock price hits the profit take before hitting the stop loss, record a profit
                elif profit_take_hit.size > 0 and (stop_loss_hit.size == 0 or profit_take_hit[0] < stop_loss_hit[0]):
                    trade = (stop_sell - profit_take_price) * shares_to_trade  # Record the profit in dollars

                # Update current balance for next trade
                current_balance += trade
                trades.append(trade)

        print(f"We end up with: {current_balance}, and a maximum winner of: {max(trades)} and looser of {min(trades)}")
        return trades


