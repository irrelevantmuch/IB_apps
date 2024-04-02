from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QObject, QReadWriteLock, QAbstractTableModel, QSize
from PyQt5 import QtCore
# from math import isnan
# from PyQt5.QtGui import QBrush, QColor


from dataHandling.Constants import Constants

import numpy as np
import pandas as pd

from dataHandling.DataManagement import DataManager


class PositionDataManager(DataManager):

    _open_positions = None
    _stock_positions = None
    daily_pnl = 0.0
    unrealized_pnl = 0.0
    _pnl_requests = dict()
    _pnl_data_reqs = set()

    needs_position_fetch = True

    account_number = None
    
    def __init__(self, callback=None, name="DataManagent"):
        super().__init__(callback, name) 

        self.data_object = PositionObject()


    def getDataObject(self):
        return self.data_object


    def run(self):
        super().run()
        self.ib_request_signal.emit({'type': 'reqAccountSummary'})


    def connectSignalsToSlots(self):
        super().connectSignalsToSlots()
        self.ib_interface.account_updater.connect(self.accountUpdate, Qt.QueuedConnection)
        self.ib_interface.account_updater.connect(self.data_object.accountUpdate, Qt.QueuedConnection)


    @pyqtSlot(str, dict)
    def accountUpdate(self, signal, sub_signal):
        # print(f"PositionDataManager.accountUpdate {signal} {sub_signal}")

        if signal == 'another_constnats':
            self.account_number = sub_signal['account']
            if self.needs_position_fetch:
                # print("Only once")
                self.ib_request_signal.emit({'type': 'reqAccountUpdates', 'subscribe': True, 'account_number': self.account_number})
                self.needs_position_fetch = False


    # def updatePNL(self, req_id, daily_pnl, unrealized_pnl):
    #     self.daily_pnl = daily_pnl
    #     self.unrealized_pnl = unrealized_pnl
    #     self.api_updater.emit(Constants.PNL_RETRIEVED, dict())


    # def updateSinglePNL(self, req_id, daily_pnl, unrealized_pnl):        
    #     numeric_id = self._pnl_requests[req_id]
    #     if numeric_id in self._open_positions['UID'].values:
    #         self._open_positions.loc[self._open_positions['UID'] == numeric_id, 'DPNL'] = daily_pnl
    #         self._open_positions.loc[self._open_positions['UID'] == numeric_id, 'UPNL'] = unrealized_pnl
    #     elif numeric_id in self._stock_positions['UID'].values:
    #         self._stock_positions.loc[self._stock_positions['UID'] == numeric_id, 'DPNL'] = daily_pnl
    #         self._stock_positions.loc[self._stock_positions['UID'] == numeric_id, 'UPNL'] = unrealized_pnl
        
    #     if req_id in self._pnl_data_reqs:
    #         self._pnl_data_reqs.remove(req_id)

    #         if len(self._pnl_data_reqs) < 4:
    #             for item in self._pnl_data_reqs:
    #                 numeric_id = self._pnl_requests[item]
    #         if len(self._pnl_data_reqs) == 0: self.api_updater.emit(Constants.IND_PNL_COMPLETED, dict())
        


    # def stopPositionRequest(self):
    #     print("Are we properly calling it quits?")
    #     self.ib_interface.reqAccountUpdates(False, self.account_number)


    
    # def positionsFetched(self):
    #     self.stopPositionRequest()

    #     self._open_positions["UPNL"] = np.nan
    #     self._open_positions["DPNL"] = np.nan

    #     self.ib_interface.reqPnL(Constants.PNL_REQUID, str(self.account_number), "")

    #     index = 0        
    #     for id in pd.concat([self._stock_positions['UID'], self._open_positions['UID']]):
            
    #         if self.getCountFor(id) != 0:
            
    #             req_id = Constants.BASE_PNL_REQUID+index
    #             self._pnl_data_reqs.add(req_id)
    #             self.ib_interface.reqPnLSingle(req_id, str(self.account_number), "", int(id))
    #             self._pnl_requests[req_id] = id
    #             index += 1



class PositionObject(QObject):

    _open_positions = None
    
    account_downloading_complete = False
    _lock = QReadWriteLock()
    position_signal = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()

        self.resetDataFrame()


    def resetDataFrame(self):
        self._open_positions = pd.DataFrame( {'UID': pd.Series(dtype='int'), Constants.SYMBOL: pd.Series(dtype='string'), 'SECURITY_TYPE': pd.Series(dtype='string'), 'CONTRACT': pd.Series(dtype='string'), 'PRICE': pd.Series(dtype='float'), 'COUNT': pd.Series(dtype='float'), 'UNREALIZED_PNL': pd.Series(dtype='float')} )
        

    @pyqtSlot(str, dict)
    def accountUpdate(self, signal, sub_signal):
        print(f"PositionObject.accountUpdate {signal} {self}")
        
        if signal == 'another_constnats':
            pass
            # print(f"PositionObject.accountUpdate {signal} {sub_signal}")
        elif signal == "whats_this":
            # print(sub_signal)
            self.updatePositions(sub_signal)
        elif signal == 'anotheranother':
            self.account_downloading_complete = True


    def updatePositions(self, new_positions):
        print("PositionObject.updatePositions")
        
        # if self.account_downloading_complete:
        #     self.resetDataFrame()
        #     self.account_downloading_complete = False            

        contract = new_positions['contract']
        marketPrice = new_positions['market_price']
        position = new_positions['position']
        unrealizedPNL = new_positions['unrealized_pnl']
        
        self.position_signal.emit(Constants.DATA_WILL_CHANGE, dict())

        self._lock.lockForWrite()
        prior_count = len(self._open_positions)
        new_position = pd.DataFrame.from_records([{'UID': str(contract.conId), Constants.SYMBOL: contract.symbol, 'CONTRACT': contract, 'SECURITY_TYPE': contract.secType, 'PRICE': marketPrice, 'SECURITY_TYPE': contract.secType, 'COUNT': position, 'UNREALIZED_PNL': unrealizedPNL}])
        self._open_positions = pd.concat([self._open_positions, new_position], ignore_index=True)
        new_index = self._open_positions.index[-1]
        self._lock.unlock()

        print(self._open_positions)

        self.position_signal.emit(Constants.DATA_STRUCTURE_CHANGED, {'index': new_index})
        self.position_signal.emit(Constants.DATA_DID_CHANGE, {'index': new_index})


    def getIndicesForUpdate(self, sub_signal):
        return None


    def getFrameFor(self, selection_type, identifier=None):
        if selection_type == 'OPTIONS_BY_INSTRUMENT':
            return self._open_positions[(self._open_positions['SECURITY_TYPE'] == Constants.OPTION) & (self._open_positions[Constants.SYMBOL] == identifier)]
        elif selection_type == Constants.OPTION:
            return self._open_positions[self._open_positions['SECURITY_TYPE'] == Constants.OPTION]
        elif selection_type == Constants.STOCK:
            return self._open_positions[self._open_positions['SECURITY_TYPE'] == Constants.STOCK]
        elif selection_type == 'STOCKS_LONG':
            return self._open_positions[(self._open_positions['SECURITY_TYPE'] == Constants.STOCK) & (self._open_positions['COUNT'] > 0)]
        elif selection_type == 'STOCKS_SHORT':
            return self._open_positions[(self._open_positions['SECURITY_TYPE'] == Constants.STOCK) & (self._open_positions['COUNT'] < 0)]
        return None


    def getRowCountFor(self, selection_type, identifier=None):
        return len(self.getFrameFor(selection_type, identifier))


    def getColumnCountFor(self, selection_type, identifier=None):
        try:
            return len(self.getFrameFor(selection_type, identifier).iloc[0])
        except:
            return 0


    def getRowFor(self, row_index, selection_type, identifier):
        return self.getFrameFor(selection_type, identifier).iloc[row_index]

    def getRowIndexFor(self, row_label, selection_type, identifier):
        try:
            return self.getFrameFor(selection_type, identifier).index.get_loc(row_label)
        except KeyError:
            return None
    
    def getValueForColRow(self, column_name, row_index, selection_type, identifier):
        return self.getFrameFor(selection_type, identifier).iloc[row_index][column_name]


    def getOptionPositions(self):
        return self.getFrameFor(Constants.OPTION)


    def getStockPositions(self):
        return self.getFrameFor(Constants.STOCK)

    def sortByColumn(self, column_name, ascending=True):
        self._open_positions.sort_values(by=column_name, ascending=ascending, inplace=True)


class PositionDataModel(QAbstractTableModel):

    # model_updater = pyqtSignal(str, dict)
    # greyout_stale = True
    # changed_list = set()

    def __init__(self, table_data, selection_type, parameter, **kwargs):
        super().__init__(**kwargs)
        self._table_data = table_data
        self._table_data.position_signal.connect(self.tableDataUpdate)
        self._selection_type = selection_type
        self._parameter = parameter

        self._headers = ['UID',Constants.SYMBOL, 'COUNT', 'PRICE']
        self._function_labels = [lambda x: str(x), lambda x: x, lambda x: f"{x:.0f}", lambda x: f"{x:.2f}"]
        print(f"PositionDataManager._function_labels {len(self._function_labels)}")
        print(self._function_labels)
                # self._table_data.processing_updater.connect(self.tableDataUpdate, Qt.QueuedConnection)

        # if header_labels is not None:
        #     self.header_labels = header_labels
        # else:
        #     self.header_labels = list(self._mapping.values())

        # if output_functions is not None:
        #     self.output_functions = output_functions
        # else:
        #     self.output_functions = [str] * self.columnCount()


    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        
        return QAbstractTableModel.headerData(self, section, orientation, role)



    def rowCount(self, parent=QtCore.QModelIndex()):
        return self._table_data.getRowCountFor(self._selection_type, self._parameter)


    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self._headers)


    def data(self, index, role=Qt.DisplayRole):
        # print(f"PositionDataModel.data {index}")
        if role == Qt.DisplayRole:
            column_name = self._headers[index.column()]
            # print(str(self._table_data.getValueForColRow(index.column(),index.row(), self._selection_type, self._parameter)))
            current_function = self._function_labels[index.column()]
            cell_string = current_function(self._table_data.getValueForColRow(column_name, index.row(), self._selection_type, self._parameter))
            return cell_string
 

    @pyqtSlot(str, dict)
    def tableDataUpdate(self, signal, sub_signal):
        print(f"PositionDataModel.tableDataUpdate {signal}")
        if signal == Constants.DATA_WILL_CHANGE:
            self.layoutAboutToBeChanged.emit()
        elif signal == Constants.DATA_DID_CHANGE:
            row_index = self._table_data.getRowIndexFor(sub_signal['index'], self._selection_type, self._parameter)
            if row_index is not None:
                left_index = self.index(row_index, 0)
                right_index = self.index(row_index, self.columnCount() - 1)
                self.dataChanged.emit(left_index, right_index)
        elif signal == Constants.DATA_STRUCTURE_CHANGED:
            if self._table_data.getRowIndexFor(sub_signal['index'], self._selection_type, self._parameter) is not None:
                self.layoutChanged.emit()


    def sort(self, col, order=Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()
        column_name = self._headers[col]
        self._table_data.sortByColumn(column_name, ascending=(order==Qt.AscendingOrder))
        self.layoutChanged.emit()

