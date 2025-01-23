
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

from datetime import datetime, timedelta, date
from pytz import timezone
from PyQt6.QtCore import pyqtSlot
import numpy as np
import pandas as pd

from generalFunctionality.GenFunctions import getTradingHours
from generalFunctionality.DateTimeFunctions import getCurrentUtcTime, getLocalizedDt, convertToUtcTimestamp, todayDT, utcLocalize, dtFromDate
from dataHandling.Constants import Constants, MINUTES_PER_BAR, RESAMPLING_BARS
from dataHandling.DataProcessor import DataProcessor
from .ComparisonDataWrapper import ComparisonDataWrapper
from dataHandling.HistoryManagement.SpecBufferedManager import SpecBufferedManagerIB as BufferedDataManager


class ComparisonProcessor(DataProcessor):

    selected_bar_type = Constants.FIVE_MIN_BAR
    minutes_per_bar = MINUTES_PER_BAR
    period_days = {'Day': 1, '2 Day': 2, '5 Day': 5, 'Month': 30, '2 Months': 60}

    selected_duration = 'Max'

    show_line = True

    check_list = None
    regular_hours = False
    primary_graph_data = dict()
    focus_list = None
    conversion_type = Constants.INDEXED
    yesterday_close = False

    selected_date = todayDT()

    def __init__(self, history_manager, bar_types, stock_list):
        self.buffered_manager = BufferedDataManager(history_manager)
        super().__init__(stock_list)
        self.data_object = ComparisonDataWrapper(set(stock_list))
        
        self.bar_types = bar_types


    def setStockList(self, stock_list):
        self.check_list = {key: True for key in stock_list.keys()}
        self.data_object.setUIDs(set(stock_list.keys()))
        super().setStockList(stock_list)


    def getDataObject(self):
        return self.data_object


    def moveToThread(self, thread):
        self.data_object.moveToThread(thread)
        super().moveToThread(thread)


    @pyqtSlot(bool)
    def fetchStockRangeData(self, in_full=False):
        start_date = self.selected_date
        start_date = utcLocalize(start_date)
        end_date = dtFromDate(self.getEndDate())
        end_date = utcLocalize(end_date)
        end_date = min(end_date, getCurrentUtcTime())
        self.buffered_manager.fetchStockDataForPeriod(self.selected_bar_type, start_date, end_date, in_full)


    @pyqtSlot(str, dict)
    def bufferUpdate(self, signal, sub_signal):
        if signal == Constants.HAS_NEW_DATA:
            uid = sub_signal['uid']
            if uid in self._stock_list:
                self.updateFrameForHistory([uid])

            
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
        self.stock_df = pd.DataFrame({Constants.PRICE: pd.Series(dtype='float'),
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
                self.selected_date = dtFromDate(value.toPyDate())
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
        if uids is None:
            self.primary_graph_data = dict()
            uids = list(self._stock_list.keys())

        if self.check_list is not None:
            self.recalculateGraphLines(uids, self.check_list)
            self.recalcFocusData()
            self.data_object.updatePrimaryGraphData(self.primary_graph_data, self.selected_bar_type, forced_reset=forced_reset)


    def recalculateGraphLines(self, uids, check_list):
        for key in (k for k in uids if check_list[k]):
            time_indices, dt_indices = self.getTimeIndices(key)
            filtered_data_frame = self.getTimeFilteredBars(key, time_indices, dt_indices)
            
            if filtered_data_frame is not None:
                symbol = self._stock_list[key][Constants.SYMBOL]
                base_price = self.getBasePrice(filtered_data_frame, key, self.selected_date)
                graph_line = self.calculateSingleLine(filtered_data_frame, base_price, symbol)
                if graph_line is not None:
                    self.primary_graph_data[key] = graph_line
    

    def recalcFocusData(self):
        pass

        # if (self.primary_graph_data is not None) and (len(self.primary_graph_data) > 0):
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



    def calculateSingleLine(self, filtered_frame, base_price, symbol):
        price_data = filtered_frame[Constants.CLOSE].values
        low_data = filtered_frame[Constants.LOW].values
        high_data = filtered_frame[Constants.HIGH].values

        if len(filtered_frame) > 0:
            graph_line = dict()
            graph_line['time_indices'] = filtered_frame.index.to_numpy()
            graph_line['original_dts'] = filtered_frame['original_dts'].to_numpy()
            graph_line['label'] = symbol
            graph_line['bar_type'] = self.selected_bar_type
            graph_line['original'] = price_data
            min_value = min(price_data)
            max_value = max(price_data)
            graph_line['adapted'] = self.convertData(price_data.copy(), base_price=base_price, min_price=min_value, max_price=max_value, to_type=self.conversion_type)
            graph_line['adapted_low'] = self.convertData(low_data.copy(), base_price=base_price, min_price=min_value, max_price=max_value, to_type=self.conversion_type)
            graph_line['adapted_high'] = self.convertData(high_data.copy(), base_price=base_price, min_price=min_value, max_price=max_value, to_type=self.conversion_type)
            
            return graph_line

        return None



    def generateTimeIndices(self, start_time, end_time, bar_type):

                # Generate the full datetime range for all days
        time_stamp_range = pd.date_range(start=start_time, end=end_time, freq=RESAMPLING_BARS[bar_type])

        if bar_type != Constants.DAY_BAR:

            start_time, end_time = getTradingHours(bar_type, self.regular_hours)
            # Filter to keep only the times between 9:30 and 16:00, excluding weekends
            time_stamp_range = time_stamp_range[((time_stamp_range.time >= pd.Timestamp(start_time).time()) & 
                                         (time_stamp_range.time <= pd.Timestamp(end_time).time())) &
                                        ((time_stamp_range.dayofweek >= 0) & (time_stamp_range.dayofweek <= 4))]

        datetime_list = time_stamp_range.to_list()

        return datetime_list


    def getEndDate(self):
        if self.selected_duration == 'Max':
            days = 1+(date.today() - self.selected_date.date()).days
        else:
            days = self.period_days[self.selected_duration]
        return (self.selected_date + timedelta(days=days))


    def getTimeIndices(self, key):
        timezone = self._stock_list[key]['time_zone']

        bar_type = self.selected_bar_type
        
        start_time = getLocalizedDt(self.selected_date, timezone)
        end_time = getLocalizedDt(self.getEndDate(), timezone)
        bar_times = self.generateTimeIndices(start_time, end_time, bar_type)
        bar_timestamps = [convertToUtcTimestamp(dt) for dt in bar_times]
        return bar_timestamps, bar_times


    def getBasePrice(self, filtered_data_frame, key, start_date):
        if self.yesterday_close and self.data_buffers.bufferExists(key, Constants.DAY_BAR):
            day_frame = self.data_buffers.getBufferFor(key, Constants.DAY_BAR)
            
            datetime_for_start = datetime(start_date.year, start_date.month, start_date.day)

                #todo, make this contingent on instrument tz
            nyc_timezone = timezone(Constants.NYC_TIMEZONE)
            datetime_for_start = nyc_timezone.localize(datetime_for_start)

            try:
                closest_index = day_frame.index.get_loc(datetime_for_start)
                closest_label = day_frame.index[closest_index-1]
                return day_frame.loc[closest_label, Constants.CLOSE]
            except KeyError:
                print("Yesterday's close not present")
            
        return filtered_data_frame.iloc[0][Constants.CLOSE]



    def getTimeFilteredBars(self, key, time_indices, dt_bars):
        if self.data_buffers.bufferExists(key, self.selected_bar_type):
            bar_frame = self.data_buffers.getBufferFor(key, self.selected_bar_type)
            
            dt_series = pd.Series(data=dt_bars, index=time_indices)

            filtered_frame = bar_frame[bar_frame.index.isin(time_indices)].copy()

            filtered_frame['original_dts'] = dt_series.reindex(filtered_frame.index)
            if len(filtered_frame) > 0:
                return filtered_frame

        return None
        

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
    