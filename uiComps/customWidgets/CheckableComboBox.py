
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

from PyQt6.QtWidgets import QComboBox
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt 


class CheckableComboBox(QComboBox):
    
    key_list = dict()
    _changed = False

    def __init__(self):
        super(CheckableComboBox, self).__init__()
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QtGui.QStandardItemModel(self))

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Unchecked)
        else:
            item.setCheckState(Qt.CheckState.Checked)

        self._changed = True


    def itemState(self, index):
        item = self.model().item(index, 0)
        if item is not None:
            return (item.checkState() == Qt.CheckState.Checked)
        else:
            return False

    def getSelectionAt(self, index):
        return self.itemState(index), self.key_list[index]


    def itemStates(self):
        return {k: self.itemState(i) for i, k in self.key_list.items()}


    def selectedItems(self):
        return [key for key in self.key_list.keys() if self.itemState(key)]


    def deselectAll(self):
        for index in range(self.count()):
            self.model().item(index, 0).setCheckState(Qt.CheckState.Unchecked)
        

    def selectAll(self):

        for index in range(self.count()):
            self.model().item(index, 0).setCheckState(Qt.CheckState.Checked)
        

    def noItemsSelected(self):
        for index in range(self.count()):
            if self.model().item(index, 0).checkState() == Qt.CheckState.Checked:
                return False
        return True
        

    def allItemsSelected(self):
        for index in range(self.count()):
            if self.model().item(index, 0).checkState() == Qt.CheckState.Unchecked:
                return False
        return True


    def hidePopup(self):
        if not self._changed:
            super(CheckableComboBox, self).hidePopup()
        self._changed = False
        

    def disableSelection(self):
        for index in range(self.count()):
            self.model().item(index, 0).setEnabled(False)
    
    def enableSelection(self):
        for index in range(self.count()):
            self.model().item(index, 0).setEnabled(True)
        


    def setSelectionByList(self, selection_list):
        for index, key in self.key_list.items():
            if selection_list[key]: item_state = Qt.CheckState.Checked
            else: item_state = Qt.CheckState.Unchecked
            self.model().item(index, 0).setCheckState(item_state)


    def disableSelection(self):
        for index in range(self.count()):
            self.model().item(index, 0).setEnabled(False)
    
    def enableSelection(self):
        for index in range(self.count()):
            self.model().item(index, 0).setEnabled(True)
        


