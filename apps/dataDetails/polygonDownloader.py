import requests
import datetime
import json
import pandas as pd
from dataHandling.Constants import Constants
from dateutil.relativedelta import relativedelta
import time
import sys
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal


    # The Polygon.io API key
API_KEY = 'your_polygon_key'

    # Define the base URL
base_url = 'https://api.polygon.io'


class PolygonDownloader(QObject):

    api_updater = pyqtSignal(str, dict)

    def run(self):
        print("We start the thread")


    def getTimeRange(self, time_range):
        
            # Convert the dates to string
        end_date_str = time_range[1].strftime('%Y-%m-%d')
        start_date_str = time_range[0].strftime('%Y-%m-%d')

        return start_date_str, end_date_str


    def makeURL(self, symbol, time_range, bar_type):

        count, unit = self.getCountAndUnit(bar_type)

        # Define the API endpoint for 1-minute bar data
        start_str, end_str = self.getTimeRange(time_range)
        url = f'{base_url}/v2/aggs/ticker/{symbol}/range/{count}/{unit}/{start_str}/{end_str}?'
        
        return url

    @pyqtSlot(list, str, tuple)
    def downloadForSymbols(self, symbols, bar_type, time_range):
        data_dict = dict()
        for symbol in symbols:
            data_dict[symbol] = self.downloadForSymbol(symbol, bar_type, time_range)
        self.api_updater.emit(Constants.POLYGON_REQUESTS_COMPLETED, dict())

    def getCountAndUnit(self, polygon_bar):
        split_polygon_bar = polygon_bar.split()
        count = int(split_polygon_bar[0])
        unit = split_polygon_bar[1]
        return count, unit


    @pyqtSlot(str, str, tuple)
    def downloadForSymbol(self, symbol, bar_type, time_range):

        print(f"We attempt to download {symbol} for {bar_type} between {time_range[0]} to {time_range[1]}")
        # Specify the columns you're interested in
        columns = ['o', 'h', 'l', 'c', 'v', 't']
        symbol_df = pd.DataFrame(columns=columns)
        counter = 0

        url = self.makeURL(symbol, time_range, bar_type)

        # While there are pages
        while url:
            # Make the HTTP request
            url += '&apiKey=' + API_KEY + '&limit=50000'
            
            response = requests.get(url)

            # Check for successful request
            if response.status_code == 200:
                # Parse the JSON response
                data = response.json()
                
                symbol_df = pd.concat([symbol_df, pd.DataFrame(data['results'], columns=columns)])
                
                # Get the next page URL
                url = data.get('next_url')
                counter += 1
            else:

                print(f'Request failed with status code {response.status_code}')
                break


        symbol_df = self.fixTimeZones(symbol_df)

        # Rename columns
        column_names = { 'o': Constants.OPEN, 'h': Constants.HIGH, 'l': Constants.LOW, 'c': Constants.CLOSE, 'v': Constants.VOLUME }
        symbol_df.rename(columns=column_names, inplace=True)

        file_name = Constants.POLYGON_BUFFER_FOLDER + symbol + '_' + bar_type + '.pkl'
        symbol_df.to_pickle(file_name)
        # Remove the name of the index column
        
        self.api_updater.emit(Constants.POLYGON_REQUEST_COMPLETED, {'symbol': symbol, 'bar_type': bar_type})


    def fixTimeZones(self, unix_ms_frame):
            # Convert timestamps to datetime and set as index
        unix_ms_frame['t'] = pd.to_datetime(unix_ms_frame['t'], unit='ms')
        unix_ms_frame.set_index('t', inplace=True)
        unix_ms_frame.index.rename(None, inplace=True)
            # Polygon provides UTC, we want New York
        unix_ms_frame.index = unix_ms_frame.index.tz_localize('UTC')
        unix_ms_frame.index = unix_ms_frame.index.tz_convert('America/New_York')
        return unix_ms_frame
