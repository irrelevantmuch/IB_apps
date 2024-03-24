from PyQt5.QtCore import QThread, pyqtSlot, Qt, pyqtSignal
from PyQt5 import QtWidgets
from dataHandling.Constants import Constants
from AppLauncherWindow import AppLauncherWindow

import sys, os, time
from uiComps.Logging import Logger
import yappi
import asyncio

from dataHandling.ibFTPdata import downloadShortData

from apps.listManaging.listManager import ListManager
from apps.polygonDownload.dataDownloader import DataDownloader
from apps.optionPositions.optionsPositionListing import OptionPositions
from apps.optionVisualization.optionsVisualization import OptionVisualization
from apps.comparisons.comparisonLists import ComparisonList
from apps.alerting.alertManager import AlertManager
from apps.tradeMaker.tradeMaker import TradeMaker
from apps.tradeRunner.tradeRunner import TradeRunner
from apps.dataAnalysis.dataAnalysis import DataAnalysis
from apps.treeFitter.treeFitter import TreeFitter
from apps.bayesianFitter.bayesianFitter import BayesianFitter
from apps.movers.moversLists import MoversList
from apps.positionManaging.positionManager import PositionManager
from IBConnector import IBConnector

QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class AppLauncher(AppLauncherWindow, IBConnector):

    running_apps = []
    data_source = "IBKR"

    def __init__(self):
        super().__init__()
        self.loggin_instance = Logger.instance()
        self.loggin_instance.setLogWindow(self.log_window)
        self.real_tws_button.setChecked(True)
        self.connectionSelection()
        self.updateConnectionStatus('closed')

        print(f"AppLauncher init {int(QThread.currentThreadId())}")
        

    def updateConnectionStatus(self, status):
        if status == Constants.CONNECTION_OPEN:
            self.statusbar.showMessage("Connection Open")
            self.toggleAppButtons(True, interface=self.data_source)
            return

        self.statusbar.showMessage("Offline")


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
            self.data_source = "IBKR"
        elif self.finazon_data_radio.isChecked():
            self.data_source = "Finazon"
            

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
        new_app = OptionPositions(self.data_management.ib_interface)
        self.running_apps.append(new_app)
        new_app.show()
    

    def openOptionVizApp(self):
        if not self.appRunning(OptionVisualization):
            option_manager = self.getNewOptionManager()
            symbol_manager = self.getNewSymbolManager(identifier='option_symbol_manager')
            new_app = OptionVisualization(option_manager, symbol_manager)
            self.running_apps.append(new_app)
            new_app.show()


    def openStocksApp(self):
        data_manager = self.getNewPositionManager()
        new_app = PositionManager(data_manager)
        self.running_apps.append(new_app)
        new_app.show()
    

    def openAlertApp(self):
        history_manager, indicator_processor = self.getHistoryWithIndicator()
        alert_app = AlertManager(history_manager, indicator_processor)
        self.running_apps.append(alert_app)
        alert_app.show()


    def openAnalysisApp(self):
        history_manager = self.getHistoryManager()
        new_app = DataAnalysis(history_manager)
        self.running_apps.append(new_app)
        new_app.show()


    def openDataDetailsApp(self):
        new_app = DataDownloader()
        self.running_apps.append(new_app)
        new_app.show()


    def openManualTraderApp(self):
        order_manager = self.getOrderManager()
        history_manager = self.getHistoryManagerIB(identifier='manual_trader_history')
        symbol_manager = self.getNewSymbolManager(identifier='trader_symbol_manager')
        new_app = TradeMaker(order_manager, history_manager, symbol_manager)
        self.running_apps.append(new_app)
        new_app.show()


    def openAutoTraderApp(self):
        order_manager = self.getOrderManager()
        history_manager = self.getHistoryManager()
        new_app = TradeRunner(order_manager, history_manager)
        self.running_apps.append(new_app)
        new_app.show()


    def openMoversApp(self):
        if not self.appRunning(MoversList):
            history_manager = self.getHistoryManager()

            new_app = MoversList(history_manager)
            self.running_apps.append(new_app)
            new_app.close_signal.connect(self.closedMoversApp)
            new_app.show()


    def closedMoversApp(self):
        for app in self.running_apps:
            if isinstance(app, MoversList):
                self.running_apps.remove(app)
                break

    def openFittingApp(self):
        new_app = TreeFitter()
        self.running_apps.append(new_app)
        new_app.show()


    def openComparisonApp(self):
        history_manager = self.getHistoryManager()
        new_app = ComparisonList(history_manager)
        self.running_apps.append(new_app)
        new_app.show()


    def openListManager(self):
        symbol_manager = self.getNewSymbolManager(identifier='list_symbol_manager')
        history_manager = self.getHistoryManager()
        option_manager = self.getNewOptionManager()
        new_app = ListManager(symbol_manager, history_manager, option_manager)
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


if __name__ == "__main__":

        # Set the environment variables
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("macos")
    app.aboutToQuit.connect(app.deleteLater)
    window = AppLauncher()
    window.show()
    app.exec_()



