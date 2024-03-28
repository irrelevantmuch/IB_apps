from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
import telebot 
from telebot import types 

import json

new_session_message = "\t_____________________\n\n**🚀 New Session Alert 🚀**"

class TelegramBot(QObject):

    message_tracker = dict()

    def __init__(self): #, api_id, api_hash, bot_token, bot_username, message):
        super().__init__()
        print("TelegramBot.__init__")
        self.bot_inf = self.readBotInfo()
        print(self.bot_inf)
        self.bot = telebot.TeleBot(self.bot_inf['token'])
    
        self.bot.send_message(self.bot_inf['chat_id'], new_session_message, parse_mode= 'HTML')
        self.createHandlers()

    def createHandlers(self):
        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            self.bot.send_message(message.chat.id, message.text)


    @pyqtSlot(str, float, dict, float)
    def sendMessage(self, symbol, latest_price, alert_lines, latest_daily_rsi):

        new_message = self.createMessage(symbol, latest_price, alert_lines, latest_daily_rsi)
        if symbol in self.message_tracker:
            self.bot.delete_message(chat_id=self.bot_inf['chat_id'], message_id=self.message_tracker[symbol].message_id)
        self.message_tracker[symbol] = self.bot.send_message(self.bot_inf['chat_id'], new_message, disable_web_page_preview=True, parse_mode= 'HTML')


    def createMessage(self, symbol, latest_price, alert_lines, latest_daily_rsi):
        tv_url = f"https://www.tradingview.com/chart/?symbol={symbol}"

        if latest_daily_rsi > 0:
            if latest_daily_rsi < 40:
               strength = "🔴"
            elif latest_daily_rsi > 60:
                strength = "🟢"
            else:
                strength = "🟠"
            
            message = f"<a href='{tv_url}'>{symbol}</a> (<b>{latest_price:.2f}</b>) - Daily RSI: <b>{latest_daily_rsi:.2f}</b> {strength}" 
        else:
            message = f"<a href='{tv_url}'>{symbol}</a> (<b>{latest_price:.2f}</b>):"
            
        for (bar_type, alert_type), alert_object in alert_lines.items():
            if (alert_type == 'down steps') or (alert_type == 'up steps broken') or (alert_type == 'rsi crossing down'):
                emoticon = '🔴'
            elif (alert_type == 'up steps') or (alert_type == 'down steps broken') or (alert_type == 'rsi crossing up'):
                emoticon = '🟢'
            else:
                emoticon = '🟠'

            message += "\n"
            if alert_type.startswith('up steps'):
                message += f"{emoticon} {alert_object['UpSteps']} {alert_type} ({alert_object['UpMove']:.2f}%) on the {bar_type}"
            elif alert_type.startswith('down steps'):
                message += f"{emoticon} {alert_object['DownSteps']} {alert_type} ({alert_object['DownMove']:.2f}%) on the {bar_type}"
            else:    
                message += f"{emoticon} {alert_object} {alert_type} on the {bar_type}"

        return message


    @pyqtSlot()
    def run(self):
        def target():
            self.bot.polling(non_stop=True, timeout=90)
         
        self.polling_thread = Thread(target=target, daemon=True)
        self.polling_thread.start()
        print("TelegramBot.run but don't get here")
    

    def readBotInfo(self):
        file_name = './data/telegram_bot_info.json'
        try:
            with open(file_name) as json_file:
                json_dict = json.load(json_file)
                return json_dict
        except (IOError, OSError) as e:
            return dict()



