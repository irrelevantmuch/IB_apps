
#############PURPOSE OF THIS CLASS IS TO ADAPT REQUEST UPDATES TO THE QUICKER FINAZON API, where the same splits are not necesarry

from dataHandling.Constants import Constants, MAIN_BAR_TYPES
from dataHandling.DataStructures import DetailObject
from .BufferedManager import BufferedDataManager

from pytz import timezone
from datetime import datetime
from dateutil.relativedelta import relativedelta

from PyQt5.QtCore import pyqtSignal, pyqtSlot


class FinazonBufferedDataManager(BufferedDataManager):


    execute_request_signal = pyqtSignal()

        # print("BufferedManager.connectSignalsToSlots finished")


    def fetchNextStock(self, bar_types=None, full_fetch=False):
        print("BufferedManager.fetchNextStock")
        if bar_types is None:
            bar_types = MAIN_BAR_TYPES

        uid, value = self.stocks_to_fetch.popitem()
        details = DetailObject(symbol=value[Constants.SYMBOL], exchange=value['exchange'], numeric_id=uid)

        for bar_type in bar_types:
            date_ranges = self.getDataRanges(uid, bar_type, full_fetch)
            for begin_date, end_date in date_ranges:
                self.create_request_signal.emit(details, begin_date, end_date, bar_type)

        if full_fetch:
            if len(self.stocks_to_fetch) > 0:
                self.fetchNextStock(bar_types=bar_types, full_fetch=full_fetch)
            else:
                # print("Or here")
                self.execute_request_signal.emit()
        else:
            # print("Via here")
            self.group_request_signal.emit('stock_group')
            self.execute_request_signal.emit()


    @pyqtSlot(str, bool, bool)
    def requestUpdates(self, update_bar=Constants.ONE_MIN_BAR, keep_up_to_date=False, propagate_updates=False, update_list=None, needs_disconnect=False, allow_splitting=True):
        print(f"BufferedManager.requestUpdates {update_bar} {keep_up_to_date} {propagate_updates}")

        if needs_disconnect: self.history_manager.cleanup_done_signal.disconnect()
        
        if update_list is None:
            update_list = self._buffering_stocks.copy()

        if allow_splitting and self.smallerThanFiveMin(update_bar):
            self.requestSmallUpdates(update_bar, keep_up_to_date, propagate_updates, update_list)
        else:
            for uid in update_list:
                update_list[uid]['begin_date'] = self.getOldestEndDate(uid)
            
            self.request_update_signal.emit(update_list, update_bar, keep_up_to_date, propagate_updates)


    def requestSmallUpdates(self, update_bar, keep_up_to_date, propagate_updates, update_list):
        print(f"BufferedManager.requestSmallUpdates")
        now_time = datetime.now(timezone(Constants.NYC_TIMEZONE))
        five_min_update_list = dict()
        for uid in update_list:
            begin_date = self.getOldestEndDate(uid)
            total_seconds = int((now_time-begin_date).total_seconds())
            if total_seconds > 10800:
                five_min_update_list[uid] = update_list[uid]
                five_min_update_list[uid]['begin_date'] = begin_date

        
        for uid in update_list:
            update_list[uid]['begin_date'] = now_time - relativedelta(minutes=180)
        
        if len(five_min_update_list) > 0:
            self.request_update_signal.emit(five_min_update_list, Constants.FIVE_MIN_BAR, False, propagate_updates)
            self.queued_update_requests.append({'bar_type': update_bar, 'update_list': update_list, 'keep_up_to_date': keep_up_to_date})
        else:
            self.request_update_signal.emit(update_list, update_bar, keep_up_to_date, propagate_updates)


