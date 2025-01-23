
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

from PyQt6 import QtWidgets
from PyQt6.QtCore import QLocale
from PyQt6.QtCore import Qt 
from ibapi.order import Order

class OrderDialog(QtWidgets.QDialog):

    def __init__(self, symbol, price_level, long_order, parent=None):
        super().__init__(parent)

        self.setTitle(symbol, long_order)

        self.setupFields(long_order)


    def getOrder(self):
        count = self.count_field.value()
        limit_price = self.limit_field.text()
        stop_trigger = self.stop_trigger_field.text()
        stop_limit = self.stop_limit_field.text()
        profit_take = self.profit_take_field.text()

        #order_details = OrderDetails(count, limit, stop_trigger, stop_limit, profit_take)

        return BracketOrder(12345678, "BUY", count, limit_price, profit_take, stop_trigger)
        

    def setTitle(self, symbol, long_order):
        order_type = "Long" if long_order else "Short"
        self.setWindowTitle(f"{order_type} Order for: {symbol}")
        

    def setupFields(self,long_order):
        locale = QLocale(QLocale.English, QLocale.UnitedStates)

        self.count_field = QtWidgets.QSpinBox(self)
        self.count_field.setRange(1,10_000)
        self.count_field.setSingleStep(1)
        self.count_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.limit_field = QtWidgets.QDoubleSpinBox(self)
        self.limit_field.setLocale(locale)
        self.limit_field.setRange(0.01,10_000)
        self.limit_field.setSingleStep(0.01)
        self.limit_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.stop_trigger_field = QtWidgets.QDoubleSpinBox(self)
        self.stop_trigger_field.setLocale(locale)
        self.stop_trigger_field.setRange(0.01,10_000)
        self.stop_trigger_field.setSingleStep(0.01)
        self.stop_trigger_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.stop_limit_field = QtWidgets.QDoubleSpinBox(self)
        self.stop_limit_field.setLocale(locale)
        self.stop_limit_field.setRange(0.01,10_000)
        self.stop_limit_field.setSingleStep(0.01)
        self.stop_limit_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.profit_take_field = QtWidgets.QDoubleSpinBox(self)
        self.profit_take_field.setLocale(locale)
        self.profit_take_field.setRange(0.01,10_000)
        self.profit_take_field.setSingleStep(0.01)
        self.profit_take_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self);
        
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout = QtWidgets.QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignBottom)
        order_type = "Buy" if long_order else "Sell"
        layout.addRow(f"{order_type} limit", self.limit_field)
        layout.addRow("Count", self.count_field)
        layout.addRow("Stop Trigger", self.stop_trigger_field)
        layout.addRow("Stop Limit", self.stop_limit_field)
        layout.addRow("Profit Take", self.profit_take_field)

        layout.addWidget(buttonBox)


class StepOrderDialog(QtWidgets.QDialog):

    def __init__(self, symbol, direction_str, parent=None):
        super().__init__(parent)
        if direction_str == "Up":
            order_type = "Sell"
        elif direction_str == "Down":
            order_type = "Buy"

        self.setTitle(symbol, order_type)

        self.setupFields(order_type)


    def getOrder(self):
        count = self.count_field.value()
        entry_trigger_margin = self.entry_trigger_margin_field.text()
        entry_limit_margin = self.entry_limit_margin_field.text()
        stop_trigger_margin = self.stop_trigger_margin_field.text()
        stop_limit_margin = self.stop_limit_margin_field.text()

        return {'count': count, 'entry_trigger_margin': entry_trigger_margin, 'entry_limit_margin': entry_limit_margin, 'stop_trigger_margin': stop_trigger_margin,'stop_limit_margin': stop_limit_margin}
        

    def setTitle(self, symbol, order_type):
        self.setWindowTitle(f"{order_type} Order for: {symbol}")
        

    def setupFields(self, order_type):
        locale = QLocale(QLocale.English, QLocale.UnitedStates)

        self.count_field = QtWidgets.QSpinBox(self)
        self.count_field.setRange(1,10_000)
        self.count_field.setSingleStep(1)
        self.count_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.entry_trigger_margin_field = QtWidgets.QDoubleSpinBox(self)
        self.entry_trigger_margin_field.setLocale(locale)
        self.entry_trigger_margin_field.setRange(0.01,10_000)
        self.entry_trigger_margin_field.setSingleStep(0.01)
        self.entry_trigger_margin_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.entry_limit_margin_field = QtWidgets.QDoubleSpinBox(self)
        self.entry_limit_margin_field.setLocale(locale)
        self.entry_limit_margin_field.setRange(0.01,10_000)
        self.entry_limit_margin_field.setSingleStep(0.01)
        self.entry_limit_margin_field.setValue(0.1)
        self.entry_limit_margin_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.stop_trigger_margin_field = QtWidgets.QDoubleSpinBox(self)
        self.stop_trigger_margin_field.setLocale(locale)
        self.stop_trigger_margin_field.setRange(0.01,10_000)
        self.stop_trigger_margin_field.setSingleStep(0.01)

        self.stop_trigger_margin_field.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.stop_limit_margin_field = QtWidgets.QDoubleSpinBox(self)
        self.stop_limit_margin_field.setLocale(locale)
        self.stop_limit_margin_field.setRange(0.01,10_000)
        self.stop_limit_margin_field.setValue(0.1)
        self.stop_limit_margin_field.setSingleStep(0.01)
        self.stop_limit_margin_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self);
        buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("Submit")
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout = QtWidgets.QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignBottom)
        
        layout.addRow("Count", self.count_field)
        layout.addRow("Entry Trigger Margin", self.entry_trigger_margin_field)
        layout.addRow("Entry Limit Margin", self.entry_limit_margin_field)
        layout.addRow("Stop Trigger Margin", self.stop_trigger_margin_field)
        layout.addRow("Stop Limit Margin", self.stop_limit_margin_field)

        layout.addWidget(buttonBox)



class OrderDetails:

    def __init__(self, count, limit, stop_trigger, stop_limit, profit_take):

         self.count = count
         self.limit = limit
         self.stop_trigger = stop_trigger
         self.stop_limit = stop_limit
         self.profit_take = profit_take


def BracketOrder(parentOrderId, action, quantity, limitPrice, takeProfitLimitPrice, stopLossPrice):

    #This will be our main or "parent" order
    parent = Order()
    parent.orderId = parentOrderId
    parent.action = action
    parent.orderType = "LMT"
    parent.totalQuantity = quantity
    parent.lmtPrice = limitPrice
    parent.eTradeOnly = ''
    parent.firmQuoteOnly = ''
    #The parent and children orders will need this attribute set to False to prevent accidental executions.
    #The LAST CHILD will have it set to True, 
    parent.transmit = False

    takeProfit = Order()
    takeProfit.orderId = parent.orderId + 1
    takeProfit.action = "SELL" if action == "BUY" else "BUY"
    takeProfit.orderType = "LMT"
    takeProfit.totalQuantity = quantity
    takeProfit.lmtPrice = takeProfitLimitPrice
    takeProfit.parentId = parentOrderId
    takeProfit.eTradeOnly = ''
    takeProfit.firmQuoteOnly = ''
    
    takeProfit.transmit = False

    stopLoss = Order()
    stopLoss.orderId = parent.orderId + 2
    stopLoss.action = "SELL" if action == "BUY" else "BUY"
    stopLoss.orderType = "STP"
    stopLoss.auxPrice = stopLossPrice
    stopLoss.totalQuantity = quantity
    stopLoss.parentId = parentOrderId
    #In this case, the low side order will be the last child being sent. Therefore, it needs to set this attribute to True 
    #to activate all its predecessors
    stopLoss.eTradeOnly = ''
    stopLoss.firmQuoteOnly = ''
    
    stopLoss.transmit = True

    bracketOrder = [parent, takeProfit, stopLoss]
    return bracketOrder



