# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'optionsGraph.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from uiComps.qtGeneration.Movers_UI import Ui_MainWindow as Movers_UI
from dataHandling.UserDataManagement import getStockListNames
from dataHandling.Constants import TableType
from uiComps.generalUIFunctionality import ProcessorWindow


class MoversWindow(ProcessorWindow, Movers_UI):

    column_for_name = {'Price': 1, 'Day': 2, 'Week': 3, '2 Weeks': 4, 'Month': 5, "2 Months": 6, "6 Months": 7 , "1 Year": 8}
    period_options = ["Day", "Week", "2 Weeks", "Month", "2 Months", "3 Months", "6 Months", "1 Year"]
    corr_period_options = ["2 hours", "4 hours", "Today", "24 hours", "1 week", "2 week", "Month", "2 Months", "3 Months", "6 Months", "max"]
    

    def __init__(self, bar_types):
        ProcessorWindow.__init__(self)
        Movers_UI.__init__(self)

        self.bar_types = bar_types

        self.setupUi(self)

        self.populateBoxes()
        self.setupActions()
        # self.setupAlignment()
        #self.setTableProperties()

        #self.step_table.verticalHeader().setResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.step_down_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.step_up_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.high_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.low_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        btn = self.overview_table.findChild(QtWidgets.QAbstractButton)
        btn.setText("TEST")
        btn.setToolTip('DOES THIS SHOW?')

        self.list_of_tables = [self.overview_table, self.low_table, self.high_table, self.step_up_table, self.step_down_table, self.rsi_table, self.rel_rsi_table, self.index_correlation_table]

        self.overview_widget.table_type = TableType.overview
        self.from_low_widget.table_type = TableType.from_low
        self.from_high_widget.table_type = TableType.from_high
        self.steps_up_widget.table_type = TableType.up_step
        self.steps_down_widget.table_type = TableType.down_step
        self.inside_bar_widget.table_type = TableType.inside_bar
        self.rsi_widget.table_type = TableType.rsi
        self.rel_rsi_widget.table_type = TableType.rel_rsi
        self.corr_widget.table_type = TableType.index_corr

        self.overview_table.table_type = TableType.overview
        self.low_table.table_type = TableType.from_low
        self.high_table.table_type = TableType.from_high
        self.step_up_table.table_type = TableType.up_step
        self.step_down_table.table_type = TableType.down_step
        self.rsi_table.table_type = TableType.rsi
        self.rel_rsi_table.table_type = TableType.rel_rsi
        self.index_correlation_table.table_type = TableType.index_corr

        for tbl in self.list_of_tables:
            tbl.setSortingEnabled(True)
        
        self.keep_up_box.setEnabled(False)
        
        self.connectScrollbars()



    def connectScrollbars(self):

        def move_other_scrollbars(idx, bar):
            scrollbars = {tbl.verticalScrollBar() for tbl in self.list_of_tables}
            scrollbars.remove(bar)
            for bar in scrollbars:
                bar.setValue(idx)

        for tbl in self.list_of_tables:
            scrollbar = tbl.verticalScrollBar()
            scrollbar.valueChanged.connect(lambda idx,bar=scrollbar: move_other_scrollbars(idx, bar))
#            self.layout.addWidget(tbl)


    def setupActions(self):
        self.fetch_button.clicked.connect(self.fetchData)
        self.period_selector.currentTextChanged.connect(self.periodSelection)
        self.index_selector.currentIndexChanged.connect(self.indexSelection)
        self.keep_up_box.stateChanged.connect(self.keepUpToDate, Qt.QueuedConnection)
        self.use_stale_box.stateChanged.connect(self.greyoutStale)
        self.list_selector.currentIndexChanged.connect(self.listSelection)
        self.tab_widget.currentChanged.connect(self.onTabChange) 

        self.step_up_table.clicked.connect(lambda i: self.prepOrder(i, "Up"))
        self.step_down_table.clicked.connect(lambda i: self.prepOrder(i, "Down"))
        self.overview_table.clicked.connect(self.overviewClicked)
        self.rsi_table.clicked.connect(self.showChart)
        self.rel_rsi_table.clicked.connect(lambda i: self.showChart(i, vs_index=True))
        
        self.corr_frame_selector.currentTextChanged.connect(self.correlationTimeFrameUpdate)
        self.corr_bar_counter.currentTextChanged.connect(self.updateCorrBarCount)
        

    def populateBoxes(self):
        self.stock_lists = getStockListNames()
        for file_name, list_name in self.stock_lists:
            self.list_selector.addItem(list_name)

        self.period_selector.blockSignals(True)
        for item in self.period_options:
            self.period_selector.addItem(item)
        self.period_selector.blockSignals(False)

        self.corr_frame_selector.addItems(self.bar_types)

        selection_list = [x*6 for x in range(2,15)]
        self.corr_bar_counter.addItems(map(str,selection_list))


    def onTabChange(self, value):
        self.period_selector.setEnabled(value==0)

    def setTableProperties(self):
        for column_index in range(2,9):
            self.low_table.horizontalHeader().setSectionResizeMode(column_index, QtWidgets.QHeaderView.Stretch)
            self.high_table.horizontalHeader().setSectionResizeMode(column_index, QtWidgets.QHeaderView.Stretch)

        # for column_index in self.step_mapping.keys():
        #     self.step_up_table.horizontalHeader().setSectionResizeMode(column_index, QtWidgets.QHeaderView.ResizeToContents)
        #     self.step_down_table.horizontalHeader().setSectionResizeMode(column_index, QtWidgets.QHeaderView.ResizeToContents)

        #self.step_up_table.horizontalHeader().setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeToContents)


    def setupAlignment(self):
        #TODO: Why is this still here?
        pass
        # alignDelegate = AlignDelegate(self.overview_table)
        # percAlignDelegate = PercAlignDelegate(self.overview_table)
        # bigNumAlignDelegate = BigNumberAlignDelegate(self.overview_table)
        # self.overview_table.setItemDelegateForColumn(1, alignDelegate)
        # self.overview_table.setItemDelegateForColumn(2, alignDelegate)
        # self.overview_table.setItemDelegateForColumn(3, percAlignDelegate)
        # self.overview_table.setItemDelegateForColumn(4, alignDelegate)
        # self.overview_table.setItemDelegateForColumn(5, percAlignDelegate)
        # self.overview_table.setItemDelegateForColumn(6, percAlignDelegate)
        # self.overview_table.setItemDelegateForColumn(7, bigNumAlignDelegate)


 

        

