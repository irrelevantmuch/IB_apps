
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


from dataHandling.Constants import Constants
from dataHandling.DataStructures import DetailObject
from datetime import datetime
from dataHandling.HistoryManagement.BufferedManager import BufferedDataManager
from dataHandling.HistoryManagement.FinazonBufferedManager import FinazonBufferedDataManager

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread


class SpecBufferedDataManager:

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
    request_update_signal = pyqtSignal(dict, dict, str, bool, bool)
    group_request_signal = pyqtSignal(str)
    execute_request_signal = pyqtSignal(int)


    ################ CALLBACK

    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, data_dict):
        print(f"SpecBufferedDataManager.apiUpdate {signal}")
        if (signal == Constants.HISTORICAL_GROUP_COMPLETE) and (data_dict['type'] == 'range_group'):
            self.api_updater.emit(Constants.HISTORICAL_GROUP_COMPLETE, dict())
        else:
            super().apiUpdate(signal, data_dict)


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
                
                missing_ranges = self.data_buffers.getMissingRanges(uid, bar_type, (start_date, end_date))
                for missing_range in missing_ranges:
                    request_list.append((details, bar_type, missing_range)) 
            else:
                request_list.append((details, bar_type, (start_date, end_date)))

        return request_list


    def processRequests(self):
        
        for request in self._request_buffer:
            details, bar_type, date_range = request
            self.create_request_signal.emit(details, date_range[0], date_range[1], bar_type)

        self.group_request_signal.emit('range_group')
        self.execute_request_signal.emit(2_000)


    @pyqtSlot(str, bool, bool)
    def requestUpdates(self, update_bar=Constants.ONE_MIN_BAR, keep_up_to_date=False, propagate_updates=False, update_list=None, needs_disconnect=False):
        print(f"BufferedManager.requestUpdates {update_bar}")
        
        if update_list is None:
            update_list = self._buffering_stocks.copy()

        begin_dates = dict()
        for uid in update_list:
            begin_dates[uid] = self.getMinimumStoredDate(uid)
        
        self.request_update_signal.emit(update_list, begin_dates, update_bar, keep_up_to_date, propagate_updates)


    @pyqtSlot()
    def cancelUpdates(self):
        if self.history_manager.is_updating:
            self.reset_signal.emit()

 

class SpecbufferedManagerIB(SpecBufferedDataManager, BufferedDataManager):
    pass

class SpecbufferedManagerFZ(SpecBufferedDataManager, FinazonBufferedDataManager):
    pass
