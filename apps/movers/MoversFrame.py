
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

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from PyQt5.QtCore import QObject, QReadWriteLock, pyqtSignal
from dataHandling.Constants import Constants

class MoversFrame(QObject):

    _lock = QReadWriteLock()
    processing_updater = pyqtSignal(str, dict)

    _data_frame = None

    def setDataFrame(self, data_frame):
        self.processing_updater.emit(Constants.DATA_WILL_CHANGE, dict())
        self._lock.lockForWrite()
        self._data_frame = data_frame
        self._ascending_order = {key: False for key in self._data_frame.columns}

        self._lock.unlock()
        self.processing_updater.emit(Constants.DATA_STRUCTURE_CHANGED, dict())
        self.processing_updater.emit(Constants.DATA_DID_CHANGE, dict())


    def getValueForColRow(self, column, row):
        self._lock.lockForRead()
        try:
            return self._data_frame[column].iloc[row]
        finally:
            self._lock.unlock()


    def getIndexForRow(self, row):
        self._lock.lockForRead()
        try:
            return self._data_frame.index[row]
        except:
            return None
        finally:
            self._lock.unlock()


    def sortIndex(self, ascending=True):
        self._lock.lockForRead()
        try:
            self._data_frame.sort_index(ascending=ascending, inplace=True)
        finally:
            self._lock.unlock()


    def sortValuesForColumn(self, column):
        self._lock.lockForRead()
        try:
            self._ascending_order[column] = not self._ascending_order[column]
            self._data_frame.sort_values(column, ascending=self._ascending_order[column], inplace=True)
        finally:
            self._lock.unlock()


    def getCount(self):
        self._lock.lockForRead()
        try:
            return len(self._data_frame.index)
        except:
            return 0
        finally:
            self._lock.unlock()


    def getValueFor(self, uid, column_name):
        self._lock.lockForRead()
        value = self._data_frame.loc[uid, column_name]
        self._lock.unlock()
        return value


    def updateValueFor(self, uid, column_name, new_value):
        self._lock.lockForWrite()
        change = self._data_frame.loc[uid, column_name] != new_value
        self._data_frame.loc[uid, column_name] = new_value    
        self._lock.unlock()
        if change:
            row_index = self._data_frame.index.get_loc(uid)
            self.processing_updater.emit(Constants.DATA_DID_CHANGE, {'row_index': row_index, 'column_name': column_name, 'new_value': new_value})


