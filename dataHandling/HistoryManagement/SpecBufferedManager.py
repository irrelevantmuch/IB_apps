
from dataHandling.Constants import Constants, MAIN_BAR_TYPES, DT_BAR_TYPES, MINUTES_PER_BAR
from dataHandling.DataStructures import DetailObject
from dataHandling.TradeManagement.UserDataManagement import readStockList
from datetime import datetime
from pytz import timezone
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from generalFunctionality.GenFunctions import barStartTime, barEndTime, standardBeginDateFor
from .BufferedManager import BufferedDataManager

import sys
import time
import numpy as np
import pandas as pd

from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, QThread, Qt, QEventLoop


class SpecBufferedDataManager(BufferedDataManager):

    api_updater = pyqtSignal(str, dict)

    alternate_list = None
    partial_update = False
    max_day_diff = 3
    stocks_to_fetch = dict()
    updated_through = dict()
    initial_fetch = True

    queued_update_requests = []

    reset_signal = pyqtSignal()
    create_request_signal = pyqtSignal(DetailObject, datetime, datetime, str)
    request_update_signal = pyqtSignal(dict, str, bool)
    group_request_signal = pyqtSignal()
    execute_request_signal = pyqtSignal(int)


    def __init__(self, history_manager, name="BufferedManager"):
        super().__init__(history_manager, name)
        self.data_buffers.propagateUpdates = False

    ################ CALLBACK

    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, data_dict):
        if signal == Constants.HISTORICAL_GROUP_COMPLETE:
            self.api_updater.emit(Constants.HISTORICAL_GROUP_COMPLETE, dict())
            # self.initial_fetch = False


    ################ CREATING AND TRIGGERING HISTORIC REQUESTS


    def fetchStockDataForPeriod(self, bar_type, start_date, end_date):
        print(f"BufferedManager.fetchLatestStockData on thread: {int(QThread.currentThreadId())}")
        self._request_buffer = self.makeRequestList(bar_type, start_date, end_date)

        if len(self._request_buffer) > 0:
            self.processRequests()

        self.history_manager.process_owner = self       
            

    def makeRequestList(self, bar_type, start_date, end_date):
        request_list = []
        for uid, value in self._buffering_stocks.items():
            details = DetailObject(symbol=value[Constants.SYMBOL], exchange=value['exchange'], numeric_id=uid)

            if self.data_buffers.bufferExists(uid, bar_type):
                current_ranges = self.data_buffers.getRangesForBuffer(uid, bar_type)
                missing_ranges = self.getMissingRanges(current_ranges, (start_date, end_date))
                for missing_range in missing_ranges:
                    request_list.append((details, bar_type, missing_range)) 
            else:
                request_list.append((details, bar_type, (start_date, end_date)))

        return request_list


    def getMissingRanges(self, current_ranges, desired_range):
        return [desired_range]


    def processRequests(self):
        
        for request in self._request_buffer:
            details, bar_type, date_range = request
            self.create_request_signal.emit(details, date_range[0], date_range[1], bar_type)

        self.group_request_signal.emit()
        self.execute_request_signal.emit(2_000)


    @pyqtSlot(str, bool)
    def requestUpdates(self, update_bar=Constants.ONE_MIN_BAR, keep_up_to_date=False, update_list=None, needs_disconnect=False):
        print(f"BufferedManager.requestUpdates {update_bar}")
        
        if update_list is None:
            update_list = self._buffering_stocks.copy()

        now_time = datetime.now(timezone(Constants.NYC_TIMEZONE))
        for uid in update_list:
            update_list[uid]['begin_date'] = self.getBeginDate(uid, update_bar, now_time)
        
        self.request_update_signal.emit(update_list, update_bar, keep_up_to_date) #, keep_up_to_date)


    @pyqtSlot()
    def cancelUpdates(self):
        if self.history_manager.is_updating:
            self.reset_signal.emit()

 

