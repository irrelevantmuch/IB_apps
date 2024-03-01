from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
import telebot 
from telebot import types 

import json


class TelegramBot(QObject):

    telegram_signal = pyqtSignal(str)

    def __init__(self): #, api_id, api_hash, bot_token, bot_username, message):
        super().__init__()

        self.telegram_signal.connect(self.sendMessage, Qt.QueuedConnection)
        self.bot_inf = self.readBotInfo()
        self.bot = telebot.TeleBot(self.bot_inf['token'])
        # self.bot.send_message(self.bot_inf['chat_id'], "<b>bold</b> bold", parse_mode= 'HTML')
        self.createHandlers()

    def createHandlers(self):
        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            self.bot.send_message(message.chat.id, message.text)


    @pyqtSlot(str)
    def sendMessage(self, message_text):
        print(f"Is this the problem? {self.bot_inf['chat_id']}")
        self.bot.send_message(self.bot_inf['chat_id'], message_text, parse_mode= 'HTML')


    @pyqtSlot()
    def run(self):
        self.bot.polling(non_stop=True, timeout=90)
    

    def readBotInfo(self):
        file_name = './data/bot_info.json'
        try:
            with open(file_name) as json_file:
                json_dict = json.load(json_file)
                return json_dict
        except (IOError, OSError) as e:
            return dict()



