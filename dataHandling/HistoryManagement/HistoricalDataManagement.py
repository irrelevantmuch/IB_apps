
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

from PyQt5.QtCore import QTimer, pyqtSlot, QThread, Qt, pyqtSignal

from ibapi.contract import Contract
from ibapi.common import BarData


import pandas as pd
import re

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone
import sys, math, time
from operator import attrgetter

from dataHandling.Constants import Constants
from dataHandling.DataStructures import DetailObject
from generalFunctionality.GenFunctions import dateFromString, dateToString, pdDateFromIBString, dateFromIBString

from dataHandling.DataManagement import DataManager
from dataHandling.HistoryManagement.DataBuffer import DataBuffers


class HistoricalDataManager(DataManager):
    
    _uid_by_req = dict()
    _bar_type_by_req = dict()
    _grouped_req_ids = []
    
    _hist_buffer_reqs = set()       #general log of open history requests, allows for creating unique id's
    _update_requests = set()        #open updating requests
    _is_updating = set()
    _last_update_time = dict()
    _propagating_updates = dict()
    _recently_cancelled_req_id = set()

    _priority_uids = []
    _historicalDFs = dict()          #frames for data collection 
    _request_buffer = []             #buffer holding the historical requests

    update_delay = 10
    most_recent_first = False       #order in which requests are processed

    _initial_fetch_complete = dict()
    
    queue_cap = Constants.OPEN_REQUEST_MAX

    

    regular_hours = 0
    controller = None
    process_owner = None

    cleanup_done_signal = pyqtSignal()

    
    def __init__(self, callback=None):
        super().__init__(callback=callback, name="HistoricalDataManager") 
        self.data_buffers = DataBuffers(Constants.BUFFER_FOLDER)


    def moveToThread(self, thread):
        self.data_buffers.moveToThread(thread)
        super().moveToThread(thread)


    def getDataBuffer(self):
        return self.data_buffers


    def addNewListener(self, controller, listener_function):
        self.api_updater.connect(listener_function, Qt.QueuedConnection)
        self.controller = controller


    def lockForCentralUpdating(self, controller):
        self.controller = controller
        self.api_updater.emit(Constants.HISTORY_LOCK, dict())


    def unlockCentralUpdating(self):
        self.api_updater.emit(Constants.HISTORY_UNLOCK, dict())


    @pyqtSlot(str)
    def setFrequency(self, frequency):
        units, metric = re.match(r"(\d+)([sm])$", frequency).groups()
        if metric == 'm':
            self.update_delay = 60 * float(units)
        elif metric == 's':
            self.update_delay = float(units)
        

    @pyqtSlot(str)
    def stopTracking(self, uid):
        delay = 1_000
        # print(f"HistoricalDataManager.cancelActiveRequests {int(QThread.currentThreadId())}")
        relevant_requests = [req_id for req_id, track_uid in self._uid_by_req.items() if track_uid == uid]

        for req_id in relevant_requests:
            if req_id in self._is_updating:
                self.ib_request_signal.emit({'type': 'cancelHistoricalData', 'req_id': req_id})
                self._is_updating.remove(req_id)
            if req_id in self._update_requests:
                self.ib_request_signal.emit({'type': 'cancelHistoricalData', 'req_id': req_id})
                self._update_requests.remove(req_id)
            if req_id in self._hist_buffer_reqs:
                self.ib_request_signal.emit({'type': 'cancelHistoricalData', 'req_id': req_id})
                self._hist_buffer_reqs.remove(req_id)

        self.performUidCleanupFor(uid)
        for req_id in relevant_requests:
            self.performReqIdCleanupFor(req_id)


    def performUidCleanupFor(self, uid):
        print("HistoricalDataManager.performUidCleanupFor")
        if uid in self._historicalDFs: del self._historicalDFs[uid]
        if uid in self._last_update_time: del self._last_update_time[uid]
        if uid in self._priority_uids: self._priority_uids.remove(uid)



    def performReqIdCleanupFor(self, req_id):
        self.processGroupSignal(req_id, supress_signal=True)
        if req_id in self._uid_by_req: del self._uid_by_req[req_id]
        if req_id in self._bar_type_by_req: del self._bar_type_by_req[req_id]

        self._recently_cancelled_req_id.add(req_id)
        


    @pyqtSlot()
    def cancelActiveRequests(self):
        delay = 1_000
        print(f"HistoricalDataManager.cancelActiveRequests {int(QThread.currentThreadId())}")
        self._is_updating = set()
        self.stopActiveTimers()
        self.stopActiveRequests()

        QTimer.singleShot(delay, self.performFinalCleanup)
        

    def performFinalCleanup(self):
        self.cleanupReqDicts()
        self.cleanup_done_signal.emit()
        

    def cleanupReqDicts(self):
        print("HistoricalDataManager.cleanupReqDicts")
        self._historicalDFs = dict()
        self._is_updating = set()
        self._uid_by_req = dict()
        self._bar_type_by_req = dict()
        self._grouped_req_ids = []
        self._last_update_time = dict()
        self._priority_uids = []


    def stopActiveTimers(self):
        if hasattr(self, 'history_exec_timer') and (self.history_exec_timer is not None) and self.history_exec_timer.isActive():
            self.history_exec_timer.stop()

        if hasattr(self, 'earliest_req_timer') and self.earliest_req_timer.isActive():
            self.earliest_req_timer.stop()
        
        self._request_buffer = []


    def stopActiveRequests(self):
        cancelled_ids = []
        for req_id in self._is_updating:
            cancelled_ids.append(req_id)
            self.ib_request_signal.emit({'type': 'cancelHistoricalData', 'req_id': req_id})
        self._is_updating = set()

        for req_id in self._update_requests:
            cancelled_ids.append(req_id)
            self.ib_request_signal.emit({'type': 'cancelHistoricalData', 'req_id': req_id})
        self._update_requests = set()

        for req_id in self._hist_buffer_reqs:
            cancelled_ids.append(req_id)
            self.ib_request_signal.emit({'type': 'cancelHistoricalData', 'req_id': req_id})
        self._hist_buffer_reqs = set()


######## HISTORICAL DATA REQUEST CREATION


    @pyqtSlot(DetailObject, datetime, datetime, str)
    def createRequestsForContract(self, contract_details, start_date, end_date, bar_type):
        # print(f"HistoryManagement.createRequestsForContract {contract_details.symbol} {bar_type}")
        weeks, days, seconds = self.getTimeSplits(start_date, end_date)
        contract = self.getContractFor(contract_details)
        requests = self.createBufferRequests(contract, end_date, bar_type, weeks, days, seconds)

        if len(requests) > 0:
            self._request_buffer += requests
        

    def createBufferRequests(self, contract, end_date, bar_type, weeks, days, seconds):
        requests = []
        
        chunk_size = self.getWeekChunkSize(bar_type)
                # Calculate the number of full chunks and the remainder
        num_chunks, remainder = divmod(weeks, chunk_size)
        if remainder > 0: num_chunks += 1
        
        # Iterate over the chunks
        for index in range(num_chunks):
            if index == 0 and remainder > 0:
                begin_date = end_date - relativedelta(weeks=remainder)
                requests = self.addRequest(requests, contract, bar_type, f"{remainder} W", begin_date, end_date)
            else:
                begin_date = end_date - relativedelta(weeks=chunk_size)
                requests = self.addRequest(requests, contract, bar_type, f"{chunk_size} W", begin_date, end_date)
            
            end_date = begin_date

        # Handle days
        if days > 0:
            begin_date = end_date - relativedelta(days=days)
            requests = self.addRequest(requests, contract, bar_type, f"{days} D", begin_date, end_date)
            end_date = begin_date

        # Handle seconds
        if seconds > 0:
            begin_date = end_date - relativedelta(seconds=seconds)

            requests = self.addRequest(requests, contract, bar_type, f"{max(seconds, self.getMinSecondsForBarType(bar_type))} S", begin_date, end_date)
        
        return requests
      

    @pyqtSlot(str)
    def groupCurrentRequests(self, group_type: str):
        new_group = set([request.req_id for request in self._request_buffer])
        self._grouped_req_ids.append({'group_type': group_type, 'group_ids': new_group})


    def addRequest(self, requests, contract, bar_type, period, begin_date, end_date):

        req_id = self.getNextBufferReqID()
        self._hist_buffer_reqs.add(req_id)
        self.addUIDbyReq(contract.conId, req_id)
        self._bar_type_by_req[req_id] = bar_type
        requests.append(HistoryRequest(req_id, contract, end_date, period, bar_type))
        # print(f"HistoricalDataManager.addRequest {req_id} {end_date} {period} {bar_type}")
        return requests


    def getTimeSplits(self, start_date, end_date): 

        difference = end_date - start_date
        total_seconds = int(difference.total_seconds())

            # Define the number of seconds in a day and a week
        seconds_per_day = 24 * 60 * 60
        seconds_per_week = 7 * seconds_per_day

            # Calculate the number of weeks, remaining days and seconds
        num_weeks = total_seconds // seconds_per_week
        remaining_seconds = total_seconds % seconds_per_week
        num_days = remaining_seconds // seconds_per_day
        num_seconds = remaining_seconds % seconds_per_day

        return num_weeks, num_days, num_seconds


    @pyqtSlot(dict, str, bool, bool)
    @pyqtSlot(dict, str, bool, bool, bool)
    def requestUpdates(self, stock_list, bar_type, keep_up_to_date, propagate_updates=False, prioritize_uids=False):
        print(f"HistoryManagement.requestUpdates are we prioritizing? {keep_up_to_date} {propagate_updates}")
        # print([stock_inf[Constants.SYMBOL] for _, stock_inf in stock_list.items()])

        for uid, stock_inf in stock_list.items():
                
            if prioritize_uids: self._priority_uids.append(uid)

            details = DetailObject(symbol=stock_inf[Constants.SYMBOL], exchange=stock_inf['exchange'], numeric_id=uid)

            end_date = datetime.now(timezone(Constants.NYC_TIMEZONE))
            begin_date = stock_list[uid]['begin_date']
            total_seconds = int((end_date-begin_date).total_seconds())

            self.createUpdateRequests(details, bar_type, total_seconds, keep_up_to_date, propagate_updates)

        self.iterateHistoryRequests(100)        


    def createUpdateRequests(self, contract_details, bar_type, time_in_sec, keep_up_to_date=True, propagate_updates=False):
        # print(f"HistoricalDataManager.createUpdateRequests {keep_up_to_date} {propagate_updates}")
        req_id = self.getNextBufferReqID()
        uid = contract_details.numeric_id
        contract = self.getContractFor(contract_details)

        if keep_up_to_date:
            self._is_updating.add(req_id)
            self._initial_fetch_complete[req_id] = False

        self._propagating_updates[req_id] = propagate_updates

        self._historicalDFs[req_id] = pd.DataFrame(columns=[Constants.OPEN, Constants.HIGH, Constants.LOW, Constants.CLOSE, Constants.VOLUME])
        self.addUIDbyReq(uid, req_id)
        self._bar_type_by_req[req_id] = bar_type
        if time_in_sec > Constants.SECONDS_IN_DAY:
            total_days = int(math.ceil(time_in_sec/(Constants.SECONDS_IN_DAY)))
            self._request_buffer.append(HistoryRequest(req_id, contract, "", f"{total_days} D", bar_type, keep_up_to_date))
        else:
            self._request_buffer.append(HistoryRequest(req_id, contract, "", f"{(time_in_sec+300)} S", bar_type, keep_up_to_date))
        
        self._hist_buffer_reqs.add(req_id)
        self._update_requests.add(req_id)



    def addUIDbyReq(self, uid, req_id):
        if req_id in self._uid_by_req:
            for _ in range(20):
                print("*****" * 30)
                print(f"CRASH BECAUSE {req_id} IS TAKEN")
                print("*****" * 30)
            sys.exit()
        
        self._uid_by_req[req_id] = uid



    def getMinSecondsForBarType(self, bar_type): 
        if bar_type == Constants.DAY_BAR:
            return 24*3600
        elif bar_type == Constants.FOUR_HOUR_BAR:
            return 4*3600
        elif bar_type == Constants.HOUR_BAR:
            return 3600
        elif bar_type == Constants.FIFTEEN_MIN_BAR:
            return 15*60
        elif bar_type == Constants.FIVE_MIN_BAR:
            return 5*60
        elif bar_type == Constants.THREE_MIN_BAR:
            return 3*60
        elif bar_type == Constants.TWO_MIN_BAR:
            return 2*60
        elif bar_type == Constants.ONE_MIN_BAR:
            return 1*60
        else:
            return Constants.MIN_SECONDS


    def getWeekChunkSize(self, bar_type):
        if bar_type == Constants.DAY_BAR:
            return 52
        elif bar_type == Constants.FOUR_HOUR_BAR:
            return 25
        elif bar_type == Constants.HOUR_BAR:
            return 15
        elif bar_type == Constants.FIFTEEN_MIN_BAR:
            return 10
        elif bar_type == Constants.FIVE_MIN_BAR or bar_type == Constants.THREE_MIN_BAR or bar_type == Constants.TWO_MIN_BAR or bar_type == Constants.ONE_MIN_BAR:
            return 5
        else:
            return 52   

######## HISTORICAL DATA REQUEST EXECUTION

    def hasQueuedRequests(self):     
        return len(self._request_buffer) > 0


    @pyqtSlot(int)
    def iterateHistoryRequests(self, delay=11_000):
        # print(f"HistoricalDataManager on thread: {int(QThread.currentThreadId())}")
        if self.hasQueuedRequests():
            self.history_exec_timer = QTimer()
            self.history_exec_timer.timeout.connect(self.executeHistoryRequest)
            QTimer.singleShot(0, self.executeHistoryRequest)    #we want to do the first one without delay
            self.history_exec_timer.start(delay)


    @pyqtSlot()
    def executeHistoryRequest(self):
        print(f"HistoricalDataManager.executeHistoryRequest on thread: {int(QThread.currentThreadId())}")
        if self.hasQueuedRequests():
            # print("WHAT NOW?")
            if self.ib_interface.getActiveReqCount() < self.queue_cap:
                hr = self.getNextHistoryRequest()
                self._historicalDFs[hr.req_id] = pd.DataFrame(columns=[Constants.OPEN, Constants.HIGH, Constants.LOW, Constants.CLOSE, Constants.VOLUME])
                request = dict()
                request['type'] = 'reqHistoricalData'
                request['req_id'] = hr.req_id
                request['contract'] = hr.contract
                request['end_date'] = hr.getEndDateString()
                print(request['end_date'])
                request['duration'] = hr.period_string
                request['bar_type'] = hr.bar_type
                request['regular_hours'] = self.regular_hours
                request['keep_up_to_date'] = hr.keep_updating
                self.ib_request_signal.emit(request)
                self.api_updater.emit(Constants.HISTORICAL_REQUEST_SUBMITTED, {'req_id': hr.req_id})
        
        if len(self._request_buffer) == 0:
            self.history_exec_timer.stop()
            self.history_exec_timer = None


    def getNextHistoryRequest(self):
        if self.most_recent_first:
            mostRecent = max(self._request_buffer, key=attrgetter('end_date'))
            self._request_buffer.remove(mostRecent)
            return mostRecent
        else:
            return self._request_buffer.pop(0)


####################

    def getNextBufferReqID(self):
        all_reserved_requests = self._hist_buffer_reqs | self._update_requests | self._is_updating | self._recently_cancelled_req_id
        if len(all_reserved_requests) == 0:
            return Constants.BASE_HIST_DATA_REQID
        return max(all_reserved_requests) + 1


    def getContractFor(self, contract_details):
        contract = Contract()
        contract.exchange = Constants.SMART
        contract.secType = Constants.STOCK
        contract.symbol = contract_details.symbol
        contract.conId = contract_details.numeric_id
        contract.primaryExchange = contract_details.exchange
        return contract


    def isUpdatingRequest(self, req_id):
        return req_id in self._update_requests or req_id in self._is_updating


    @pyqtSlot(list)
    def fetchEarliestDates(self, stock_list, delay=50):

        self.earliest_uid_by_req = dict()
        self.earliest_date_by_uid = dict()

        for index, (uid, contract_details) in enumerate(stock_list.items()):        
            req_id = Constants.BASE_HIST_EARLIEST_REQID + index
            self.earliest_uid_by_req[req_id] = uid

            self.earliest_request_buffer[req_id] = contract_details
        self.iterateEarliestDateReqs(delay)
  

    def iterateEarliestDateReqs(self, delay):
        self.earliest_req_timer = QTimer()
        self.earliest_req_timer.timeout.connect(self.executeEarliestDateReq)
        self.earliest_req_timer.start(delay)


    def executeEarliestDateReq(self):
        if len(self.earliest_request_buffer) > 0:
            (req_id, contract_details) = self.earliest_request_buffer.popitem()

            contract = Contract()
            contract.exchange = Constants.SMART
            contract.secType = Constants.STOCK
            contract.symbol = contract_details[Constants.SYMBOL]
            contract.conId = self.earliest_uid_by_req[req_id]   ##TODO this is not ok
            contract.primaryExchange = contract_details[Constants.EXCHANGE]
                
            request = dict()
            request['type'] = 'reqHeadTimeStamp'
            request['req_id'] = req_id
            request['contract'] = contract
            self.ib_request_signal.emit(request)
            
        if len(self.earliest_request_buffer) == 0:
            self.earliest_req_timer.stop()

############### IB Interface callbacks

    
    @pyqtSlot(int, str)
    def relayEarliestDate(self, req_id, head_time_stamp):
        uid = self.earliest_uid_by_req[req_id]

        date_time_obj = dateFromString(head_time_stamp, sep='-')
        ny_timezone = timezone(Constants.NYC_TIMEZONE)
        date_time_obj = ny_timezone.localize(date_time_obj)
        self.earliest_date_by_uid[uid] = date_time_obj
        
        if req_id in self.earliest_uid_by_req:
            del self.earliest_uid_by_req[req_id]
            if len(self.earliest_uid_by_req) == 0:
                self.api_updater.emit(Constants.DATES_RETRIEVED, dict())
             
    
    def connectSignalsToSlots(self):
        super().connectSignalsToSlots()
        
        self.ib_interface.historical_bar_signal.connect(self.relayBarData, Qt.QueuedConnection)
        self.ib_interface.historical_data_end_signal.connect(self.signalHistoryDataComplete, Qt.QueuedConnection)
        self.ib_interface.historical_dates_signal.connect(self.relayEarliestDate, Qt.QueuedConnection)
        self.ib_interface.history_error.connect(self.historyError, Qt.QueuedConnection)


    @pyqtSlot(int, BarData)
    def relayBarData(self, req_id, bar):
        if (req_id in self._historicalDFs) and (req_id in self._uid_by_req) and bar.volume != 0:
            uid = self._uid_by_req[req_id]
            bar_type = self._bar_type_by_req[req_id]

            new_row = {Constants.OPEN: bar.open, Constants.HIGH: bar.high, Constants.LOW: bar.low, Constants.CLOSE: bar.close, Constants.VOLUME: float(bar.volume)}

            self._historicalDFs[req_id].loc[pdDateFromIBString(bar.date, bar_type)] = new_row

            if (req_id in self._is_updating) and self._initial_fetch_complete[req_id] and (req_id in self._last_update_time):
                if (uid in self._priority_uids) or ((time.time() - self._last_update_time[req_id]) > self.update_delay):
                    completed_req = self.getCompletedHistoryObject(req_id, None, None)
                    self.data_buffers.processUpdates(completed_req, self._propagating_updates[req_id])
                    self._last_update_time[req_id] = time.time()


    @pyqtSlot(int)
    def historyError(self, req_id):
        # print(f"HistoricalDataManager.historyError {req_id}")
        if req_id in self._uid_by_req:
            uid = self._uid_by_req[req_id]
            
            self.processGroupSignal(req_id)
            if req_id in self._update_requests:
                self._update_requests.remove(req_id)
            
            del self._uid_by_req[req_id]


    def processGroupSignal(self, req_id, supress_signal=False):
        for group_index in range(len(self._grouped_req_ids)):
            if req_id in self._grouped_req_ids[group_index]['group_ids']:
                self._grouped_req_ids[group_index]['group_ids'].remove(req_id)
                if len(self._grouped_req_ids[group_index]['group_ids']) == 0:
                    if not(supress_signal):
                        group_type = self._grouped_req_ids[group_index]['group_type']
                        self.api_updater.emit(Constants.HISTORICAL_GROUP_COMPLETE, {'type': group_type})
                    del self._grouped_req_ids[group_index]
                    return


    @pyqtSlot(int, str, str)
    def signalHistoryDataComplete(self, req_id, start, end):
        # print(f"HistoricalDataManager.signalHistoryDataComplete")
        if req_id in self._hist_buffer_reqs:
            self._hist_buffer_reqs.remove(req_id)
            completed_req = self.getCompletedHistoryObject(req_id, start, end)

            if self.isUpdatingRequest(req_id):
                self.data_buffers.processUpdates(completed_req, self._propagating_updates[req_id])
            else:
                self.data_buffers.processData(completed_req)

            self.api_updater.emit(Constants.HISTORICAL_REQUEST_COMPLETED, completed_req)
            uid = completed_req['key']
            
            self.processGroupSignal(req_id)
            if req_id in self._update_requests:
                print(self._update_requests)
                self._update_requests.remove(req_id)
                if req_id in self._is_updating:
                    self._last_update_time[req_id] = time.time()
                    self._initial_fetch_complete[req_id] = True
                if len(self._update_requests) == 0:
                    self.api_updater.emit(Constants.HISTORICAL_UPDATE_COMPLETE, {'completed_uid': uid})

            if not (req_id in self._is_updating):
                del self._uid_by_req[req_id]
                del self._bar_type_by_req[req_id]


    def getCompletedHistoryObject(self, req_id, start, end):
        completed_req = dict()
        uid = self._uid_by_req[req_id]
        completed_req['key'] = self._uid_by_req[req_id]
        completed_req['data'] = self._historicalDFs.pop(req_id)
        if (req_id in self._is_updating): self._historicalDFs[req_id] = pd.DataFrame(columns=[Constants.OPEN, Constants.HIGH, Constants.LOW, Constants.CLOSE, Constants.VOLUME])
        completed_req['req_id'] = req_id
        
        if (start is not None) and (end is not None):
            start_date = dateFromIBString(start)
            end_date = dateFromIBString(end)
            completed_req['range'] = (start_date, end_date)
        else:
            completed_req['range'] = None
        completed_req['bar type'] = self._bar_type_by_req[req_id]

        return completed_req


class HistoryRequest():

    def __init__(self, req_id, contract, end_date, period_string, bar_type, keep_updating=False):
        self.req_id = req_id
        self.contract = contract
        self.end_date = end_date
        self.period_string = period_string
        self.bar_type = bar_type
        self.keep_updating = keep_updating

    def getEndDateString(self):
        if self.end_date == "":
            return ""
        else:
            datetime_string = dateToString(self.end_date)
            return datetime_string + " US/Eastern" 



    # def createBarUpdateRequests(self, contract_details, bar_type, time_in_sec, keep_up_to_date=True):
    #     req_id = self.getNextBufferReqID()

    #     uid = contract_details.numeric_id
    #     contract = self.getContractFor(contract_details)

    #     self._historicalDFs[req_id] = pd.DataFrame(columns=[Constants.OPEN, Constants.HIGH, Constants.LOW, Constants.CLOSE, Constants.VOLUME])
        
    #     self.addUIDbyReq(uid, req_id)
    #     self._bar_type_by_req[req_id] = bar_type
    #     self._request_buffer.append(HistoryRequest(req_id, contract, "", f"{max(time_in_sec, 60)} S", bar_type, keep_up_to_date))
    #     self._hist_buffer_reqs.add(req_id)
    #     self._update_requests.add(req_id)
