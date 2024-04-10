
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

from PyQt5.QtCore import Qt, QAbstractTableModel, pyqtSignal, pyqtSlot, QEvent
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDoubleSpinBox, QSpinBox, QPushButton, QStyledItemDelegate
from dataHandling.Constants import Constants

class SpinBoxDelegate(QStyledItemDelegate):
    
    def __init__(self, widget_type, parent=None):
        super().__init__(parent)
        
        self.widget_type = widget_type


    def createEditor(self, parent, option, index):
        if self.widget_type == 'double_spin_box':
            editor = QDoubleSpinBox(parent)
            editor.setMinimum(-1000)
        elif self.widget_type == 'int_spin_box':
            editor = QSpinBox(parent)
            editor.setMinimum(0)
            
        editor.setAlignment(Qt.AlignRight)
        
        editor.setMaximum(10000) 
        return editor

    
    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        print(f"OrderDataModel.setEditorData {value} {type(value)}")
        editor.setValue(value)


    def setModelData(self, editor, model, index):
        model.setData(index, editor.value(), Qt.EditRole)


class ButtonDelegate(QStyledItemDelegate):
    button_click_signal = pyqtSignal(int)  # Signal to emit when button is clicked, passing row number

    def __init__(self, button_text, parent=None):
        super(ButtonDelegate, self).__init__(parent)
        self.button_text = button_text

    def paint(self, painter, option, index):
        if not self.parent().indexWidget(index):
            button = QPushButton(self.parent())
            button.setText(self.button_text)
            button.clicked.connect(lambda: self.button_click_signal.emit(index.row()))
            self.parent().setIndexWidget(index, button)


class CheckBoxDelegate(QStyledItemDelegate):
    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonPress:
            # Toggle the state
            currentValue = model.data(index, Qt.CheckStateRole)
            newState = Qt.Unchecked if currentValue == Qt.Checked else Qt.Checked
            model.setData(index, newState, Qt.CheckStateRole)
            return True  # Indicate the event has been handled
        return False  # For other events, return False


class OrderDataModel(QAbstractTableModel):

    order_edit_update = pyqtSignal(int, dict)

    def __init__(self, order_data, colummn_headers, **kwargs):
        super().__init__(**kwargs)
        
        self._order_data = order_data
        self._order_data.order_buffer_signal.connect(self.tableDataUpdate, Qt.QueuedConnection)
        self._header_labels = colummn_headers


    @pyqtSlot(str, int)
    def tableDataUpdate(self, signal, order_id):
        print(f"OrderDataModel.tableDataUpdate {signal} {order_id}")
        if signal == Constants.DATA_WILL_CHANGE:
            self.layoutAboutToBeChanged.emit()
        elif signal == Constants.DATA_DID_CHANGE:
            pass
            # if 'column_name' in order_id:
            #     column_index = self.getMappingIndex(order_id['column_name'])
            #     if column_index is not None:
            #         index = self.index(order_id['row_index'], column_index)
            #         success = self.setData(index, order_id['new_value'])
            #         self.changed_list.add(index)
            #         self.dataChanged.emit(index, index)
            # else:
            #     top_left = self.index(0, 0)
            #     bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
            #     self.dataChanged.emit(top_left, bottom_right)
        elif signal == Constants.DATA_STRUCTURE_CHANGED:
            self.layoutChanged.emit()


    def isEditableColumn(self, index):
        editable_columns = [self._header_labels.index(col_name) for col_name in ['Count', 'Limit', 'Stop level']]
        return index in editable_columns


    def rowCount(self, parent=QtCore.QModelIndex()):
        print(f"OrderDataModel.rowCount {self._order_data.getOrderCount}")
        return self._order_data.getOrderCount()


    def columnCount(self, parent=QtCore.QModelIndex()):
        print(f"OrderDataModel.columnCount {len(self._header_labels)}")
        return len(self._header_labels) + 1


    def headerData(self, section, orientation, role=Qt.DisplayRole):        
        if (role == Qt.DisplayRole) and (orientation == Qt.Horizontal):
            if section < len(self._header_labels):
                return self._header_labels[section]
            else:
                return 'Cancel'
        
        return super().headerData(section, orientation, role)


    def flags(self, index):
        if self.isEditableColumn(index.column()):
            return super().flags(index) | Qt.ItemIsEditable
        else:
            return super().flags(index)


    def data(self, index, role=Qt.DisplayRole):
        
        if index.column() < len(self._header_labels):
            column_name = self._header_labels[index.column()]
            if role == Qt.DisplayRole:
                return str(self._order_data.getDataForColumn(index.row(), column_name))
            elif role == Qt.EditRole:
                return self._order_data.getDataForColumn(index.row(), column_name)
            elif role == Qt.TextAlignmentRole:
                return Qt.AlignRight | Qt.AlignVCenter

        return None


    def setData(self, index, value, role=Qt.EditRole):
        column_name = self._header_labels[index.column()]
        if role == Qt.EditRole:
            prop_type = self._order_data.getPropTypeForColumn(column_name)
            self.order_edit_update.emit(self._order_data.getOrderId(index.row()), {prop_type: value})
            return True
        return False



class StairDataModel(QAbstractTableModel):

    stair_edit_update = pyqtSignal(tuple, dict)

    def __init__(self, stair_tracker, headers, **kwargs):
        super().__init__(**kwargs)
        self._stair_tracker = stair_tracker
        self._stair_tracker.stair_buffer_signal.connect(self.tableDataUpdate, Qt.QueuedConnection)
        self._header_labels = headers
        self.check_states = {}  # Store checkbox states for each index


    @pyqtSlot(str)
    def tableDataUpdate(self, signal):
        if signal == Constants.DATA_WILL_CHANGE:
            self.layoutAboutToBeChanged.emit()
        elif signal == Constants.DATA_DID_CHANGE:
            pass
            # if 'column_name' in order_id:
            #     column_index = self.getMappingIndex(order_id['column_name'])
            #     if column_index is not None:
            #         index = self.index(order_id['row_index'], column_index)
            #         success = self.setData(index, order_id['new_value'])
            #         self.changed_list.add(index)
            #         self.dataChanged.emit(index, index)
            # else:
            #     top_left = self.index(0, 0)
            #     bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
            #     self.dataChanged.emit(top_left, bottom_right)
        elif signal == Constants.DATA_STRUCTURE_CHANGED:
            self.layoutChanged.emit()


    def rowCount(self, parent=QtCore.QModelIndex()):
        return self._stair_tracker.getRowCount()


    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self._header_labels)


    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if (role == Qt.DisplayRole) and (orientation == Qt.Horizontal):
            return self._header_labels[section]
        return super().headerData(section, orientation, role)


    def flags(self, index):
        flags = super().flags(index)
        if index.column() == 0 and (index.row() % 3 == 1 or index.row() % 3 == 2):
            flags |= Qt.ItemIsUserCheckable
        elif self.isEditableColumn(index.column()):
            flags |= Qt.ItemIsEditable

        return flags


    def isEditableColumn(self, column_index):
        editable_columns = [self._header_labels.index(col_name) for col_name in ['Count', 'Trigger', 'Limit']]
        return column_index in editable_columns


    def data(self, index, role=Qt.DisplayRole):

        if role == Qt.CheckStateRole and index.column() == 0 and (index.row() % 3 == 1 or index.row() % 3 == 2):
            return self.check_states.get(index, Qt.Unchecked)
        elif index.column() <= 4:
            if index.column() == 0:
                value = self._stair_tracker.getNameForRow(index.row())
            elif index.column() == 1:
                value = self._stair_tracker.getOrderAction(index.row())
            elif index.column() == 2:
                value = self._stair_tracker.getOrderCount(index.row())
            elif index.column() == 3:
                value = self._stair_tracker.getTriggerOffsetForRow(index.row())
            elif index.column() == 4:
                value = self._stair_tracker.getLimitOffsetForRow(index.row())


            if role == Qt.DisplayRole:
                return str(value)
            elif role == Qt.EditRole:
                return value
        
        return None


    def setData(self, index, value, role=Qt.EditRole):
        column_name = self._header_labels[index.column()]
        row = index.row()
        property_type = self._stair_tracker.getPropertyFor(column_name, row)

        if role == Qt.EditRole:
            key, _ = self._stair_tracker.getKeyAndTypeForRow(row)
            self.stair_edit_update.emit(key, {property_type: value})
            return True
        elif role == Qt.CheckStateRole and index.column() == 0:
            self.check_states[index] = value
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return False

