import pandas as pd
from dataHandling.Constants import Constants
from dataHandling.DataStructures import DetailObject

from PyQt5.QtCore import pyqtSlot

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pandas import to_datetime as to_pandas_datetime
from pytz import timezone

import sys
from generalFunctionality.GenFunctions import addRSIsEMAs
from dataHandling.HistoryManagement.BufferedManager import BufferedDataManager

class LiveBufferManager(BufferedDataManager):

    counter = 0
    short_term_buffers = dict()
    live_data_on = False

    live_stock_feats = dict()


    def updateBuffers(self):
        pass


    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, data_dict):
        if self.live_data_on:
            if signal == Constants.HISTORICAL_REQUEST_COMPLETED:
                # if ~self.data_loaded:
                #     self.processHistory(data_dict)
                # else:
                self.updateBars(data_dict)
            elif signal == Constants.HISTORICAL_GROUP_COMPLETE:
                print("WHEN DO WE COME HERE >>>>>>>>>>>>")
                self.makeHistoricalRequests()
     
            #self.api_updater.emit(signal, data_dict)
        else:
            super().apiUpdate(signal, data_dict)


    def setStockList(self, buffering_stocks):
        super().setStockList(buffering_stocks)
        self.live_list = buffering_stocks

    
    # def requestUpdates(self, bar_type):
        
    #     self.live_data_on = True
    #     self.short_term_buffers = dict()

    #     for uid, value in self.live_list.items():
    #         self.short_term_buffers[uid] = pd.DataFrame(columns=[Constants.OPEN, Constants.HIGH, Constants.LOW, Constants.CLOSE, Constants.VOLUME])
    #         details = DetailObject(symbol=value[Constants.SYMBOL], exchange=value['exchange'], numeric_id=uid)
            
    #         seconds = 4*60*60
    #         self.history_manager.createBarUpdateRequests(details, bar_type, seconds, keep_up_to_date=True)
                
    #     if self.history_manager.hasQueuedRequests():
    #         self.history_manager.iterateHistoryRequests(delay=100)

    def requestUpdates(self, update_bar=Constants.FIVE_MIN_BAR, keep_up_to_date=False, update_list=None):
        self.live_data_on = True
        
        if update_list is None:
            update_list = self._buffering_stocks.copy()

        end_date = datetime.now(timezone(Constants.NYC_TIMEZONE))
        for uid in update_list:
            begin_date = None
            if self.data_buffers.bufferExists(uid, update_bar):
                existing_ranges = self.data_buffers.getRangesForBuffer(uid, update_bar)
                if len(existing_ranges) > 0:
                    begin_date = existing_ranges[-1][1]
                    update_list[uid]['begin_date'] = begin_date

            if begin_date is None:
                update_list[uid]['begin_date'] = standardBeginDateFor(end_date, update_bar)

        self.request_update_signal.emit(update_list, keep_up_to_date)


    def getLastTradingTime(self):
                # Get the current date and time
        current_time = datetime.now().astimezone(timezone('US/Eastern'))
        weekday = current_time.weekday()
        end_date = ''

        # If current time is after market closing time (20:00), get the closing time
        if current_time.hour >= 20:
            end_date = current_time.replace(hour=20, minute=0, second=0).strftime('%Y%m%d %H:%M:%S')
        # If current time is before market opening time (4:00), get the closing time of the previous day
        elif current_time.hour < 4:
            end_date = (current_time - timedelta(days=1)).replace(hour=20, minute=0, second=0).strftime('%Y%m%d %H:%M:%S')
        else:
            end_date = current_time.strftime('%Y%m%d %H:%M:%S')

        # On weekends, get the closing time of Friday
        if weekday == 5 or weekday == 6:
            last_friday = current_time - timedelta(days=(current_time.weekday() - 4))
            end_date = last_friday.replace(hour=20, minute=0, second=0).strftime('%Y%m%d %H:%M:%S')

        return end_date


    def updateLiveStockFeatures(self, keys):

        if keys is None:
            keys = self.short_term_buffers.keys()

        for uid in keys:

            stock_df = self.short_term_buffers[uid]
            
            #what do we need to get?
            #The current RSI
            rsi = stock_df.iloc[-1]['rsi']
            hourly_rsi = self.getHourlyRSI(uid)
            yesterday_close = self.getYesterdayClose(uid)
            morning_open = self.getMorningOpen(uid)
            self.live_stock_feats[uid] = {'rsi': rsi, 'hourly rsi': hourly_rsi, 'yesterday close': yesterday_close, 'morning open': morning_open}

    
    def getLiveAttributes(self, uid):
        return self.live_stock_feats[uid]


    def getHourlyRSI(self, uid):
        self.existing_buffers[uid, '1 hour'] = addRSIsEMAs(self.existing_buffers[uid, '1 hour'])

        return self.existing_buffers[uid, '1 hour'].iloc[-1]['rsi']


    def getYesterdayClose(self, uid):
        return self.existing_buffers[uid, '1 day'].iloc[-2][Constants.CLOSE]


    def getMorningOpen(self, uid):
        return self.existing_buffers[uid, '1 day'].iloc[-1][Constants.OPEN]


    def updateBars(self, bar_data):
        stock_uid = bar_data['key']
        bar_type = bar_data['bar type']
        updated_indices = bar_data['data'].index

        self.short_term_buffers[stock_uid] = bar_data['data'].combine_first(self.short_term_buffers[stock_uid])
        self.short_term_buffers[stock_uid] = addRSIsEMAs(self.short_term_buffers[stock_uid])
        self.incoorporateUpdates(stock_uid, '1 hour', updated_indices)
        
        self.api_updater.emit(Constants.HAS_NEW_DATA, {'uid': stock_uid, 'bar_types': [bar_type]})


    def incoorporateUpdates(self, uid, for_bar_type, updated_indices):
        curr_last_index = self.existing_buffers[uid, for_bar_type].index.max()
        t_last_index = curr_last_index
        
        while any(x > t_last_index for x in updated_indices):
            t_last_index = self.moveIndex(t_last_index, for_bar_type)
        
        while t_last_index >= curr_last_index:
            start_time_bar = self.barStartTime(t_last_index, for_bar_type)
            end_time_bar = self.barEndTime(t_last_index, for_bar_type)
            if any((x >= start_time_bar and x < end_time_bar) for x in updated_indices):
        
                relevant_indices = [x for x in updated_indices if (x >= self.barStartTime(t_last_index, for_bar_type) and x < self.barEndTime(t_last_index, for_bar_type))]
                new_bar = self.getBarFromIndices(uid, relevant_indices)
                
                if t_last_index in self.existing_buffers[uid, for_bar_type].index:
                    self.augmentBarWith(uid, for_bar_type, t_last_index, new_bar)        
                else:
                    self.existing_buffers[uid, for_bar_type].loc[t_last_index, [Constants.OPEN, Constants.HIGH, Constants.LOW, Constants.CLOSE, Constants.VOLUME]] = new_bar

                    
            t_last_index = self.moveIndex(t_last_index, for_bar_type, forward=False)

        self.existing_buffers[uid, for_bar_type].sort_index(inplace=True)


    def getBarFromIndices(self, uid, indices):
        bar_high = sys.float_info.min
        bar_low = sys.float_info.max
        bar_open = self.short_term_buffers[uid].loc[indices[0], Constants.OPEN]
        bar_close = self.short_term_buffers[uid].loc[indices[-1], Constants.CLOSE]
        bar_volume = sum(self.short_term_buffers[uid].loc[indices, Constants.VOLUME].values)
        
        for index in indices:
            if index in self.short_term_buffers[uid].index:
                bar = self.short_term_buffers[uid].loc[index]
                if bar[Constants.LOW] < bar_low: bar_low = bar[Constants.LOW]
                if bar[Constants.HIGH] > bar_high: bar_high = bar[Constants.HIGH]

        return {Constants.OPEN: bar_open, Constants.HIGH: bar_high, Constants.LOW: bar_low, Constants.CLOSE: bar_close, Constants.VOLUME: bar_volume}

