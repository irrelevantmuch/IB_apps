from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QLabel, QHBoxLayout, QTableWidgetItem
from datetime import datetime
from dataHandling.Constants import Constants

class DateTableWidgetItem(QTableWidgetItem):
    def __init__(self, date_string, *args, **kwargs):
        super(DateTableWidgetItem, self).__init__(date_string, *args, **kwargs)
        self.date = datetime.strptime(date_string, Constants.READABLE_DATE_FORMAT)  # Adjust date format as needed

    def __lt__(self, other):
        return self.date < other.date


class TaskProgressWindow(QDialog):

    def __init__(self, df, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Task Progress")

        self.layout = QVBoxLayout(self)

        # Create labels and layout for status counts
        self.pending_label = QLabel(self)
        self.submitted_label = QLabel(self)
        self.completed_label = QLabel(self)
        self.status_layout = QHBoxLayout()
        self.status_layout.addWidget(self.pending_label)
        self.status_layout.addWidget(self.submitted_label)
        self.status_layout.addWidget(self.completed_label)
        self.layout.addLayout(self.status_layout)

        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setSortingEnabled(True)
        self.table.setHorizontalHeaderLabels(["Req ID", "Ticker ID", "Bars", "Duration", "End date", "Status"])
        self.layout.addWidget(self.table)

        self.df = df

        self.setLayout(self.layout)
        self.updateTable()


    def addTasks(self, df):
        self.df = pd.concat([self.df, df]).reset_index(drop=True)
        self.updateTable()


    def updateTaskStatus(self, req_id, status):
        self.df.loc[self.df['Req ID'] == req_id, 'Status'] = status
        self.updateTable()


    def updateTable(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)  # clear the table
        for i in self.df.index:
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(self.df.loc[i, "Req ID"])))
            self.table.setItem(i, 1, QTableWidgetItem(str(self.df.loc[i, "Ticker ID"])))
            self.table.setItem(i, 2, QTableWidgetItem(self.df.loc[i, "Bars"]))
            self.table.setItem(i, 3, QTableWidgetItem(self.df.loc[i, "Duration"]))
            date_item = DateTableWidgetItem(self.df.loc[i, "End Date"])
            self.table.setItem(i, 4, date_item)
            status_item = QTableWidgetItem(self.df.loc[i, "Status"])
            status_item = self.setColorForStatus(status_item)
            self.table.setItem(i, 5, status_item)
        
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

        # Update status counts
        pending_count = (self.df['Status'] == "-1: Pending").sum()
        submitted_count = (self.df['Status'] == "0: Submitted").sum()
        completed_count = (self.df['Status'] == "1: Completed").sum()
        self.pending_label.setText(f"Pending: {pending_count}")
        self.submitted_label.setText(f"Submitted: {submitted_count}")
        self.completed_label.setText(f"Completed: {completed_count}")


    def setColorForStatus(self, item):
        status = item.text()
        if status == "-1: Pending":
            item.setForeground(QBrush(QColor('lightgrey')))
        elif status == "0: Submitted":
            item.setForeground(QBrush(QColor('orange')))
        elif status == "1: Completed":
            item.setForeground(QBrush(QColor('green')))
        else:
            item.setForeground(QBrush(QColor('red')))

        return item

