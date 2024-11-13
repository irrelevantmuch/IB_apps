
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

from PyQt5 import QtCore, QtWidgets

def findRowForValue(table, value, column):
    for row in range(table.rowCount()):

        if table.item(row, column).data(QtCore.Qt.DisplayRole) == value:
            return row

    return -1


def addAccountsToSelector(accounts, selector, def_account=""):
    selector.blockSignals(True)
    masked_accounts = [maskAccountString(account) for account in accounts]
    selector.addItems(masked_accounts)
    try:
        def_index = accounts.index(def_account)
        selector.setCurrentIndex(def_index)
    except ValueError:
        pass

    selector.blockSignals(False)
    
def maskAccountString(unm_str):
    mask_length = len(unm_str) - 3
    masked = unm_str[:1] + '*' * mask_length + unm_str[-2:]
    return masked


def getNumericItem(float_value):
    item = QtWidgets.QTableWidgetItem()
    item.setData(QtCore.Qt.DisplayRole, float(float_value))
    return item
    

class AlignDelegate(QtWidgets.QStyledItemDelegate):

    def initStyleOption(self, option, index):
        super(AlignDelegate, self).initStyleOption(option, index)
        option.displayAlignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter

class PercAlignDelegate(QtWidgets.QStyledItemDelegate):

    def initStyleOption(self, option, index):
        super(PercAlignDelegate, self).initStyleOption(option, index)
        option.displayAlignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter

    def displayText(self, text, locale):
        """
        Display `text` in the selected with the selected number
        of digits

        text:   string / QVariant from QTableWidget to be rendered
        locale: locale for the text
        """
        return "{:.2f}%".format(text)


class PriceAlignDelegate(QtWidgets.QStyledItemDelegate):

    def initStyleOption(self, option, index):
        super(PriceAlignDelegate, self).initStyleOption(option, index)
        option.displayAlignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter

    def displayText(self, text, locale):
        """
        Display `text` in the selected with the selected number
        of digits

        text:   string / QVariant from QTableWidget to be rendered
        locale: locale for the text
        """
        return "{:.2f}".format(text)


class BigNumberAlignDelegate(QtWidgets.QStyledItemDelegate):

    def initStyleOption(self, option, index):
        super(BigNumberAlignDelegate, self).initStyleOption(option, index)
        option.displayAlignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter

    def displayText(self, text, locale):
        """
        Display `text` in the selected with the selected number
        of digits

        text:   string / QVariant from QTableWidget to be rendered
        locale: locale for the text
        """
        if text.startswith(">"):
            text = text.replace(">", "")
            return ">{:,}".format(int(text)) 
        elif text == "":
            return "Not Av."
        else:
            return "{:,}".format(int(text))