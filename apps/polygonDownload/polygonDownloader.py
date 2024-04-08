
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

import requests
import pandas as pd
from dataHandling.Constants import Constants
from dataHandling.UserDataManagement import readApiKeys
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

api_keys = readApiKeys()

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

    @pyqtSlot(list, list, tuple)
    def downloadForSymbols(self, symbols, bar_types, time_range):
        self.total_count = len(symbols) * len(bar_types)
        self.symbol_count = len(symbols)

        data_dict = dict()
        for symbol in symbols:
            data_dict[symbol] = self.downloadForSymbol(symbol, bar_types, time_range)
        self.api_updater.emit(Constants.POLYGON_REQUESTS_COMPLETED, dict())

    def getCountAndUnit(self, polygon_bar):
        split_polygon_bar = polygon_bar.split()
        count = int(split_polygon_bar[0])
        unit = split_polygon_bar[1]
        return count, unit


    @pyqtSlot(str, list, tuple)
    def downloadForSymbol(self, symbol, bar_types, time_range):

        print(f"We attempt to download {symbol} for {bar_types} between {time_range[0]} to {time_range[1]}")
        # Specify the columns you're interested in
        columns = ['o', 'h', 'l', 'c', 'v', 't']

        for bar_type in bar_types:
            symbol_df = pd.DataFrame(columns=columns)
            counter = 0

            url = self.makeURL(symbol, time_range, bar_type)

            # While there are pages
            while url:
                # Make the HTTP request
                url += '&apiKey=' + api_keys[Constants.POLYGON_SOURCE] + '&limit=50000'
                
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

            # symbol_df[Constants.HIGH] = pd.to_numeric(symbol_df[Constants.HIGH])
            # symbol_df[Constants.LOW] = pd.to_numeric(symbol_df[Constants.LOW])
            # symbol_df[Constants.OPEN] = pd.to_numeric(symbol_df[Constants.OPEN])
            # symbol_df[Constants.CLOSE] = pd.to_numeric(symbol_df[Constants.CLOSE])
            # symbol_df[Constants.VOLUME] = pd.to_numeric(symbol_df[Constants.VOLUME])
            symbol_df = symbol_df.apply(pd.to_numeric, errors='coerce', axis=0)

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
