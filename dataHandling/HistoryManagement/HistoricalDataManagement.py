
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

from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData
from ibapi.ticktype import TickTypeEnum

import pandas as pd

from zoneinfo import ZoneInfo
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from pytz import utc
import sys, math, time, re
from operator import attrgetter

from generalFunctionality.DateTimeFunctions import dateFromString, dateToString, pdDateFromIBString, utcDtFromIBString
from generalFunctionality.GenFunctions import stringRange
from PyQt6.QtCore import QThread, QObject, Qt, pyqtSignal, pyqtSlot, QTimer


from dataHandling.HistoryManagement.DataBuffer import DataBuffers
from dataHandling.DataStructures import DetailObject
from dataHandling.Constants import Constants, MINUTES_PER_BAR
from dataHandling.IBConnectivity import IBConnectivity


class HistoricalDataManager(IBConnectivity):

    historical_bar_signal = pyqtSignal(int, BarData)
    historial_end_signal = pyqtSignal(int, str, str)
    cleanup_done_signal = pyqtSignal()        

    timeout_delay = 30_000
    update_delay = 10
    
    queue_cap = Constants.OPEN_REQUEST_MAX

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        
        self.initializeRequestTracking()
        self.data_buffers = DataBuffers(Constants.BUFFER_FOLDER)
        self.most_recent_first = True       #order in which requests are processed
        self.smallest_bar_first = True
        self.regular_hours = 0



    def initializeRequestTracking(self):
        
            #queue of to submit historical requests
        self._request_queue = []    

            #id's by req_id
        self._uid_by_req = dict()
        self._req_by_owner = dict()
        self._bar_type_by_req = dict()
        self._date_ranges_by_req = dict()

        self._grouped_req_ids = []
        
            #update tracking
        self._update_requests = set()        #open updating requests
        self._initial_fetch_complete = dict()
        self._keep_up_requests = set()            #open updating requests
        self._last_update_time = dict()
        self._propagating_data = dict()
        self._priority_uids = set()                #to prioritize data for live updating         
        
        self._contract_details_by_uid = dict()

            #data bufffers
        self._historical_dfs = dict()          #frames for data collection 

        self._cancelling_req_ids = set()


    def moveToThread(self, thread):
        self.data_buffers.moveToThread(thread)
        super().moveToThread(thread)


    def getDataBuffer(self):
        return self.data_buffers

    def registerOwner(self):

        owner_id = super().registerOwner()
        self._req_by_owner[owner_id] = set()
        return owner_id


    def deregisterOwner(self, owner_id):
        super().deregisterOwner(owner_id)
        del self._req_by_owner[owner_id]


    @pyqtSlot()
    def startConnection(self):
        super().startConnection()
        
        print(f"HistoricalDataManager.startConnection: {int(QThread.currentThreadId())}")
        self.timeout_timer = QTimer()
        self.timeout_timer.setInterval(self.timeout_delay)
        self.timeout_timer.timeout.connect(self.handleTimeout)

            #we connect slots to be signalled from callbacks to get on the current thread
        self.historical_bar_signal.connect(self.processHistoricalBar, Qt.ConnectionType.QueuedConnection)
        self.historial_end_signal.connect(self.processHistoricalDataEnd, Qt.ConnectionType.QueuedConnection)


    def addNewListener(self, controller, listener_function):
        self.api_updater.connect(listener_function, Qt.ConnectionType.QueuedConnection)
        
        #do something with controller?

    
    @property
    def is_updating(self):
        return len(self._keep_up_requests) > 0


    @pyqtSlot(str)
    def setFrequency(self, frequency):
        units, metric = re.match(r"(\d+)([sm])$", frequency).groups()
        if metric == 'm':
            self.update_delay = 60 * float(units)
        elif metric == 's':
            self.update_delay = float(units)
        

    @pyqtSlot(int)
    def stopTracking(self, uid):
        relevant_requests = [req_id for req_id, track_uid in self._uid_by_req.items() if track_uid == uid]
        self._cancelling_req_ids.update(relevant_requests)
        for req_id in relevant_requests:
            if req_id in self._keep_up_requests:
                self._keep_up_requests.remove(req_id)
            if req_id in self._update_requests:
                self._update_requests.remove(req_id)
            
            if self.req_id_manager.isActiveHistID(req_id):
                self.req_id_manager.clearHistReqID(req_id)
                self.makeRequest({'type': 'cancelHistoricalData', 'req_id': req_id})

        QTimer.singleShot(1_000, lambda: self.performCleanupFor(uid, relevant_requests))
        

    def performCleanupFor(self, uid, relevant_requests):
        if uid in self._historical_dfs: del self._historical_dfs[uid]
        if uid in self._priority_uids: self._priority_uids.remove(uid)

        for req_id in relevant_requests:
            self.processGroupSignal(req_id, supress_signal=True)
            if req_id in self._uid_by_req: del self._uid_by_req[req_id]
            if req_id in self._last_update_time: del self._last_update_time[req_id]
            if req_id in self._date_ranges_by_req: del self._date_ranges_by_req[req_id]
            if req_id in self._bar_type_by_req: del self._bar_type_by_req[req_id]

        self._cancelling_req_ids.difference_update(relevant_requests)


    @pyqtSlot(int)
    def cancelActiveRequests(self, owner_id=None):
        delay = 1_000
        
        self.stopActiveTimers(owner_id)        
        cancelled_ids = self.stopActiveRequests(owner_id)

        QTimer.singleShot(delay, lambda: self.performFinalCleanup(cancelled_ids))
        

    @pyqtSlot()
    def handleTimeout(self):
        print("HistoricalDataManager.handleTimeout")
        open_req_ids = self.req_id_manager.getAllHistIDs()
        for req_id in open_req_ids:
            if (req_id not in self._keep_up_requests):
                self.cleanupAndNotify(req_id)
                # self.makeRequest({'type': 'cancelHistoricalData', 'req_id': req_id})


    def performFinalCleanup(self, cancelled_ids):
        self._cancelling_req_ids.difference_update(cancelled_ids)
        self.cleanup_done_signal.emit()


    def stopActiveTimers(self, owner_id=None):
        if owner_id is not None:
            for req in reversed(self._request_queue):
                self._request_queue.remove(req)
            if len(self._request_queue) == 0:
                if hasattr(self, 'history_exec_timer') and (self.history_exec_timer is not None) and self.history_exec_timer.isActive():
                    self.history_exec_timer.stop()
        else:    
            if hasattr(self, 'history_exec_timer') and (self.history_exec_timer is not None) and self.history_exec_timer.isActive():
                self.history_exec_timer.stop()

            if hasattr(self, 'earliest_req_timer') and self.earliest_req_timer.isActive():
                self.earliest_req_timer.stop()
            
            self._request_queue = []


    def stopActiveRequests(self, owner_id=None):
        super().stopActiveRequests(owner_id)
        # active_ids = set()
        # active_ids.update(self._keep_up_requests)
        # active_ids.update(self._update_requests)
        # active_ids.update(self._all_req_ids)
        active_ids = self.req_id_manager.getAllHistIDs()
        if owner_id is not None:
            active_ids = active_ids.intersection(self._req_by_owner[owner_id])

        self._cancelling_req_ids.update(active_ids)
        for req_id in active_ids:
            self.makeRequest({'type': 'cancelHistoricalData', 'req_id': req_id})

        self._keep_up_requests = self._keep_up_requests - active_ids
        self._update_requests = self._update_requests - active_ids

        self.req_id_manager.clearHistReqIDs(active_ids)

        return active_ids


######## HISTORICAL DATA REQUEST CREATION


    @pyqtSlot(int, DetailObject, datetime, datetime, str)
    @pyqtSlot(int, DetailObject, datetime, datetime, str, bool)
    def createRequestsForContract(self, owner_id, contract_details, start_date, end_date, bar_type, propagate_data=False):
        weeks, days, seconds = self.getTimeSplits(start_date, end_date)
        
        requests = self.createBufferRequests(owner_id, contract_details, end_date, bar_type, weeks, days, seconds, propagate_data)

        if len(requests) > 0:
            self._request_queue += requests
        

    def createBufferRequests(self, owner_id, contract_details, end_date, bar_type, weeks, days, seconds, propagate_data=False):
        requests = []
        
        contract = self.getContractFor(contract_details)
        self._contract_details_by_uid[contract_details.numeric_id] = contract_details

        chunk_size = self.getWeekChunkSize(bar_type)
            # Calculate the number of full chunks and the remainder
        num_chunks, remainder = divmod(weeks, chunk_size)
        if remainder > 0: num_chunks += 1
        
            # Iterate over the chunks
        for index in range(num_chunks):
            if index == 0 and remainder > 0:
                begin_date = end_date - relativedelta(weeks=remainder)
                requests = self.addRequestTo(owner_id, requests, contract, bar_type, f"{remainder} W", begin_date, end_date, propagate_data)
            else:
                begin_date = end_date - relativedelta(weeks=chunk_size)
                requests = self.addRequestTo(owner_id, requests, contract, bar_type, f"{chunk_size} W", begin_date, end_date, propagate_data)
            
            end_date = begin_date

            # Handle days
        if days > 0:
            begin_date = end_date - relativedelta(days=days)
            requests = self.addRequestTo(owner_id, requests, contract, bar_type, f"{days} D", begin_date, end_date, propagate_data)
            end_date = begin_date

            # Handle seconds
        if seconds > 0:
            begin_date = end_date - relativedelta(seconds=seconds)
            requests = self.addRequestTo(owner_id, requests, contract, bar_type, f"{max(seconds, self.getMinSecondsForBarType(bar_type))} S", begin_date, end_date, propagate_data)
        
        return requests
      

    @pyqtSlot(str)
    def groupCurrentRequests(self, group_type: str):
        new_group = set([request.req_id for request in self._request_queue])
        self._grouped_req_ids.append({'group_type': group_type, 'group_ids': new_group})


    def addRequestTo(self, owner_id, requests, contract, bar_type, period, begin_date, end_date, propagate_data=False):
        req_id = self.req_id_manager.getNextHistID(self._cancelling_req_ids)
        self._req_by_owner[owner_id].add(req_id)
        self.addUIDbyReq(contract.conId, req_id)
        self._propagating_data[req_id] = propagate_data
        self._bar_type_by_req[req_id] = bar_type
        self._date_ranges_by_req[req_id] = (begin_date, end_date)
        requests.append(HistoryRequest(req_id, contract, end_date, period, bar_type))
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
        if remaining_seconds < seconds_per_day:
            num_days = 0
            num_seconds = remaining_seconds
        else:
            num_days = int(math.ceil(remaining_seconds/seconds_per_day))
            num_seconds = 0

        return num_weeks, num_days, num_seconds


    @pyqtSlot(int, dict, dict, str, bool, bool)
    @pyqtSlot(int, dict, dict, str, bool, bool, bool)
    def requestUpdates(self, owner_id, stock_list, begin_dates, bar_type, keep_up_to_date, propagate_updates=False, prioritize_uids=False):
        print("HistoricalDataManager.requestUpdates")
        for uid, stock_inf in stock_list.items():
                
            if prioritize_uids:
                self._priority_uids.add(uid)

            details = DetailObject(numeric_id=uid, **stock_inf)

            end_date = datetime.now(utc)
            total_seconds = int((end_date-begin_dates[uid]).total_seconds())
            date_range = (begin_dates[uid], end_date)
            self.createUpdateRequests(owner_id, details, bar_type, total_seconds, date_range, keep_up_to_date, propagate_updates)

        self.iterateHistoryRequests(100)        


    @pyqtSlot(Contract)
    def turnOnRealtimeBarsFor(self, contract):        
        req_id = self.req_id_manager.getNextHistID(self._cancelling_req_ids)
        self._uid_by_req[req_id] = contract.conId
        self.makeRequest({'type': 'reqRealTimeBars', 'req_id': req_id, 'contract': contract})


    @pyqtSlot(str)
    def turnOffRealtimeBarsFor(self, cancel_uid):
        for req_id, uid in self._uid_by_req.items():
            if uid == cancel_uid:
                self.cancelRealTimeBars(req_id)


    def createUpdateRequests(self, owner_id, contract_details, bar_type, time_in_sec, date_range, keep_up_to_date=True, propagate_updates=False):
        req_id = self.req_id_manager.getNextHistID(self._cancelling_req_ids)
        print(req_id)
        self._req_by_owner[owner_id].add(req_id)
        uid = contract_details.numeric_id
        self._contract_details_by_uid[uid] = contract_details
        contract = self.getContractFor(contract_details)

        if keep_up_to_date:
            self._keep_up_requests.add(req_id)
            self._initial_fetch_complete[req_id] = False

        self._propagating_data[req_id] = propagate_updates

        self._historical_dfs[req_id] = pd.DataFrame(columns=[Constants.OPEN, Constants.HIGH, Constants.LOW, Constants.CLOSE, Constants.VOLUME])
        self.addUIDbyReq(uid, req_id)
        self._bar_type_by_req[req_id] = bar_type
        self._date_ranges_by_req[req_id] = date_range
        if time_in_sec > Constants.SECONDS_IN_DAY:
            total_days = int(math.ceil(time_in_sec/(Constants.SECONDS_IN_DAY)))
            self._request_queue.append(HistoryRequest(req_id, contract, "", f"{total_days} D", bar_type, keep_up_to_date))
        else:
            self._request_queue.append(HistoryRequest(req_id, contract, "", f"{(time_in_sec+300)} S", bar_type, keep_up_to_date))
        

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
        return len(self._request_queue) > 0


    @pyqtSlot(int)
    def iterateHistoryRequests(self, delay=11_000):
        if self.hasQueuedRequests():
            self.history_exec_timer = QTimer()
            self.history_exec_timer.timeout.connect(self.executeHistoryRequest)
            QTimer.singleShot(0, self.executeHistoryRequest)    #we want to do the first one without delay
            self.history_exec_timer.start(delay)


    @pyqtSlot()
    def executeHistoryRequest(self):
        if self.hasQueuedRequests():
            if self.req_id_manager.getActiveReqCount() < self.queue_cap:
                hr = self.getNextHistoryRequest()   
                self._historical_dfs[hr.req_id] = pd.DataFrame(columns=[Constants.OPEN, Constants.HIGH, Constants.LOW, Constants.CLOSE, Constants.VOLUME])
                request = dict()
                request['type'] = 'reqHistoricalData'
                request['req_id'] = hr.req_id
                request['contract'] = hr.contract
                request['end_date'] = hr.getEndDateString()
                request['duration'] = hr.period_string
                request['bar_type'] = hr.bar_type
                if hr.bar_type == Constants.DAY_BAR:
                    request['regular_hours'] = 1
                else:
                    request['regular_hours'] = self.regular_hours
                request['keep_up_to_date'] = hr.keep_updating
                if not(hr.keep_updating): self.timeout_timer.start()
                self.makeRequest(request)
                self.api_updater.emit(Constants.HISTORICAL_REQUEST_SUBMITTED, {'req_id': hr.req_id})
        
        if len(self._request_queue) == 0:
            self.history_exec_timer.stop()
            self.history_exec_timer = None


    def getNextHistoryRequest(self):
        if self.smallest_bar_first and self.most_recent_first:
            next_element = max(self._request_queue, key=lambda x: (-MINUTES_PER_BAR[x.bar_type], x.end_date))
        elif self.smallest_bar_first and self.most_recent_first:
            next_element = min(self._request_queue, key=lambda x: MINUTES_PER_BAR[x.bar_type])
        elif self.most_recent_first:
            next_element = max(self._request_queue, key=lambda x: x.end_date)
        else:
            next_element = self._request_queue[0]

        self._request_queue.remove(next_element)
        return next_element


####################


    def getContractFor(self, contract_details):
        contract = Contract()
        contract.exchange = Constants.SMART
        contract.secType = Constants.STOCK
        contract.symbol = contract_details.symbol
        contract.conId = contract_details.numeric_id
        contract.primaryExchange = contract_details.exchange
        return contract


    def isUpdateRequest(self, req_id):
        return req_id in self._update_requests or req_id in self._keep_up_requests


    @pyqtSlot(list)
    def fetchEarliestDates(self, stock_list, delay=50):

        self.earliest_uid_by_req = dict()
        self.earliest_date_by_uid = dict()

        for index, (uid, contract_details) in enumerate(stock_list.items()):        
            req_id = Constants.BASE_HIST_EARLIEST_REQID + index
            self.earliest_uid_by_req[req_id] = uid

            self.earliest_request_queue[req_id] = contract_details
        self.iterateEarliestDateReqs(delay)
  

    def iterateEarliestDateReqs(self, delay):
        self.earliest_req_timer = QTimer()
        self.earliest_req_timer.timeoutstartConnection(self.executeEarliestDateReq)
        self.earliest_req_timer.start(delay)


    def executeEarliestDateReq(self):
        if len(self.earliest_request_queue) > 0:
            (req_id, contract_details) = self.earliest_request_queue.popitem()

            contract = Contract()
            contract.exchange = Constants.SMART
            contract.secType = Constants.STOCK
            contract.symbol = contract_details[Constants.SYMBOL]
            contract.conId = self.earliest_uid_by_req[req_id]   ##TODO this is not ok
            contract.primaryExchange = contract_details[Constants.EXCHANGE]
                
            request = {'type': 'reqHeadTimeStamp', 'req_id': req_id, 'contract': contract}
            self.makeRequest(request)
            
        if len(self.earliest_request_queue) == 0:
            self.earliest_req_timer.stop()


############### IB Interface callbacks

    def headTimestamp(self, req_id: int, head_time_stamp: str):
        super().headTimestamp(req_id, head_time_stamp)
        
        self.cancelHeadTimeStamp(req_id)
        uid = self.earliest_uid_by_req[req_id]

        date_time_obj = dateFromString(head_time_stamp, sep='-')
        date_time_obj = utc.localize(date_time_obj)
        self.earliest_date_by_uid[uid] = date_time_obj
        
        if req_id in self.earliest_uid_by_req:
            del self.earliest_uid_by_req[req_id]
            if len(self.earliest_uid_by_req) == 0:
                self.api_updater.emit(Constants.DATES_RETRIEVED, dict())


    def historicalData(self, req_id, bar):
        super().historicalData(req_id, bar)
        if self.req_id_manager.isHistDataRequest(req_id):
            self.historical_bar_signal.emit(req_id, bar)
            
            

    def historicalDataUpdate(self, req_id, bar):
        super().historicalDataUpdate(req_id, bar)
        self.historical_bar_signal.emit(req_id, bar)


    @pyqtSlot(int, BarData)
    def processHistoricalBar(self, req_id, bar):
        if (req_id in self._historical_dfs) and (req_id in self._uid_by_req) and bar.volume != 0:
            uid = self._uid_by_req[req_id]
            instrument_tz = self._contract_details_by_uid[uid].time_zone
            bar_type = self._bar_type_by_req[req_id]
            new_row = {Constants.OPEN: bar.open, Constants.HIGH: bar.high, Constants.LOW: bar.low, Constants.CLOSE: bar.close, Constants.VOLUME: float(bar.volume)}

            if bar_type == Constants.DAY_BAR:   # we need a special case, because for the day bar we get a date ("20231204"), rather than unix seconds timestamps
                date_time = pd.to_datetime(bar.date, format="%Y%m%d")
                date_time = date_time.tz_localize(instrument_tz)
                self._historical_dfs[req_id].loc[int(date_time.astimezone(utc).timestamp())] = new_row
            else:
                self._historical_dfs[req_id].loc[int(bar.date)] = new_row

            if (req_id in self._keep_up_requests) and self._initial_fetch_complete[req_id] and (req_id in self._last_update_time):
                if (uid in self._priority_uids) or ((time.time() - self._last_update_time[req_id]) > self.update_delay):
                    completed_req = self.createCompletedReqFor(req_id, None, None)
                    if completed_req is not None:
                        self.data_buffers.processNewData(completed_req, self._propagating_data[req_id])
                        self._last_update_time[req_id] = time.time()


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


    def historicalDataEnd(self, req_id: int, start: str, end: str):
        super().historicalDataEnd(req_id, start, end)

        self.historial_end_signal.emit(req_id, start, end)


    @pyqtSlot(int, str, str)
    def processHistoricalDataEnd(self, req_id, start, end):
        self.timeout_timer.start()
        if self.req_id_manager.isActiveHistID(req_id):
            completed_req = self.createCompletedReqFor(req_id, start, end)
            if completed_req is not None:
                self.data_buffers.processNewData(completed_req, self._propagating_data[req_id])
            
            self.cleanupAndNotify(req_id)


    def cleanupAndNotify(self, req_id):
        self.processGroupSignal(req_id)
        if self.req_id_manager.isActiveHistID(req_id):
            uid = self._uid_by_req[req_id]
            if req_id in self._update_requests:
                self._update_requests.remove(req_id)
                if req_id in self._keep_up_requests:
                    self._last_update_time[req_id] = time.time()
                    self._initial_fetch_complete[req_id] = True
                if len(self._update_requests) == 0:
                    self.timeout_timer.stop()
                    self.api_updater.emit(Constants.HISTORICAL_UPDATE_COMPLETE, {'completed_uid': uid})

            if not (req_id in self._keep_up_requests):
                del self._uid_by_req[req_id]
                del self._bar_type_by_req[req_id]
                del self._date_ranges_by_req[req_id]
                if req_id in self._historical_dfs:
                    print("Do we ever come here?")
                    del self._historical_dfs[req_id]     #in case we come here through a timeout
                for key in self._req_by_owner:
                    if req_id in self._req_by_owner[key]: self._req_by_owner[key].remove(req_id)

                    #TODO is the conditional necesarry? shouldn't it always be in this list, when is it not?
                self.req_id_manager.clearHistReqID(req_id)                


    def createCompletedReqFor(self, req_id, start, end):
        completed_req = dict()
        completed_req['key'] = self._uid_by_req[req_id]
        completed_req['data'] = self._historical_dfs.pop(req_id)

        if len(completed_req['data']) == 0: return None
        
        first_date_stamp = datetime.fromtimestamp(completed_req['data'].index.min(), tz=utc)
        last_date_stamp = datetime.fromtimestamp(completed_req['data'].index.max(), tz=utc)
        
        completed_req['req_id'] = req_id
        completed_req['bar type'] = self._bar_type_by_req[req_id]

        if not ((start is None) or (end is None)):
            completed_req['requested_range'] = self._date_ranges_by_req[req_id]
            if first_date_stamp < completed_req['requested_range'][0]:
                completed_req['requested_range'] = (first_date_stamp, completed_req['requested_range'][1])
            # completed_req['returned_range'] = (utcDtFromIBString(start), utcDtFromIBString(end))
        else:
            range_end = last_date_stamp + timedelta(minutes=MINUTES_PER_BAR[completed_req['bar type']])
            completed_req['requested_range'] = (first_date_stamp, range_end)
            # completed_req['returned_range'] = ret_range

        if (req_id in self._keep_up_requests):
            self._historical_dfs[req_id] = pd.DataFrame(columns=[Constants.OPEN, Constants.HIGH, Constants.LOW, Constants.CLOSE, Constants.VOLUME])

        return completed_req


        #############super functionality methods

    def realtimeBar(self, reqId: int, time:int, open_: float, high: float, low: float, close: float, volume: float, wap: float, count: int):
        super().realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)
        date_time = datetime.fromtimestamp(time)

    
    def error(self, req_id, errorCode, errorString, advancedOrderRejectJson=None):
        print(f"HistoricalDataManager.error {req_id} {errorCode} {errorString}")
        if errorCode == 200 or errorCode == 162:
            if self.req_id_manager.isHistoryRequest(req_id):
                self.cleanupAndNotify(req_id)

        super().error(req_id, errorCode, errorString, advancedOrderRejectJson=None)


class HistoryRequest():

    def __init__(self, req_id, contract, end_date, period_string, bar_type, keep_updating=False):
        self.req_id = req_id
        self.contract = contract
        self.end_date = end_date
        self.period_string = period_string
        self.bar_type = bar_type
        self.keep_updating = keep_updating


    def __repr__(self):
        return f"HistoryRequest({self.contract.symbol}, {self.end_date},{self.period_string}, {self.bar_type})"

    def getEndDateString(self):
        if self.end_date == "":
            return ""
        else:
            datetime_string = dateToString(self.end_date)
            return datetime_string + " UTC" 

