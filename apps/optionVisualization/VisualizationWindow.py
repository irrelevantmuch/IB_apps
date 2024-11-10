
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

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'optionsGraph.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5.QtCore import pyqtSlot, pyqtSignal
from dataHandling.Constants import Constants, OptionConstrType
from uiComps.qtGeneration.Visualization_UI import Ui_MainWindow as Visualization_UI
from datetime import datetime
from pytz import timezone

from uiComps.generalUIFunctionality import MyAppWindow
from generalFunctionality.SymbolFinderImpl import SymbolFinderImplementation
from generalFunctionality.GenFunctions import getExpirationString, getDaysTillExpiration


from uiComps.customWidgets.PlotWidgets.OptionPlotWidget import PremiumPlotWidget, OptionPlotWidget
from uiComps.customWidgets.PlotWidgets.OptionAllPlotWidget import OptionAllPlotWidget


class VisualizationWindow(MyAppWindow, Visualization_UI, SymbolFinderImplementation):


    constr_types = [OptionConstrType.single, OptionConstrType.vertical_spread, OptionConstrType.butterfly, OptionConstrType.split_butterfly, OptionConstrType.iron_condor, OptionConstrType.topped_ratio_spread]

    min_exp = None
    max_exp = None
    min_strike = None
    max_strike = None

    min_all_strike = pyqtSignal(float)
    max_all_strike = pyqtSignal(float)
    min_all_expiration = pyqtSignal(int)
    max_all_expiration = pyqtSignal(int)
        

    def __init__(self):
        super().__init__()
        MyAppWindow.__init__(self)
        Visualization_UI.__init__(self)
        SymbolFinderImplementation.__init__(self)

        self.setupUi(self)

        self.connectSearchField()
        self.connectActions()
        self.populateBoxes()
        self.setupGraphs()
        self.disableInterface() 
        self.fetch_all_button.setEnabled(False)

        
    def populateBoxes(self):
        for item in self.constr_types:
            self.structure_type.addItem(item.value)


    def connectActions(self):
        self.expiration_box.currentIndexChanged.connect(self.expirationSelectionChange)
        self.strike_box.currentIndexChanged.connect(self.strikeSelectionChange)
        self.structure_type.currentTextChanged.connect(self.structureSelectionChanged)
        self.call_put_group.buttonClicked.connect(self.callPutAction)
        self.buy_sell_group.buttonClicked.connect(self.buySellAction)
        self.upper_offset_box.currentTextChanged.connect(self.constructionPropsChange)
        self.premium_price_strike_group.buttonClicked.connect(self.radioStrikeSelection)
        self.premium_price_all_group.buttonClicked.connect(self.radioAllSelection)
        self.fetch_all_button.clicked.connect(self.fetchAllStrikes)
        self.base_ratio_box.valueChanged.connect(self.constructionPropsChange)
        self.upper_ratio_box.valueChanged.connect(self.constructionPropsChange)
        self.lower_ratio_box.valueChanged.connect(self.constructionPropsChange)
        
        self.min_strike_plt_box.currentIndexChanged.connect(self.minStrikePlotChange)
        self.max_strike_plt_box.currentIndexChanged.connect(self.maxStrikePlotChange)
        self.min_exp_plt_box.currentIndexChanged.connect(self.minExpPlotChange)
        self.max_exp_plt_box.currentIndexChanged.connect(self.maxExpPlotChange)


    def setupGraphs(self):     

        self.strike_plot = PremiumPlotWidget(self, labels=['Premium', 'Change'])
        self.strike_plot_layout.addWidget(self.strike_plot)

        self.expiration_plot = OptionPlotWidget(self, inverted=True)
        self.exp_plot_layout.addWidget(self.expiration_plot)

        self.exp_grouped_plot = OptionAllPlotWidget(self, 'expiration_grouped', 'Strike Price ($)', legend_alignment='right')
        self.exp_grouped_plot_layout.addWidget(self.exp_grouped_plot)
 
        
        self.strike_grouped_plot = OptionAllPlotWidget(self, 'strike_grouped', 'Days Till Expiriation', legend_alignment='left')
        self.strike_grouped_plot_layout.addWidget(self.strike_grouped_plot)


        self.price_est_plot = OptionAllPlotWidget(self, 'price_est', 'Price Movement ($)', legend_alignment='right')
        self.pl_layout.addWidget(self.price_est_plot)

        

    
    def updatePlotPrice(self, price):
        pass
        #self.strike_plot.updatePrice(price)


    def disableInterface(self):
        self.toggleInterface(False)


    def enableInterface(self):
        self.toggleInterface(True)


    def toggleInterface(self, enabled):
        self.resetInputBoxes(self.constr_type)
        self.expiration_box.setEnabled(enabled)
        self.strike_box.setEnabled(enabled)


    def updateOptionGUI(self, expirations, strikes):
        self.applySignalBlock(True)
        self.clearOptionGUI()
        self.populateExpirationBoxes(expirations)
        self.populateStrikeBoxes(strikes)
        self.enableInterface()
        self.applySignalBlock(False)


    def applySignalBlock(self, value):
        self.expiration_box.blockSignals(value)
        self.strike_box.blockSignals(value)
        

        self.min_exp_plt_box.blockSignals(value)
        self.max_exp_plt_box.blockSignals(value)
        self.min_strike_plt_box.blockSignals(value)
        self.max_strike_plt_box.blockSignals(value)
        

    def setGUIValues(self, boundaries):
        min_exp, max_exp, min_strike, max_strike = boundaries
        
        self.min_exp = min_exp
        self.max_exp = max_exp
        self.min_strike = min_strike
        self.max_strike = max_strike



    def clearOptionGUI(self):
        self.expiration_box.clear()
        self.strike_box.clear()

        self.min_exp_box.clear()
        self.max_exp_box.clear()        
        self.min_strike_box.clear()
        self.max_strike_box.clear()

        self.min_strike_plt_box.clear()
        self.max_strike_plt_box.clear()
        self.min_exp_plt_box.clear()
        self.max_exp_plt_box.clear()


    def minStrikePlotChange(self, value):
        self.min_all_strike.emit(self.strike_pairs[value][0])


    def maxStrikePlotChange(self, value):
        self.max_all_strike.emit(self.strike_pairs[value][0])


    def minExpPlotChange(self, value):
        self.min_all_expiration.emit(self.expiration_pairs[value][0])


    def maxExpPlotChange(self, value):
        self.max_all_expiration.emit(self.expiration_pairs[value][0])


    def populateStrikeBoxes(self, strikes):
        strike_strings = list(map(str, strikes))
        self.strike_pairs = list(sorted(zip(strikes, strike_strings)))
        sorted_strike_strings = [item[1] for item in self.strike_pairs]
        sorted_strikes = [item[0] for item in self.strike_pairs]

        self.strike_box.addItems(sorted_strike_strings)

        self.min_strike_box.addItems(sorted_strike_strings)
        self.max_strike_box.addItems(sorted_strike_strings)

        if self.max_strike is not None:
            max_strike_index = sorted_strikes.index(self.max_strike)
            self.max_strike_box.setCurrentText(sorted_strike_strings[max_strike_index])
        else:
            self.max_strike_box.setCurrentIndex(len(sorted_strike_strings)-1)

        if self.min_strike is not None:
            min_strike_index = sorted_strikes.index(self.min_strike)
            self.min_strike_box.setCurrentText(sorted_strike_strings[min_strike_index])

        self.min_strike_plt_box.addItems(sorted_strike_strings)
        self.max_strike_plt_box.addItems(sorted_strike_strings)
        self.max_strike_plt_box.setCurrentIndex(len(sorted_strike_strings)-1)


    def populateExpirationBoxes(self, expirations):
        days_till_exp = [getDaysTillExpiration(exp) for exp in expirations]
        expiration_pp_str = [getExpirationString(exp) for exp in expirations]
        
        self.expiration_pairs = list(sorted(zip(days_till_exp, expiration_pp_str, expirations)))
        sorted_expiration_strings = [item[1] for item in self.expiration_pairs]
        sorted_expirations = [item[0] for item in self.expiration_pairs]

        
        self.expiration_box.addItems(sorted_expiration_strings)

        self.min_exp_box.addItems(sorted_expiration_strings)
        self.max_exp_box.addItems(sorted_expiration_strings)
        self.max_exp_box.setCurrentIndex(len(sorted_expiration_strings)-1)

        if self.max_exp is not None:
            max_exp_index = sorted_expirations.index(self.max_exp)
            self.max_exp_box.setCurrentText(sorted_expiration_strings[max_exp_index])
        else:
            self.max_exp_box.setCurrentIndex(len(sorted_expiration_strings)-1)

        if self.min_exp is not None:
            min_exp_index = sorted_expirations.index(self.min_exp)
            self.min_exp_box.setCurrentText(sorted_expiration_strings[min_exp_index])


        self.min_exp_plt_box.addItems(sorted_expiration_strings)
        self.max_exp_plt_box.addItems(sorted_expiration_strings)
        self.max_exp_plt_box.setCurrentIndex(len(sorted_expiration_strings)-1)

