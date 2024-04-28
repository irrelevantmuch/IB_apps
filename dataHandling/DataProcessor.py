
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

from PyQt5.QtCore import QThread, QObject, pyqtSlot, Qt
from dataHandling.Constants import Constants
from datetime import datetime
import pandas as pd
from pytz import timezone

class DataProcessor(QObject):

    stock_df = None
    previous_df = None
    _index_list = None
    stale_delay_secs = 15 * 60

    initial_fetch = False

    def __init__(self, stock_list=None, index_list=None):
        super().__init__()
        print("DataProcessor.init")
        self.data_buffers = self.buffered_manager.data_buffers
        self.data_buffers.buffer_updater.connect(self.bufferUpdate, Qt.QueuedConnection)
        self.initial_stock_list = stock_list
        self.initial_index_list = index_list


    def moveToThread(self, thread):
        self.buffered_manager.moveToThread(thread)
        super().moveToThread(thread)
    

    @pyqtSlot()
    def run(self):
        print(f"Dataprocessor is running on {int(QThread.currentThreadId())}")
        if self.initial_index_list is not None:
            self._index_list = self.initial_index_list

        self.setStockList(self.initial_stock_list)

    def stop(self):
        print("THIS SHOULD BE MADE DEPENDENT ON WHETHER THE OWNER IS SINGULAR")
        # self.buffered_manager.reset_signal.emit()


############## DATA PROCESSING



    @pyqtSlot(dict)
    def setStockList(self, stock_list):
        self._stock_list = stock_list

        if self._index_list is not None:
            merged_dict = {**stock_list, **self._index_list}
            self.buffered_manager.setStockList(merged_dict)
        else:
            self.buffered_manager.setStockList(stock_list)


    def determineStale(self):
        keys = self._stock_list.keys()
        now_time = int(datetime.utcnow().timestamp())
        
        for uid in keys:
            self.stock_df.loc[uid, Constants.STALE] = True      #We assume data is stale

            if self.data_buffers.bufferExists(uid, Constants.FIVE_MIN_BAR):
                last_five_min_mark = self.data_buffers.getIndicesFor(uid, Constants.FIVE_MIN_BAR).max()
                        
                time_del = (now_time - last_five_min_mark)
                if time_del < self.stale_delay_secs:
                    self.stock_df.loc[uid, Constants.STALE] = False   
            

    def getBarData(self, uid, bar_type):
        if self.data_buffers.bufferExists(uid, bar_type):
            return self.data_buffers.getBufferFor(uid, bar_type)
        return None




