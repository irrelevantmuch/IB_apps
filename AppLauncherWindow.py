
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
from uiComps.qtGeneration.AppLauncher_UI import Ui_MainWindow as AppLauncher_UI
from dataHandling.Constants import Constants


class AppLauncherWindow(QMainWindow, AppLauncher_UI):

    def __init__(self):
        QMainWindow.__init__(self)
        AppLauncher_UI.__init__(self)
        
        self.setupUi(self)
        
        self.toggleAppButtons(False)
        self.setupActions()
        

    def toggleAppButtons(self, enabled, interface=Constants.IB_SOURCE):
        if interface == Constants.IB_SOURCE:
            for button in self.ib_group.buttons():
                button.setEnabled(enabled)
            for button in self.general_history_group.buttons():
                button.setEnabled(enabled)
        elif interface == Constants.FINAZON_SOURCE:
            for button in self.ib_group.buttons():
                button.setEnabled(False)
            for button in self.general_history_group.buttons():
                button.setEnabled(enabled)



    def setupActions(self):
            #opening apps
        self.open_movers.clicked.connect(self.openMoversApp)
        self.open_option_pos.clicked.connect(self.openOptionPosApp)
        self.open_option_viz.clicked.connect(self.openOptionVizApp)
        self.open_position_manager.clicked.connect(self.openPositionsApp)
        self.open_poly_downloader.clicked.connect(self.openDataDetailsApp)
        self.open_movers.clicked.connect(self.openMoversApp)
        self.verify_conn_button.clicked.connect(self.verifyConnection)
        # self.open_fitter.clicked.connect(self.openFittingApp)
        # self.open_analysis.clicked.connect(self.openAnalysisApp)
        self.open_man_trader.clicked.connect(self.openManualTraderApp)
        # self.open_auto_trader.clicked.connect(self.openAutoTraderApp)
        self.fetch_rates.clicked.connect(self.downloadShortRateData)
        self.open_list_manager.clicked.connect(self.openListManager)
        self.open_comparisons.clicked.connect(self.openComparisonApp)
        self.open_alert_system.clicked.connect(self.openAlertApp)
        self.default_account_selector.currentIndexChanged.connect(self.defaultAccountChange)
        self.telegram_checkbox.stateChanged.connect(self.toggleTelegramBot)
        self.data_group.buttonClicked.connect(self.dataSelection)
        self.trading_type_group.buttonClicked.connect(self.connectionSelection)
