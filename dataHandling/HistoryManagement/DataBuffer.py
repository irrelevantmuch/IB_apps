
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

from dataHandling.Constants import Constants, MAIN_BAR_TYPES, DT_BAR_TYPES, MINUTES_PER_BAR, RESAMPLING_BARS, RESAMPLING_DT_BARS, RESAMPLING_SECONDS
from generalFunctionality.GenFunctions import stringRange
from dataHandling.HistoryManagement.RangeObject import RangeObject
import pandas as pd
from datetime import datetime, timedelta
from pytz import utc
from zoneinfo import ZoneInfo
from PyQt5.QtCore import pyqtSignal, QThread, QReadWriteLock, QObject


class DataBuffers(QObject):

    save_on = False

    _locks = dict()
    _buffers = dict()
    _indicators = dict()
    _date_ranges = dict()

    buffer_updater = pyqtSignal(str, dict)

    bars_to_propagate = DT_BAR_TYPES


    def __init__(self, data_folder):
        super().__init__()
        self.data_folder = data_folder

    ###### read/write protected buffer interactions

    def setBufferFor(self, uid, bar_type, buffered_data, req_ranges_list=None):
        if not ((uid, bar_type) in self._locks):
            self._locks[uid, bar_type] = QReadWriteLock()

        self._locks[uid, bar_type].lockForWrite()
        self._buffers[uid, bar_type] = buffered_data
        
        if not((uid, bar_type) in self._date_ranges) or (req_ranges_list is not None):
            self._date_ranges[uid, bar_type] = RangeObject(requested_ranges=req_ranges_list) 
        self._locks[uid, bar_type].unlock()


    def addToBuffer(self, uid, bar_type, new_data, new_req_range=None):
        self._locks[uid, bar_type].lockForWrite()
        
        if len(new_data) < 3:
            for idx, row in new_data.iterrows():
                self._buffers[uid, bar_type].loc[idx, row.keys()] = row
        else: 
            self._buffers[uid, bar_type] = new_data.combine_first(self._buffers[uid, bar_type])
        
        if (new_req_range is not None):
            self._date_ranges[uid, bar_type].addRanges(new_req_range)
            
        self._locks[uid, bar_type].unlock()
        

    def getBufferFor(self, uid, bar_type):
        
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].copy()
        finally:
            self._locks[uid, bar_type].unlock()
    

    def bufferExists(self, uid, bar_type):
        return (uid, bar_type) in self._buffers


    def containsRange(self, uid, bar_type, inner_range):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._date_ranges[uid, bar_type].containsRange(inner_range)
        finally:
            self._locks[uid, bar_type].unlock()
    

    def withinRange(self, uid, bar_type, dt_obj):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._date_ranges[uid, bar_type].withinRange(dt_obj)
        finally:
            self._locks[uid, bar_type].unlock()


    def getAllUIDs(self):
        return [key for key in self._buffers.keys]


    def getValuesForColumn(self, uid, bar_type, column_name):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].loc[column_name].values
        finally:
            self._locks[uid, bar_type].unlock()


    def getIndicesFor(self, uid, bar_type):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].index
        finally:
            self._locks[uid, bar_type].unlock()


    def getValueForColumnByIndex(self, uid, bar_type, column, indices):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].loc[indices, column].values
        finally:
            self._locks[uid, bar_type].unlock()


    def getLatestPrice(self, uid):
        smallest_bar_type = None
        for bar_type in DT_BAR_TYPES:
            if self.bufferExists(uid, bar_type):
                smallest_bar_type = bar_type
                break

        if smallest_bar_type is not None:
            self._locks[uid, smallest_bar_type].lockForRead()
            try:
                return self._buffers[uid, smallest_bar_type].iloc[-1][Constants.CLOSE].copy()
            finally:
                self._locks[uid, smallest_bar_type].unlock()
        else:
            return -1.0


    def getLatestRow(self, uid, bar_type):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].iloc[-1].copy()
        finally:
            self._locks[uid, bar_type].unlock()

        

    def getBarsFromLabelIndex(self, uid, bar_type, index):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].loc[index:].copy()
        finally:
            self._locks[uid, bar_type].unlock()


    def hasBarForDtIndex(self, uid, bar_type, dt_index):
        ts_index = dt_index.timestamp()
        self._locks[uid, bar_type].lockForRead()
        try:
            return ts_index in self._buffers[uid, bar_type].index
        finally:
            self._locks[uid, bar_type].unlock()

    def getBarForIntIndex(self, uid, bar_type, int_index):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].iloc[int_index].copy()
        finally:
            self._locks[uid, bar_type].unlock()


    def getBarsFromIntIndex(self, uid, bar_type, int_index):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].iloc[int_index:].copy()
        finally:
            self._locks[uid, bar_type].unlock()


    def setValueForColumnAtIndex(self, uid, bar_type, column, indices, values):
        self._locks[uid, bar_type].lockForWrite()
        self._buffers[uid, bar_type].loc[indices, column] = value
        self._locks[uid, bar_type].unlock()


    def getIndexAtPos(self, uid, bar_type, pos):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].index[pos]
        finally:
            self._locks[uid, bar_type].unlock()


    def getLastIndexLabel(self, uid, bar_type):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].index[-1]
        finally:
            self._locks[uid, bar_type].unlock()
        

    def getColumnValueForPos(self, uid, bar_type, column, pos):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].iloc[pos][column]
        finally:
            self._locks[uid, bar_type].unlock()


    def getColumnFor(self, uid, bar_type, column_name):
        self._locks[uid, bar_type].lockForRead()
        try:
            if column_name in self._buffers[uid, bar_type]:
                return self._buffers[uid, bar_type][column_name].copy()
            else:
                return None
        finally:
            self._locks[uid, bar_type].unlock()


    ##################### Sorting

    def sortIndex(self, uid, bar_type, ascending=True):
        self._locks[uid, bar_type].lockForWrite()
        self._buffers[uid, bar_type].sort_index(ascending=ascending, inplace=True)
        self._locks[uid, bar_type].unlock()


    def sortValuesForColumn(self, uid, bar_type, column, ascending=True):
        self._locks[uid, bar_type].lockForWrite()
        self._buffers[uid, bar_type].sort_values(column, ascending=ascending, inplace=True)
        self._locks[uid, bar_type].unlock()


   ##################### Range management


    def getMissingRangesFor(self, uid, bar_type, desired_range):
        self._locks[uid, bar_type].lockForRead()
        try:
            current_ranges = self._date_ranges[uid, bar_type].getRanges()
            return self.determineMissingRanges(desired_range, current_ranges)
        finally:
            self._locks[uid, bar_type].unlock()


    def getRangesForBuffer(self, uid, bar_type):
        self._locks[uid, bar_type].lockForRead()
        try:
            if (uid, bar_type) in self._date_ranges:
                return self._date_ranges[uid, bar_type].getRanges()
            return []
        finally:
            self._locks[uid, bar_type].unlock()


    def determineMissingRanges(self, desired_range, current_ranges):
        desired_start, desired_end = desired_range
        missing_ranges = []
        current_start = desired_start

        for start, end in current_ranges:
            if start > current_start:  # There is a gap before this range begins
                # Ensure we add a gap only if it's within the desired range
                if current_start < min(desired_end, start):
                    missing_ranges.append((current_start, min(desired_end, start)))
            current_start = max(current_start, end)  # Move current_start beyond the current range
        
        # After processing all existing ranges, check if there's still a gap at the end
        if current_start < desired_end:
            missing_ranges.append((current_start, desired_end))
        return missing_ranges


   ##################### Indicator addition

    def setIndicatorValues(self, uid, bar_type, new_value_dict):
        
        self._locks[uid, bar_type].lockForWrite()
        if not((uid, bar_type) in self._indicators):
            self._indicators[uid, bar_type] = dict()
        self._indicators[uid, bar_type].update(new_value_dict)
        self._locks[uid, bar_type].unlock()


    def getIndicatorValues(self, uid, bar_type, indicators):
        self._locks[uid, bar_type].lockForRead()
        try:
            if ((uid, bar_type) in self._indicators) and all(indicator in self._indicators[uid, bar_type] for indicator in indicators):
                ind_dict = {ind: value for ind, value in self._indicators[uid, bar_type].items() if ind in indicators}
                return ind_dict
            else:
                return None
        finally:
            self._locks[uid, bar_type].unlock()
        
 

    ##################### Loading and saving

    def loadBuffers(self, stock_list=None, force_load=False, reset_existing_buffers=False, bar_types=MAIN_BAR_TYPES):
        if reset_existing_buffers:
            self._buffers = dict()
        
        for uid in stock_list:
            for bar_type in bar_types:
                    #we only load if not loaded yet as an already loaded buffer likely contains more data
                if not self.bufferExists(uid, bar_type):
                    self.loadExistingBuffer(uid, bar_type)

        self.buffer_updater.emit(Constants.DATA_LOADED_FROM_FILE, {'uids': list(stock_list.keys())})


    def loadExistingBuffer(self, uid, bar_type):
        try:
            file_name = self.data_folder + str(uid) + '_' + bar_type + '.pkl'
            existing_buffer = pd.read_pickle(file_name)
            self.setBufferFor(uid, bar_type, existing_buffer, req_ranges_list=existing_buffer.attrs['requested_ranges'])
        except Exception as inst:
            pass


    def saveBuffer(self, uid, bar_type):
        file_name = self.data_folder + str(uid) + '_' + bar_type + '.pkl'
        self._locks[uid, bar_type].lockForRead()
        
        cols_to_exclude = ['rsi', 'up_ema', 'down_ema']
        temp_df = self._buffers[uid, bar_type][self._buffers[uid, bar_type].columns.difference(cols_to_exclude)]
        temp_df.attrs['requested_ranges'] = self._date_ranges[uid, bar_type].getRequestedRanges()
        temp_df.to_pickle(file_name)

        self._locks[uid, bar_type].unlock()


    ##################### Processing

    def hasData(self):
        return len(self._buffers) == 0


    def isSavableBartype(self, bar_type):
        return MINUTES_PER_BAR[bar_type] >= 5


    def processNewData(self, data_dict, propagate_data=False):
            #we want to reuse these so names for clarity
        curr_bar_type = data_dict['bar type']
        updated_bar_types = [curr_bar_type]
        uid = data_dict['key']
        
        if len(data_dict['data']) > 0:
            
                #we put the new data in the buffer
            if self.bufferExists(uid, curr_bar_type):
                self.addToBuffer(uid, curr_bar_type, data_dict['data'], new_req_range=data_dict['requested_range'])
            else:
                self.setBufferFor(uid, curr_bar_type, data_dict['data'], req_ranges_list=[data_dict['requested_range']])

            first_indices = {curr_bar_type: data_dict['data'].index.min()}
            last_indices = {curr_bar_type: data_dict['data'].index.max()}
            greater_bars = []
            
            if propagate_data:
                    
                    #we want to use the updated bars on lower time frames to complete bars on higher time frames
                greater_bars = self.getBarsAbove(curr_bar_type)

                for to_bar_type in greater_bars:

                    from_bar_type = self.getUpdateBarType(to_bar_type)
                    if (from_bar_type in first_indices):    #this ensures the from has been updated, but may be superfluous
                        new_indices, return_type = self.propagateUpdates(uid, from_bar_type, to_bar_type, data_dict['requested_range'])
                        if len(new_indices) > 0:
                            first_indices[to_bar_type] = new_indices.min()
                            last_indices[to_bar_type] = new_indices.max()
                            updated_bar_types.append(to_bar_type)

                #other components need to know the data is updated
            self.buffer_updater.emit(Constants.HAS_NEW_DATA, {'uid': uid, 'updated_from': first_indices, 'update_through': last_indices, 'bars': [curr_bar_type] + greater_bars, 'state': 'update'})

                #if it was proper fetch we want to save
            if (data_dict['requested_range'] is not None) and self.save_on:
                for bar_type in updated_bar_types:
                    if self.isSavableBartype(bar_type): self.saveBuffer(uid, bar_type)
            

    def propagateToHighOrderBars(self, origin_bars, to_bar_type):
        origin_bars['datetime_utc'] = pd.to_datetime(origin_bars.index, unit='s') 
        origin_bars['datetime_nyc'] = origin_bars['datetime_utc'].dt.tz_localize(utc).dt.tz_convert(Constants.NYC_TIMEZONE)
        origin_bars.set_index('datetime_nyc', inplace=True)

        if to_bar_type == Constants.FOUR_HOUR_BAR:
            updated_bars = origin_bars.resample('4H').agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last', Constants.VOLUME: 'sum'}).dropna()
        elif to_bar_type == Constants.DAY_BAR:
            origin_bars = origin_bars.between_time('09:30', '15:59')
            updated_bars = origin_bars.resample('D').agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last', Constants.VOLUME: 'sum'}).dropna()

        updated_bars.index = updated_bars.index.map(lambda x: int(x.timestamp()))
        updated_bars.index.name = None
        
        updated_indices = updated_bars.index
        return updated_indices, updated_bars
        
        
    def propagateToLowerOrderBars(self, origin_bars, to_bar_type):
        indices_for_grouping = ((origin_bars.index - Constants.BASE_TIMESTAMP_NY) // RESAMPLING_SECONDS[to_bar_type]) * RESAMPLING_SECONDS[to_bar_type] + Constants.BASE_TIMESTAMP_NY
        origin_bars['Grouping Indices'] = indices_for_grouping.tolist()

        updated_bars = origin_bars.groupby('Grouping Indices').agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last', Constants.VOLUME: 'sum'}).dropna()
        updated_bars.index.name = None

        updated_indices = updated_bars.index
        return updated_indices, updated_bars    


    def propagateUpdates(self, uid, from_bar_type, to_bar_type, new_req_range, update_full=True):
        updatable_range = self.getUpdatableRange(new_req_range, uid, from_bar_type, to_bar_type)
        updated_indices = pd.Int64Index([])

            # we ensure the origin data exists
        if updatable_range is not None:
            if self.bufferExists(uid, from_bar_type):
                from_frame = self.getBufferFor(uid, from_bar_type)
                    
                existing_indices = from_frame.index
                indices_in_range = existing_indices[(existing_indices >= updatable_range[0].timestamp()) & (existing_indices < updatable_range[1].timestamp())]
                origin_bars = from_frame.loc[indices_in_range]

                if to_bar_type == Constants.FOUR_HOUR_BAR or to_bar_type == Constants.DAY_BAR:
                    updated_indices, updated_bars = self.propagateToHighOrderBars(origin_bars, to_bar_type)
                else:
                    updated_indices, updated_bars = self.propagateToLowerOrderBars(origin_bars, to_bar_type)

                if self.bufferExists(uid, to_bar_type):   
                    self.addToBuffer(uid, to_bar_type, updated_bars, new_req_range=updatable_range)
                else:
                    self.setBufferFor(uid, to_bar_type, updated_bars, req_ranges_list=[updatable_range])
            
        return updated_indices, to_bar_type


    def getNearestNineThirties(self, dt):
        dt_nyc_time = dt.astimezone(ZoneInfo(Constants.NYC_TIMEZONE))
        current_day_930 = dt_nyc_time.replace(hour=9, minute=30, second=0, microsecond=0)
        previous_930 = current_day_930 if dt_nyc_time >= current_day_930 else current_day_930 - timedelta(days=1)
        next_930 = current_day_930 if dt_nyc_time < current_day_930 else current_day_930 + timedelta(days=1)
        return previous_930.astimezone(utc), next_930.astimezone(utc)


    def capAtFour(self, dt):
        cap_time = dt.astimezone(ZoneInfo(Constants.NYC_TIMEZONE)).replace(hour=16, minute=0, second=0, microsecond=0)
        return min(dt, cap_time.astimezone(utc))

    def barFollowing(self, dt, bar_type):
        freq = RESAMPLING_DT_BARS[bar_type]
        return pd.Timestamp(dt).ceil(freq).to_pydatetime()


    def barPreceeding(self, dt, bar_type):
        freq = RESAMPLING_DT_BARS[bar_type]
        return pd.Timestamp(dt).floor(freq).to_pydatetime()


    def getUpdatableRange(self, new_range, uid, from_bar_type, to_bar_type):
        if to_bar_type == Constants.DAY_BAR:
            timestamp_before, timestamp_after = self.getNearestNineThirties(new_range[0])
            end_time = self.capAtFour(new_range[1])     #don't think this is necesarry
        else:
            timestamp_before = self.barPreceeding(new_range[0], to_bar_type)
            timestamp_after = self.barFollowing(new_range[0], to_bar_type)
            end_time = new_range[1]

        if self.withinRange(uid, from_bar_type, timestamp_before):
            return (timestamp_before, end_time)
        elif (timestamp_after < end_time):
            return (timestamp_after, end_time)
        else:
            return None



    def getBarsAbove(self, bar_type):
        bar_list = []
        for bar in self.bars_to_propagate:
            if (MINUTES_PER_BAR[bar] > MINUTES_PER_BAR[bar_type]):
                bar_list.append(bar)
        return bar_list


    def getUpdateBarType(self, to_bar_type):
        if to_bar_type == Constants.ONE_MIN_BAR: return Constants.ONE_MIN_BAR
        elif to_bar_type == Constants.TWO_MIN_BAR: return Constants.ONE_MIN_BAR
        elif to_bar_type == Constants.THREE_MIN_BAR: return Constants.ONE_MIN_BAR
        elif to_bar_type == Constants.FIVE_MIN_BAR: return Constants.ONE_MIN_BAR
        elif to_bar_type == Constants.FIFTEEN_MIN_BAR: return Constants.FIVE_MIN_BAR
        elif to_bar_type == Constants.HOUR_BAR: return Constants.FIFTEEN_MIN_BAR
        elif to_bar_type == Constants.FOUR_HOUR_BAR: return Constants.HOUR_BAR
        elif to_bar_type == Constants.DAY_BAR: return Constants.FIFTEEN_MIN_BAR



    def moveIndex(self, time_index, bar_type, forward=True):
        shift = relativedelta(minutes=MINUTES_PER_BAR[bar_type])
        if forward:
            return time_index + shift
        else:
            return time_index - shift


    def augmentBarWith(self, uid, bar_type, index, new_bar):
        if new_bar[Constants.LOW] < self.getValueForColumnByIndex(uid, bar_type, Constants.LOW, index):
            self.setValueForColumnAtIndex(self, uid, bar_type, Constants.LOW, index, new_bar[Constants.LOW])
        if new_bar[Constants.HIGH] > self.getValueForColumnByIndex(uid, bar_type, Constants.HIGH, index):
            self.setValueForColumnAtIndex(self, uid, bar_type, Constants.HIGH, index, new_bar[Constants.HIGH])
        if new_bar[Constants.VOLUME] > self.getValueForColumnByIndex(uid, bar_type, Constants.VOLUME, index):
            self.setValueForColumnAtIndex(self, uid, bar_type, Constants.VOLUME, index, new_bar[Constants.VOLUME])
        self.setValueForColumnAtIndex(self, uid, bar_type, Constants.CLOSE, index, new_bar[Constants.CLOSE])


    def getBarFromIndices(self, uid, from_bar_type, indices):
        bar_open = self.getValueForColumnByIndex(uid, from_bar_type, Constants.OPEN, indices[0])
        bar_close = self.getValueForColumnByIndex(uid, from_bar_type, Constants.CLOSE, indices[-1])
        bar_volume = sum(self.getValueForColumnByIndex(uid, from_bar_type, Constants.VOLUME, indices).values)
        bar_low = self.getValueForColumnByIndex(uid, from_bar_type, Constants.LOW, indices).min()
        bar_high = self.getValueForColumnByIndex(uid, from_bar_type, Constants.HIGH, indices).max()
        return {Constants.OPEN: bar_open, Constants.HIGH: bar_high, Constants.LOW: bar_low, Constants.CLOSE: bar_close, Constants.VOLUME: bar_volume}

    
