
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


#############PURPOSE OF THIS CLASS IS TO ADAPT REQUEST UPDATES TO THE QUICKER FINAZON API, where the same splits are not necesarry

from dataHandling.Constants import Constants, MAIN_BAR_TYPES
from dataHandling.DataStructures import DetailObject
from .BufferedManager import BufferedDataManager

from pytz import timezone
from datetime import datetime
from dateutil.relativedelta import relativedelta

from PyQt6.QtCore import pyqtSignal, pyqtSlot


class FinazonBufferedDataManager(BufferedDataManager):


    execute_request_signal = pyqtSignal()


    def fetchNextStock(self, bar_types=None, full_fetch=False):
        if bar_types is None:
            bar_types = MAIN_BAR_TYPES

        uid, value = self.stocks_to_fetch.popitem()
        details = DetailObject(numeric_id=uid, **value)

        for bar_type in bar_types:
            date_ranges = self.getDataRanges(uid, bar_type, full_fetch)
            for begin_date, end_date in date_ranges:
                self.create_request_signal.emit(details, begin_date, end_date, bar_type)

        if full_fetch:
            if len(self.stocks_to_fetch) > 0:
                self.fetchNextStock(bar_types=bar_types, full_fetch=full_fetch)
            else:
                self.execute_request_signal.emit()
        else:
            self.group_request_signal.emit('stock_group')
            self.execute_request_signal.emit()


    @pyqtSlot(str, bool, bool)
    def requestUpdates(self, update_bar=Constants.ONE_MIN_BAR, keep_up_to_date=False, propagate_updates=False, update_list=None, needs_disconnect=False, allow_splitting=True):
        
        if needs_disconnect: self.history_manager.cleanup_done_signal.disconnect()
        
        if update_list is None:
            update_list = self._buffering_stocks.copy()

        if allow_splitting and self.smallerThanFiveMin(update_bar):
            self.requestSmallUpdates(update_bar, keep_up_to_date, propagate_updates, update_list)
        else:
            begin_dates = dict()
            for uid in update_list:
                begin_dates[uid] = self.getOldestEndDate(uid)
            
            self.request_update_signal.emit(update_list, update_bar, keep_up_to_date, propagate_updates)


    def requestSmallUpdates(self, update_bar, keep_up_to_date, propagate_updates, update_list):
        now_time = datetime.now(timezone(Constants.NYC_TIMEZONE))
        five_min_update_list = dict()

        begin_dates = dict()
        for uid in update_list:
            begin_date = self.getOldestEndDate(uid)
            total_seconds = int((now_time-begin_date).total_seconds())
            if total_seconds > 10800:
                five_min_update_list[uid] = update_list[uid]
                begin_dates[uid] = begin_date

        print("THERE IS CLEARLY AN ERROR HERE, WHY THE PREVIOUS LOOP ONLY TO OVERWRITE THE BEGIN_DATA???")
        for uid in update_list:
            begin_dates[uid] = now_time - relativedelta(minutes=180)
        
        if len(five_min_update_list) > 0:
            self.request_update_signal.emit(five_min_update_list, begin_dates, Constants.FIVE_MIN_BAR, False, propagate_updates)
            self.queued_update_requests.append({'bar_type': update_bar, 'update_list': update_list, 'keep_up_to_date': keep_up_to_date})
        else:
            self.request_update_signal.emit(update_list, begin_dates, update_bar, keep_up_to_date, propagate_updates)


