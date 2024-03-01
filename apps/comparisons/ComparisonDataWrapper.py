from PyQt5.QtCore import QObject, QReadWriteLock, pyqtSignal
from dataHandling.Constants import Constants

class ComparisonDataWrapper(QObject):

    _frame_lock = QReadWriteLock()
    _graph_data_lock = QReadWriteLock()

    primary_uids = None

    primary_graph_dict = dict()

    processing_updater = pyqtSignal(str, dict)

    _data_frame = None

    def setDataFrame(self, data_frame):
        self.processing_updater.emit(Constants.DATA_WILL_CHANGE, dict())
        self._lock.lockForWrite()
        self._data_frame = data_frame
        self._lock.unlock()
        self.processing_updater.emit(Constants.DATA_STRUCTURE_CHANGED, dict())
        self.processing_updater.emit(Constants.DATA_DID_CHANGE, dict())


    def getValueForColRow(self, column, row):
        self._frame_lock.lockForRead()
        try:
            return self._data_frame[column].iloc[row]
        finally:
            self._frame_lock.unlock()


    def getIndexForRow(self, row):
        self._frame_lock.lockForRead()
        try:
            return self._data_frame.index[row]
        except:
            return None
        finally:
            self._frame_lock.unlock()


    def sortIndex(self, ascending=True):
        self._frame_lock.lockForRead()
        try:
            self._data_frame.sort_index(ascending=ascending, inplace=True)
        finally:
            self._frame_lock.unlock()


    def sortValuesForColumn(self, column, ascending=True):
        self._frame_lock.lockForRead()
        try:
            self._data_frame.sort_values(column, ascending=ascending, inplace=True)
        finally:
            self._frame_lock.unlock()


    def getCount(self):
        self._frame_lock.lockForRead()
        try:
            return len(self._data_frame.index)
        except:
            return 0
        finally:
            self._frame_lock.unlock()


    def updatePrimaryGraphData(self, data_dict, forced_reset=False):
        
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


    def getLines(self, for_type):
        if for_type == 'comparison_plot':
            return self.primary_graph_dict
        elif for_type == 'focus_plot':
            return self.primary_graph_dict #focus_dict


    def getLineData(self, for_type, for_uid):
        if for_type == 'comparison_plot':
            return self.primary_graph_dict[for_uid]
        elif for_type == 'focus_plot':
            return self.primary_graph_dict[for_uid]


    def getPlotParameters(self, for_type):
        if for_type == 'comparison_plot':
            return list(self.primary_graph_dict.keys()), len(self.primary_graph_dict)
        return list(self.primary_graph_dict.keys()), len(self.primary_graph_dict)
        #return dict(), 0
