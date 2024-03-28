from PyQt5.QtCore import Qt
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QCompleter


class SymbolCompleter(QCompleter):

    ConcatenationRole = Qt.UserRole + 1
        
    def __init__(self, delegate, parent=None):
        super().__init__(parent)
        self.delegate = delegate
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.refreshModel()

        self.highlighted[QtCore.QModelIndex].connect(self.highlightedCompletion)

    def refreshModel(self):
        self.model = QStandardItemModel(self)
        self.setModel(self.model)

    def addToList(self, details):
        item = QStandardItem(details.symbol + " (" + details.long_name + " @" + details.exchange + ")")
        item.setData(details)
        self.model.appendRow(item)

    def highlightedCompletion(self, value):
        sourceIndex = self.completionModel().mapToSource(value)
        details = self.model.itemFromIndex(sourceIndex).data()
        self.delegate.selectedContract(details)
        

class Validator(QtGui.QValidator):
    def validate(self, string, pos):
        return QtGui.QValidator.Acceptable, string.upper(), pos

