
from dataHandling.Constants import Constants, MAIN_BAR_TYPES, QUICK_BAR_TYPES, DT_BAR_TYPES, MINUTES_PER_BAR
from dataHandling.DataStructures import DetailObject
from dataHandling.TradeManagement.UserDataManagement import readStockList
from datetime import datetime
from pytz import timezone
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from generalFunctionality.GenFunctions import barStartTime, barEndTime, standardBeginDateFor

import sys
import time
import numpy as np
import pandas as pd

from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, QThread, Qt, QEventLoop


class LiveDataManager(QObject):

    api_updater = pyqtSignal(str, dict)

    _tracking_stocks = dict()

    initial_fetch = True

    stop_tracking_signal = pyqtSignal(str)
    create_request_signal = pyqtSignal(DetailObject, datetime, datetime, str)
    request_update_signal = pyqtSignal(dict, str, bool, bool)
    group_request_signal = pyqtSignal(str)
    execute_request_signal = pyqtSignal(int)


    def __init__(self, history_manager, name="BufferedManager"):
        super().__init__()

        self.name = name
        self.history_manager = history_manager
        self.data_buffers = history_manager.getDataBuffer()
        self.data_buffers.bars_to_propagate = QUICK_BAR_TYPES
        self.history_manager.addNewListener(self, self.apiUpdate)
        

    def moveToThread(self, thread):
        super().moveToThread(thread)
        self.connectSignalsToSlots()


    def connectSignalsToSlots(self):
        self.stop_tracking_signal.connect(self.history_manager.stopTracking, Qt.QueuedConnection)
        self.create_request_signal.connect(self.history_manager.createRequestsForContract, Qt.QueuedConnection)
        self.request_update_signal.connect(self.history_manager.requestUpdates, Qt.QueuedConnection)
        self.group_request_signal.connect(self.history_manager.groupCurrentRequests, Qt.QueuedConnection)
        self.execute_request_signal.connect(self.history_manager.iterateHistoryRequests, Qt.QueuedConnection)

    
    ################ STOCK HANDLING

    def setStockTracker(self, uid, stock_inf, bar_selection, do_not_remove):
        print(f"BufferedManager.setStockList is performed on {int(QThread.currentThreadId())}")

        to_remove = [uid for uid in self._tracking_stocks if uid not in do_not_remove]
        if len(to_remove) != 0:
            self.removeStockFromList(to_remove)

        self.initial_fetch = True
        self._tracking_stocks.update({uid: stock_inf})

        self.fetchBasebars(uid, stock_inf, primary_bar=bar_selection)
        self.requestTrackingUpdates(uid, stock_inf)


    def removeStockFromList(self, to_cancel_uid):
        for uid in to_cancel_uid:
            self.stop_tracking_signal.emit(uid)
            del self._tracking_stocks[uid]


    ################ CALLBACK

    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, data_dict):
        pass
        # if signal == Constants.HISTORICAL_GROUP_COMPLETE:
        #     if len(self.stocks_to_fetch) != 0:
        #         self.fetchNextStock()
        #     elif self.partial_update:
        #         self.requestUpdates(update_list=self.update_list)
        #         self.partial_update = False
        #     else:
        #         self.api_updater.emit(Constants.ALL_DATA_LOADED, dict())
        #         self.initial_fetch = False
        # elif signal == Constants.HISTORICAL_UPDATE_COMPLETE:
        #     self.api_updater.emit(Constants.ALL_DATA_LOADED, dict())
        #     self.initial_fetch = False


    def standardBeginDateFor(self, end_date, bar_type):

        if bar_type == Constants.FIVE_MIN_BAR:
            begin_date = end_date - relativedelta(days=1)
        elif bar_type == Constants.FIFTEEN_MIN_BAR:
            begin_date = end_date - relativedelta(days=1)
        elif bar_type == Constants.HOUR_BAR:
            begin_date = end_date - relativedelta(days=3)
        elif bar_type == Constants.FOUR_HOUR_BAR:
            begin_date = end_date - relativedelta(days=7)
        elif bar_type == Constants.DAY_BAR:
            begin_date = end_date - relativedelta(days=30)
        
        return begin_date


    ################ CREATING AND TRIGGERING HISTORIC REQUEST

    def fetchBasebars(self, uid, stock_inf, bar_types=QUICK_BAR_TYPES, primary_bar=None):
        details = DetailObject(symbol=stock_inf[Constants.SYMBOL], exchange=stock_inf['exchange'], numeric_id=uid)
        
            #We'll fetch get the smallers one from the updating
        to_fetch_bars = list(set(bar_types) - set([Constants.ONE_MIN_BAR, Constants.TWO_MIN_BAR, Constants.THREE_MIN_BAR]))
        end_date = datetime.now(timezone(Constants.NYC_TIMEZONE))

        if primary_bar is not None:
            if primary_bar in to_fetch_bars:
                to_fetch_bars.remove(primary_bar)
                to_fetch_bars.insert(0, primary_bar)

        for bar_type in to_fetch_bars:
            begin_date = self.standardBeginDateFor(end_date, bar_type)
            self.create_request_signal.emit(details, begin_date, end_date, bar_type)

        self.group_request_signal.emit(uid)
        self.execute_request_signal.emit(2_000)


    def requestTrackingUpdates(self, uid, stock_inf, update_bar=Constants.ONE_MIN_BAR, prioritize_uids=True):
        print("BufferedManager.requestUpdates")
        
        end_date = datetime.now(timezone(Constants.NYC_TIMEZONE))
        stock_inf['begin_date'] = end_date - relativedelta(minutes=180)
        self.request_update_signal.emit({uid: stock_inf}, update_bar, True, prioritize_uids)
        

    ################ DATE AND RANGE HANDLING


    @pyqtSlot()
    def cancelUpdates(self):
        print("We ask for cancelling")
        if self.history_manager.is_updating:
            print("We trigger a reset in history_manager")
            self.reset_signal.emit()


    ################ DATA PROCESSING

