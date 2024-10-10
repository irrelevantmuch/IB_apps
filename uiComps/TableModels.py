
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

from PyQt5.QtCore import Qt, QAbstractTableModel, pyqtSignal, QSize, QTimer, pyqtSlot
from PyQt5 import QtCore
from dataHandling.Constants import Constants
from math import isnan
from PyQt5.QtGui import QBrush, QColor


class PandasDataModel(QAbstractTableModel):

    # model_updater = pyqtSignal(str, dict)
    greyout_stale = True
    changed_list = set()

    def __init__(self, table_data, mapping, header_labels=None, output_functions=None, **kwargs):
        super(PandasDataModel, self).__init__(**kwargs)
        self._table_data = table_data
        self._mapping = mapping

        self._table_data.processing_updater.connect(self.tableDataUpdate, Qt.QueuedConnection)

        if header_labels is not None:
            self.header_labels = header_labels
        else:
            self.header_labels = list(self._mapping.values())

        if output_functions is not None:
            self.output_functions = output_functions
        else:
            self.output_functions = [str] * self.columnCount()


    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Vertical:
            if role == Qt.DisplayRole:
                return self._table_data.getValueForColRow(Constants.SYMBOL, section)
            elif role == Qt.BackgroundRole:
                return QBrush(QColor(255, 255, 230))
            elif role == Qt.ForegroundRole:
                return QBrush(QColor(0, 0, 100))    
        elif role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_labels[section]
        
        return QAbstractTableModel.headerData(self, section, orientation, role)


    def onVerticalHeaderClicked(self, section_index):
        print(f"TableModels.onVerticalHeaderClicked {section_index}")
        self.layoutAboutToBeChanged.emit() 
        self._table_data.sortValuesForColumn(Constants.SYMBOL)
        
        self.layoutChanged.emit()


    def rowCount(self, parent=QtCore.QModelIndex()):
        return self._table_data.getCount()


    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self._mapping.keys())     #len(self.datatable.columns.values) 


    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if index.column() in self._mapping:
                column_name = self._mapping[index.column()]
                row = index.row()
                if column_name == '__INDEX__':
                    return self.output_functions[index.column()](self._table_data.getIndexForRow(row))
                else:
                    return self.output_functions[index.column()](self._table_data.getValueForColRow(column_name,row))
        elif role == Qt.TextAlignmentRole:
            # if self._mapping[index.column()] == Constants.PRICE:
            return Qt.AlignRight | Qt.AlignVCenter


    def setDataFrame(self, newframe):
        self.layoutAboutToBeChanged.emit()
        self._table_data = newframe
        self.layoutChanged.emit()
        

    def getStockFor(self, row):
        return self._table_data.getValueForColRow(Constants.SYMBOL,row), self._table_data.getIndexForRow(row)


    def sort(self, col, order=Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()
        if self._mapping[col] == '__INDEX__':
            self._table_data.sortIndex(ascending=(order==Qt.AscendingOrder))
        else:
            self._table_data.sortValuesForColumn(self._mapping[col]) #, ascending=(order==Qt.AscendingOrder))
        self.layoutChanged.emit()


    @pyqtSlot(str, dict)
    def tableDataUpdate(self, signal, sub_signal):
        if signal == Constants.DATA_WILL_CHANGE:
            self.layoutAboutToBeChanged.emit()
        elif signal == Constants.DATA_DID_CHANGE:
            if 'column_name' in sub_signal:
                column_index = self.getMappingIndex(sub_signal['column_name'])
                if column_index is not None:
                    #print(f"TableModels.tableDataUpdate {id(self)} we update {sub_signal['column_name']}, {sub_signal['row_index']}")
                    index = self.index(sub_signal['row_index'], column_index)
                    success = self.setData(index, sub_signal['new_value']) #, Qt.EditRole
                    self.changed_list.add(index)
                    self.dataChanged.emit(index, index)
            else:
                top_left = self.index(0, 0)
                bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
                self.dataChanged.emit(top_left, bottom_right)
        elif signal == Constants.DATA_STRUCTURE_CHANGED:
            self.layoutChanged.emit()


    def isChanged(self, index):
        if index in self.changed_list:
            self.changed_list.remove(index)
            return True
        else:
            return False

    def getMappingIndex(self, column_name):
        # Iterate through the dictionary items
        for key, value in self._mapping.items():
            if value == column_name:
                return key
        return None

            
        


class PandasStaleModel(PandasDataModel):

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if index.column() in self._mapping:
                column_name = self._mapping[index.column()]
                row = index.row()
                return self.output_functions[index.column()](self._table_data.getValueForColRow(column_name, row))
        elif role == Qt.BackgroundRole:
            if self._table_data.getValueForColRow(Constants.STALE, index.row()) and self.greyout_stale:
                return QBrush(QColor(230, 230, 230))
        else:
            return super().data(index, role)
            # return QtCore.QVariant()

        



# class MemoryModel(PandasStaleModel):

#     current_values = None

#     previous_column_count = 0
#     previous_row_count = 0

#     def __init__(self, table_data, mapping, header_labels=None, output_functions=None):
#         super(MemoryModel, self).__init__(table_data, mapping, header_labels=header_labels, output_functions=output_functions)
#         self.current_values = np.zeros((self.rowCount(), self.columnCount()))


#     def resetMemoryModel(self, signal):
#         if signal == Constants.DATA_STRUCTURE_CHANGED:
#             self.current_values = np.zeros((self.rowCount(), self.columnCount()))


#     def updateValue(self, row, column, value):
#         change = self.current_values[row, column] != 0.0 and not np.isnan(self.current_values[row, column]) and self.current_values[row, column] != value
#         if type(value) is not str:
#             self.current_values[row, column] = value

#         return change


#     def sort(self, col, order=Qt.AscendingOrder):
#         self.tableDataUpdate(Constants.DATA_STRUCTURE_CHANGED, dict())
#         super().sort(col, order=order)


class OverviewModel(PandasStaleModel):

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()

        if index.column() in self._mapping:
            column_name = self._mapping[index.column()]

            # if role == Qt.BackgroundRole:
            #     changed = self.updateValue(row, index.column(), self._table_data.getValueForColRow(column_name, row))
        
            #     if changed:
            #         QTimer.singleShot(250, lambda: self.dataChanged.emit(index, index))
            #         return QBrush(QColor(180, 180, 255))

            if column_name.endswith('_FROM'):
                if isnan(self._table_data.getValueForColRow(column_name,row)): return super().data(index, role)
                
                if role == Qt.BackgroundRole and not(self._table_data.getValueForColRow(Constants.STALE, row) and self.greyout_stale):
                    move = self._table_data.getValueForColRow(column_name,row)
                    intensity = int(move*2)
                    return QBrush(QColor(255, 255, max(255-intensity,0)))
            elif column_name.endswith('_MOVE'):
                if isnan(self._table_data.getValueForColRow(column_name,row)): return super().data(index, role)

                if role == Qt.BackgroundRole and not(self._table_data.getValueForColRow(Constants.STALE, row) and self.greyout_stale):
                    intensity = int(self._table_data.getValueForColRow(column_name,row)*10)
                    if intensity > 0:
                        return QBrush(QColor(max(0, 255-intensity), 255, max(0, 255-intensity)))
                    else:
                        return QBrush(QColor(255, max(0, 255+intensity), max(0, 255+intensity)))


        return super().data(index, role)
                

class LevelModel(PandasStaleModel):

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        
        column_name = self._mapping[index.column()]
        if column_name.endswith('_Low') or column_name.endswith('_High'):
            if role == Qt.BackgroundRole and not(self._table_data.getValueForColRow(Constants.STALE,row) and self.greyout_stale):
                value = self._table_data.getValueForColRow(column_name,row)

                if isnan(value): return super().data(index, role)

                diff = self._table_data.getValueForColRow(column_name + '_Diff',row)
                price = self._table_data.getValueForColRow('PRICE',row)
                perc_move = 100*diff/price
                blue_intensity = max(255-int(20/max(perc_move,0.001)), 0)
                return QBrush(QColor(255, 255, blue_intensity))
            elif role == Qt.DisplayRole:
                value = self._table_data.getValueForColRow(column_name,row)
                diff = self._table_data.getValueForColRow(column_name + '_Diff',row)
                return f"{value:.2f} - {diff:.2f}"

        return super().data(index, role)


    def sort(self, col, order=Qt.AscendingOrder):

        column_name = self._mapping[col]
        if column_name.endswith('_Low') or column_name.endswith('_High'):
            # self.model_updater.emit(Constants.DATA_WILL_CHANGE, dict())
            self._table_data.sortValuesForColumn(column_name + '_Diff', ascending=(order==Qt.AscendingOrder))
            # self.model_updater.emit(Constants.DATA_DID_CHANGE, dict())
        else:
            super().sort(col, order)


class StepModel(PandasStaleModel):


    def data(self, index, role=Qt.DisplayRole):
        row = index.row()

        if index.column() in self._mapping:
            column_name = self._mapping[index.column()]

            if column_name.endswith('Steps'):
                if isnan(self._table_data.getValueForColRow(column_name,row)): return super().data(index, role)
                
                if role == Qt.BackgroundRole and not self._table_data.getValueForColRow(Constants.STALE,row):
                    
                    # changed = self.isChanged(index)
                    # if changed:
                    #     QTimer.singleShot(250, lambda: self.dataChanged.emit(index, index))

                    # if changed: 
                    #     return QBrush(QColor(180, 180, 255))
                    # else:
                    steps = self._table_data.getValueForColRow(column_name,row)
                    move = abs(self._table_data.getValueForColRow(column_name + '_Move',row))
                    if isnan(steps): return super().data(index, role)
                    intensity = int(5 * (steps + move))
                    return QBrush(QColor(255, 255, max(255-intensity,0)))
                elif role == Qt.DisplayRole:
                    steps = self._table_data.getValueForColRow(column_name,row)
                    if isnan(steps): return super().data(index, role)
                    move = abs(self._table_data.getValueForColRow(column_name + '_Move',row))
                    return f"{steps:.2f} - {move:.2f}%"
        elif role == Qt.BackgroundRole and not (self._table_data.getValueForColRow(Constants.STALE,row) and self.greyout_stale):
            return QBrush(QColor(170, 170, 255))
        elif role == Qt.SizeHintRole:
            return QSize(5, 0)

        return super().data(index, role)
                

class RSIModel(PandasStaleModel):


    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        column_name = self._mapping[index.column()]
        if column_name.endswith('_RSI'):
            if role == Qt.BackgroundRole and not (self._table_data.getValueForColRow(Constants.STALE, row) and self.greyout_stale):
                changed = self.isChanged(index)

                if changed:
                    QTimer.singleShot(250, lambda: self.dataChanged.emit(index, index))

                rsi = self._table_data.getValueForColRow(column_name,row)
                if isnan(rsi): return super().data(index, role)

                if changed: 
                    return QBrush(QColor(180, 180, 255))
                elif column_name.startswith('Difference'):
                    intensity = abs(rsi)
                    return QBrush(QColor(255, 255, 255-intensity*3))
                elif (rsi > 60) and (rsi < 99):
                    intensity = rsi - 60
                    return QBrush(QColor(255-intensity*6, 255, 255-intensity*6))
                elif (rsi < 40) and (rsi > 1):
                    intensity = 40 - rsi
                    return QBrush(QColor(255, 255-intensity*6, 255-intensity*6))

        return super().data(index, role)


class CorrModel(PandasStaleModel):


    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        column_name = self._mapping[index.column()]
        if column_name.endswith('_CORR'):

            if role == Qt.BackgroundRole and not (self._table_data.getValueForColRow(Constants.STALE, row) and self.greyout_stale):
                # changed = self.updateValue(row, index.column(), self._table_data.getValueForColRow(column_name,row))
        
                # if changed:
                #     QTimer.singleShot(250, lambda: self.dataChanged.emit(index, index))

                r_coef = self._table_data.getValueForColRow(column_name,row)
                if isnan(r_coef): return super().data(index, role)

                # if changed: 
                #     return QBrush(QColor(180, 180, 255))
                # el
                if r_coef > 0.3:
                    green_factor = r_coef * 100
                    return QBrush(QColor(255-green_factor, 255, 255-green_factor))
                elif r_coef < -0.3:
                    red_factor = r_coef * -100
                    return QBrush(QColor(255, 255-red_factor, 255-red_factor))

        return super().data(index, role)


class ListCorrModel(CorrModel):

    # def sort(self, col, order=Qt.AscendingOrder):
        # self.model_updater.emit(Constants.DATA_WILL_CHANGE, dict())
        # self._table_data.sort_values("CORR_VALUES", ascending=(order==Qt.AscendingOrder), key=lambda x: x.apply(lambda y: y[col]), inplace=True)
        # self.model_updater.emit(Constants.DATA_DID_CHANGE, dict())


    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return self._table_data.getValueForColRow(Constants.SYMBOL, section)
        return super().headerData(section, orientation, role)


    def data(self, index, role=Qt.DisplayRole):

        row = index.row()
        column = index.column()
    
        corr_list = self._table_data.getValueForColRow("CORR_VALUES",row)
        if not isinstance(corr_list, list) and isnan(corr_list):
            if role == Qt.DisplayRole:
                return "Nan"
            else:
                return super().data(index, role)

        if column < len(corr_list):
            r_coef = corr_list[column]
            
            if role == Qt.DisplayRole:
                return f"{r_coef:.2f}"
            elif role == Qt.BackgroundRole and not(self._table_data.getValueForColRow(Constants.STALE, row) and self.greyout_stale):
                # changed = self.updateValue(row, column, r_coef)
        
                # if changed:
                #     QTimer.singleShot(250, lambda: self.dataChanged.emit(index, index))

                # changed = False
                if isnan(r_coef): return super().data(index, role)

                # if changed: 
                #     return QBrush(QColor(180, 180, 255))
                # el
                if r_coef > 0.3:
                    green_factor = r_coef * 150
                    return QBrush(QColor(255-green_factor, 255, 255-green_factor))
                elif r_coef < -0.3:
                    red_factor = r_coef * -150
                    return QBrush(QColor(255, 255-red_factor, 255-red_factor))

        return super().data(index, role)

