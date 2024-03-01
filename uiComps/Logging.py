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
