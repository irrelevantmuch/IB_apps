
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

from PyQt6.QtCore import Qt
from PyQt6 import QtCore, QtGui
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QCompleter


class SymbolCompleter(QCompleter):

    ConcatenationRole = Qt.ItemDataRole.UserRole + 1
        
    def __init__(self, delegate, parent=None):
        super().__init__(parent)
        self.delegate = delegate
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
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
        return QtGui.QValidator.State.Acceptable, string.upper(), pos

