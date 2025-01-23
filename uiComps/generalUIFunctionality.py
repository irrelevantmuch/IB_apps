
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

from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import pyqtSignal, Qt
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
            item.setCheckState(Qt.CheckState.Checked)
        else:
            item.setCheckState(Qt.CheckState.Unchecked)

    ticker_box.blockSignals(False)


class MyAppWindow(QMainWindow):

    closing = pyqtSignal()

    def closeEvent(self, event):
        self.closing.emit()  # Emit the custom signal
        event.accept()


class ProcessorWindow(MyAppWindow):

    def closeEvent(self, *args, **kwargs):
        
        self.data_processor.stop()
        self.data_processor.deleteLater()
        self.processor_thread.quit()
        self.processor_thread.wait()
        super().closeEvent(*args, **kwargs)
        