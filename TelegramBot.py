
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

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
import telebot 
from telebot import types 

from threading import Thread
import json
import re

new_session_message = "\t_____________________\n\n**🚀 New Session Alert 🚀**"

class TelegramBot(QObject):

    alert_tracker = dict()
    message_id_tracker = set()
    temp_reply_id = None
    incoming_message_signal = pyqtSignal(str, dict)

    def __init__(self): #, api_id, api_hash, bot_token, bot_username, message):
        super().__init__()
        self.bot_inf = self.readBotInfo()
        self.bot = telebot.TeleBot(self.bot_inf['token'])
    
        session_message_object = self.bot.send_message(self.bot_inf['chat_id'], new_session_message, parse_mode= 'HTML')
        self.message_id_tracker.add(session_message_object.message_id)
        self.createHandlers()

    def createHandlers(self):
        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            self.temp_reply_id = message.message_id
            photo_path = './data/graphs/sharing_graph.webp'
            command, params = self.parseCommands(message.text)
            self.incoming_message_signal.emit(command, params)
            # with open(photo_path, 'rb') as photo:
            #     self.bot.send_photo(message.chat.id, photo)
            # self.bot.send_message(message.chat.id, message.text)


    def parseCommands(self, message):
        token_list = re.split("[., !?:()]+", message)
        command = token_list[0]
        param_dict = dict()
        for token in token_list[1:]:
            param = re.split("=", token)
            param_dict[param[0]] = param[1]
        return command, param_dict


    @pyqtSlot(str, dict)
    def sendMessage(self, message_type, message_properties):

        if message_type == 'alert_message':
            new_message = self.createAlertMessage(message_properties)
            symbol = message_properties['symbol']
            if symbol in self.alert_tracker:
                self.deleteMessage(self.alert_tracker[symbol].message_id)
                del self.alert_tracker[symbol]
            message_obj = self.bot.send_message(self.bot_inf['chat_id'], new_message, disable_web_page_preview=True, parse_mode= 'HTML')
            self.alert_tracker[symbol] = message_obj
            self.message_id_tracker.add(message_obj.message_id)
        elif message_type == 'image_message':
            with open(message_properties['path'], 'rb') as photo:
                self.bot.send_photo(self.bot_inf['chat_id'], photo, reply_to_message_id=self.temp_reply_id)
            self.bot.delete_message(chat_id=self.bot_inf['chat_id'], message_id=self.temp_reply_id)

        
        

    def deleteMessage(self, message_id):
        self.bot.delete_message(chat_id=self.bot_inf['chat_id'], message_id=message_id)
        self.message_id_tracker.remove(message_id)
        

    def createAlertMessage(self, message_properties):
        symbol = message_properties['symbol']
        latest_price = message_properties['latest_price']
        alert_lines = message_properties['alert_lines']

        tv_url = f"https://www.tradingview.com/chart/?symbol={symbol}"


        if 'daily_move' in message_properties:  
            if message_properties['daily_move'] > 0:
                color_indicator = "🟢"
            else:
                color_indicator = "🔻"
            message = f"<a href='{tv_url}'>{symbol}</a> (<b>{latest_price:.2f} • {color_indicator}{message_properties['daily_move']:.1f}%</b>)" 
        else:
            message = f"<a href='{tv_url}'>{symbol}</a> (<b>{latest_price:.2f}</b>)" 
        if 'daily_rsi' in message_properties:
            if message_properties['daily_rsi'] < 40:
               strength = "🔴"
            elif message_properties['daily_rsi'] > 60:
                strength = "🟢"
            else:
                strength = "🟠"
            message += f"- Daily rsi: <b>{message_properties['daily_rsi']:.1f}</b> {strength}"
        
        message += ":"
            
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


    def cleanupMessages(self):
        for message_id in self.message_id_tracker:
            self.bot.delete_message(chat_id=self.bot_inf['chat_id'], message_id=message_id)


    @pyqtSlot()
    def run(self):
        def target():
            self.bot.polling(non_stop=True, timeout=90)
         
        self.polling_thread = Thread(target=target, daemon=True)
        self.polling_thread.start()
    

    def readBotInfo(self):
        file_name = './data/telegram_bot_info.json'
        try:
            with open(file_name) as json_file:
                json_dict = json.load(json_file)
                return json_dict
        except (IOError, OSError) as e:
            return dict()



