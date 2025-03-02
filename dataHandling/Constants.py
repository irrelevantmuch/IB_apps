
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

from typing import Final

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 18 16:52:13 2019

@author: vriesdejelmer
"""

class Constants:

    SYMBOL_CHANGE: Final = 0
    SYMBOL_SUBMIT: Final = 1

    SYMBOL_SEARCH_REQID: Final = 2

    PNL_REQID: Final = 5
    ACCOUNT_SUMMARY_REQID: Final = 6
    SEC_DEF_OPTION_PARAM_REQID: Final = 7
    BASE_PRICE_REQID: Final = 1_000_000
    BASE_OPTION_BUFFER_REQID: Final = 2_000_000
    BASE_OPTION_LIVE_REQID: Final = 3_000_000
    BASE_HIST_MIN_MAX_REQID: Final = 4_000_000
    BASE_HIST_DATA_REQID: Final = 5_000_000
    BASE_HIST_BARS_REQID: Final = 6_000_000
    BASE_MKT_STOCK_REQID: Final = 7_000_000
    BASE_PNL_REQID: Final = 8_000_000
    BASE_HIST_EARLIEST_REQID: Final = 9_000_000
    BASE_ORDER_REQID: Final = 10_000_000
    OPTION_CONTRACT_DEF_ID: Final = 11_000_000
    REQID_STEP: Final = 1_000_000

    SECONDS_IN_DAY: Final = 86400
    
    TIME_FORMAT: Final = '%Y%m%d %H:%M:%S %z'
    TIME_FORMAT_NO_TZ: Final = '%Y%m%d %H:%M:%S'
    READABLE_DATE_FORMAT: Final = "%H:%M:%S - %d-%m-%Y"
    
    BEGINNING_OF_TIME: Final = "1970-01-01 01:00:00"

    LOCAL_ADDRESS: Final = "127.0.0.1"

    TRADING_TWS_SOCKET: Final = 7496
    PAPER_TWS_SOCKET: Final = 7497
    TRADING_IBG_SOCKET: Final = 4001
    PAPER_IBG_SOCKET: Final = 4002

    POLYGON_SOURCE: Final = "Polygon Data Source"
    FINAZON_SOURCE: Final = "Finazon Data Source"
    IB_SOURCE: Final = "IB Data Source"

    OPEN_REQUEST_MAX: Final = 50

    MIN_SECONDS: Final = 300

    MAX_DEFAULT_LINES: Final = 15

    PREFFERED_DIFFS_LARGE: Final = [10.0, 5.0, 15.0, 20.0, 5.0, 4.0, 3.0,2.0,1.0]
    PREFFERED_DIFFS_SMALL: Final = [5.0, 10.0, 4.0, 3.0,2.0,1.0]

    CALL: Final = "C"
    PUT: Final = "P"

    BUY: Final = "BUY"
    SELL: Final = "SELL"

    DISPLAY_TIME: Final = "DISPLAY_TIME"

    BUFFER_FOLDER: Final = './data/downloads/buffers/'
    ANAYLIS_RESULTS_FOLDER: Final = './data/treeAnalysis/'
    POLYGON_BUFFER_FOLDER: Final = './data/downloads/polygon_buffers/'
    FINAZON_BUFFER_FOLDER: Final = './data/downloads/finazon_buffers/'
    OPTION_CHAIN_FOLDER: Final = './data/downloads/option_buffers/'

    BASE_TIMESTAMP_UTC: Final = 1704067200
    BASE_TIMESTAMP_NY: Final = 1704085200      #We need some timestamp to anchor bars to, to ensure, e.g., the 3m bar starts at 9:30, not 9:31

    BID: Final = "BID"
    ASK: Final = "ASK"
    
    LAST: Final = "LAST"

    SYMBOL: Final = "symbol"

    OPEN: Final = 'OPEN'
    HIGH: Final = 'HIGH'
    LOW: Final = 'LOW'
    CLOSE: Final = "CLOSE"
    VOLUME: Final = 'VOLUME'
    STOCK: Final = 'STK'
    OPTION: Final = 'OPT'
    CFD: Final = 'CFD'
    CASH: Final = 'CASH'
    COMMODITY: Final = 'CMDTY'
    WARRANT: Final = 'WAR'


    MAX: Final = "MAX"
    MIN: Final = "MIN"

    CFD: Final = "CFD"

    USD: Final = "USD"

    MAX_DATE: Final = "MAX_DATE"
    MAX_FROM: Final = "MAX_FROM"
    MIN_DATE: Final = "MIN_DATE"
    MIN_FROM: Final = "MIN_FROM"

    CORR_VALUES: Final = "CORR_VALUES"

    DAY_MOVE: Final = "Day_MOVE"
    YESTERDAY_CLOSE: Final = "YESTERDAY_CLOSE"
    STALE: Final = "STALE"

    PRICE: Final = 'PRICE'
    
    STRIKE: Final = 'STRIKE'

    NORMALIZED: Final = "Normalized"
    INDEXED: Final = "Indexed"
    
    PREMIUM: Final = 'PREMIUM'

    EXPIRATIONS: Final = 'EXPIRATIONS'
    NAMES: Final = 'NAMES'
    DAYS_TILL_EXP: Final = 'DAYS_TILL_EXP'

    DEFAULT_OPT_EXC: Final = "SMART" #"CBOE" #"AMEX"
    EXCHANGE: Final = 'exchange'
    SMART: Final = "SMART"
    FIRST_AVAILABLE_DATE: Final = "First Available Date"

    TRADES: Final = 'TRADES'

    OPTION_DATA_EXP: Final = "Expiration Type"
    OPTION_DATA_STRIKE: Final = "Strike Type"

    UP_STEPS: Final = 'up_steps'
    DOWN_STEPS: Final = 'down_steps'
    BULL_BARS: Final = 'bull_bars'
    BEAR_BARS: Final = 'bear_bars'
    TOP_REVERSAL: Final = 'top_reversal'
    BOTTOM_REVERSAL: Final = 'bottom_reversal'

    POSITIONS_UPDATED: Final = "Positions updated"
    DATE_RETRIEVED: Final = "Dates retrieved"
    OPTION_INFO_LOADED: Final = "Options info loaded"
    OPTION_PRICE_UPDATE: Final = "Option Price Updated"
    OPTIONS_MOSTLY_LOADED: Final = "Most options loaded"
    OPTIONS_LOADED: Final = "Options loaded"
    UNDERLYING_PRICE_UPDATE: Final = "Underlying Price Updated"
    CONTRACT_DETAILS_RETRIEVED: Final = "Contract details retrieved"
    CONTRACT_DETAILS_FINISHED: Final = "Contract details finished"
    CONNECTION_OPEN: Final = "Connection open"
    CONNECTION_CLOSED: Final = "Connection closed"
    CONNECTION_STATUS_CHANGED: Final = "Connection Status Changed"
    HISTORICAL_MIN_MAX_FETCH_COMPLETE: Final = "Historical MinMax Fetch Complete"
    HISTORICAL_DATA_FETCH_COMPLETE: Final = "Historical Data Fetch Complete"
    HISTORICAL_BUFFER_FETCH_COMPLETE: Final = "Historical Buffer Fetch Complete"
    HISTORICAL_REQUESTS_COMPLETED: Final = "Historical Requests Complete"
    HISTORICAL_GROUP_COMPLETE: Final = "Historical Group Complete"
    HISTORICAL_UPDATE_COMPLETE: Final = "Historical Update Complete"
    PRICE_COLLECTION_COMPLETE: Final = "Prices Fetched"
    LIST_SELECTION_UPDATE: Final = "List Selection Updated"
    PNL_RETRIEVED: Final = "PNL Updated"
    IND_PNL_COMPLETED: Final = "Individual PnLs retrieved"
    HAS_NEW_DATA: Final = "New data avaible by key"
    HAS_NEW_VALUES: Final = "New values avaible by key"
    DATA_RELOADED: Final = "Data has been reloaded"
    ALL_DATA_LOADED: Final = "All requests completed"
    DATA_LOADED_FROM_FILE: Final = "Previously buffered data loaded"
    HISTORY_LOCK: Final = "Historical Data Manager Locked"
    HISTORY_UNLOCK: Final = "Historical Data Manager Unlocked"
    QUEUED_NEW_TASKS: Final = "New tasks being queued"
    HISTORICAL_REQUEST_COMPLETED: Final = "Historical Request Complete"
    HISTORICAL_DATA_READY: Final = "Historical Data Ready"
    HISTORICAL_REQUEST_SUBMITTED: Final = "Historical Request Submitted"
    POLYGON_REQUEST_COMPLETED: Final = "Polygon Request Complete"
    POLYGON_REQUESTS_COMPLETED: Final = "Polygon Requests Complete"
    PROGRESS_UPDATE: Final = "Progress Update"
    PROPERTY_UPDATE: Final = "Property Update"
    ACTIVE_REQUESTS_CANCELLED: Final = "Active Requests Cancelled"

    MANAGED_ACCOUNT_LIST: Final = "Managed account list"
    SELECTED_KEYS_CHANGED: Final = "Selected keys changed"

    LAST_FIVE_AT: Final = "LAST_FIVE_AT"
    CALCULATED_AT: Final = "CALCULATED_AT"

    DAY_LOW: Final = "Day_LOW"
    DAY_HIGH: Final = "Day_HIGH"
    DAY_LOW_DIFF: Final = "Day_LOW_DIFF"
    DAY_HIGH_DIFF: Final = "Day_HIGH_DIFF"          

    NYC_TIMEZONE: Final = 'US/Eastern'

    DATA_STRUCTURE_CHANGED: Final = "Data structure change"
    DATA_WILL_CHANGE: Final = "Data about to change"
    DATA_DID_CHANGE: Final = "Data just changed"
    DATA_LINES_WILL_RENEW: Final = "Data lines will renew"
    DATA_LINES_UPDATED: Final = "Data lines updated"        

    ONE_MIN_BAR: Final = '1 min'
    TWO_MIN_BAR: Final = '2 mins'
    THREE_MIN_BAR: Final = '3 mins'
    FIVE_MIN_BAR: Final = '5 mins'
    FIFTEEN_MIN_BAR: Final = '15 mins'
    HOUR_BAR: Final = '1 hour'
    FOUR_HOUR_BAR: Final = '4 hours'
    TWELVE_HOUR_BAR: Final = '12 hours'
    DAY_BAR: Final = '1 day'
    THREE_DAY_BAR: Final = '3 days'
    WEEK_BAR: Final = '1 week'


QUICK_BAR_TYPES: Final = [Constants.ONE_MIN_BAR, Constants.TWO_MIN_BAR, Constants.THREE_MIN_BAR, Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR, Constants.HOUR_BAR]
MAIN_BAR_TYPES: Final = [Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR, Constants.HOUR_BAR, Constants.FOUR_HOUR_BAR, Constants.DAY_BAR] #, Constants.THREE_DAY_BAR, Constants.WEEK_BAR]
DT_BAR_TYPES: Final = [Constants.ONE_MIN_BAR, Constants.TWO_MIN_BAR, Constants.THREE_MIN_BAR, Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR, Constants.HOUR_BAR, Constants.FOUR_HOUR_BAR, Constants.DAY_BAR] #, Constants.THREE_DAY_BAR, Constants.WEEK_BAR]
DOWNLOADABLE_BAR_TYPES: Final = {Constants.ONE_MIN_BAR: Constants.ONE_MIN_BAR, Constants.TWO_MIN_BAR: Constants.TWO_MIN_BAR, Constants.THREE_MIN_BAR: Constants.THREE_MIN_BAR, Constants.FIVE_MIN_BAR: Constants.FIVE_MIN_BAR, Constants.FIFTEEN_MIN_BAR: Constants.FIFTEEN_MIN_BAR, Constants.HOUR_BAR: Constants.HOUR_BAR, Constants.FOUR_HOUR_BAR: Constants.HOUR_BAR, Constants.DAY_BAR: Constants.DAY_BAR, Constants.THREE_DAY_BAR: Constants.DAY_BAR, Constants.WEEK_BAR: Constants.DAY_BAR}
RESAMPLING_BARS: Final = {Constants.TWO_MIN_BAR: '2min', Constants.THREE_MIN_BAR: '3min', Constants.FIVE_MIN_BAR: '5min', Constants.FIFTEEN_MIN_BAR: '15min', Constants.HOUR_BAR: '1h', Constants.FOUR_HOUR_BAR: '4h', Constants.DAY_BAR: 'D', Constants.THREE_DAY_BAR: '3D', Constants.WEEK_BAR: 'W'}
RESAMPLING_DT_BARS: Final = {Constants.TWO_MIN_BAR: '2min', Constants.THREE_MIN_BAR: '3min', Constants.FIVE_MIN_BAR: '5min', Constants.FIFTEEN_MIN_BAR: '15min', Constants.HOUR_BAR: 'h', Constants.FOUR_HOUR_BAR: '4h', Constants.DAY_BAR: 'D', Constants.THREE_DAY_BAR: '3D', Constants.WEEK_BAR: 'W'}
RESAMPLING_SECONDS: Final = {Constants.TWO_MIN_BAR: 120, Constants.THREE_MIN_BAR: 180, Constants.FIVE_MIN_BAR: 300, Constants.FIFTEEN_MIN_BAR: 900, Constants.HOUR_BAR: 3600, Constants.FOUR_HOUR_BAR: 14400, Constants.DAY_BAR: 86400, Constants.THREE_DAY_BAR: 259200, Constants.WEEK_BAR: 604800}


MINUTES_PER_BAR: Final = {Constants.ONE_MIN_BAR: 1, Constants.TWO_MIN_BAR: 2, Constants.THREE_MIN_BAR: 3, Constants.FIVE_MIN_BAR: 5, Constants.FIFTEEN_MIN_BAR: 15, Constants.HOUR_BAR: 60, Constants.FOUR_HOUR_BAR: 240, Constants.DAY_BAR: 1440, Constants.THREE_DAY_BAR: 4320, Constants.WEEK_BAR: 10080}

# importing enum for enumerations
import enum
    
# creating enumerations using class
class OptionConstrType(enum.Enum):
    single = "Single Option"
    butterfly = "Butterfly"
    topped_ratio_spread = "Topped Spread"
    split_butterfly = "Split Butterfly"
    iron_condor = "Iron Condor"
    vertical_spread = "Vertical Spread"
    bw_butterfly = "BW Butterfly"
 

 # creating enumerations using class
class TradingPriority(enum.Enum):
    daily = "Daily"
    swing = "Swing"
    long_term = "Long Term"


    # creating enumerations using class
class TableType(enum.Enum):
    rsi = "RSI"
    inside_bar = "Inside Bars"
    overview = "Overview"
    rel_rsi = "Relative RSI"
    up_step = "Bull Stair Step"
    down_step = "Bear Stair Step"
    from_low = "From Low"
    from_high = "From High"
    index_corr = "Index Correlation"
