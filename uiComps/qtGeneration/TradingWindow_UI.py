# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'UIComps/QTGeneration/TradingWindow.ui'
#
# Created by: PyQt5 UI code generator 5.15.7
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 649)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(800, 600))
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setMinimumSize(QtCore.QSize(800, 600))
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.vertical_stack = QtWidgets.QVBoxLayout()
        self.vertical_stack.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.vertical_stack.setContentsMargins(20, 20, 20, 10)
        self.vertical_stack.setSpacing(10)
        self.vertical_stack.setObjectName("vertical_stack")
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.label_17 = QtWidgets.QLabel(self.centralwidget)
        self.label_17.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_17.setObjectName("label_17")
        self.horizontalLayout_8.addWidget(self.label_17)
        self.account_selector = QtWidgets.QComboBox(self.centralwidget)
        self.account_selector.setObjectName("account_selector")
        self.horizontalLayout_8.addWidget(self.account_selector)
        self.vertical_stack.addLayout(self.horizontalLayout_8)
        self.symbol_layout = QtWidgets.QHBoxLayout()
        self.symbol_layout.setObjectName("symbol_layout")
        self.symbol_radio = QtWidgets.QRadioButton(self.centralwidget)
        self.symbol_radio.setChecked(True)
        self.symbol_radio.setObjectName("symbol_radio")
        self.input_selection_group = QtWidgets.QButtonGroup(MainWindow)
        self.input_selection_group.setObjectName("input_selection_group")
        self.input_selection_group.addButton(self.symbol_radio)
        self.symbol_layout.addWidget(self.symbol_radio)
        self.search_field = QuickLineEdit(self.centralwidget)
        self.search_field.setObjectName("search_field")
        self.symbol_layout.addWidget(self.search_field)
        self.vertical_stack.addLayout(self.symbol_layout)
        self.list_layout = QtWidgets.QHBoxLayout()
        self.list_layout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.list_layout.setObjectName("list_layout")
        self.list_radio = QtWidgets.QRadioButton(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.list_radio.sizePolicy().hasHeightForWidth())
        self.list_radio.setSizePolicy(sizePolicy)
        self.list_radio.setChecked(False)
        self.list_radio.setObjectName("list_radio")
        self.input_selection_group.addButton(self.list_radio)
        self.list_layout.addWidget(self.list_radio)
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_4.setObjectName("label_4")
        self.list_layout.addWidget(self.label_4)
        self.list_selector = QtWidgets.QComboBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.list_selector.sizePolicy().hasHeightForWidth())
        self.list_selector.setSizePolicy(sizePolicy)
        self.list_selector.setObjectName("list_selector")
        self.list_layout.addWidget(self.list_selector)
        self.label = QtWidgets.QLabel(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")
        self.list_layout.addWidget(self.label)
        self.ticker_selection = QtWidgets.QComboBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ticker_selection.sizePolicy().hasHeightForWidth())
        self.ticker_selection.setSizePolicy(sizePolicy)
        self.ticker_selection.setObjectName("ticker_selection")
        self.list_layout.addWidget(self.ticker_selection)
        self.vertical_stack.addLayout(self.list_layout)
        self.tab_widget = QtWidgets.QTabWidget(self.centralwidget)
        self.tab_widget.setObjectName("tab_widget")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.tab_2)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.buy_radio = QtWidgets.QRadioButton(self.tab_2)
        self.buy_radio.setChecked(True)
        self.buy_radio.setObjectName("buy_radio")
        self.buy_sell_group = QtWidgets.QButtonGroup(MainWindow)
        self.buy_sell_group.setObjectName("buy_sell_group")
        self.buy_sell_group.addButton(self.buy_radio)
        self.horizontalLayout_6.addWidget(self.buy_radio)
        self.sell_radio = QtWidgets.QRadioButton(self.tab_2)
        self.sell_radio.setChecked(False)
        self.sell_radio.setObjectName("sell_radio")
        self.buy_sell_group.addButton(self.sell_radio)
        self.horizontalLayout_6.addWidget(self.sell_radio)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem)
        self.label_12 = QtWidgets.QLabel(self.tab_2)
        self.label_12.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_12.setObjectName("label_12")
        self.horizontalLayout_6.addWidget(self.label_12)
        self.bid_price_button = QtWidgets.QPushButton(self.tab_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bid_price_button.sizePolicy().hasHeightForWidth())
        self.bid_price_button.setSizePolicy(sizePolicy)
        self.bid_price_button.setMinimumSize(QtCore.QSize(80, 0))
        self.bid_price_button.setMaximumSize(QtCore.QSize(80, 16777215))
        self.bid_price_button.setBaseSize(QtCore.QSize(80, 0))
        self.bid_price_button.setObjectName("bid_price_button")
        self.horizontalLayout_6.addWidget(self.bid_price_button)
        self.label_13 = QtWidgets.QLabel(self.tab_2)
        self.label_13.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_13.setObjectName("label_13")
        self.horizontalLayout_6.addWidget(self.label_13)
        self.last_price_button = QtWidgets.QPushButton(self.tab_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.last_price_button.sizePolicy().hasHeightForWidth())
        self.last_price_button.setSizePolicy(sizePolicy)
        self.last_price_button.setMinimumSize(QtCore.QSize(80, 0))
        self.last_price_button.setMaximumSize(QtCore.QSize(80, 16777215))
        self.last_price_button.setBaseSize(QtCore.QSize(80, 0))
        self.last_price_button.setObjectName("last_price_button")
        self.horizontalLayout_6.addWidget(self.last_price_button)
        self.label_14 = QtWidgets.QLabel(self.tab_2)
        self.label_14.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_14.setObjectName("label_14")
        self.horizontalLayout_6.addWidget(self.label_14)
        self.ask_price_button = QtWidgets.QPushButton(self.tab_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ask_price_button.sizePolicy().hasHeightForWidth())
        self.ask_price_button.setSizePolicy(sizePolicy)
        self.ask_price_button.setMinimumSize(QtCore.QSize(80, 0))
        self.ask_price_button.setMaximumSize(QtCore.QSize(80, 16777215))
        self.ask_price_button.setBaseSize(QtCore.QSize(80, 0))
        self.ask_price_button.setObjectName("ask_price_button")
        self.horizontalLayout_6.addWidget(self.ask_price_button)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem1)
        self.gridLayout_4.addLayout(self.horizontalLayout_6, 0, 0, 1, 1)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_15 = QtWidgets.QLabel(self.tab_2)
        self.label_15.setObjectName("label_15")
        self.horizontalLayout_7.addWidget(self.label_15)
        self.count_field = QtWidgets.QSpinBox(self.tab_2)
        self.count_field.setMinimum(1)
        self.count_field.setMaximum(9999999)
        self.count_field.setProperty("value", 1)
        self.count_field.setObjectName("count_field")
        self.horizontalLayout_7.addWidget(self.count_field)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem2)
        self.market_order_box = QtWidgets.QCheckBox(self.tab_2)
        self.market_order_box.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.market_order_box.setObjectName("market_order_box")
        self.horizontalLayout_7.addWidget(self.market_order_box)
        self.label_16 = QtWidgets.QLabel(self.tab_2)
        self.label_16.setObjectName("label_16")
        self.horizontalLayout_7.addWidget(self.label_16)
        self.limit_field = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.limit_field.setMaximum(99999.0)
        self.limit_field.setSingleStep(1.0)
        self.limit_field.setProperty("value", 0.0)
        self.limit_field.setObjectName("limit_field")
        self.horizontalLayout_7.addWidget(self.limit_field)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem3)
        self.submit_button = QtWidgets.QPushButton(self.tab_2)
        self.submit_button.setStyleSheet("")
        self.submit_button.setObjectName("submit_button")
        self.horizontalLayout_7.addWidget(self.submit_button)
        self.gridLayout_4.addLayout(self.horizontalLayout_7, 1, 0, 1, 1)
        self.bottom_layout_2 = QtWidgets.QHBoxLayout()
        self.bottom_layout_2.setObjectName("bottom_layout_2")
        self.stop_loss_check = QtWidgets.QCheckBox(self.tab_2)
        self.stop_loss_check.setChecked(False)
        self.stop_loss_check.setObjectName("stop_loss_check")
        self.bottom_layout_2.addWidget(self.stop_loss_check)
        self.stop_trigger_field = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.stop_trigger_field.setMaximum(99999.0)
        self.stop_trigger_field.setSingleStep(1.0)
        self.stop_trigger_field.setObjectName("stop_trigger_field")
        self.bottom_layout_2.addWidget(self.stop_trigger_field)
        self.stop_limit_check = QtWidgets.QCheckBox(self.tab_2)
        self.stop_limit_check.setChecked(False)
        self.stop_limit_check.setObjectName("stop_limit_check")
        self.bottom_layout_2.addWidget(self.stop_limit_check)
        self.stop_limit_field = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.stop_limit_field.setMaximum(99999.0)
        self.stop_limit_field.setSingleStep(1.0)
        self.stop_limit_field.setObjectName("stop_limit_field")
        self.bottom_layout_2.addWidget(self.stop_limit_field)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.bottom_layout_2.addItem(spacerItem4)
        self.profit_take_check = QtWidgets.QCheckBox(self.tab_2)
        self.profit_take_check.setChecked(False)
        self.profit_take_check.setObjectName("profit_take_check")
        self.bottom_layout_2.addWidget(self.profit_take_check)
        self.profit_limit_field = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.profit_limit_field.setMaximum(99999.0)
        self.profit_limit_field.setSingleStep(1.0)
        self.profit_limit_field.setObjectName("profit_limit_field")
        self.bottom_layout_2.addWidget(self.profit_limit_field)
        self.gridLayout_4.addLayout(self.bottom_layout_2, 2, 0, 1, 1)
        self.tab_widget.addTab(self.tab_2, "")
        self.tab_3 = QtWidgets.QWidget()
        self.tab_3.setObjectName("tab_3")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.tab_3)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.combo_buy_radio = QtWidgets.QRadioButton(self.tab_3)
        self.combo_buy_radio.setChecked(True)
        self.combo_buy_radio.setObjectName("combo_buy_radio")
        self.combo_buy_sell_group = QtWidgets.QButtonGroup(MainWindow)
        self.combo_buy_sell_group.setObjectName("combo_buy_sell_group")
        self.combo_buy_sell_group.addButton(self.combo_buy_radio)
        self.horizontalLayout_5.addWidget(self.combo_buy_radio)
        self.combo_sell_radio = QtWidgets.QRadioButton(self.tab_3)
        self.combo_sell_radio.setChecked(False)
        self.combo_sell_radio.setObjectName("combo_sell_radio")
        self.combo_buy_sell_group.addButton(self.combo_sell_radio)
        self.horizontalLayout_5.addWidget(self.combo_sell_radio)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem5)
        self.gridLayout_3.addLayout(self.horizontalLayout_5, 0, 0, 1, 1)
        self.bottom_layout = QtWidgets.QHBoxLayout()
        self.bottom_layout.setObjectName("bottom_layout")
        self.label_10 = QtWidgets.QLabel(self.tab_3)
        self.label_10.setObjectName("label_10")
        self.bottom_layout.addWidget(self.label_10)
        self.combo_limit_field = QtWidgets.QDoubleSpinBox(self.tab_3)
        self.combo_limit_field.setMaximum(99999.0)
        self.combo_limit_field.setSingleStep(0.01)
        self.combo_limit_field.setObjectName("combo_limit_field")
        self.bottom_layout.addWidget(self.combo_limit_field)
        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.bottom_layout.addItem(spacerItem6)
        self.label_9 = QtWidgets.QLabel(self.tab_3)
        self.label_9.setObjectName("label_9")
        self.bottom_layout.addWidget(self.label_9)
        self.combo_sl_trigger_field = QtWidgets.QDoubleSpinBox(self.tab_3)
        self.combo_sl_trigger_field.setMaximum(99999.0)
        self.combo_sl_trigger_field.setSingleStep(0.01)
        self.combo_sl_trigger_field.setObjectName("combo_sl_trigger_field")
        self.bottom_layout.addWidget(self.combo_sl_trigger_field)
        self.combo_sl_check = QtWidgets.QCheckBox(self.tab_3)
        self.combo_sl_check.setChecked(True)
        self.combo_sl_check.setObjectName("combo_sl_check")
        self.bottom_layout.addWidget(self.combo_sl_check)
        self.combo_stop_limit_field = QtWidgets.QDoubleSpinBox(self.tab_3)
        self.combo_stop_limit_field.setMaximum(99999.0)
        self.combo_stop_limit_field.setSingleStep(0.01)
        self.combo_stop_limit_field.setObjectName("combo_stop_limit_field")
        self.bottom_layout.addWidget(self.combo_stop_limit_field)
        spacerItem7 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.bottom_layout.addItem(spacerItem7)
        self.oco_button = QtWidgets.QPushButton(self.tab_3)
        self.oco_button.setObjectName("oco_button")
        self.bottom_layout.addWidget(self.oco_button)
        self.gridLayout_3.addLayout(self.bottom_layout, 1, 0, 1, 1)
        self.tab_widget.addTab(self.tab_3, "")
        self.stair_step_tab = QtWidgets.QWidget()
        self.stair_step_tab.setObjectName("stair_step_tab")
        self.gridLayout = QtWidgets.QGridLayout(self.stair_step_tab)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.step_buy_radio = QtWidgets.QRadioButton(self.stair_step_tab)
        self.step_buy_radio.setChecked(True)
        self.step_buy_radio.setObjectName("step_buy_radio")
        self.step_buy_sell_group = QtWidgets.QButtonGroup(MainWindow)
        self.step_buy_sell_group.setObjectName("step_buy_sell_group")
        self.step_buy_sell_group.addButton(self.step_buy_radio)
        self.verticalLayout.addWidget(self.step_buy_radio)
        self.step_sell_radio = QtWidgets.QRadioButton(self.stair_step_tab)
        self.step_sell_radio.setObjectName("step_sell_radio")
        self.step_buy_sell_group.addButton(self.step_sell_radio)
        self.verticalLayout.addWidget(self.step_sell_radio)
        self.horizontalLayout_2.addLayout(self.verticalLayout)
        self.label_5 = QtWidgets.QLabel(self.stair_step_tab)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_2.addWidget(self.label_5)
        self.step_bar_label = QtWidgets.QLabel(self.stair_step_tab)
        self.step_bar_label.setObjectName("step_bar_label")
        self.horizontalLayout_2.addWidget(self.step_bar_label)
        spacerItem8 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem8)
        self.gridLayout_5 = QtWidgets.QGridLayout()
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.step_stop_trigger_offset_box = QtWidgets.QDoubleSpinBox(self.stair_step_tab)
        self.step_stop_trigger_offset_box.setKeyboardTracking(False)
        self.step_stop_trigger_offset_box.setMinimum(-99.99)
        self.step_stop_trigger_offset_box.setSingleStep(0.01)
        self.step_stop_trigger_offset_box.setProperty("value", 0.0)
        self.step_stop_trigger_offset_box.setObjectName("step_stop_trigger_offset_box")
        self.gridLayout_5.addWidget(self.step_stop_trigger_offset_box, 1, 3, 1, 1)
        self.step_entry_limit_offset_box = QtWidgets.QDoubleSpinBox(self.stair_step_tab)
        self.step_entry_limit_offset_box.setKeyboardTracking(False)
        self.step_entry_limit_offset_box.setMinimum(-99.99)
        self.step_entry_limit_offset_box.setSingleStep(0.01)
        self.step_entry_limit_offset_box.setProperty("value", 0.0)
        self.step_entry_limit_offset_box.setObjectName("step_entry_limit_offset_box")
        self.gridLayout_5.addWidget(self.step_entry_limit_offset_box, 0, 5, 1, 1)
        self.step_entry_trigger_offset_box = QtWidgets.QDoubleSpinBox(self.stair_step_tab)
        self.step_entry_trigger_offset_box.setKeyboardTracking(False)
        self.step_entry_trigger_offset_box.setMinimum(-99.99)
        self.step_entry_trigger_offset_box.setSingleStep(0.01)
        self.step_entry_trigger_offset_box.setObjectName("step_entry_trigger_offset_box")
        self.gridLayout_5.addWidget(self.step_entry_trigger_offset_box, 0, 3, 1, 1)
        self.step_stop_trigger_label = QtWidgets.QLabel(self.stair_step_tab)
        self.step_stop_trigger_label.setObjectName("step_stop_trigger_label")
        self.gridLayout_5.addWidget(self.step_stop_trigger_label, 1, 2, 1, 1)
        self.label_18 = QtWidgets.QLabel(self.stair_step_tab)
        self.label_18.setObjectName("label_18")
        self.gridLayout_5.addWidget(self.label_18, 0, 4, 1, 1)
        self.label_6 = QtWidgets.QLabel(self.stair_step_tab)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_6.setFont(font)
        self.label_6.setObjectName("label_6")
        self.gridLayout_5.addWidget(self.label_6, 1, 1, 1, 1)
        self.step_stop_limit_offset_box = QtWidgets.QDoubleSpinBox(self.stair_step_tab)
        self.step_stop_limit_offset_box.setKeyboardTracking(False)
        self.step_stop_limit_offset_box.setMinimum(-99.99)
        self.step_stop_limit_offset_box.setSingleStep(0.01)
        self.step_stop_limit_offset_box.setProperty("value", 0.0)
        self.step_stop_limit_offset_box.setObjectName("step_stop_limit_offset_box")
        self.gridLayout_5.addWidget(self.step_stop_limit_offset_box, 1, 5, 1, 1)
        self.label_7 = QtWidgets.QLabel(self.stair_step_tab)
        self.label_7.setObjectName("label_7")
        self.gridLayout_5.addWidget(self.label_7, 0, 2, 1, 1)
        self.step_stop_limit_label = QtWidgets.QLabel(self.stair_step_tab)
        self.step_stop_limit_label.setObjectName("step_stop_limit_label")
        self.gridLayout_5.addWidget(self.step_stop_limit_label, 1, 4, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.stair_step_tab)
        font = QtGui.QFont()
        font.setBold(True)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.gridLayout_5.addWidget(self.label_3, 0, 1, 1, 1)
        self.step_stoploss_check = QtWidgets.QCheckBox(self.stair_step_tab)
        self.step_stoploss_check.setText("")
        self.step_stoploss_check.setChecked(True)
        self.step_stoploss_check.setObjectName("step_stoploss_check")
        self.gridLayout_5.addWidget(self.step_stoploss_check, 1, 0, 1, 1)
        self.horizontalLayout_2.addLayout(self.gridLayout_5)
        self.gridLayout.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.step_profit_check = QtWidgets.QCheckBox(self.stair_step_tab)
        font = QtGui.QFont()
        font.setBold(True)
        self.step_profit_check.setFont(font)
        self.step_profit_check.setObjectName("step_profit_check")
        self.horizontalLayout_3.addWidget(self.step_profit_check)
        spacerItem9 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem9)
        self.step_profit_factor_radio = QtWidgets.QRadioButton(self.stair_step_tab)
        self.step_profit_factor_radio.setEnabled(True)
        self.step_profit_factor_radio.setChecked(True)
        self.step_profit_factor_radio.setObjectName("step_profit_factor_radio")
        self.step_profit_selection_group = QtWidgets.QButtonGroup(MainWindow)
        self.step_profit_selection_group.setObjectName("step_profit_selection_group")
        self.step_profit_selection_group.addButton(self.step_profit_factor_radio)
        self.horizontalLayout_3.addWidget(self.step_profit_factor_radio)
        self.step_profit_factor_spin = QtWidgets.QSpinBox(self.stair_step_tab)
        self.step_profit_factor_spin.setEnabled(True)
        self.step_profit_factor_spin.setKeyboardTracking(False)
        self.step_profit_factor_spin.setProperty("value", 0)
        self.step_profit_factor_spin.setObjectName("step_profit_factor_spin")
        self.horizontalLayout_3.addWidget(self.step_profit_factor_spin)
        self.step_profit_offset_radio = QtWidgets.QRadioButton(self.stair_step_tab)
        self.step_profit_offset_radio.setEnabled(True)
        self.step_profit_offset_radio.setObjectName("step_profit_offset_radio")
        self.step_profit_selection_group.addButton(self.step_profit_offset_radio)
        self.horizontalLayout_3.addWidget(self.step_profit_offset_radio)
        self.step_profit_offset_spin = QtWidgets.QDoubleSpinBox(self.stair_step_tab)
        self.step_profit_offset_spin.setEnabled(True)
        self.step_profit_offset_spin.setKeyboardTracking(False)
        self.step_profit_offset_spin.setSingleStep(1.0)
        self.step_profit_offset_spin.setProperty("value", 0.0)
        self.step_profit_offset_spin.setObjectName("step_profit_offset_spin")
        self.horizontalLayout_3.addWidget(self.step_profit_offset_spin)
        self.step_profit_price_radio = QtWidgets.QRadioButton(self.stair_step_tab)
        self.step_profit_price_radio.setEnabled(True)
        self.step_profit_price_radio.setObjectName("step_profit_price_radio")
        self.step_profit_selection_group.addButton(self.step_profit_price_radio)
        self.horizontalLayout_3.addWidget(self.step_profit_price_radio)
        self.step_profit_price_spin = QtWidgets.QDoubleSpinBox(self.stair_step_tab)
        self.step_profit_price_spin.setEnabled(True)
        self.step_profit_price_spin.setKeyboardTracking(False)
        self.step_profit_price_spin.setMaximum(10000.0)
        self.step_profit_price_spin.setSingleStep(0.01)
        self.step_profit_price_spin.setObjectName("step_profit_price_spin")
        self.horizontalLayout_3.addWidget(self.step_profit_price_spin)
        spacerItem10 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem10)
        spacerItem11 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem11)
        self.gridLayout.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QtWidgets.QLabel(self.stair_step_tab)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.step_count_field = QtWidgets.QSpinBox(self.stair_step_tab)
        self.step_count_field.setKeyboardTracking(False)
        self.step_count_field.setMaximum(1000)
        self.step_count_field.setProperty("value", 0)
        self.step_count_field.setObjectName("step_count_field")
        self.horizontalLayout.addWidget(self.step_count_field)
        spacerItem12 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem12)
        self.step_button = QtWidgets.QPushButton(self.stair_step_tab)
        font = QtGui.QFont()
        font.setPointSize(15)
        self.step_button.setFont(font)
        self.step_button.setObjectName("step_button")
        self.horizontalLayout.addWidget(self.step_button)
        self.gridLayout.addLayout(self.horizontalLayout, 4, 0, 1, 1)
        self.line = QtWidgets.QFrame(self.stair_step_tab)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.gridLayout.addWidget(self.line, 3, 0, 1, 1)
        self.line_2 = QtWidgets.QFrame(self.stair_step_tab)
        self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_2.setObjectName("line_2")
        self.gridLayout.addWidget(self.line_2, 1, 0, 1, 1)
        self.tab_widget.addTab(self.stair_step_tab, "")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.tab)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.order_table = QtWidgets.QTableView(self.tab)
        self.order_table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked|QtWidgets.QAbstractItemView.EditKeyPressed|QtWidgets.QAbstractItemView.SelectedClicked)
        self.order_table.setObjectName("order_table")
        self.gridLayout_6.addWidget(self.order_table, 0, 0, 1, 1)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.radioButton_3 = QtWidgets.QRadioButton(self.tab)
        self.radioButton_3.setObjectName("radioButton_3")
        self.verticalLayout_2.addWidget(self.radioButton_3)
        self.radioButton_2 = QtWidgets.QRadioButton(self.tab)
        self.radioButton_2.setObjectName("radioButton_2")
        self.verticalLayout_2.addWidget(self.radioButton_2)
        self.radioButton = QtWidgets.QRadioButton(self.tab)
        self.radioButton.setObjectName("radioButton")
        self.verticalLayout_2.addWidget(self.radioButton)
        self.cancel_all_button = QtWidgets.QPushButton(self.tab)
        self.cancel_all_button.setObjectName("cancel_all_button")
        self.verticalLayout_2.addWidget(self.cancel_all_button)
        self.gridLayout_6.addLayout(self.verticalLayout_2, 0, 1, 1, 1)
        self.tab_widget.addTab(self.tab, "")
        self.tab_4 = QtWidgets.QWidget()
        self.tab_4.setObjectName("tab_4")
        self.gridLayout_7 = QtWidgets.QGridLayout(self.tab_4)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.step_order_table = QtWidgets.QTableView(self.tab_4)
        self.step_order_table.setObjectName("step_order_table")
        self.gridLayout_7.addWidget(self.step_order_table, 0, 0, 1, 1)
        self.tab_widget.addTab(self.tab_4, "")
        self.vertical_stack.addWidget(self.tab_widget)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.product_label = QtWidgets.QLabel(self.centralwidget)
        self.product_label.setObjectName("product_label")
        self.horizontalLayout_4.addWidget(self.product_label)
        self.label_8 = QtWidgets.QLabel(self.centralwidget)
        self.label_8.setObjectName("label_8")
        self.horizontalLayout_4.addWidget(self.label_8)
        self.price_label = QtWidgets.QLabel(self.centralwidget)
        self.price_label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.price_label.setObjectName("price_label")
        self.horizontalLayout_4.addWidget(self.price_label)
        spacerItem13 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem13)
        self.label_11 = QtWidgets.QLabel(self.centralwidget)
        self.label_11.setObjectName("label_11")
        self.horizontalLayout_4.addWidget(self.label_11)
        self.bar_selector = QtWidgets.QComboBox(self.centralwidget)
        self.bar_selector.setObjectName("bar_selector")
        self.horizontalLayout_4.addWidget(self.bar_selector)
        self.vertical_stack.addLayout(self.horizontalLayout_4)
        self.gridLayout_2.addLayout(self.vertical_stack, 0, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 24))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.tab_widget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Trade Maker"))
        self.label_17.setText(_translate("MainWindow", "Account:"))
        self.symbol_radio.setText(_translate("MainWindow", "Symbol Search"))
        self.list_radio.setText(_translate("MainWindow", "List Selection"))
        self.label_4.setText(_translate("MainWindow", "Lists:"))
        self.label.setText(_translate("MainWindow", "Ticker:"))
        self.buy_radio.setText(_translate("MainWindow", "Buy"))
        self.sell_radio.setText(_translate("MainWindow", "Sell"))
        self.label_12.setText(_translate("MainWindow", "Bid:"))
        self.bid_price_button.setText(_translate("MainWindow", "100.0"))
        self.label_13.setText(_translate("MainWindow", "Last"))
        self.last_price_button.setText(_translate("MainWindow", "100.0"))
        self.label_14.setText(_translate("MainWindow", "Ask:"))
        self.ask_price_button.setText(_translate("MainWindow", "100.0"))
        self.label_15.setText(_translate("MainWindow", "Count"))
        self.market_order_box.setText(_translate("MainWindow", "Market"))
        self.label_16.setText(_translate("MainWindow", "Limit"))
        self.submit_button.setText(_translate("MainWindow", "BUY"))
        self.stop_loss_check.setText(_translate("MainWindow", "Stop level"))
        self.stop_limit_check.setText(_translate("MainWindow", "Limit"))
        self.profit_take_check.setText(_translate("MainWindow", "Profit Level"))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_2), _translate("MainWindow", "General Order"))
        self.combo_buy_radio.setText(_translate("MainWindow", "Buy"))
        self.combo_sell_radio.setText(_translate("MainWindow", "Sell"))
        self.label_10.setText(_translate("MainWindow", "Limit level"))
        self.label_9.setText(_translate("MainWindow", "Stop level"))
        self.combo_sl_check.setText(_translate("MainWindow", "Stop Limit"))
        self.oco_button.setText(_translate("MainWindow", "Place"))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_3), _translate("MainWindow", "OCO"))
        self.step_buy_radio.setText(_translate("MainWindow", "Buy break up"))
        self.step_sell_radio.setText(_translate("MainWindow", "Sell break down"))
        self.label_5.setText(_translate("MainWindow", "of the"))
        self.step_bar_label.setText(_translate("MainWindow", "xx bars"))
        self.step_stop_trigger_label.setText(_translate("MainWindow", "trigger offset"))
        self.label_18.setText(_translate("MainWindow", "limit offset"))
        self.label_6.setText(_translate("MainWindow", "Stop:"))
        self.label_7.setText(_translate("MainWindow", "trigger offset"))
        self.step_stop_limit_label.setText(_translate("MainWindow", "limit offset"))
        self.label_3.setText(_translate("MainWindow", "Entry:"))
        self.step_profit_check.setText(_translate("MainWindow", "Profit take"))
        self.step_profit_factor_radio.setText(_translate("MainWindow", "Factor"))
        self.step_profit_offset_radio.setText(_translate("MainWindow", "Offset"))
        self.step_profit_price_radio.setText(_translate("MainWindow", "Price:"))
        self.label_2.setText(_translate("MainWindow", "Count"))
        self.step_button.setText(_translate("MainWindow", "Track/Place"))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.stair_step_tab), _translate("MainWindow", "Stairstep"))
        self.radioButton_3.setText(_translate("MainWindow", "Session"))
        self.radioButton_2.setText(_translate("MainWindow", "Session/New"))
        self.radioButton.setText(_translate("MainWindow", "Bind All"))
        self.cancel_all_button.setText(_translate("MainWindow", "Cancel All"))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab), _translate("MainWindow", "Manage orders"))
        self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_4), _translate("MainWindow", "Stairsteps orders"))
        self.product_label.setText(_translate("MainWindow", "Product"))
        self.label_8.setText(_translate("MainWindow", ": "))
        self.price_label.setText(_translate("MainWindow", "Price"))
        self.label_11.setText(_translate("MainWindow", "Bars:"))
from uiComps.customWidgets.QuickLineEdit import QuickLineEdit
