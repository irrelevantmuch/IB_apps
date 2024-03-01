from PyQt5 import QtCore, QtWidgets

def findRowForValue(table, value, column):
    for row in range(table.rowCount()):

        if table.item(row, column).data(QtCore.Qt.DisplayRole) == value:
            return row

    return -1


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