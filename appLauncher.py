
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

from PyQt5.QtCore import QThread, pyqtSlot, Qt, pyqtSignal
from PyQt5 import QtWidgets
from dataHandling.Constants import Constants
from AppLauncherWindow import AppLauncherWindow

import sys, os, time
from uiComps.Logging import Logger

from dataHandling.ibFTPdata import downloadShortData

from apps.listManaging.listManager import ListManager
from apps.polygonDownload.dataDownloader import DataDownloader
from apps.optionPositions.optionsPositionListing import OptionPositions
from apps.optionVisualization.optionsVisualization import OptionVisualization
from apps.comparisons.comparisonLists import ComparisonList
from apps.alerting.alertManager import AlertManager
from apps.tradeMaker.tradeMaker import TradeMaker
from apps.movers.moversLists import MoversList
from apps.positionManaging.positionManager import PositionApp
from IBConnector import IBConnector
from TelegramBot import TelegramBot

QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class AppLauncher(AppLauncherWindow, IBConnector):

    running_apps = []
    data_source = Constants.IB_SOURCE
    ib_connected = False
    telegram_signal = pyqtSignal(str, dict)
    telegram_bot = None

    def __init__(self):
        super().__init__()
        self.logging_instance = Logger.instance()
        self.logging_instance.setLogWindow(self.log_window)
        self.real_tws_button.setChecked(True)
        self.connectionSelection()
        self.updateConnectionStatus('closed')


    def updateConnectionStatus(self, status):
        print(f"AppLauncher.updateConnectionStatus {status}")
        if status == Constants.CONNECTION_OPEN:
            self.statusbar.showMessage("Connection Open")
            self.toggleAppButtons(True, interface=self.data_source)
            self.ib_connected = True
        else:
            self.statusbar.showMessage("Offline")
            self.ib_connected = False


    def connectionSelection(self):
        if self.real_tws_button.isChecked():
            self.setTradingOptions(Constants.LOCAL_ADDRESS, Constants.TRADING_TWS_SOCKET, False)
        elif self.paper_tws_button.isChecked():
            self.setTradingOptions(Constants.LOCAL_ADDRESS, Constants.PAPER_TWS_SOCKET, False)
        elif self.real_ibg_button.isChecked():
            self.setTradingOptions(Constants.LOCAL_ADDRESS, Constants.TRADING_IBG_SOCKET, False)
        elif self.paper_ibg_button.isChecked():
            self.setTradingOptions(Constants.LOCAL_ADDRESS, Constants.PAPER_IBG_SOCKET, False)
        elif self.custom_button.isChecked():
            self.setTradingOptions(Constants.LOCAL_ADDRESS, Constants.TRADING_IBG_SOCKET, True)


    def dataSelection(self):
        if self.ib_data_radio.isChecked():
            self.data_source = Constants.IB_SOURCE
            self.toggleAppButtons(self.ib_connected, interface=Constants.IB_SOURCE)

        elif self.finazon_data_radio.isChecked():
            self.toggleAppButtons(True, interface=Constants.FINAZON_SOURCE)

            self.data_source = Constants.FINAZON_SOURCE
            

    def appRunning(self,app_type):
        current_app = None
        for app in self.running_apps:
            if isinstance(app, app_type):
                current_app = app
                break

        if current_app is not None:
            current_app.activateWindow()
            current_app.raise_()
            return True
        else:
            return False


    def openOptionPosApp(self):
        position_manager = self.getNewPositionManager()
        new_app = OptionPositions(position_manager)
        self.running_apps.append(new_app)
        new_app.show()
    

    def openOptionVizApp(self):
        if not self.appRunning(OptionVisualization):
            option_manager = self.getOptionManager()
            symbol_manager = self.getNewSymbolManager(identifier='option_symbol_manager')
            new_app = OptionVisualization(option_manager, symbol_manager)
            self.running_apps.append(new_app)
            new_app.show()


    def openStocksApp(self):
        position_manager = self.getNewPositionManager()
        new_app = PortfolioManager(position_manager)
        self.running_apps.append(new_app)
        new_app.show()
    
    
    def openPositionsApp(self):
        position_manager = self.getNewPositionManager()
        order_manager = self.getOrderManager()
        new_app = PositionApp(position_manager, order_manager)
        self.running_apps.append(new_app)
        new_app.show()
    

    def openAlertApp(self):
        buffered_manager, indicator_processor = self.getBufferedManagerWithIndicator(indicators={'rsi', 'steps'})
        alert_app = AlertManager(buffered_manager, indicator_processor, QThread())
        if self.telegram_bot is not None:
            alert_app.setTelegramListener(self.telegram_signal)
        self.running_apps.append(alert_app)
        alert_app.show()



    def openDataDetailsApp(self):
        new_app = DataDownloader(QThread())
        self.running_apps.append(new_app)
        new_app.show()


    def openManualTraderApp(self):
        order_manager = self.getOrderManager()
        history_manager = self.getHistoryManagerIB(identifier='manual_trader_history')
        symbol_manager = self.getNewSymbolManager(identifier='trader_symbol_manager')
        new_app = TradeMaker(order_manager, history_manager, symbol_manager)
        self.running_apps.append(new_app)
        new_app.show()


    def openMoversApp(self):
        if not self.appRunning(MoversList):
            buffered_manager = self.getBufferedManager()

            new_app = MoversList(buffered_manager, QThread())
            self.running_apps.append(new_app)
            new_app.show()


    def cleanupClosedApp(self):
        print("AppLauncher.cleanupClosedApp")
        for app in self.running_apps:
            if isinstance(app, MoversList):
                self.running_apps.remove(app)
                break


    def openComparisonApp(self):
        buffered_manager = self.getBufferedManager()
        new_app = ComparisonList(buffered_manager, QThread())
        if self.telegram_bot is not None:
            new_app.telegram_signal = self.telegram_signal
            self.telegram_bot.incoming_message_signal.connect(new_app.processTelegram)
        self.running_apps.append(new_app)
        new_app.show()


    def openListManager(self):
        symbol_manager = self.getNewSymbolManager(identifier='list_symbol_manager')
        buffered_manager = self.getBufferedManager()
        option_manager = self.getOptionManager()
        new_app = ListManager(symbol_manager, buffered_manager, option_manager)
        self.running_apps.append(new_app)
        new_app.show()


    def historyUpdates(self, signal):
        print(f"AppLauncher.historyUpdates: {signal}")


    def downloadShortRateData(self):
        downloadShortData("data/")


    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, sub_signal):
        if signal == Constants.CONNECTION_STATUS_CHANGED:
            self.updateConnectionStatus(sub_signal['connection_status'])
 

    def setTradingOptions(self, local_address, trading_socket, editable):
        self.local_address = local_address
        self.address_line.setText(local_address)
        self.socket_line.setText(str(trading_socket))
        self.trading_socket = trading_socket
        self.address_line.setEnabled(editable)
        self.socket_line.setEnabled(editable)


    def toggleTelegramBot(self, checked):
        print(f"AppLauncher.toggleTelegramBot {checked}")
        if checked:
            self.setupTelegramBot()
        else:
            print("KILLING TELEGRAM BOT NOT IMPLEMENTED")
    

    def setupTelegramBot(self):
                # Setup the bot logic and thread
        self.telegram_bot = TelegramBot()  # Replace with your actual token
        self.telegram_signal.connect(self.telegram_bot.sendMessage, Qt.QueuedConnection)
        self.telegram_bot.run()
        print(f"AppLauncher init {int(QThread.currentThreadId())}")
        

    def closeEvent(self, *args, **kwargs):
        if self.telegram_bot is not None:
            self.telegram_bot.cleanupMessages()


if __name__ == "__main__":

        # Set the environment variables
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("macos")
    app.aboutToQuit.connect(app.deleteLater)
    window = AppLauncher()
    window.show()
    app.exec_()



