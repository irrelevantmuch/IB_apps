from PyQt5 import QtCore
from dataHandling.Constants import Constants


def addCheckableTickersTo(ticker_box, stock_list, check_list):
    sorted_keys = sorted(stock_list, key=lambda x: (stock_list[x][Constants.SYMBOL]))

    key_list = dict()
    ticker_box.blockSignals(True)
    ticker_box.clear()

    for index, key in enumerate(sorted_keys):
        value = stock_list[key]
        key_list[index] = key
        ticker_box.key_list = key_list
        
        ticker_box.addItem(value[Constants.SYMBOL])
        item = ticker_box.model().item(index, 0)
        
        if check_list[key]:
            item.setCheckState(QtCore.Qt.Checked)
        else:
            item.setCheckState(QtCore.Qt.Unchecked)

    ticker_box.blockSignals(False)
