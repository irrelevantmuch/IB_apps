
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

from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, Qt
from dataHandling.Constants import Constants
from dataHandling.DataStructures import DetailObject
from dataHandling.HistoryManagement.LiveBufferedManager import LiveDataManager

class LiveTickerProcessor(QObject):

    initial_fetch = False
    data_updater = pyqtSignal(str, dict)
    price_request_signal = pyqtSignal(DetailObject)
    finished = pyqtSignal()
    selected_bar_type = None
    ticker_inf = None


    def __init__(self, history_manager):
        super().__init__()

        self.history_manager = history_manager
        self.buffered_manager = LiveDataManager(history_manager)
        self.connectSignalsToSlots()
        

    def connectSignalsToSlots(self):
        self.buffered_manager.api_updater.connect(self.apiUpdate)
        
        self.price_request_signal.connect(self.history_manager.requestMarketData, Qt.QueuedConnection)
        self.buffered_manager.data_buffers.buffer_updater.connect(self.bufferUpdate, Qt.QueuedConnection)
        
    def moveToThread(self, thread):
        self.buffered_manager.moveToThread(thread)
        super().moveToThread(thread)
        

    @pyqtSlot()
    def run(self):
        pass
        

    def stop(self):
        self.buffered_manager.deregister()
        #perform cleanup here
        
    @pyqtSlot(tuple, set)
    def setTicker(self, ticker_inf, do_not_remove=set()):
        self.initial_fetch = True
        self.all_data_loaded = False
        self.updating_on = False
        self.ticker_inf = ticker_inf
        self.buffered_manager.setStockTracker(ticker_inf[0], ticker_inf[1], self.selected_bar_type, do_not_remove)
        details = DetailObject(self.ticker_inf[0], **self.ticker_inf[1])
        
        self.price_request_signal.emit(details)


    @pyqtSlot(str)
    def setBarType(self, bar_type):
        self.selected_bar_type = bar_type
        
        if self.ticker_inf is not None:
            if self.buffered_manager.data_buffers.bufferExists(self.ticker_inf[0], bar_type):
                self.data_updater.emit(Constants.HISTORICAL_DATA_READY, {'uid': self.ticker_inf[0], 'bars': [bar_type]})


    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, sub_signal):
        if (signal == Constants.ALL_DATA_LOADED) and (not self.all_data_loaded) and (not self.updating_on):

            self.buffered_manager.requestUpdates(update_bar=Constants.ONE_MIN_BAR, keep_up_to_date=True, prioritize_uids=True)
            self.all_data_loaded = True


    @pyqtSlot(str, dict)
    def bufferUpdate(self, signal, sub_signal):
        if signal == Constants.HAS_NEW_DATA and (self.ticker_inf[0] == sub_signal['uid']):
            if self.initial_fetch:
                if self.selected_bar_type in sub_signal['bars']:
                    self.data_updater.emit(Constants.HISTORICAL_DATA_READY, sub_signal)
                    self.initial_fetch = False
            else:                
                self.data_updater.emit(Constants.HAS_NEW_DATA, sub_signal) #, {'bars': bars})
                

