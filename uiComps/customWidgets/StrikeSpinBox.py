
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
import numpy as np

class StrikeSpinBox(QtWidgets.QSpinBox):

    # constructor
    def __init__(self, parent = None):
        super(StrikeSpinBox, self).__init__(parent)

        self.setStrikes([1,2,3])
  

      # method setString
    # similar to set value method
    def setStrikes(self, strikes):
        # making tuple from the string list
        self._strikes = strikes
  
        # setting range to it the spin box
        self.setRange(0, len(strikes)-1)
        

    def onValueChanged(self, i):
        if not self.isValid(i):
            self.setValue(self.before_value)
        else:
            self.newValueChanged.emit(i)
            self.before_value = i


    def setStrike(self, value):
        array = np.asarray(self._strikes)
        idx = (np.abs(array - value)).argmin()
        self.setValue(idx)


    # overwriting the textFromValue method
    def textFromValue(self, value):
        if value >= 0 and value < len(self._strikes):
            return str(self._strikes[value])
        return "NA"


#  importing libraries
# from PyQt6.QtWidgets import * 
# from PyQt6 import QtCore, QtGui
# from PyQt6.QtGui import * 
# from PyQt6.QtCore import * 
# import sys
  
# # custom class for String Spin Box
# class StringBox(QSpinBox):
  
#     # constructor
#     def __init__(self, parent = None):
#         super(StringBox, self).__init__(parent)
  
#         # string values
#         strings = ["a", "b", "c", "d", "e", "f", "g"]
  
#         # calling setStrings method
#         self.setStrings(strings)
  
#     # method setString
#     # similar to set value method
#     def setStrings(self, strings):
  
#         # making strings list
#         strings = list(strings)
  
#         # making tuple from the string list
#         self._strings = tuple(strings)
  
#         # creating a dictionary
#         self._values = dict(zip(strings, range(len(strings))))
  
#         # setting range to it the spin box
#         self.setRange(0, len(strings)-1)
  
#     # overwriting the textFromValue method
#     def textFromValue(self, value):
  
#         # returning string from index
#         # _string = tuple
#         return self._strings[value]
  
# class Window(QMainWindow):
  
#     def __init__(self):
#         super().__init__()
  
#         # setting title
#         self.setWindowTitle("Python ")
  
#         # setting geometry
#         self.setGeometry(100, 100, 600, 400)
  
#         # calling method
#         self.UiComponents()
  
#         # showing all the widgets
#         self.show()
  
#         # method for widgets
#     def UiComponents(self):
  
#         # creating a string spin box
#         string_spin_box = StringBox(self)
  
#         # setting geometry to the spin box
#         string_spin_box.setGeometry(100, 100, 200, 40)
  
  
# # create pyqt5 app
# App = QApplication(sys.argv)
  
# # create the instance of our Window
# window = Window()