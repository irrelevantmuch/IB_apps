from datetime import datetime, timedelta, time, date
from dateutil.relativedelta import relativedelta
from pandas import to_datetime as to_pandas_datetime
from pytz import timezone


from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5 import QtCore

from scipy.stats import linregress

import requests
import numpy as np
import pandas as pd
import json

from generalFunctionality.GenFunctions import calculateCorrelation
from dataHandling.Constants import Constants, TableType, MINUTES_PER_BAR
from dataHandling.DataProcessor import DataProcessor
from .ComparisonDataWrapper import ComparisonDataWrapper


class ComparisonProcessor(DataProcessor):

    selected_bar_type = Constants.FIVE_MIN_BAR
    minutes_per_bar = MINUTES_PER_BAR
    period_days = {'Day': 1, '2 Day': 2, '5 Day': 5, 'Month': 30, '2 Months': 60}

    selected_duration = 'Day'

    show_line = True

    check_list = None
    regular_hours = True
    primary_graph_data = None
    focus_graph_data = None
    focus_list = None
    comparison_list = None
    conversion_type = Constants.INDEXED
    yesterday_close = True

    selected_date = date.today()

    def __init__(self, history_manager, bar_types, stock_list):
        self.data_object = ComparisonDataWrapper()
        super().__init__(history_manager, stock_list)
        self.bar_types = bar_types
        

    def setStockList(self, stock_list):
        self.check_list = {key: True for key in stock_list.keys()}
        super().setStockList(stock_list)


    def getDataObject(self):
        return self.data_object


    def moveToThread(self, thread):
        self.data_object.moveToThread(thread)
        super().moveToThread(thread)


    @pyqtSlot(str, dict)
    def bufferUpdate(self, signal, sub_signal):
        if signal == Constants.HAS_NEW_DATA:
            uid = sub_signal['uid']
            if uid in self._stock_list:
                self.updateFrameForHistory(uid)

            
        elif signal == Constants.ALL_DATA_LOADED or signal == Constants.DATA_LOADED_FROM_FILE or signal == Constants.HISTORICAL_UPDATE_COMPLETE:
            self.updateFrameForHistory()


    def updateFrameForHistory(self, uids=None, selected_tab=None, forced_reset=False):
        if uids is None:
            uids = [uid for uid in self._stock_list]

        if self.stock_df is None:
            self.initDataFrame()
        else:
            self.previous_df = self.stock_df.copy()
        
        # if table_type is None or table_type == TableType.index_corr:
        if selected_tab is None:
            # self.calculateAutoCorrelation()
            self.recalculateGraphData(uids, forced_reset=forced_reset)
        else:
            if selected_tab == 2:
                pass
                # self.calculateAutoCorrelation()
            else:
                self.recalculateGraphData(uids, forced_reset=forced_reset)        
      

    def initDataFrame(self):
        keys = self._stock_list.keys()
        self.stock_df = pd.DataFrame( {Constants.PRICE: pd.Series(dtype='float'),
                                        Constants.CORR_VALUES: pd.Series(dtype='object'),
                                        Constants.STALE: pd.Series(dtype='bool'), Constants.CALCULATED_AT: pd.Series(dtype='datetime64[ns]'), Constants.LAST_FIVE_AT: pd.Series(dtype='datetime64[ns]')}
                                , index=list(keys))
        
        self.stock_df[Constants.SYMBOL] = [self._stock_list[key][Constants.SYMBOL] for key in keys]


    @pyqtSlot(dict)
    def updateProperties(self, property_dict):
        for prop, value in property_dict.items():
            if prop == "conversion_type":
                self.conversion_type = value
            elif prop == "regular_hours_type":
                self.regular_hours = value
            elif prop == "date_selection_type":
                self.selected_date = value.toPyDate()
            elif prop == "yesterday_close_type":
                self.yesterday_close = value
            elif prop == "bar_change_type":
                self.selected_bar_type = value
            elif prop == "period_duration":
                self.selected_duration = value
        self.recalculateGraphData(forced_reset=True)
            

    @pyqtSlot(dict)
    def setCheckLists(self, check_list):
        self.check_list = check_list
        self.recalculateGraphData(forced_reset=True)
    

    def getSuperfluousStocks(self, previous_comparison_list):
        superfluous_list = dict()
        for uid in previous_comparison_list.keys():
            if not(uid in self._stock_list):
                superfluous_list[uid] = previous_comparison_list[uid]

        return superfluous_list


    def recalculateGraphData(self, uids=None, forced_reset=False):
        # print(f"ComparisonProcessor.recalculateGraphData {uids}")
        if uids is None:
            self.primary_graph_data = dict()
            uids = list(self._stock_list.keys())

        print(f"ComparisonProcessor.recalculateGraphData {uids}")
        if self.check_list is not None:
            self.recalculateGraphLines(uids, self.check_list)
            self.recalcFocusData()
            self.data_object.updatePrimaryGraphData(self.primary_graph_data, forced_reset=forced_reset)


    def recalculateGraphLines(self, uids, check_list):
        print(f"ComparisonProcessor.recalculateGraphLines {uids} {check_list}")
        time_indices, bar_spec_frames = self.getTimeFilteredBars(uids, check_list)

        for (key, filtered_data_frame) in bar_spec_frames.items():
            symbol = self._stock_list[key][Constants.SYMBOL]
            if self.yesterday_close and self.data_buffers.bufferExists(key, Constants.DAY_BAR):
                base_price = self.getPreviousDayClose(key, self.selected_date)
            else:
                base_price = filtered_frame.iloc[0][Constants.CLOSE]
            graph_line = self.calculateSingleLine(filtered_data_frame, base_price, time_indices, symbol)
            if graph_line is not None:
                self.primary_graph_data[key] = graph_line
    

    def recalcFocusData(self):
        pass

        # if (self.primary_graph_data is not None) and (len(self.primary_graph_data) > 0):
        #     print("ComparisonProcessor.recalcFocusData")
        #     focus_list = [next(iter(self.primary_graph_data))]

        #     focus_key_iterator = iter(focus_list)
        #     overlapping_indices = self.primary_graph_data[next(focus_key_iterator)]['time_indices']
        #     for key in focus_key_iterator:
        #         overlapping_indices = overlapping_indices.intersection(self.primary_graph_data[key]['time_indices'])

        #     focus_key_iterator = iter(focus_list)
        #     current_line = self.primary_graph_data[next(focus_key_iterator)]
        #     indexer = current_line['time_indices'].get_indexer(overlapping_indices)
        #     indexer = indexer[indexer != -1]
        #     base_line = current_line['adapted'][indexer]
        #     print(f"    How do we make a selection of this? {type(base_line)} {type(overlapping_indices)}")
        #     for key in focus_key_iterator:
        #         current_line = self.primary_graph_data[next(focus_key_iterator)]
        #         indexer = current_line['time_indices'].get_indexer(overlapping_indices)
        #         indexer = indexer[indexer != -1]
        #         base_line += current_line['adapted'][indexer]

        #     for key in self.primary_graph_data:
        #         current_line = self.primary_graph_data[key]['adapted']
        #         indexer = current_line['time_indices'].get_indexer(overlapping_indices)
        #         indexer = indexer[indexer != -1]
        #         self.primary_graph_data[key]['focus'] = current_line/base_line



    def calculateSingleLine(self, filtered_frame, base_price, time_indices, symbol):
        price_data = filtered_frame[Constants.CLOSE].values
        low_data = filtered_frame[Constants.LOW].values
        high_data = filtered_frame[Constants.HIGH].values

        print(time_indices)
        int_indices = [time_indices.index(date_index) for date_index in filtered_frame.index]
        time_index_sel = [date_index for date_index in filtered_frame.index]

        if len(filtered_frame) > 0:
            graph_line = dict()
            unix_time_indices = pd.to_datetime(time_index_sel) #, utc=False)
            unix_time_indices = (unix_time_indices.tz_localize(None) - pd.Timestamp("1970-01-01 02:00:00")) // pd.Timedelta('1s')
            
            graph_line['time_indices'] = unix_time_indices
            graph_line['label'] = symbol
            graph_line['indices'] = int_indices
            graph_line['original'] = price_data
            min_value = min(price_data)
            max_value = max(price_data)
            graph_line['adapted'] = self.convertData(price_data.copy(), base_price=base_price, min_price=min_value, max_price=max_value, to_type=self.conversion_type)
            graph_line['adapted_low'] = self.convertData(low_data.copy(), base_price=base_price, min_price=min_value, max_price=max_value, to_type=self.conversion_type)
            graph_line['adapted_high'] = self.convertData(high_data.copy(), base_price=base_price, min_price=min_value, max_price=max_value, to_type=self.conversion_type)
            
            graph_line = self.insertDayBreak(graph_line, time_index_sel)

            return graph_line

        return None


    def insertDayBreak(self, graph_line, time_index_sel):
        day_change_ind = np.where(np.diff([dt.date() for dt in time_index_sel]))[0] + 1
        graph_line['time_indices'] = np.insert(np.array(graph_line['time_indices']).astype(float), day_change_ind, np.nan)
        graph_line['indices'] = np.insert(np.array(graph_line['indices']).astype(float), day_change_ind, np.nan)
        graph_line['original'] = np.insert(np.array(graph_line['original']).astype(float), day_change_ind, np.nan)
        graph_line['adapted'] = np.insert(np.array(graph_line['adapted']).astype(float), day_change_ind, np.nan)
        graph_line['adapted_low'] = np.insert(np.array(graph_line['adapted_low']).astype(float), day_change_ind, np.nan)
        graph_line['adapted_high'] = np.insert(np.array(graph_line['adapted_high']).astype(float), day_change_ind, np.nan)
        return graph_line


    def generateTimeIndices(self, start_time, end_time, bar_type, inclusive=False):
        print("ComparisonProcessor.generateTimeIndices")
        if bar_type == Constants.DAY_BAR:
            time_delta = timedelta(days=1)
        else:            
            bar_minutes = self.minutes_per_bar[bar_type]
            time_delta = timedelta(minutes=bar_minutes)

        if inclusive:
            end_time_ind = end_time
        else:
            end_time_ind = end_time - time_delta

        print("ComparisonProcessor.generateTimeIndices")
        index_list = [start_time]
        new_date = start_time
        while new_date < end_time_ind:
            new_date = new_date+time_delta
            if self.barWithinHours(new_date, bar_type):
                index_list.append(new_date)
            
        nyc_timezone = timezone(Constants.NYC_TIMEZONE)
        index_list = [nyc_timezone.localize(dt) for dt in index_list]
        index_list = to_pandas_datetime(index_list).tolist()
        print("ComparisonProcessor.generateTimeIndices")
        print(index_list)
        return index_list


    def barWithinHours(self, bar, bar_type):
        if self.selected_bar_type == Constants.DAY_BAR:
            return True
        elif self.regular_hours:
            if bar_type == Constants.HOUR_BAR:
                first_hour_day = 9; last_hour_day = 16; first_minutes_day = 0
            else:
                first_hour_day = 9; last_hour_day = 16; first_minutes_day = 30
            
            return (time(first_hour_day, first_minutes_day) <= bar.time() <= time(last_hour_day, 0))
        return True


    def getEndDate(self):
        if self.selected_duration == 'Max':
            days = 1+(date.today() - self.selected_date).days
        else:
            days = self.period_days[self.selected_duration]
        return (self.selected_date + timedelta(days=days))


    def getDatetimeRange(self):
        print(f"ComparisonProcessor.getDatetimeRange {self.selected_date}")
        bar_type = self.selected_bar_type
        
        print(f"ComparisonProcessor.getDatetimeRange 1")
        start_time = datetime.combine(self.selected_date, time(hour=0, minute=0))
        print(f"ComparisonProcessor.getDatetimeRange 11")
        end_time = datetime.combine(self.getEndDate(), time(hour=0, minute=0))
        print(f"ComparisonProcessor.getDatetimeRange 111")
        time_indices = self.generateTimeIndices(start_time, end_time, bar_type)
        print(f"ComparisonProcessor.getDatetimeRange 1111")
        nyc_timezone = timezone(Constants.NYC_TIMEZONE)
        print(f"ComparisonProcessor.getDatetimeRange 11111")
        pandas_start_time = to_pandas_datetime(nyc_timezone.localize(start_time))
        print(f"ComparisonProcessor.getDatetimeRange 111111")
        pandas_end_time = to_pandas_datetime(nyc_timezone.localize(end_time))
        
        return pandas_start_time, pandas_end_time, time_indices


    def getPreviousDayClose(self, key, start_date):
        day_frame = self.data_buffers.getBufferFor(key, Constants.DAY_BAR)
        
        # print(type(day_frame.index))
        # print(day_frame.index.dtype)
        # print(type(start_date))
        
        datetime_version = datetime(start_date.year, start_date.month, start_date.day)
        closest_index = day_frame.index.get_loc(datetime_version, method='ffill')
        closest_label = day_frame.index[closest_index]

        return day_frame.loc[closest_label, Constants.CLOSE]


    def getTimeFilteredBars(self, uids, check_list):
        print("ComparisonProcessor.getTimeFilteredBars")
        start_time, end_time, time_indices = self.getDatetimeRange()
        filtered_bar_frames = dict()
        for key in uids:
            print(f"Is this the obstacle? {self.data_buffers.bufferExists(key, self.selected_bar_type)}")
            if self.data_buffers.bufferExists(key, self.selected_bar_type) and check_list[key]:
                bar_frame = self.data_buffers.getBufferFor(key, self.selected_bar_type)
                print(f"What do we get for {self._stock_list[key]} {self.selected_bar_type}")
                print(bar_frame.index)
                filtered_frame = bar_frame.loc[(bar_frame.index>=start_time) & (bar_frame.index<end_time)]
                print(filtered_frame.index)
                if len(filtered_frame) > 0:
                    filtered_bar_frames[key] = filtered_frame

        return time_indices, filtered_bar_frames
        

    def convertData(self, stock_price, base_price, min_price, max_price, to_type):

        if to_type == Constants.NORMALIZED:
            if min_price is None: min_price = min(stock_price)
            if max_price is None: max_price = max(stock_price)
            top_bottom_delta = (max_price-min_price)
            if top_bottom_delta == 0:
                stock_price = np.full(stock_price.shape, 0.5)
            else:
                stock_price -= min_price
                stock_price /= (max_price-min_price)
        elif to_type == Constants.INDEXED:
            stock_price = (stock_price/base_price)*100
            stock_price -= 100
            
        return stock_price
    