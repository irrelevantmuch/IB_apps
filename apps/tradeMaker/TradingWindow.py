
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
# Created by: PyQt6 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6.QtCore import QObject, QEvent
from uiComps.generalUIFunctionality import MyAppWindow
from uiComps.qtGeneration.TradingWindow_UI import Ui_MainWindow as TradingWindow_UI
from dataHandling.Constants import Constants
from generalFunctionality.SymbolFinderImpl import SymbolFinderImplementation
from generalFunctionality.UIFunctions import addAccountsToSelector
from uiComps.customWidgets.PlotWidgets.CandlePlotWidget import CandlePlotWidget

 
class MousePressEventFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            # Explicitly call selectAll if the event is a mouse press
            obj.selectAll()
        return super().eventFilter(obj, event)



class TradingWindow(MyAppWindow, TradingWindow_UI, SymbolFinderImplementation): #, SymbolFinderImplementation

    current_selection = None
    bar_types = [Constants.ONE_MIN_BAR, Constants.TWO_MIN_BAR, Constants.THREE_MIN_BAR, Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR, Constants.HOUR_BAR]
    selected_bar_type = Constants.FIFTEEN_MIN_BAR
    

    def __init__(self):
        MyAppWindow.__init__(self)
        TradingWindow_UI.__init__(self)
        SymbolFinderImplementation.__init__(self)

        self.setupUi(self)
        self.connectSearchField()
        
        self.populateBarSelector()
        
        self.trade_plot = CandlePlotWidget(self.setLevelsFromChart)
        self.vertical_stack.insertWidget(4, self.trade_plot)
        self.connectActions()

        focus_filter = MousePressEventFilter()
        self.search_field.installEventFilter(focus_filter)


    def populateBarSelector(self):
        self.bar_selector.addItems(self.bar_types)
        self.bar_selector.setCurrentIndex(self.bar_types.index(self.selected_bar_type))



    def setBaseGuiValues(self, accounts, default_account, selected_input_button):
        self.count_field.setValue(10)
        self.step_count_field.setValue(10)
        
        addAccountsToSelector(accounts, self.account_selector, default_account)
        self.forceEmitToggleRadio(selected_input_button, self.input_selection_group)
        self.forceEmitToggleRadio(self.buy_radio, self.buy_sell_group)
        self.forceEmitToggleRadio(self.step_buy_radio, self.step_buy_sell_group)
        self.forceEmitToggleRadio(self.step_profit_factor_radio, self.step_profit_selection_group)
        self.forceEmitStateCheck(self.step_profit_check, False)
        self.forceEmitStateCheck(self.step_stoploss_check, False)
        self.forceEmitStateCheck(self.profit_take_check, False)
        self.forceEmitStateCheck(self.market_order_box, False)
        self.forceEmitStateCheck(self.stop_loss_check, False)
        self.forceEmitStateCheck(self.stop_limit_check, False)

        self.step_profit_factor_spin.setValue(2)
        self.step_profit_offset_spin.setValue(1.0)
        self.step_profit_price_spin.setValue(100.0)
        

        self.barSelection(Constants.FIFTEEN_MIN_BAR)
        self.stepProfitTakeCheck(False)
        

    def forceEmitToggleRadio(self, radio_button, radio_group):
        if radio_button.isChecked():
            radio_group.buttonToggled.emit(radio_button, True)
        else:
            radio_button.setChecked(True)


    def forceEmitStateCheck(self, check_button, new_value):
        if check_button.isChecked() == new_value:
            check_button.stateChanged.emit(new_value)
        else:
            check_button.setChecked(new_value)
        

    def setLevels(self, type, level):
        pass


    def connectActions(self):
        self.bar_selector.currentTextChanged.connect(self.barSelection)

        self.buy_sell_group.buttonToggled.connect(self.buySellSelection)
        self.combo_buy_sell_group.buttonToggled.connect(self.comboBuySellSelection)
        self.step_buy_sell_group.buttonToggled.connect(self.stepBuySellSelection)
        self.step_profit_selection_group.buttonToggled.connect(self.stepProfitSelection)

        self.market_order_box.toggled.connect(self.makeMarket)

        self.submit_button.clicked.connect(self.placeComboOrder)
        self.oco_button.clicked.connect(self.placeOcoOrder)
        self.step_button.clicked.connect(self.placeStepOrder)

        self.list_selector.currentIndexChanged.connect(self.listSelection)
        self.ticker_selection.currentIndexChanged.connect(self.tickerSelection)
    
        self.step_entry_trigger_offset_box.valueChanged.connect(lambda new_value: self.stepLevelChange(new_value, "entry_trigger_offset"))
        self.step_entry_limit_offset_box.valueChanged.connect(lambda new_value: self.stepLevelChange(new_value, "entry_limit_offset"))
        self.step_count_field.valueChanged.connect(lambda new_value: self.stepLevelChange(new_value, "count"))
        self.step_stop_trigger_offset_box.valueChanged.connect(lambda new_value: self.stepLevelChange(new_value, "stop_trigger_offset"))
        self.step_stop_limit_offset_box.valueChanged.connect(lambda new_value: self.stepLevelChange(new_value, "stop_limit_offset"))
        self.step_profit_factor_spin.valueChanged.connect(lambda new_value: self.stepLevelChange(new_value, "profit_factor_level"))
        self.step_profit_offset_spin.valueChanged.connect(lambda new_value: self.stepLevelChange(new_value, "profit_offset_level"))
        self.step_profit_price_spin.valueChanged.connect(lambda new_value: self.stepLevelChange(new_value, "profit_price_level"))
        self.step_profit_check.stateChanged.connect(self.stepProfitTakeCheck)
        self.step_stoploss_check.stateChanged.connect(self.stepStoplossCheck)
        self.account_selector.currentIndexChanged.connect(self.accountChange)

        self.input_selection_group.buttonClicked.connect(self.listSelectionChange)
        self.stop_limit_check.stateChanged.connect(self.stopLimitCheck)
        self.stop_loss_check.stateChanged.connect(self.stoplossCheck)
        self.profit_take_check.stateChanged.connect(self.profitTakeCheck)

        self.cancel_all_button.clicked.connect(self.cancelAllTrades)
    

        self.ask_price_button.clicked.connect(lambda: self.fillOutPriceFields(self.ask_price_button))
        self.last_price_button.clicked.connect(lambda: self.fillOutPriceFields(self.last_price_button))
        self.bid_price_button.clicked.connect(lambda: self.fillOutPriceFields(self.bid_price_button))
    
    
