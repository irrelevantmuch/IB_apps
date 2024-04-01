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

    account_number = None
    
    def __init__(self, callback=None, name="DataManagent"):
        super().__init__(callback, name) 

        self.data_object = PositionObject()


    def getDataObject(self):
        return self.data_object


    def run(self):
        super().run()
        self.connectSignalsToSlots()
        self.ib_request_signal.emit({'type': 'reqAccountSummary'})


    def connectSignalsToSlots(self):
        super().connectSignalsToSlots()
        self.ib_interface.account_updater.connect(self.accountUpdate, Qt.QueuedConnection)
        self.ib_interface.account_updater.connect(self.data_object.accountUpdate, Qt.QueuedConnection)


    @pyqtSlot(str, dict)
    def accountUpdate(self, signal, sub_signal):
        # print(f"PositionDataManager.accountUpdate {signal} {sub_signal}")

        if signal == 'another_constnats':
            # print(f"PositionObject.accountUpdate {signal} {sub_signal}")
            self.account_number = sub_signal['account']
            self.ib_request_signal.emit({'type': 'reqAccountUpdates', 'subscribe': True, 'account_number': self.account_number})


    def updatePNL(self, req_id, daily_pnl, unrealized_pnl):
        self.daily_pnl = daily_pnl
        self.unrealized_pnl = unrealized_pnl
        self.api_updater.emit(Constants.PNL_RETRIEVED, dict())


    def updateSinglePNL(self, req_id, daily_pnl, unrealized_pnl):        
        numeric_id = self._pnl_requests[req_id]
        if numeric_id in self._open_positions['ID'].values:
            self._open_positions.loc[self._open_positions['ID'] == numeric_id, 'DPNL'] = daily_pnl
            self._open_positions.loc[self._open_positions['ID'] == numeric_id, 'UPNL'] = unrealized_pnl
        elif numeric_id in self._stock_positions['ID'].values:
            self._stock_positions.loc[self._stock_positions['ID'] == numeric_id, 'DPNL'] = daily_pnl
            self._stock_positions.loc[self._stock_positions['ID'] == numeric_id, 'UPNL'] = unrealized_pnl
        
        if req_id in self._pnl_data_reqs:
            self._pnl_data_reqs.remove(req_id)

            if len(self._pnl_data_reqs) < 4:
                for item in self._pnl_data_reqs:
                    numeric_id = self._pnl_requests[item]
            if len(self._pnl_data_reqs) == 0: self.api_updater.emit(Constants.IND_PNL_COMPLETED, dict())
        


    # def stopPositionRequest(self):
    #     print("Are we properly calling it quits?")
    #     self.ib_interface.reqAccountUpdates(False, self.account_number)


    
    def positionsFetched(self):
        self.stopPositionRequest()

        self._open_positions["UPNL"] = np.nan
        self._open_positions["DPNL"] = np.nan

        self.ib_interface.reqPnL(Constants.PNL_REQID, str(self.account_number), "")

        index = 0        
        for id in pd.concat([self._stock_positions['ID'], self._open_positions['ID']]):
            
            if self.getCountFor(id) != 0:
            
                req_id = Constants.BASE_PNL_REQID+index
                self._pnl_data_reqs.add(req_id)
                self.ib_interface.reqPnLSingle(req_id, str(self.account_number), "", int(id))
                self._pnl_requests[req_id] = id
                index += 1



class PositionObject(QObject):

    _open_positions = None
    
    account_downloading_complete = False
    _lock = QReadWriteLock()
    position_signal = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()

        self.resetDataFrame()


    def resetDataFrame(self):
        self._open_positions = pd.DataFrame( {'ID': pd.Series(dtype='int'), Constants.SYMBOL: pd.Series(dtype='string'), 'SECURITY_TYPE': pd.Series(dtype='string'), 'CONTRACT': pd.Series(dtype='string'), 'PRICE': pd.Series(dtype='float'), 'COUNT': pd.Series(dtype='float'), 'UNREALIZED_PNL': pd.Series(dtype='float')} )
        

    @pyqtSlot(str, dict)
    def accountUpdate(self, signal, sub_signal):
        if signal == 'another_constnats':
            print(f"PositionObject.accountUpdate {signal} {sub_signal}")
        elif signal == "whats_this":
            self.updatePositions(sub_signal)
        elif signal == 'anotheranother':
            self.account_downloading_complete = True


    def updatePositions(self, new_positions):
        print("PositionObject.updatePositions")
        self.position_signal.emit(Constants.DATA_WILL_CHANGE, dict())
        if self.account_downloading_complete:
            self.resetDataFrame()
            self.account_downloading_complete = False            

        contract = new_positions['contract']
        marketPrice = new_positions['market_price']
        position = new_positions['position']
        unrealizedPNL = new_positions['unrealized_pnl']

        self._lock.lockForWrite()
        prior_count = len(self._open_positions)
        new_position = pd.DataFrame.from_records([{'ID': str(contract.conId), Constants.SYMBOL: contract.symbol, 'CONTRACT': contract, 'SECURITY_TYPE': contract.secType, 'PRICE': marketPrice, 'SECURITY_TYPE': contract.secType, 'COUNT': position, 'UNREALIZED_PNL': unrealizedPNL}])
        self._open_positions = pd.concat([self._open_positions, new_position], ignore_index=True)
        new_count = len(self._open_positions)
        self._lock.unlock()

        if prior_count != new_count:
            self.position_signal.emit(Constants.DATA_STRUCTURE_CHANGED, dict())

        self.position_signal.emit(Constants.DATA_DID_CHANGE, dict())



    def getFrameFor(self, selection_type, identifier=None):
        if selection_type == 'OPTIONS_BY_INSTRUMENT':
            return self._open_positions[(self._open_positions['SECURITY_TYPE'] == Constants.OPTION) & (self._open_positions['ID'] == identifier)]
        elif selection_type == Constants.OPTION:
            return self._open_positions[self._open_positions['SECURITY_TYPE'] == Constants.OPTION]
        elif selection_type == Constants.STOCK:
            return self._open_positions[self._open_positions['SECURITY_TYPE'] == Constants.STOCK]
        return None


    def getRowCountFor(self, selection_type, identifier=None):
        return len(self.getFrameFor(selection_type, identifier))


    def getColumnCountFor(self, selection_type, identifier=None):
        try:
            return len(self.getFrameFor(selection_type, identifier).iloc[0])
        except:
            return 0


    def getRowFor(self, row_index, selection_type, identifier):
        print("PositionDataManager.getOptionPositions")
        return self.getFrameFor(selection_type, identifier).iloc[row_index]

    
    def getValueForColRow(self, column_index, row_index, selection_type, identifier):
        print("PositionDataManager.getOptionPositions")
        return self.getFrameFor(selection_type, identifier).iat[row_index, column_index]


    def getOptionPositions(self):
        print("PositionDataManager.getOptionPositions")
        return self.getFrameFor(Constants.OPTION)


    def getStockPositions(self):
        return self.getFrameFor(Constants.STOCK)



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

        self.random_names = [
            'feqdpt', 'qcavhhx', 'sra', 'qvm', 'mfme', 'xha', 'jijhh', 'nnhefh', 
            'dynqlk', 'xtipp', 'mmdvnyd', 'gxyev', 'imfmgbe', 'tjshku', 'dadav', 
            'lglo', 'twcpx', 'eupi', 'mrbvta', 'kwp'
        ]
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
            return self.random_names[section]
        
        return QAbstractTableModel.headerData(self, section, orientation, role)


    # def onVerticalHeaderClicked(self, section_index):
    #     print(f"TableModels.onVerticalHeaderClicked {section_index}")
    #     self.layoutAboutToBeChanged.emit() 
    #     self._table_data.sortValuesForColumn(Constants.SYMBOL)
        
    #     self.layoutChanged.emit()


    def rowCount(self, parent=QtCore.QModelIndex()):
        print("PositionDataModel.rowCount")
        print(self._table_data.getRowCountFor(self._selection_type, self._parameter))
        return self._table_data.getRowCountFor(self._selection_type, self._parameter)


    def columnCount(self, parent=QtCore.QModelIndex()):
        print("PositionDataModel.columnCount")
        print(self._table_data.getColumnCountFor(self._selection_type, self._parameter))
        return self._table_data.getColumnCountFor(self._selection_type, self._parameter)


    def data(self, index, role=Qt.DisplayRole):
        print(f"PositionDataModel.data {index}")
        if role == Qt.DisplayRole:
            print(str(self._table_data.getValueForColRow(index.column(),index.row(), self._selection_type, self._parameter)))
            return str(self._table_data.getValueForColRow(index.column(),index.row(), self._selection_type, self._parameter))
        else:
            return super().data(index, role)
        # elif role == Qt.TextAlignmentRole:
        #     # if self._mapping[index.column()] == Constants.PRICE:
        #     return Qt.AlignRight | Qt.AlignVCenter


    # def setDataFrame(self, newframe):
    #     self.layoutAboutToBeChanged.emit()
    #     self._table_data = newframe
    #     self.layoutChanged.emit()
        

    # def getStockFor(self, row):
    #     return self._table_data.getValueForColRow(Constants.SYMBOL,row), self._table_data.getIndexForRow(row)


    # def sort(self, col, order=Qt.AscendingOrder):
    #     self.layoutAboutToBeChanged.emit()
    #     if self._mapping[col] == '__INDEX__':
    #         self._table_data.sortIndex(ascending=(order==Qt.AscendingOrder))
    #     else:
    #         self._table_data.sortValuesForColumn(self._mapping[col]) #, ascending=(order==Qt.AscendingOrder))
    #     self.layoutChanged.emit()


    @pyqtSlot(str, dict)
    def tableDataUpdate(self, signal, sub_signal):
        print(f"PositionDataModel.tableDataUpdate {signal}")
        if signal == Constants.DATA_WILL_CHANGE:
            self.layoutAboutToBeChanged.emit()
        elif signal == Constants.DATA_DID_CHANGE:
            top_left = self.index(0, 0)
            bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right)

            # if 'column_name' in sub_signal:
            #     column_index = self.getMappingIndex(sub_signal['column_name'])
            #     if column_index is not None:
            #         #print(f"TableModels.tableDataUpdate {id(self)} we update {sub_signal['column_name']}, {sub_signal['row_index']}")
            #         index = self.index(sub_signal['row_index'], column_index)
            #         success = self.setData(index, sub_signal['new_value']) #, Qt.EditRole
            #         self.changed_list.add(index)
            #         self.dataChanged.emit(index, index)
            # else:
            #     top_left = self.index(0, 0)
            #     bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
            #     self.dataChanged.emit(top_left, bottom_right)
        elif signal == Constants.DATA_STRUCTURE_CHANGED:
            self.layoutChanged.emit()


    # def isChanged(self, index):
    #     if index in self.changed_list:
    #         self.changed_list.remove(index)
    #         return True
    #     else:
    #         return False

    # def getMappingIndex(self, column_name):
    #     # Iterate through the dictionary items
    #     for key, value in self._mapping.items():
    #         if value == column_name:
    #             return key
    #     return None

