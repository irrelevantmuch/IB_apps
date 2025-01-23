
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

from PyQt6.QtCore import pyqtSignal
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QTableWidgetItem, QWidget
from uiComps.qtGeneration.OptionsTab_UI import Ui_Form as OptionsTab
from uiComps.qtGeneration.SpecOptionsTab_UI import Ui_Form as SpecOptionsTab
from dataHandling.Constants import Constants
from dataHandling.TradeManagement.PositionDataManagement import PositionDataModel
from datetime import datetime

from generalFunctionality.UIFunctions import getNumericItem, AlignDelegate, PriceAlignDelegate


class OptionTabWidget(QWidget):

    individual = False
    tab_name = ""

    def __init__(self, data_object, selection_type, parameter='general'):
        super().__init__()
        
        self.setupUi()
        self.setModelData(data_object, selection_type, parameter)


    def setupUi(self):
        new_form = OptionsTab() 
        new_form.setupUi(self)
        self.options_table = new_form.options_table
        self.options_table.setSortingEnabled(True)


    def setModelData(self, data_object, selection_type, parameter='general'):
        self.data_model = PositionDataModel(data_object, selection_type, parameter)
        self.options_table.setModel(self.data_model)

    

class SpecOptionTabWidget(OptionTabWidget):

    previous_price = 0.0
    total_value = 0.0
    text_updater = pyqtSignal(str)
    days_to_expiration = float("inf")

    def setupUi(self):
        new_form = SpecOptionsTab() 
        new_form.setupUi(self)
        self.getFormReferences(new_form)   
        self.individual = True     
        self.notes_window.textChanged.connect(self.textChanged)

    def textChanged(self):
        self.text_updater.emit(self.tab_name)

    def getNotesText(self):
        return self.notes_window.toPlainText()

    def getFormReferences(self, new_form):
        self.options_table = new_form.options_table
        self.days_till_label = new_form.days_till_label
        self.total_value_label = new_form.total_value_label
        self.unrealized_pnl_label = new_form.unrealized_pnl_label
        self.underlying_price_label = new_form.underlying_price_label
        self.notes_window = new_form.notes_window

    # def setData(self, positions):
    #     super().setData(positions)

    #     unrealized_pnl = 0.0
        
    #     for _, position in positions.iterrows():
    #         unrealized_pnl += position['UNREALIZED_PNL']
    #         mkt_value = position['PRICE'] * float(position['CONTRACT'].multiplier) * float(position['COUNT'])
    #         self.total_value += mkt_value            

    #         datetime_obj = datetime.strptime(position['CONTRACT'].lastTradeDateOrContractMonth, '%Y%m%d')
    #         today = datetime.today()
    #         days_delta = (datetime_obj - today).days
    #         if days_delta < self.days_to_expiration:
    #             self.days_to_expiration = days_delta
        
    #     self.days_till_label.setText(str(self.days_to_expiration))
    #     self.total_value_label.setText("{:.2f}".format(self.total_value))
    #     self.setPNLPosition(unrealized_pnl)

        

    def setPrice(self, price):
        if self.previous_price != 0.0:
            if self.previous_price > price:
                self.underlying_price_label.setText('<font color="red">' + str(price) + '</font>')
            else:
                self.underlying_price_label.setText('<font color="green">' + str(price) + '</font>')
        else:
            self.underlying_price_label.setText(str(price))
        self.previous_price = price


    def setPNLPosition(self, unrealized_pnl):
        if unrealized_pnl > 0:
            self.unrealized_pnl_label.setText('<font color="green">' + "{:.2f}".format(unrealized_pnl) + '</font>')
        else:
            self.unrealized_pnl_label.setText('<font color="red">' + "{:.2f}".format(unrealized_pnl) + '</font>')
        

