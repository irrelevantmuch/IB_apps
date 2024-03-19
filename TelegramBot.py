from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
import telebot 
from telebot import types 

import json


class TelegramBot(QObject):

    message_tracker = dict()

    def __init__(self): #, api_id, api_hash, bot_token, bot_username, message):
        super().__init__()
        print("TelegramBot.__init__")
        self.bot_inf = self.readBotInfo()
        print(self.bot_inf)
        self.bot = telebot.TeleBot(self.bot_inf['token'])
        # self.bot.send_message(self.bot_inf['chat_id'], "<b>bold</b> bold", parse_mode= 'HTML')
        self.createHandlers()

    def createHandlers(self):
        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            self.bot.send_message(message.chat.id, message.text)


    @pyqtSlot(str, float, list)
    def sendMessage(self, symbol, latest_price, alert_lines):
        new_message = self.createMessage(symbol, latest_price, alert_lines)
        if symbol in self.message_tracker:
            self.bot.edit_message_text(new_message, chat_id=self.bot_inf['chat_id'], message_id=self.message_tracker[symbol].message_id, disable_web_page_preview=True, parse_mode= 'HTML')
        else:
            self.message_tracker[symbol] = self.bot.send_message(self.bot_inf['chat_id'], new_message, disable_web_page_preview=True, parse_mode= 'HTML')


    def createMessage(self, symbol, latest_price, alert_lines):
        # (: {level} {alert_type} (<b>{percentage:.1f}%</b>)
        message = f"<a href='https://www.tradingview.com/chart/?symbol={symbol}'>{symbol}</a> (<b>{latest_price:.2f}</b>):" 

        for line in alert_lines:
            message += "\n"
            message += line

        return message


    @pyqtSlot()
    def run(self):
        def target():
            self.bot.polling(non_stop=True, timeout=90)
         
        self.polling_thread = Thread(target=target, daemon=True)
        self.polling_thread.start()
        print("TelegramBot.run but don't get here")
    

    def readBotInfo(self):
        file_name = './data/bot_info.json'
        try:
            with open(file_name) as json_file:
                json_dict = json.load(json_file)
                return json_dict
        except (IOError, OSError) as e:
            return dict()



