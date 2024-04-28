
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

import numpy as np
import pandas as pd
import itertools

from PyQt5.QtCore import pyqtSlot, QThread

import time
from datetime import datetime, timedelta
from pytz import timezone

from dataHandling.Constants import Constants, TableType
from dataHandling.DataProcessor import DataProcessor
from .MoversFrame import MoversFrame
from dataHandling.HistoryManagement.BufferedManager import BufferedDataManager
from generalFunctionality.GenFunctions import subtract_days, subtract_weeks, subtract_months, addRSIsEMAs, getLowsHighsCount, calculateCorrelation

class MoversProcessor(DataProcessor):

    comparison_list = None
    time_period = "Month"

    data_wrapper = None

    corr_bar_type = Constants.FIVE_MIN_BAR
    corr_bar_count = 24
        
    max_delay_min = 5

        #these don't get assigned....
    last_rsi_update = None
    last_step_update = None
    last_corr_update = None
    last_overview_update = None

    last_uid_update = dict()

    relative_frame_buffer = dict()

    comp_uid = None
    current_table_type = TableType.overview

    step_types = ['5 mins_DownSteps', '5 mins_UpSteps', '15 mins_DownSteps', '15 mins_UpSteps', '1 hour_DownSteps', '1 hour_UpSteps', '4 hours_DownSteps', '4 hours_UpSteps', '1 day_DownSteps', '1 day_UpSteps']
    period_functions = {"Day": subtract_days(1),
                    "Week": subtract_weeks(1),
                    "2 Weeks": subtract_weeks(2),
                    "Month": subtract_months(1),
                    "2 Months": subtract_months(2),
                    "3 Months": subtract_months(3),
                    "6 Months": subtract_months(6),
                    "1 Year": subtract_months(12)}


    def __init__(self, buffered_manager, bar_types, stock_list, index_list=None):
        self.data_wrapper = MoversFrame()
        self.buffered_manager = buffered_manager
        super().__init__(stock_list, index_list)
        self.bar_types = bar_types
        
        if index_list is not None:
            self.comp_uid = next(iter(index_list))


    def getDataObject(self):
        return self.data_wrapper
        

    def moveToThread(self, thread):
        self.data_wrapper.moveToThread(thread)
        super().moveToThread(thread)


    def setStockList(self, stock_list):
        print(f"MoversProcessor.setStockList is running on {int(QThread.currentThreadId())}")
        self.stock_df = None
        self.relative_frame_buffer = dict()
        super().setStockList(stock_list)
        # self.updateFrameForHistory()
        

    def isUpdatable(self):
        for stock in self._stock_list:
            if not self.buffered_manager.allRangesUpToDate(stock):
                return False

        return True


    @pyqtSlot(str, dict)
    def bufferUpdate(self, signal, sub_signal):
        if signal == Constants.HAS_NEW_DATA:
            uid = sub_signal['uid']
            if uid in self._stock_list:
                now_time = datetime.now(timezone(Constants.NYC_TIMEZONE))
                delay_dif = timedelta(seconds=3)
                # for uid, update_time in self.last_uid_update.items():
                #     if uid in uids and (now_time - update_time) < delay_dif:
                #         uids.remove(uid)

                self.last_uid_update[uid] = now_time

                if 'bars' in sub_signal:
                    bars = sub_signal['bars']
                else:
                    bars = None
                if 'updated_from' in sub_signal:
                    updated_from = sub_signal['updated_from']
                else:
                    updated_from = None

                self.updateFrameForHistory(updates_uids=[uid], bar_types=bars, updated_from=updated_from)
        elif signal == Constants.DATA_LOADED_FROM_FILE:
            self.updateFrameForHistory()



    def compSelection(self, new_index):
        self.comp_uid = new_index
        self.updateFrameForHistory()


    def updateFrameForHistory(self, updates_uids=None, bar_types=None, updated_from=None):

        if self.stock_df is None:
            self.initDataFrame()
        
        if updates_uids is None:
            updates_uids = self.stock_df.index.values

        if bar_types is not None:
            updated_pairs = list(itertools.product(updates_uids, bar_types))
        else:
            updated_pairs = list(itertools.product(updates_uids, self.bar_types))

        if len(updated_pairs) > 0:

            self.updatePrices(updates_uids)

            if self.buffered_manager.initial_fetch or (self.current_table_type == TableType.overview or self.current_table_type == TableType.from_low or self.current_table_type == TableType.from_high):
                self.calculateDayMove(updated_list=updates_uids)
                self.calculateMinMax(self.time_period, updated_list=updates_uids)
                self.calculateFromLowHigh(updated_list=updates_uids)
            
            if self.buffered_manager.initial_fetch or (self.current_table_type == TableType.rsi):
                self.computeRSIs(updated_pairs=updated_pairs, from_indices=updated_from)

            if self.buffered_manager.initial_fetch or (self.current_table_type == TableType.rel_rsi):
                self.computeRelRSIs(updated_pairs=updated_pairs)

            if self.buffered_manager.initial_fetch or (self.current_table_type == TableType.up_step or self.current_table_type == TableType.down_step):
                self.computeSteps(updated_pairs=updated_pairs)
            
            if self.buffered_manager.initial_fetch or (self.current_table_type == TableType.index_corr):
                self.calculateIndexCorrelation(updated_list=updates_uids)
            
            self.determineStale()


    @pyqtSlot(str)
    def updatePeriodSelection(self, value):
        self.time_period = value
        self.calculateMinMax(self.time_period)


    @pyqtSlot(TableType)
    def guiSelectionChange(self, value):
        self.current_table_type = value      


    def needsUpdateFor(self, table_type): 
        now_time = datetime.now(timezone(Constants.NYC_TIMEZONE))
        delay_dif = timedelta(minutes=self.max_delay_min)

        if (table_type == TableType.overview or table_type == TableType.from_low or table_type == TableType.from_high) and (self.last_overview_update is None or (now_time - self.last_overview_update) < delay_dif):
            return True
        elif (table_type == TableType.rsi or table_type == TableType.rel_rsi) and (self.last_rsi_update is None or (now_time - self.last_rsi_update) < delay_dif):
            return True
        elif (table_type == TableType.up_step or table_type == TableType.down_step) and (self.last_step_update is None or (now_time - self.last_step_update) < delay_dif):
            return True
        elif table_type == TableType.index_corr and (self.last_corr_update is None or (now_time - self.last_corr_update) < delay_dif):
            return True
        
        return False


    def initDataFrame(self):
        keys = self._stock_list.keys()

        float_cols = [Constants.PRICE, Constants.DAY_MOVE, Constants.YESTERDAY_CLOSE, Constants.MAX, Constants.MAX_FROM, Constants.MIN, Constants.MIN_FROM]
        bar_types = self.bar_types
        float_cols += [f"{bar_type}_RSI" for bar_type in bar_types]
        float_cols += [f"{bar_type}_REL_RSI" for bar_type in bar_types]
        float_cols += ['SPY_CORR', 'QQQ_CORR', 'IWM_CORR', 'Difference_RSI', 'Difference_REL_RSI']
        float_cols += [f"{bar_type}_DownSteps" for bar_type in bar_types]
        float_cols += [f"{bar_type}_UpSteps" for bar_type in bar_types]
        float_cols += [f"{bar_type}_DownSteps_Apex" for bar_type in bar_types]
        float_cols += [f"{bar_type}_UpSteps_Apex" for bar_type in bar_types]
        float_cols += [f"{bar_type}_DownSteps_Move" for bar_type in bar_types]
        float_cols += [f"{bar_type}_UpSteps_Move" for bar_type in bar_types]
        float_cols += [f"{bar_type}_DownSteps_Level" for bar_type in bar_types]
        float_cols += [f"{bar_type}_UpSteps_Level" for bar_type in bar_types]
        float_cols += [f"{key}_LOW" for key in self.period_functions.keys()]
        float_cols += [f"{key}_HIGH" for key in self.period_functions.keys()]
        float_cols += [f"{key}_LOW_DIFF" for key in self.period_functions.keys()]
        float_cols += [f"{key}_HIGH_DIFF" for key in self.period_functions.keys()]
        float_dict = {col_name: pd.Series(dtype='float') for col_name in float_cols}
        int_dict = {col_name: pd.Series(dtype='int') for col_name in [f"{bar_type}_InnerCount" for bar_type in bar_types]}
        mixed_type_dict = {Constants.MAX_DATE: pd.Series(dtype='datetime64[ns]'), Constants.MIN_DATE: pd.Series(dtype='datetime64[ns]'), "CORR_VALUES": pd.Series(dtype='object'), Constants.STALE: pd.Series(dtype='bool')}
        mixed_type_dict.update(float_dict)
        mixed_type_dict.update(int_dict)

        self.stock_df = pd.DataFrame(mixed_type_dict, index=list(keys))

        self.stock_df[Constants.SYMBOL] = [self._stock_list[key][Constants.SYMBOL] for key in keys]
        self.data_wrapper.setDataFrame(self.stock_df)


    def updatePrices(self, uid_list=None):
        for uid in uid_list:
            if self.data_buffers.bufferExists(uid, Constants.FIVE_MIN_BAR):
                latest_available_price = self.data_buffers.getLatestPrice(uid)
                self.data_wrapper.updateValueFor(uid, Constants.PRICE, latest_available_price)


    def computeSteps(self, updated_pairs=None):
        if updated_pairs is None:
            updated_pairs = itertools.product(self.stock_df.index.values, self.bar_types)

        for uid, bar_type in updated_pairs:
            
            if self.data_buffers.bufferExists(uid, bar_type):

                stock_frame = self.data_buffers.getBufferFor(uid, bar_type)
                
                try:
                    low_move, high_move, inner_bar_specs = getLowsHighsCount(stock_frame)

                    self.data_wrapper.updateValueFor(uid, bar_type + "_UpSteps", low_move['count'])
                    self.data_wrapper.updateValueFor(uid, bar_type + "_DownSteps", high_move['count'])
                    self.data_wrapper.updateValueFor(uid, bar_type + "_UpSteps_Level", low_move['level'])
                    self.data_wrapper.updateValueFor(uid, bar_type + "_DownSteps_Level", high_move['level'])
                    self.data_wrapper.updateValueFor(uid, bar_type + "_UpSteps_Apex", low_move['apex'])
                    self.data_wrapper.updateValueFor(uid, bar_type + "_DownSteps_Apex", high_move['apex'])
                    self.data_wrapper.updateValueFor(uid, bar_type + "_UpSteps_Move", low_move['move'])
                    self.data_wrapper.updateValueFor(uid, bar_type + "_DownSteps_Move", high_move['move'])

                    self.data_wrapper.updateValueFor(uid, bar_type + "_InnerCount", inner_bar_specs['count'])
                except Exception as e:
                    print(e)
                    print(f"We don't have for the combo {uid} {bar_type}")


    def computeRSIs(self, updated_pairs=None, from_indices=None):
        # print(f"MoversProcessor.computeRSIs is running on {int(QThread.currentThreadId())}")

        if updated_pairs is None:
            updated_pairs = itertools.product(self.stock_df.index.values, self.bar_types)        

        for uid, bar_type in updated_pairs:

            starting_index = None

            # start = time.time()

            if (from_indices is not None) and (bar_type in from_indices):
                starting_index = from_indices[bar_type]
            if self.data_buffers.bufferExists(uid, bar_type):
                stock_frame = self.data_buffers.getBufferFor(uid, bar_type)
                rsi_padded_frame = addRSIsEMAs(stock_frame, starting_index)
                self.data_buffers.setBufferFor(uid, bar_type, rsi_padded_frame)
                latest_rsi = rsi_padded_frame.iloc[-1]['rsi']
                self.data_wrapper.updateValueFor(uid, bar_type + "_RSI", latest_rsi)
        
            # print(f"\tRSI for {bar_type}: {time.time() - start} seconds")

        difference_rsi = self.stock_df.loc[uid, "1 day_RSI"] - (self.stock_df.loc[uid, "5 mins_RSI"] + self.stock_df.loc[uid, "15 mins_RSI"])/2
        self.data_wrapper.updateValueFor(uid, "Difference_RSI", difference_rsi)
    

    def computeRelRSIs(self, updated_pairs=None, from_index=None):
        pass
        # print("Nope")
        # if updated_pairs is None:
        #     updated_pairs = itertools.product(self.stock_df.index.values, self.bar_types)
    
        # for uid, bar_type in updated_pairs:
        #     if self.data_buffers.bufferExists(uid, bar_type) and self.data_buffers.bufferExists(self.comp_uid, bar_type):
        #         orig_buffer = self.data_buffers.getBufferFor(uid, bar_type)
        #         comp_buffer = self.data_buffers.getBufferFor(self.comp_uid, bar_type)
        #         overlapping_indices = orig_buffer.index.intersection(comp_buffer.index)
                
        #         if from_index is not None:
        #             overlapping_indices = overlapping_indices[overlapping_indices >= from_index]
                
        #         if ((uid, self.comp_uid), bar_type) in self.relative_frame_buffer:
        #             new_frame = orig_buffer.loc[overlapping_indices]/comp_buffer.loc[overlapping_indices]
        #             self.relative_frame_buffer[(uid, self.comp_uid), bar_type] = new_frame.combine_first(self.relative_frame_buffer[(uid, self.comp_uid), bar_type])
        #         else:
        #             self.relative_frame_buffer[(uid, self.comp_uid), bar_type] = orig_buffer.loc[overlapping_indices]/comp_buffer.loc[overlapping_indices]

        #         self.relative_frame_buffer[(uid, self.comp_uid), bar_type] = addRSIsEMAs(self.relative_frame_buffer[(uid, self.comp_uid), bar_type])
        #         latest_rsi = self.relative_frame_buffer[(uid, self.comp_uid), bar_type].iloc[-1]['rsi']
        #         self.data_wrapper.updateValueFor(uid, bar_type + "_REL_RSI", latest_rsi)

        #     difference_rsi = self.stock_df.loc[uid, "1 day_REL_RSI"] - (self.stock_df.loc[uid, "5 mins_REL_RSI"] + self.stock_df.loc[uid, "15 mins_REL_RSI"])/2
        #     self.data_wrapper.updateValueFor(uid, "Difference_REL_RSI", difference_rsi)


    def getCompBarData(self, uid, bar_type):
        if ((uid, self.comp_uid), bar_type) in self.relative_frame_buffer:
            return self.relative_frame_buffer[(uid, self.comp_uid), bar_type]

        return None



    def calculateMinMax(self, time_period, updated_list=None):
        if updated_list is None:
            updated_list = self.stock_df.index.values


        max_date = self.period_functions[time_period]
        print(f"MoversProcessor.calculateMinMax {max_date}")
        print(self.period_functions)
        print(time_period)
        for uid in updated_list: 
            if self.data_buffers.bufferExists(uid, Constants.DAY_BAR):
                price = self.data_wrapper.getValueFor(uid, Constants.PRICE)
                stock_frame = self.data_buffers.getBufferFor(uid, Constants.DAY_BAR)
                stock_frame = stock_frame[stock_frame.index >= max_date]

                if not stock_frame.empty:
                    self.data_wrapper.updateValueFor(uid, Constants.MAX, stock_frame[Constants.HIGH].max())
                    self.data_wrapper.updateValueFor(uid, Constants.MAX_DATE, stock_frame[Constants.HIGH].idxmax())
                    self.data_wrapper.updateValueFor(uid, Constants.MIN, stock_frame[Constants.LOW].min())
                    self.data_wrapper.updateValueFor(uid, Constants.MIN_DATE, stock_frame[Constants.LOW].idxmin())
                    
                    min_perc_move = (price - self.data_wrapper.getValueFor(uid, Constants.MIN))/self.data_wrapper.getValueFor(uid, Constants.MIN)*100
                    max_perc_move = (self.data_wrapper.getValueFor(uid, Constants.MAX)-price)/self.data_wrapper.getValueFor(uid, Constants.MAX)*100
                    self.data_wrapper.updateValueFor(uid, Constants.MIN_FROM, min_perc_move)
                    self.data_wrapper.updateValueFor(uid, Constants.MAX_FROM, max_perc_move)
    

    def calculateFromLowHigh(self, updated_list=None):
        if updated_list is None:
            updated_list = self.stock_df.index.values

        for uid in updated_list:

            if self.data_buffers.bufferExists(uid, Constants.DAY_BAR):
        
                price = self.data_wrapper.getValueFor(uid, Constants.PRICE)
                stock_frame = self.data_buffers.getBufferFor(uid, Constants.DAY_BAR)

                self.data_wrapper.updateValueFor(uid, Constants.DAY_LOW, stock_frame[Constants.LOW].iloc[-1])
                self.data_wrapper.updateValueFor(uid, Constants.DAY_HIGH, stock_frame[Constants.HIGH].iloc[-1])
                self.data_wrapper.updateValueFor(uid, Constants.DAY_LOW_DIFF, price - stock_frame[Constants.LOW].iloc[-1])
                self.data_wrapper.updateValueFor(uid, Constants.DAY_HIGH_DIFF, stock_frame[Constants.HIGH].iloc[-1] - price)

                for period_key, max_date in self.period_functions.items():
                    sub_frame = stock_frame[stock_frame.index >= max_date]

                    self.data_wrapper.updateValueFor(uid, period_key + '_' + Constants.LOW, sub_frame[Constants.LOW].min())
                    self.data_wrapper.updateValueFor(uid, period_key + '_' + Constants.HIGH, sub_frame[Constants.HIGH].max())

                    self.data_wrapper.updateValueFor(uid, period_key + '_' + Constants.LOW + '_DIFF', price - self.data_wrapper.getValueFor(uid, period_key + '_' + Constants.LOW))
                    self.data_wrapper.updateValueFor(uid, period_key + '_' + Constants.HIGH + '_DIFF', self.data_wrapper.getValueFor(uid, period_key + '_' + Constants.HIGH) - price)

        
    def calculateDayMove(self, updated_list=None):
        if updated_list is None:
            updated_list = self.stock_df.index.values
        
        for uid in updated_list:
            
            if self.data_buffers.bufferExists(uid, Constants.DAY_BAR):

                last_known_price = self.data_wrapper.getValueFor(uid, Constants.PRICE)
                
                day_buffer = self.data_buffers.getBufferFor(uid, Constants.DAY_BAR)
                if len(day_buffer) > 1:
                    last_day_close = day_buffer[Constants.CLOSE].iloc[-2]

                    price_move_perc = ((last_known_price-last_day_close)/last_day_close)*100

                    self.data_wrapper.updateValueFor(uid, Constants.DAY_MOVE, price_move_perc)
                    self.data_wrapper.updateValueFor(uid, Constants.YESTERDAY_CLOSE, last_day_close)


    def calculateIndexCorrelation(self, updated_list=None):
        if updated_list is None:
            updated_list = self.stock_df.index.values

        
        if self._index_list is not None:
            for uid_index, uid in enumerate(updated_list):
                for index_uid in self._index_list.keys():

                    index_symbol = self._index_list[index_uid][Constants.SYMBOL]

                    if self.data_buffers.bufferExists(uid, self.corr_bar_type) and self.data_buffers.bufferExists(index_uid, self.corr_bar_type):
                        stock_frame = self.data_buffers.getBufferFor(uid, self.corr_bar_type)
                        comp_frame = self.data_buffers.getBufferFor(index_uid, self.corr_bar_type)
                        overlapping_indices = stock_frame.index.intersection(comp_frame.index)
                        if len(overlapping_indices) > self.corr_bar_count:
                            overlapping_indices = overlapping_indices[-self.corr_bar_count:]
                        stock_closes = self.data_buffers.getValueForColumnByIndex(uid, self.corr_bar_type, Constants.CLOSE, overlapping_indices)
                        index_closes = self.data_buffers.getValueForColumnByIndex(index_uid, self.corr_bar_type, Constants.CLOSE, overlapping_indices)

                        self.data_wrapper.updateValueFor(uid, index_symbol + "_CORR", calculateCorrelation(stock_closes, index_closes))
                        


        

