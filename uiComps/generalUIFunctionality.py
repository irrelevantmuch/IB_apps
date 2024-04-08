from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import pyqtSignal, Qt
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
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)

    ticker_box.blockSignals(False)


class ProcessorWindow(QMainWindow):

    close_signal = pyqtSignal()

    def closeEvent(self, *args, **kwargs):
        print("ProcessorWindow.closeEvent")
        self.data_processor.stop()
        self.processor_thread.quit()
        self.processor_thread.wait()
        super(QMainWindow, self).closeEvent(*args, **kwargs)
        self.close_signal.emit()