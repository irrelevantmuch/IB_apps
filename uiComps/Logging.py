
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

from generalFunctionality.Singleton import Singleton

from pubsub import pub

@Singleton
class Logger:

    log_window = None

    def setLogWindow(self, log_window):
        self.log_window = log_window
        pub.subscribe(self.printLine, 'log')


    def printLine(self, message):
        self.log_window.appendPlainText(message)
