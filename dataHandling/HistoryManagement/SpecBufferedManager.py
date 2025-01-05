
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


    ################ CALLBACK

    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, data_dict):
        if (signal == Constants.HISTORICAL_GROUP_COMPLETE) and (data_dict['type'] == 'range_group'):
            self.api_updater.emit(Constants.HISTORICAL_GROUP_COMPLETE, data_dict)
        else:
            super().apiUpdate(signal, data_dict)


    ################ CREATING AND TRIGGERING HISTORIC REQUESTS


    def fetchStockDataForPeriod(self, bar_type, start_date, end_date, in_full):
        self._request_buffer = self.makeRequestList(bar_type, start_date, end_date, in_full)

        if len(self._request_buffer) > 0:
            for request in self._request_buffer:
                details, bar_type, date_range = request
                self.create_request_signal.emit(self.hist_id, details, date_range[0], date_range[1], bar_type, False)
            self.group_request_signal.emit('range_group')
            self.execute_request_signal.emit(2_000)
        else:
            self.api_updater.emit(Constants.ALL_DATA_LOADED, dict())

        self.history_manager.process_owner = self       
            

    def makeRequestList(self, bar_type, start_date, end_date, in_full):
        request_list = []
        for uid, value in self._buffering_stocks.items():
            details = DetailObject(numeric_id=uid, **value)

            if not(in_full) and self.data_buffers.bufferExists(uid, bar_type):
                current_ranges = self.data_buffers.getRangesForBuffer(uid, bar_type)
                missing_ranges = self.data_buffers.getMissingRangesFor(uid, bar_type, (start_date, end_date))
                print("SpecBufferedDataManager.makeRequestList")
                print(current_ranges)
                print(missing_ranges)

                for missing_range in missing_ranges:
                    request_list.append((details, bar_type, missing_range)) 
            else:
                request_list.append((details, bar_type, (start_date, end_date)))

        return request_list


    @pyqtSlot(str, bool, bool)
    def requestUpdates(self, update_bar=Constants.ONE_MIN_BAR, keep_up_to_date=False, propagate_updates=False, update_list=None, needs_disconnect=False):
        
        if update_list is None:
            update_list = self._buffering_stocks.copy()

        begin_dates = dict()
        for uid in update_list:
            begin_dates[uid] = self.getUpdateStart(uid)
        
        self.request_update_signal.emit(self.hist_id, update_list, begin_dates, update_bar, keep_up_to_date, propagate_updates)


    @pyqtSlot()
    def cancelUpdates(self):
        if self.history_manager.is_updating:
            self.reset_signal.emit(self.hist_id)

 

class SpecBufferedManagerIB(SpecBufferedDataManager, BufferedDataManager):
    pass

class SpecbufferedManagerFZ(SpecBufferedDataManager, FinazonBufferedDataManager):
    pass
