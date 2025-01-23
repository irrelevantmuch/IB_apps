
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


from dataHandling.Constants import Constants, QUICK_BAR_TYPES
from dataHandling.DataStructures import DetailObject
from pytz import timezone
from dateutil.relativedelta import relativedelta
from datetime import datetime

from PyQt6.QtCore import pyqtSignal, QObject, pyqtSlot, QThread, Qt



class LiveDataManager(QObject):

    api_updater = pyqtSignal(str, dict)

    _tracking_stocks = dict()

    initial_fetch = True

    stop_tracking_signal = pyqtSignal(int)
    create_request_signal = pyqtSignal(int, DetailObject, datetime, datetime, str)
    request_update_signal = pyqtSignal(int, dict, dict, str, bool, bool, bool)
    group_request_signal = pyqtSignal(str)
    execute_request_signal = pyqtSignal(int)


    def __init__(self, history_manager):
        super().__init__()
        self.history_manager = history_manager
        self.hist_id = self.history_manager.registerOwner()
        self.data_buffers = history_manager.getDataBuffer()
        self.data_buffers.bars_to_propagate = QUICK_BAR_TYPES
        self.history_manager.addNewListener(self, self.apiUpdate)
        

    def moveToThread(self, thread):
        super().moveToThread(thread)
        self.connectSignalsToSlots()


    def connectSignalsToSlots(self):
        self.stop_tracking_signal.connect(self.history_manager.stopTracking, Qt.ConnectionType.QueuedConnection)
        self.create_request_signal.connect(self.history_manager.createRequestsForContract, Qt.ConnectionType.QueuedConnection)
        self.request_update_signal.connect(self.history_manager.requestUpdates, Qt.ConnectionType.QueuedConnection)
        self.group_request_signal.connect(self.history_manager.groupCurrentRequests, Qt.ConnectionType.QueuedConnection)
        self.execute_request_signal.connect(self.history_manager.iterateHistoryRequests, Qt.ConnectionType.QueuedConnection)

    
    def deregister(self):
        self.history_manager.deregisterOwner(self.hist_id)
        self.history_manager.finished.emit()


    ################ STOCK HANDLING

    def setStockTracker(self, uid, stock_inf, bar_selection, do_not_remove):

        to_remove = [uid for uid in self._tracking_stocks if uid not in do_not_remove]
        if len(to_remove) != 0:
            self.removeStockFromList(to_remove)

        self.initial_fetch = True
        self._tracking_stocks.update({uid: stock_inf})
        # self.fetchBasebars(uid, stock_inf, primary_bar=bar_selection)
        self.requestTrackingUpdates(uid, stock_inf)


    def removeStockFromList(self, to_cancel_uids):
        for uid in to_cancel_uids:
            self.stop_tracking_signal.emit(uid)
            del self._tracking_stocks[uid]


    ################ CALLBACK

    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, data_dict):
        pass
        # if signal == Constants.HISTORICAL_GROUP_COMPLETE:
        #     self.requestTrackingUpdates(self._current_stock[0], self._current_stock[1])



    ################ CREATING AND TRIGGERING HISTORIC REQUEST

    # def fetchBasebars(self, uid, stock_inf, bar_types=QUICK_BAR_TYPES, primary_bar=None):
    #     details = DetailObject(numeric_id=uid, **stock_inf)
        
    #         #We'll fetch get the smallers one from the updating
    #     to_fetch_bars = list(set(bar_types) - set([Constants.ONE_MIN_BAR, Constants.TWO_MIN_BAR, Constants.THREE_MIN_BAR]))
    #     end_date = datetime.now(timezone(Constants.NYC_TIMEZONE))

    #     if primary_bar is not None:
    #         if primary_bar in to_fetch_bars:
    #             to_fetch_bars.remove(primary_bar)
    #             to_fetch_bars.insert(0, primary_bar)

    #     for bar_type in to_fetch_bars:
    #         begin_date = end_date - relativedelta(days=1)
    #         self.create_request_signal.emit(self.hist_id, details, begin_date, end_date, bar_type)

    #     self.group_request_signal.emit('stock_combo')
    #     self.execute_request_signal.emit(50)



    def requestTrackingUpdates(self, uid, stock_inf, update_bar=Constants.ONE_MIN_BAR, prioritize_uids=True):
        
        end_date = datetime.now(timezone(Constants.NYC_TIMEZONE))
        begin_date = end_date.replace(hour=4, minute=0, second=0, microsecond=0)
        self.request_update_signal.emit(self.hist_id, {uid: stock_inf}, {uid: begin_date}, update_bar, True, True, prioritize_uids)
        


    ################ DATE AND RANGE HANDLING


    @pyqtSlot()
    def cancelUpdates(self):
        if self.history_manager.is_updating:
            self.reset_signal.emit()


    ################ DATA PROCESSING

