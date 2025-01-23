
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
from PyQt6.QtCore import QThread, pyqtSlot, Qt, pyqtSignal

from PyQt6 import QtWidgets

import sys, os, time



from AppLauncherWindow import AppLauncherWindow
from dataHandling.Constants import Constants
from uiComps.Logging import Logger
from dataHandling.UserDataManagement import loadAccountSettings, saveAccountSettings
from dataHandling.ibFTPdata import downloadShortData
from generalFunctionality.UIFunctions import addAccountsToSelector

from apps.listManaging.listManager import ListManager
# from apps.polygonDownload.dataDownloader import DataDownloader
from apps.optionPositions.optionsPositionListing import OptionPositions
from apps.optionVisualization.optionsVisualization import OptionVisualization
from apps.comparisons.comparisonLists import ComparisonList
from apps.alerting.alertManager import AlertManager
from apps.tradeMaker.tradeMaker import TradeMaker
from apps.movers.moversLists import MoversList
from dataHandling.HistoryManagement.BufferedManager import BufferedDataManager
from dataHandling.HistoryManagement.FinazonBufferedManager import FinazonBufferedDataManager 

from apps.portfolioManaging.portfolioManager import PositionManager
from apps.positionManaging.positionManager import PositionApp
from ConnectionThreadManager import ConnectionThreadManager
from TelegramBot import TelegramBot


# QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
# QSizePolicy.Policy.ExpandingQtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)



    #### Decorator for keeping track of which apps are open, as to avoid doubles
    
def appRunning(app_type, running_apps):
    current_app = None
    for app in running_apps:
        if isinstance(app, app_type):
            return app

def app_opener(app_type):
    def decorator(func):
        def wrapper(self):
            current_app = appRunning(app_type, self.running_apps)
            if not current_app:
                new_app = func(self)
                new_app.closing.connect(lambda: self.running_apps.remove(new_app))
                self.running_apps.append(new_app)
                new_app.show()
            else:
                current_app.activateWindow()
                current_app.raise_()

        return wrapper
    return decorator



class AppLauncher(AppLauncherWindow, ConnectionThreadManager):

    running_apps = []
    data_source = Constants.IB_SOURCE
    ib_connected = False
    telegram_signal = pyqtSignal(str, dict)
    telegram_bot = None
    _accounts = []

    def __init__(self):
        super().__init__()
        self.logging_instance = Logger.instance()
        self.logging_instance.setLogWindow(self.log_window)
        self.real_tws_button.setChecked(True)
        self.connectionSelection()
        self._account_settings = loadAccountSettings()
        print(f"AppLauncher.init {self._account_settings}")
        self.updateConnectionStatus(Constants.CONNECTION_CLOSED)


    def updateConnectionStatus(self, status):
        
        if status == Constants.CONNECTION_OPEN:
            self.statusbar.showMessage("Connection Open")
            self.toggleAppButtons(True, interface=self.data_source)
            self.ib_connected = True
        elif status == Constants.CONNECTION_CLOSED:
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


    @app_opener(OptionPositions)
    def openOptionPosApp(self):
        position_manager = self.getNewPositionManager()
        return OptionPositions(position_manager)
    

    @app_opener(OptionVisualization)
    def openOptionVizApp(self):
        option_manager = self.getOptionManager()
        symbol_manager = self.getNewSymbolManager(identifier='option_symbol_manager')
        return OptionVisualization(option_manager, symbol_manager)
            

    @app_opener(PositionManager)
    def openStocksApp(self):
        position_manager = self.getNewPositionManager()
        return PositionManager(position_manager)
        

    @app_opener(PositionApp)
    def openPositionsApp(self):
        position_manager = self.getNewPositionManager()
        order_manager = self.getOrderManager()
        return PositionApp(position_manager, order_manager)
        
    
    @app_opener(AlertManager)
    def openAlertApp(self):
        history_manager = self.getHistoryManager('general_history')
        indicator_processor = self.getIndicatorManager({'rsi', 'steps'}, history_manager.getDataBuffer())

        alert_app = AlertManager(history_manager, indicator_processor, QThread())
        if self.telegram_bot is not None:
            alert_app.setTelegramListener(self.telegram_signal)
        return alert_app


    @app_opener(DataDownloader)
    def openDataDetailsApp(self):
        return DataDownloader(QThread())
        

    @app_opener(TradeMaker)
    def openManualTraderApp(self):
        order_manager = self.getOrderManager()
        history_manager = self.getHistoryManagerIB(identifier='manual_trader_history')
        symbol_manager = self.getNewSymbolManager(identifier='trader_symbol_manager')
        return TradeMaker(self._accounts, self._account_settings['default_account'], order_manager, history_manager, symbol_manager)


    @app_opener(MoversList)
    def openMoversApp(self):
        history_manager = self.getHistoryManager()

        return MoversList(history_manager, QThread())

    
    @app_opener(ComparisonList)
    def openComparisonApp(self):
        
        history_manager = self.getHistoryManager()
        comp_app = ComparisonList(history_manager, QThread())
        if self.telegram_bot is not None:
            comp_app.telegram_signal = self.telegram_signal
            self.telegram_bot.incoming_message_signal.connect(comp_app.processTelegram)
        return comp_app


    @app_opener(ListManager)
    def openListManager(self):
        symbol_manager = self.getNewSymbolManager(identifier='list_symbol_manager')
        history_manager = self.getHistoryManagerIB()
        option_manager = self.getOptionManager()
        return ListManager(symbol_manager, history_manager, option_manager)
        

    def downloadShortRateData(self):
        downloadShortData("data/")


    @pyqtSlot(str, dict)
    def apiUpdate(self, signal, sub_signal):
        if signal == Constants.CONNECTION_STATUS_CHANGED:
            self.updateConnectionStatus(sub_signal['connection_status'])
        elif signal == Constants.MANAGED_ACCOUNT_LIST:
            if not(self.connectivty_ver is None) and sub_signal['owners'] == {self.ver_id}:
                self.connectivty_ver.stop()
                self.connectivty_ver = None
                self.setupAccountSelection(sub_signal['account_list'])


    def setupAccountSelection(self, accounts):
        self._accounts = [account for account in accounts.split(",") if account]
        addAccountsToSelector(self._accounts, self.default_account_selector, self._account_settings['default_account'])


    def defaultAccountChange(self, selected_index):
        self._account_settings['default_account'] = self._accounts[selected_index]
        saveAccountSettings(self._account_settings)


    def setTradingOptions(self, local_address, trading_socket, editable):
        self.local_address = local_address
        self.address_line.setText(local_address)
        self.socket_line.setText(str(trading_socket))
        self.trading_socket = trading_socket
        self.address_line.setEnabled(editable)
        self.socket_line.setEnabled(editable)


    def toggleTelegramBot(self, checked):
        if checked:
            self.setupTelegramBot()
        else:
            print("KILLING TELEGRAM BOT NOT IMPLEMENTED")
    

    def setupTelegramBot(self):
                # Setup the bot logic and thread
        self.telegram_bot = TelegramBot()  # Replace with your actual token
        self.telegram_signal.connect(self.telegram_bot.sendMessage, Qt.ConnectionType.QueuedConnection)
        self.telegram_bot.run() 
        

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
    app.exec()


