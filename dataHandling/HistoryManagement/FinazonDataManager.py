from PyQt5.QtCore import QTimer, QThread, pyqtSlot, QObject, Qt, pyqtSignal

import pandas as pd

from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
import pytz
import sys, math
from operator import attrgetter

from dataHandling.Constants import Constants, MINUTES_PER_BAR
from dataHandling.DataStructures import DetailObject
from dataHandling.IBConnectivity import IBConnectivity
from generalFunctionality.GenFunctions import dateFromString, dateToString, pdDateFromIBString, dateFromIBString
from dataHandling.UserDataManagement import readApiKeys
from dataHandling.HistoryManagement.DataBuffer import DataBuffers
import rel
import asyncio
import websockets, websocket
import json
import requests

import threading

api_keys = readApiKeys()


class WebsocketManager(QObject):
    message_received = pyqtSignal(dict)
    socket_address = f"wss://ws.finazon.io/v1?apikey={api_keys[Constants.FINAZON_SOURCE]}"
    # run_async_socket = pyqtSignal()
    is_running = True
    finished = pyqtSignal()

    # last_ticker_time = dict()
    # last_unsent_time = dict()
    # last_unsent_message = dict()

    def __init__(self, tickers=["BTC/USDC"], channel="binance"):
        super().__init__()
        self.tickers = tickers
        self.channel = channel

        self.setup_message = {
            "event": "subscribe",
            "dataset": self.channel,
            "tickers": self.tickers,
            "channel": "bars",
            "frequency": "10s",
            "aggregation": "1m"
        }

        # self.timer = QTimer()
        # self.timer.timeout.connect(lambda: self.checkForUnsentUpdates())
        # self.timer.start(3_000)

    def onMessage(self, ws, message):
        print(f"We get back {message}")
        now_time = datetime.now(timezone(Constants.NYC_TIMEZONE))
        delay_dif = timedelta(seconds=3)
        
        json_dict = json.loads(message)
        if 's' in json_dict:
            self.message_received.emit(json_dict)

    # def checkForUnsentUpdates(self):
    #     now_time = datetime.now(timezone(Constants.NYC_TIMEZONE))
    #     delay_dif = timedelta(seconds=3)
        
    #     dict_copy = self.last_unsent_time.copy()
    #     for symbol, time in dict_copy.items():
    #         if time < (now_time-delay_dif):
    #             if symbol in self.last_unsent_message:
    #                 self.message_received.emit(self.last_unsent_message[symbol])
    #                 del self.last_unsent_message[symbol]
    #                 del self.last_unsent_time[symbol]


    def onError(self, ws, error):
        print(f"Finazon websocket error: {error}")


    def onClose(self, ws, close_status_code, close_msg):
        self.finished.emit()
        print(f"Finazon websocket error: CLOSED")


    def onOpen(self, ws):
        ws.send(json.dumps(self.setup_message))

    def run(self):
        self.ws = websocket.WebSocketApp(self.socket_address, on_open=self.onOpen, on_message=self.onMessage, on_error=self.onError, on_close=self.onClose)
        self.ws.run_forever(
                # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly
                # dispatcher=rel, 
            reconnect=5,
                # Sending ping with specified interval to prevent disconnecting
            ping_interval=30, ping_timeout=10,
        )

    # @pyqtSlot()
    def close(self):
        self.ws.close()

 
class FinazonDataManager(QObject):

    bar_conversion = {Constants.ONE_MIN_BAR: "1m", Constants.TWO_MIN_BAR: "2m", Constants.THREE_MIN_BAR: "3m", Constants.FIVE_MIN_BAR: "5m",
                        Constants.FIFTEEN_MIN_BAR: "15m", Constants.HOUR_BAR: "1h", Constants.FOUR_HOUR_BAR: "4h", Constants.DAY_BAR: "1d"}


    backward_bar_conversion = {"1m": Constants.ONE_MIN_BAR, "2m": Constants.TWO_MIN_BAR, "3m": Constants.THREE_MIN_BAR, "5m": Constants.FIVE_MIN_BAR,
                        "15m": Constants.FIFTEEN_MIN_BAR, "1h": Constants.HOUR_BAR, "4h": Constants.FOUR_HOUR_BAR, "1d": Constants.DAY_BAR}


    resampleFrame = {Constants.TWO_MIN_BAR: '2T', Constants.THREE_MIN_BAR: '3T', Constants.FIVE_MIN_BAR: '5T', Constants.FIFTEEN_MIN_BAR: '15T', Constants.HOUR_BAR: '1H', Constants.FOUR_HOUR_BAR: '4H', Constants.DAY_BAR: 'D'}


    api_updater = pyqtSignal(str, dict)
    messageReceived = pyqtSignal(str)

    request_buffer = []             #buffer holding the historical requests

    regular_hours = 0

    url = "https://api.finazon.io/latest/time_series"
    headers = {"Authorization": f"apikey {api_keys[Constants.FINAZON_SOURCE]}"}

    run_ib_client_signal = pyqtSignal()
    close_signal = pyqtSignal()
    controller = None
    process_owner = None
    socket_load = 26
    ws_managers = None

    update_counter = 0

    def __init__(self):
        super().__init__()
        self.data_buffers = DataBuffers()


    def moveToThread(self, thread):
        self.data_buffers.moveToThread(thread)
        super().moveToThread(thread)


    def getDataBuffer(self):
        return self.data_buffers


    def run(self):
        print("We start running")
        

    @pyqtSlot(dict)
    def updatedBars(self, json_dict):
        # print("FinazonDataManager.updatedBars")
        keys_to_extract = ['t', 'o', 'h', 'l', 'c', 'v']
        if "p" in json_dict:
            bar_dict = {key: json_dict[key] for key in keys_to_extract}
            if bar_dict['c'] != 0:
                bar_df = self.processBars([bar_dict])
                uid = self.findKeyForSymbol(json_dict["s"])
                completed_req = self.createCompletedReq(uid, self.backward_bar_conversion[json_dict['aggr']], None, None)
                completed_req['data'] = bar_df

                self.data_buffers.processUpdates(completed_req, propagate_updates=True)
                self.update_counter += 1

                if (self.update_counter % 100) == 0:
                    print(f"We got {self.update_counter} bars back")


    def findKeyForSymbol(self, symbol):
        for key, ticker in self.realtime_tickers.items():
            if ticker == symbol:
                return key

        return None


    def createWebSocketForTickers(self, tickers):
        print("FinazonDataManager.createWebSocketForTickers")
        print(tickers)
        socket_count = min(math.ceil(len(tickers)/self.socket_load),5)
        tickers_per_socket = math.ceil(len(tickers)/socket_count)
        self.ws_managers = []
        self.ws_threads = []
        print(f"How many socket counts {socket_count}")
        for socket_index in range(socket_count):
            start_index = socket_index*tickers_per_socket
            end_index = (1+socket_index)*tickers_per_socket
            end_index = min(len(tickers),end_index)

            self.ws_managers.insert(socket_count, WebsocketManager(tickers[start_index:end_index], channel="sip_non_pro"))
            self.ws_managers[socket_index].message_received.connect(self.updatedBars, Qt.QueuedConnection)
            self.close_signal.connect(self.ws_managers[socket_index].close)
            self.ws_threads.insert(socket_count, QThread())
            self.ws_managers[socket_index].moveToThread(self.ws_threads[socket_index])
            self.ws_managers[socket_index].finished.connect(self.ws_threads[socket_index].quit)
            self.ws_managers[socket_index].finished.connect(self.ws_managers[socket_index].deleteLater)
            self.ws_threads[socket_index].finished.connect(self.ws_threads[socket_index].deleteLater)
            self.ws_threads[socket_index].started.connect(self.ws_managers[socket_index].run)
            self.ws_threads[socket_index].start()    
        

    def addNewListener(self, controller, listener_function):
        self.api_updater.connect(listener_function, Qt.QueuedConnection)
        self.controller = controller
        #self.cancelActiveRequests(controller)


    def lockForCentralUpdating(self, controller):
        self.controller = controller
        self.api_updater.emit(Constants.HISTORY_LOCK, dict())


    def unlockCentralUpdating(self):
        self.api_updater.emit(Constants.HISTORY_UNLOCK, dict())


    @pyqtSlot()
    def cancelActiveRequests(self, sender=None):
        if self.ws_managers is not None:
            for ws_man in self.ws_managers:
                ws_man.close()



######## HISTORICAL DATA REQUEST CREATION
        

    @pyqtSlot(str)
    def groupCurrentRequests(self, for_uid):
        print(f"groupCurrentRequests {for_uid}")


    @pyqtSlot(dict, str, bool, bool)
    @pyqtSlot(dict, str, bool, bool, bool)
    def requestUpdates(self, stock_list, bar_type, keep_up_to_date, propagate_updates=False, prioritize_uids=False):
        print(f"FinazonDataManager.requestUpdates {keep_up_to_date}")

        if keep_up_to_date:
            self.realtime_tickers = dict()
            tickers_to_fetch = []
            for uid, stock_inf in stock_list.items():
                self.realtime_tickers[uid] = stock_inf[Constants.SYMBOL]
                tickers_to_fetch.append(stock_inf[Constants.SYMBOL])

            self.createWebSocketForTickers(tickers_to_fetch)

        for uid, stock_inf in stock_list.items():
            print(f"Here we go {uid} {stock_inf}")
            details = DetailObject(symbol=stock_inf[Constants.SYMBOL], exchange=stock_inf['exchange'], numeric_id=uid)
            start_date = stock_list[uid]['begin_date']
            end_date = datetime.now(timezone(Constants.NYC_TIMEZONE))
            new_request = {"contract": details, "start_date": start_date, "end_date": end_date, "bar_type": Constants.ONE_MIN_BAR}
            self.request_buffer.append(new_request)

        completed_uids = []
        while len(self.request_buffer) > 0:

            request = self.request_buffer.pop()
            print(f"requestUpdates: {request}")
            completed_req = self.getBarsForRequest(request, is_one_min_update=True)
            if completed_req is not None:
                self.data_buffers.processUpdates(completed_req, propagate_updates)
                completed_uids.append(completed_req['key'])
        
        self.api_updater.emit(Constants.HISTORICAL_UPDATE_COMPLETE, {'completed_uids': completed_uids})

        if keep_up_to_date:
            self.timer = QTimer()
            self.timer.timeout.connect(lambda: self.performPeriodicUpdates(stock_list))
            self.timer.start(100_000)


    def performPeriodicUpdates(self, stock_list):
        start_date = datetime.now(timezone(Constants.NYC_TIMEZONE)) - timedelta(minutes=6)
        for uid, stock_inf in stock_list.items():
            details = DetailObject(symbol=stock_inf[Constants.SYMBOL], exchange=stock_inf['exchange'], numeric_id=uid)
            start_date = stock_list[uid]['begin_date']
            end_date = datetime.now(timezone(Constants.NYC_TIMEZONE))
            new_request = {"contract": details, "start_date": start_date, "end_date": None, "bar_type": Constants.ONE_MIN_BAR}
            self.request_buffer.append(new_request)

        while len(self.request_buffer) > 0:
            request = self.request_buffer.pop()
            completed_req = self.getBarsForRequest(request, is_one_min_update=False)
            if completed_req is not None:
                self.api_updater.emit(Constants.HISTORICAL_REQUEST_COMPLETED, completed_req)
                

    def getBarsForRequest(self, request, is_one_min_update=False):
        contract_details = request['contract']
        start_date = request['start_date']
        end_date = request['end_date']
        bar_type = request['bar_type']
        uid = request['contract'].numeric_id

        if is_one_min_update:
            if (end_date - start_date) < timedelta(hours=5):
                start_date = end_date - timedelta(hours=5)
            
            start_time = start_date.time()
            if start_time > time(20,0) or start_time < time(4,0):
                start_date = start_date - timedelta(hours=8)

        timestamp_end = None
        timestamp_start = int(start_date.timestamp())
        if end_date is not None:
            timestamp_end = int(end_date.timestamp())

        new_bars = None
        bars = []
        page = 1
        page_size = 1000
        while (new_bars is None) or len(new_bars) == page_size:
            query_params = {"dataset": "sip_non_pro",
                            "ticker": contract_details.symbol,
                            "interval": self.bar_conversion[bar_type],
                            "timezone": "America/New_York",
                            "prepost": "true",
                            # "adjust":
                            "order": "asc",
                            "start_at": str(timestamp_start),
                            "page": str(page), "page_size": str(page_size)}

            if timestamp_end is not None:
                query_params["end_at"] = str(timestamp_end)
            
            response = requests.get(self.url, headers=self.headers, params=query_params)
            try:
                new_bars = response.json()['data']
                bars += new_bars
                page += 1
            except:
                print("********************")
                print("WE GET AN ERROR")
                print(response)
                print("********************")

        if len(bars) > 0:
            
            new_bar_frame = self.processBars(bars)
            if bar_type == Constants.ONE_MIN_BAR:
                new_bar_frame = new_bar_frame[~((new_bar_frame.index.hour >= 20) | (new_bar_frame.index.hour < 4))]
            if bar_type == Constants.DAY_BAR:
                final_row = new_bar_frame.loc[new_bar_frame.index.max()]
                if final_row[Constants.CLOSE] == 0:
                    new_bar_frame.drop(new_bar_frame.index.max(), inplace=True)

            completed_req = self.createCompletedReq(uid, bar_type, start_date, new_bar_frame.index.max())
            completed_req['data'] = new_bar_frame
            return completed_req
        else:
            return None


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
        return len(self.request_buffer) > 0


    @pyqtSlot(DetailObject, datetime, datetime, str)
    def createRequestsForContract(self, contract_details, start_date, end_date, bar_type):
        new_request = {"contract": contract_details, "start_date": start_date, "end_date": end_date, "bar_type": bar_type}
        self.request_buffer.append(new_request)


    @pyqtSlot(int)
    def iterateHistoryRequests(self, delay=11_000): #this delay is only to match the interface of the IBKR historymanager. Needs to be removed

        one_min_bars, start_date = self.getOneMinForOutsideHours()
        while len(self.request_buffer) > 0:
            request = self.request_buffer.pop()
            if request['start_date'] >= start_date:
                completed_req = self.barsFromSmallerData(request, one_min_bars, start_date)
            else:
                one_min_resampled = one_min_bars['data'].resample(self.resampleFrame[request["bar_type"]]).agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last', Constants.VOLUME: 'sum'}).dropna()
                # if request['bar_type'] == Constants.FOUR_HOUR_BAR:
                #     print(f"For {request['contract'].symbol} we get:")
                #     print(one_min_resampled)
                completed_req = self.getBarsForRequest(request)
                completed_req['data'] = one_min_resampled.combine_first(completed_req['data'])
                # if request['bar_type'] == Constants.FOUR_HOUR_BAR:
                #     print(f"Final result:")
                #     print(completed_req['data'].tail(15))

            self.data_buffers.processData(completed_req)
        
        #working under the assumption that all these requests are for a single contract
        self.api_updater.emit(Constants.HISTORICAL_GROUP_COMPLETE, {"uid": request["contract"].numeric_id})


    def getOneMinForOutsideHours(self):
        smallest_index = self.getSmallestBarIndex()

            #only bars smaller than 5 mins give us outside regular hours data, so we need some of those for supplementing!
        if self.request_buffer[smallest_index] == Constants.ONE_MIN_BAR:
            base_request = self.request_buffer.pop(smallest_index)
            min_start_date = base_request['end_date'] - timedelta(days=5)
            if min_start_date < base_request['start_date']:
                base_request['start_date'] = min_start_date
                one_min_bars = self.getBarsForRequest(base_request, is_one_min_update=False)
                self.data_buffers.processData(one_min_bars)
        else:
            base_request = self.request_buffer[smallest_index].copy()
            base_request['bar_type'] = Constants.ONE_MIN_BAR
            base_request['start_date'] = base_request['end_date'] - timedelta(days=5)
            one_min_bars = self.getBarsForRequest(base_request, is_one_min_update=False)
        
        start_date = base_request['start_date']
        return one_min_bars, start_date


    def getSmallestBarIndex(self):
        smallest_bar_type = self.request_buffer[0]['bar_type']
        smallest_index = 0
        for index in range(1, len(self.request_buffer)):
            request_bar_type = self.request_buffer[index]['bar_type']
            if self.isSmallerBar(request_bar_type, smallest_bar_type):
                smallest_bar_type = request_bar_type
                smallest_index = index
        return smallest_index


    def isSmallerBar(self, bar, comp_bar):
        if comp_bar is None:
            return True
        else:
            return MINUTES_PER_BAR[bar] < MINUTES_PER_BAR[comp_bar]


    def barsFromSmallerData(self, request, smallest_bars, start_date):
        bar_type = request['bar_type']
        # print(f"FinazonDataManager.barsFromSmallerData {bar_type}")
        uid = request['contract'].numeric_id
        end_date = request['end_date']
        new_data = smallest_bars['data'].resample(self.resampleFrame[bar_type]).agg({Constants.OPEN: 'first', Constants.HIGH: 'max', Constants.LOW: 'min', Constants.CLOSE: 'last', Constants.VOLUME: 'sum'}).dropna()
        completed_req = self.createCompletedReq(uid, bar_type, start_date, end_date)
        completed_req['data'] = new_data
        return completed_req


    def processBars(self, bars):
        bar_frame = pd.DataFrame(bars)


        bar_frame['t'] = pd.to_datetime(bar_frame['t'], unit='s')  # Convert timestamp to datetime
        bar_frame.set_index('t', inplace=True)  # Set timestamp as the index
        bar_frame.index.name = None

        # Set timezone to NYC
        nyc_timezone = timezone('America/New_York')
        bar_frame.index = bar_frame.index.tz_localize('UTC').tz_convert(nyc_timezone)

        # Rename columns based on the mapping
        bar_frame.rename(columns={"o": Constants.OPEN, "h": Constants.HIGH, "l": Constants.LOW, "c": Constants.CLOSE, "v": Constants.VOLUME}, inplace=True)

        bar_frame = bar_frame.astype(float)
        bar_frame.sort_index(ascending=True, inplace=True)
        return bar_frame
        

    def createCompletedReq(self, uid, bar_type, start_date, end_date):
        completed_req = dict()
        completed_req['key'] = uid
        if (start_date is not None) and (end_date is not None):
            completed_req['range'] = (start_date, end_date)
        else:
            completed_req['range'] = None
        completed_req['bar type'] = bar_type
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
            return datetime_string[:-5] + " US/Eastern" 


