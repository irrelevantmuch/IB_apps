
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

from PyQt5.QtCore import QObject, QReadWriteLock, pyqtSignal
from dataHandling.Constants import Constants

class ComparisonDataWrapper(QObject):

    _frame_lock = QReadWriteLock()
    _graph_data_lock = QReadWriteLock()

    primary_uids = None

    primary_graph_dict = dict()

    processing_updater = pyqtSignal(str, dict)

    _data_frame = None

    def __init__(self, uids):
        super().__init__()
        self.all_uids = uids


    def setUIDs(self, uids):
        self.all_uids = uids
    # def setDataFrame(self, data_frame):
    #     self.processing_updater.emit(Constants.DATA_WILL_CHANGE, dict())
    #     self._lock.lockForWrite()
    #     self._data_frame = data_frame
    #     self._lock.unlock()
    #     self.processing_updater.emit(Constants.DATA_STRUCTURE_CHANGED, dict())
    #     self.processing_updater.emit(Constants.DATA_DID_CHANGE, dict())


    # def getValueForColRow(self, column, row):
    #     self._frame_lock.lockForRead()
    #     try:
    #         return self._data_frame[column].iloc[row]
    #     finally:
    #         self._frame_lock.unlock()


    # def getIndexForRow(self, row):
    #     self._frame_lock.lockForRead()
    #     try:
    #         return self._data_frame.index[row]
    #     except:
    #         return None
    #     finally:
    #         self._frame_lock.unlock()


    # def sortIndex(self, ascending=True):
    #     self._frame_lock.lockForRead()
    #     try:
    #         self._data_frame.sort_index(ascending=ascending, inplace=True)
    #     finally:
    #         self._frame_lock.unlock()


    # def sortValuesForColumn(self, column, ascending=True):
    #     self._frame_lock.lockForRead()
    #     try:
    #         self._data_frame.sort_values(column, ascending=ascending, inplace=True)
    #     finally:
    #         self._frame_lock.unlock()


    def getCount(self):
        return 0
        # self._frame_lock.lockForRead()
        # try:
        #     return len(self._data_frame.index)
        # except:
        #     return 0
        # finally:
        #     self._frame_lock.unlock()


    def updatePrimaryGraphData(self, data_dict, bar_type, forced_reset=False):
        self.bar_type = bar_type
        updated_keys = set(data_dict.keys())

        self._graph_data_lock.lockForWrite()
        if (not forced_reset) and self.isUpdate(updated_keys):
            self.primary_graph_dict.update(data_dict)
        else:
            self.processing_updater.emit(Constants.DATA_LINES_WILL_RENEW, dict())
            self.primary_graph_dict = data_dict
            self.primary_uids = set(data_dict.keys())
        
        
        self._graph_data_lock.unlock()
        self.processing_updater.emit(Constants.DATA_LINES_UPDATED, {'updated_uids': updated_keys})
            
        
    def isUpdate(self, data_keys):
        if self.primary_uids is None:
            return False
        else:
            return data_keys.issubset(self.primary_uids)


    @property
    def has_data(self):
        return len(self.primary_graph_dict) > 0
    

    def getLines(self, for_type):
        if for_type == 'comparison_plot':
            return self.primary_graph_dict
        elif for_type == 'focus_plot':
            return self.primary_graph_dict #focus_dict


    def getLineData(self, for_uid):
        return self.primary_graph_dict[for_uid]
    

    def getPlotParameters(self, for_type):
        if for_type == 'comparison_plot':
            return set(self.primary_graph_dict.keys()), len(self.primary_graph_dict), self.all_uids
        return set(self.primary_graph_dict.keys()), len(self.primary_graph_dict), self.all_uids
        #return dict(), 0

    def needsDayBreak(self):
        return self.bar_type == Constants.DAY_BAR
        # return ((self.bar_type == Constants.DAY_BAR) or (self.bar_type == Constants.TWO_MIN_BAR) or (self.bar_type == Constants.THREE_MIN_BAR))

