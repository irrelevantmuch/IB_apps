
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

from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QReadWriteLock, QAbstractTableModel, QSize, QObject
from PyQt5 import QtCore
from ibapi.contract import Contract

from dataHandling.Constants import Constants
from dataHandling.IBConnectivity import IBConnectivity

import numpy as np
import pandas as pd


class PositionDataManager(IBConnectivity):

    daily_pnl = 0.0
    unrealized_pnl = 0.0
    _pnl_requests = dict()
    _pnl_data_reqs = set()
    account_updater = pyqtSignal(str, dict)
    needs_position_fetch = True

    account_number = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.data_object = PositionObject()
        self.account_updater.connect(self.data_object.accountUpdate, Qt.QueuedConnection)
        self.makeRequest({'type': 'reqAccountSummary'})


    def getDataObject(self):
        return self.data_object


    def accountSummary(self, req_id: int, account: str, tag: str, value: str, currency: str):
        super().accountSummary(req_id, account, tag, value, currency)
        self.accountUpdate('another_constnats', {'account': account, 'req_id': req_id})
        

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):  
        super().updateAccountValue(key, val, currency, accountName)
        self.accountUpdate('some_constants', {'key': key, 'val': val, 'accountName': accountName})


    def updatePortfolio(self, contract: Contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):
        super().updatePortfolio(contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName)
        self.accountUpdate('whats_this', {'contract': contract, 'position': position, 'account_name': accountName, 'unrealized_pnl': unrealizedPNL, 'market_price': marketPrice})
        

    def accountDownloadEnd(self, accountName: str):
        super().accountDownloadEnd(accountName)
        self.accountUpdate("anotheranother", {'account_number': accountName})
        

    def accountUpdate(self, signal, sub_signal):
        self.account_updater.emit(signal, sub_signal)
        if signal == 'another_constnats':
            self.account_number = sub_signal['account']
            if self.needs_position_fetch:
                self.makeRequest({'type': 'reqAccountUpdates', 'subscribe': True, 'account_number': self.account_number})
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
        


class PositionObject(QObject):

    _open_positions = None
    
    account_downloading_complete = False
    _lock = QReadWriteLock()
    position_signal = pyqtSignal(str, dict)

        #made a buffer, because this object serves many TableViews all needing slightly different lists a buffer makes thing speedier
    _frame_buffer = dict()      
    _needs_update = dict()

    def __init__(self):
        super().__init__()

        self.resetDataFrame()


    def resetDataFrame(self):
        self._open_positions = pd.DataFrame( {'UID': pd.Series(dtype='int'), Constants.SYMBOL: pd.Series(dtype='string'), 'SECURITY_TYPE': pd.Series(dtype='string'), 'CONTRACT': pd.Series(dtype='string'), 'PRICE': pd.Series(dtype='float'), 'COUNT': pd.Series(dtype='float'), 'UNREALIZED_PNL': pd.Series(dtype='float')} )
        

    @pyqtSlot(str, dict)
    def accountUpdate(self, signal, sub_signal):
        if signal == 'another_constnats':
            pass
        elif signal == "whats_this":
            self.updatePositions(sub_signal)
        elif signal == 'anotheranother':
            self.account_downloading_complete = True


    def updatePositions(self, new_positions):
        contract = new_positions['contract']
        marketPrice = new_positions['market_price']
        position = new_positions['position']
        unrealizedPNL = new_positions['unrealized_pnl']
        
        self.position_signal.emit(Constants.DATA_WILL_CHANGE, dict())

        self._lock.lockForWrite()
        prior_count = len(self._open_positions)
        self._open_positions.loc[contract.conId] = {Constants.SYMBOL: contract.symbol, 'CONTRACT': contract, 'SECURITY_TYPE': contract.secType, 'PRICE': marketPrice, 'SECURITY_TYPE': contract.secType, 'COUNT': position, 'UNREALIZED_PNL': unrealizedPNL}
        
        self._lock.unlock()

        self._needs_update = {key: True for key in self._needs_update}

        self.position_signal.emit(Constants.DATA_STRUCTURE_CHANGED, {'index': contract.conId})
        self.position_signal.emit(Constants.DATA_DID_CHANGE, {'index': contract.conId})


    def getFrameFor(self, selection_type, identifier='general'):
        if selection_type == 'OPTIONS_BY_INSTRUMENT':
            selection = (self._open_positions['SECURITY_TYPE'] == Constants.OPTION) & (self._open_positions[Constants.SYMBOL] == identifier)
    
        elif selection_type == Constants.OPTION:
            selection = (self._open_positions['SECURITY_TYPE'] == Constants.OPTION)
        elif selection_type == Constants.STOCK:
            selection = (self._open_positions['SECURITY_TYPE'] == Constants.STOCK)
        elif selection_type == 'STOCKS_LONG':
            selection = (self._open_positions['SECURITY_TYPE'] == Constants.STOCK) & (self._open_positions['COUNT'] > 0)
        elif selection_type == 'STOCKS_SHORT':
            selection = (self._open_positions['SECURITY_TYPE'] == Constants.STOCK) & (self._open_positions['COUNT'] < 0)
        elif selection_type == 'ALL':
            return self._open_positions

        if selection is not None:
            if not((selection_type, identifier) in self._frame_buffer) or self.needsUpdateFor(selection_type, identifier):
                self._frame_buffer[selection_type, identifier] = self._open_positions[selection]
                self._needs_update[selection_type, identifier] = False
            return self._frame_buffer[selection_type, identifier]
        else:
            return None


    def needsUpdateFor(self, selection_type, identifier):
        if (selection_type, identifier) in self._needs_update:
            return self._needs_update[selection_type, identifier]
        return False

    def getRowCountFor(self, selection_type, identifier='general'):
        return len(self.getFrameFor(selection_type, identifier))


    def getColumnCountFor(self, selection_type, identifier='general'):
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
        self._needs_update = {key: True for key in self._needs_update}


class PositionDataModel(QAbstractTableModel):


    def __init__(self, table_data, selection_type, parameter, **kwargs):
        super().__init__(**kwargs)
        self._table_data = table_data
        self._table_data.position_signal.connect(self.tableDataUpdate)
        self._selection_type = selection_type
        self._parameter = parameter

        self._headers = [Constants.SYMBOL, 'COUNT', 'PRICE', 'EST MKT VALUE']
        self._function_labels = [lambda x: x, lambda x: f"{x:.0f}", lambda x: f"{x:.2f}", lambda x: f"{x:.2f}"]



    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        
        return QAbstractTableModel.headerData(self, section, orientation, role)



    def rowCount(self, parent=QtCore.QModelIndex()):
        return self._table_data.getRowCountFor(self._selection_type, self._parameter)


    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self._headers)


    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            column_index = index.column()
            column_name = self._headers[column_index]
            if column_name == 'EST MKT VALUE':
                price = self._table_data.getValueForColRow('PRICE', index.row(), self._selection_type, self._parameter)
                count = self._table_data.getValueForColRow('COUNT', index.row(), self._selection_type, self._parameter)
                cell_value = price * float(count)
            else:
                cell_value = self._table_data.getValueForColRow(column_name, index.row(), self._selection_type, self._parameter)
            
            current_function = self._function_labels[column_index]
            return current_function(cell_value)
            

    @pyqtSlot(str, dict)
    def tableDataUpdate(self, signal, sub_signal):
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

