# Form implementation generated from reading ui file 'UIComps/QTGeneration/DataDownloader.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 649)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(800, 600))
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setMinimumSize(QtCore.QSize(800, 600))
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.fetch_button = QtWidgets.QPushButton(parent=self.centralwidget)
        self.fetch_button.setObjectName("fetch_button")
        self.gridLayout_2.addWidget(self.fetch_button, 9, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Maximum)
        self.gridLayout_2.addItem(spacerItem, 0, 1, 1, 1)
        self.bar_combobox = QtWidgets.QComboBox(parent=self.centralwidget)
        self.bar_combobox.setObjectName("bar_combobox")
        self.gridLayout_2.addWidget(self.bar_combobox, 8, 1, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=self.centralwidget)
        self.label_5.setObjectName("label_5")
        self.gridLayout_2.addWidget(self.label_5, 5, 1, 1, 1)
        self.label = QtWidgets.QLabel(parent=self.centralwidget)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label.setObjectName("label")
        self.gridLayout_2.addWidget(self.label, 1, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=self.centralwidget)
        self.label_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.gridLayout_2.addWidget(self.label_2, 8, 0, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=self.centralwidget)
        self.label_4.setObjectName("label_4")
        self.gridLayout_2.addWidget(self.label_4, 5, 0, 1, 1)
        self.start_date_widget = QtWidgets.QCalendarWidget(parent=self.centralwidget)
        self.start_date_widget.setObjectName("start_date_widget")
        self.gridLayout_2.addWidget(self.start_date_widget, 6, 0, 1, 1)
        self.end_date_widget = QtWidgets.QCalendarWidget(parent=self.centralwidget)
        self.end_date_widget.setObjectName("end_date_widget")
        self.gridLayout_2.addWidget(self.end_date_widget, 6, 1, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Maximum)
        self.gridLayout_2.addItem(spacerItem1, 4, 1, 1, 1)
        self.search_field = QtWidgets.QLineEdit(parent=self.centralwidget)
        self.search_field.setInputMethodHints(QtCore.Qt.InputMethodHint.ImhUppercaseOnly)
        self.search_field.setClearButtonEnabled(True)
        self.search_field.setObjectName("search_field")
        self.gridLayout_2.addWidget(self.search_field, 1, 1, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Maximum)
        self.gridLayout_2.addItem(spacerItem2, 7, 1, 1, 1)
        self.gridLayout_2.setColumnStretch(0, 1)
        self.gridLayout_2.setColumnStretch(1, 1)
        self.gridLayout_2.setRowStretch(0, 1)
        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Symbol List Builder"))
        self.fetch_button.setText(_translate("MainWindow", "Fetch"))
        self.label_5.setText(_translate("MainWindow", "End Date"))
        self.label.setText(_translate("MainWindow", "Symbol Search"))
        self.label_2.setText(_translate("MainWindow", "Bar Period"))
        self.label_4.setText(_translate("MainWindow", "Start Date"))
        self.search_field.setPlaceholderText(_translate("MainWindow", "type symbol here"))
