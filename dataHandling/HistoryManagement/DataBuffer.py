import json
from dataHandling.Constants import Constants, MAIN_BAR_TYPES, DT_BAR_TYPES, MINUTES_PER_BAR
import pandas as pd
from PyQt5.QtCore import pyqtSignal, QThread, QReadWriteLock, QObject


class DataBuffers(QObject):

    propagateUpdates = True
    saveOn = False

    _locks = dict()
    _buffers = dict()
    _date_ranges = dict()

    buffer_updater = pyqtSignal(str, dict)

    bars_to_propagate = DT_BAR_TYPES
    resampleFrame = {Constants.TWO_MIN_BAR: '2T', Constants.THREE_MIN_BAR: '3T',
                    Constants.FIVE_MIN_BAR: '5T', Constants.FIFTEEN_MIN_BAR: '15T',
                    Constants.HOUR_BAR: '1H', Constants.FOUR_HOUR_BAR: '4H', Constants.DAY_BAR: 'D'}


    ###### read/write protected buffer interactions

    def setBufferFor(self, uid, bar_type, buffered_data, ranges=None):
        if not ((uid, bar_type) in self._locks):
            self._locks[uid, bar_type] = QReadWriteLock()

        self._locks[uid, bar_type].lockForWrite()
        self._buffers[uid, bar_type] = buffered_data

        if ranges is not None:
            self._date_ranges[uid, bar_type] = ranges
        self._locks[uid, bar_type].unlock()


    def getBufferFor(self, uid, bar_type):
        
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].copy()
        finally:
            self._locks[uid, bar_type].unlock()
    

    def getRangesForBuffer(self, uid, bar_type):
        self._locks[uid, bar_type].lockForRead()
        try:
            if (uid, bar_type) in self._date_ranges:
                return self._date_ranges[uid, bar_type]
            return []
        finally:
            self._locks[uid, bar_type].unlock()


    def bufferExists(self, uid, bar_type):
        return (uid, bar_type) in self._buffers


    def getAllUIDs(self):
        return [key for key in self._buffers.keys]


    def addToBuffer(self, uid, bar_type, new_data, new_range):
        
        self._locks[uid, bar_type].lockForWrite()
        
        if len(new_data) <= 2:
            for idx, row in new_data.iterrows():
                self._buffers[uid, bar_type].loc[idx] = row
        else: 
            self._buffers[uid, bar_type] = new_data.combine_first(self._buffers[uid, bar_type])
        
        if new_range is not None:
            self._date_ranges[uid, bar_type].append(new_range)            
            self._date_ranges[uid, bar_type] = self.mergeAdjRanges(self._date_ranges[uid, bar_type])
            if bar_type == Constants.FIVE_MIN_BAR:
                print(f"Merged ranges: {uid}")

                self.printRanges(self._date_ranges[uid, bar_type])

        self._locks[uid, bar_type].unlock()
        

    def printRanges(self, date_ranges):
        for date_range in date_ranges:
            print(f"Range from: {date_range[0].strftime('%Y-%m-%d %H:%M:%S')} to {date_range[1].strftime('%Y-%m-%d %H:%M:%S')}")


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
                return self._buffers[uid, smallest_bar_type].loc[index:].copy()
            finally:
                self._locks[uid, smallest_bar_type].unlock()
        else:
            return -1.0


    def getBarsFromIndex(self, uid, bar_type, index):
        self._locks[uid, bar_type].lockForRead()
        try:
            return self._buffers[uid, bar_type].loc[index:].copy()
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


    def sortIndex(self, uid, bar_type, ascending=True):
        self._locks[uid, bar_type].lockForWrite()
        self._buffers[uid, bar_type].sort_index(ascending=ascending, inplace=True)
        self._locks[uid, bar_type].unlock()


    def sortValuesForColumn(self, uid, bar_type, column, ascending=True):
        self._locks[uid, bar_type].lockForWrite()
        self._buffers[uid, bar_type].sort_values(column, ascending=ascending, inplace=True)
        self._locks[uid, bar_type].unlock()

    def rangesFor(self, uid, bar_type):
        self._locks[uid, bar_type].lockForRead()
        value = self._buffers[uid, bar_type].attrs['ranges']
        self._locks[uid, bar_type].unlock()
        return value


    ##################### Loading and saving

    def loadBuffers(self, stock_list=None, force_load=False, reset_existing_buffers=False, bar_types=MAIN_BAR_TYPES):
        print(f"DataBuffer.loadBuffers is performed on {int(QThread.currentThreadId())}")
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
            file_name = Constants.BUFFER_FOLDER + uid + '_' + bar_type + '.pkl'
            existing_buffer = pd.read_pickle(file_name)
            self.setBufferFor(uid, bar_type, pd.read_pickle(file_name), existing_buffer.attrs['ranges'])
        except Exception as inst:
            pass
            #print(f"Cannot load {uid} due to: {inst}")


    def saveBuffer(self, uid, bar_type):
        file_name = Constants.BUFFER_FOLDER + uid + '_' + bar_type + '.pkl'
        self._locks[uid, bar_type].lockForRead()
        
        cols_to_exclude = ['rsi', 'up_ema', 'down_ema']
        temp_df = self._buffers[uid, bar_type][self._buffers[uid, bar_type].columns.difference(cols_to_exclude)]
        temp_df.attrs['ranges'] = self._date_ranges[uid, bar_type]
        temp_df.to_pickle(file_name)

        self._locks[uid, bar_type].unlock()



    ##################### Processing

    def hasData(self):
        return len(self._buffers) == 0


    def isSavableBartype(self, bar_type):
        return MINUTES_PER_BAR[bar_type] >= 5


    def processData(self, data_dict):

        print(f"DataBuffer.processData is performed on {int(QThread.currentThreadId())}")
        uid = data_dict['key']
        bar_type = data_dict['bar type']
        new_data = data_dict['data']

        if self.bufferExists(uid, bar_type):
            self.addToBuffer(uid, bar_type, new_data, data_dict['range'])
        else:
            self.setBufferFor(uid, bar_type, new_data, [data_dict['range']])
            
        self.sortIndex(uid, bar_type)
        
        first_index = {bar_type: new_data.index.min()}
        self.buffer_updater.emit(Constants.HAS_NEW_DATA, {'uid': uid, 'bars': [bar_type], 'updated_from': first_index, 'state': 'update'})

        if self.isSavableBartype(bar_type) and self.saveOn:
            self.saveBuffer(uid, bar_type)
                    

    def processUpdates(self, min_data):
        # print("DataBuffer.processUpdates")

            #we want to reuse these so names for clarity
        curr_bar_type = min_data['bar type']
        updated_bar_types = [curr_bar_type]
        uid = min_data['key']
        new_data = min_data['data']
        date_range = min_data['range']

        if len(new_data) > 0:

                #we put the new data in the buffer
            if self.bufferExists(uid, curr_bar_type):
                self.addToBuffer(uid, curr_bar_type, new_data, date_range)
            else:
                self.setBufferFor(uid, curr_bar_type, new_data, [date_range])


            if self.propagateUpdates:
                    #we want to use the updated bars on lower time frames to complete bars on higher time frames
                first_indices = {curr_bar_type: new_data.index.min()}
                greater_bars = self.getBarsAbove(curr_bar_type)
                for to_bar_type in greater_bars:
                    from_bar_type = self.getUpdateBarType(to_bar_type)
                    if (from_bar_type in first_indices):    #this ensures the from has been updated, but may be superfluous
                        first_indices[to_bar_type], return_type = self.incoorporateUpdates(uid, from_bar_type, to_bar_type, date_range)
                        updated_bar_types.append(to_bar_type)

                    #other components need to know the data is updated
                self.buffer_updater.emit(Constants.HAS_NEW_DATA, {'uid': uid, 'updated_from': first_indices, 'bars': [curr_bar_type] + greater_bars, 'state': 'update'})

                #if it was proper fetch we want to save
            if (date_range is not None) and self.saveOn:
                for bar_type in updated_bar_types:
                    self.saveBuffer(uid, bar_type)
        

    def incoorporateUpdates(self, uid, from_bar_type, to_bar_type, new_range, update_full=True):
        # print(f"DataBuffer.incoorporateUpdates {uid} {from_bar_type} {to_bar_type} {new_range}")
            # we ensure the origin data exists
        if self.bufferExists(uid, from_bar_type):
            from_frame = self.getBufferFor(uid, from_bar_type)
                
            if self.bufferExists(uid, to_bar_type):
                to_frame = self.getBufferFor(uid, to_bar_type)
                    #if there is an excisting buffer for the frame we update we assume everything up until the last index
                if len(to_frame) > 1:
                    new_first_index = to_frame.index[-2]
                else:
                    new_first_index = to_frame.index[0]
                origin_bars = from_frame.loc[new_first_index:]
                # print(new_first_index)
                # print(origin_bars)
                # print(self.resampleFrame[to_bar_type])
                updated_bars = origin_bars.resample(self.resampleFrame[to_bar_type]).agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last', Constants.VOLUME: 'sum'}).dropna()
                self.addToBuffer(uid, to_bar_type, updated_bars, new_range)
            else:
                    #if no data for the time frame excisted we simply whole frame to update
                new_first_index = from_frame.index.min()
                updated_bars = from_frame.resample(self.resampleFrame[to_bar_type]).agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last', Constants.VOLUME: 'sum'}).dropna()
                self.setBufferFor(uid, to_bar_type, updated_bars, [new_range])
        
        return new_first_index, to_bar_type



    def getBarsAbove(self, bar_type):
        bar_list = []
        for bar in self.bars_to_propagate:
            if (MINUTES_PER_BAR[bar] > MINUTES_PER_BAR[bar_type]):
                bar_list.append(bar)
        return bar_list


    def getUpdateBarType(self, bar_type):
        if bar_type == Constants.ONE_MIN_BAR: return Constants.ONE_MIN_BAR
        elif bar_type == Constants.TWO_MIN_BAR: return Constants.ONE_MIN_BAR
        elif bar_type == Constants.THREE_MIN_BAR: return Constants.ONE_MIN_BAR
        elif bar_type == Constants.FIVE_MIN_BAR: return Constants.ONE_MIN_BAR
        elif bar_type == Constants.FIFTEEN_MIN_BAR: return Constants.FIVE_MIN_BAR
        elif bar_type == Constants.HOUR_BAR: return Constants.FIFTEEN_MIN_BAR
        elif bar_type == Constants.FOUR_HOUR_BAR: return Constants.HOUR_BAR
        elif bar_type == Constants.DAY_BAR: return Constants.HOUR_BAR



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

    ##################### Range management

    def mergeAdjRanges(self, date_ranges):
        for index_right in reversed(range(len(date_ranges))):
            date_range_right = date_ranges[index_right]
            for index_left in range(index_right):
                date_range_left = date_ranges[index_left]
                if date_range_right[0] <= date_range_left[1] and date_range_right[1] > date_range_left[1]:
                    date_ranges[index_left] = (date_range_left[0], date_range_right[1])
                    del date_ranges[index_right]
                    break
                elif date_range_right[1] >= date_range_left[0] and date_range_right[0] < date_range_left[0]:
                    date_ranges[index_left] = (date_range_right[0], date_range_left[1])
                    del date_ranges[index_right]
                    break

        return date_ranges

    
