from PyQt5.QtWidgets import QComboBox
from PyQt5 import QtCore, QtGui


class CheckableComboBox(QComboBox):
    
    key_list = dict()
    _changed = False

    def __init__(self):
        super(CheckableComboBox, self).__init__()
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QtGui.QStandardItemModel(self))

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        else:
            item.setCheckState(QtCore.Qt.Checked)

        self._changed = True


    def itemState(self, index):
        item = self.model().item(index, 0)
        if item is not None:
            return (item.checkState() == QtCore.Qt.Checked)
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
            self.model().item(index, 0).setCheckState(QtCore.Qt.Unchecked)
        

    def selectAll(self):

        for index in range(self.count()):
            self.model().item(index, 0).setCheckState(QtCore.Qt.Checked)
        

    def noItemsSelected(self):
        for index in range(self.count()):
            if self.model().item(index, 0).checkState() == QtCore.Qt.Checked:
                return False
        return True
        

    def allItemsSelected(self):
        for index in range(self.count()):
            if self.model().item(index, 0).checkState() == QtCore.Qt.Unchecked:
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
            if selection_list[key]: item_state = QtCore.Qt.Checked
            else: item_state = QtCore.Qt.Unchecked
            self.model().item(index, 0).setCheckState(item_state)


    def disableSelection(self):
        for index in range(self.count()):
            self.model().item(index, 0).setEnabled(False)
    
    def enableSelection(self):
        for index in range(self.count()):
            self.model().item(index, 0).setEnabled(True)
        


