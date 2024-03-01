from PyQt5.QtWidgets import QLineEdit


class QuickLineEdit(QLineEdit):
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selectAll()  