
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

from datetime import datetime, time
from pytz import timezone, utc
import numpy as np
import sys
import pandas as pd

from dataHandling.Constants import Constants, MINUTES_PER_BAR
from dateutil.relativedelta import relativedelta
from PyQt6.QtCore import QThread

def printPriority(thread_priority):
        # Print the priority level
    if thread_priority == QThread.InheritPriority:
        return "Thread priority: InheritPriority"
    elif thread_priority == QThread.IdlePriority:
        return "Thread priority: IdlePriority"
    elif thread_priority == QThread.LowestPriority:
        return "Thread priority: LowestPriority"
    elif thread_priority == QThread.NormalPriority:
        return "Thread priority: NormalPriority"
    elif thread_priority == QThread.HighPriority:
        return "Thread priority: HighPriority"
    elif thread_priority == QThread.Priority.HighestPriority:
        return "Thread priority: HighestPriority"
    elif thread_priority == QThread.TimeCriticalPriority:
        return "Thread priority: TimeCriticalPriority"


        
def isRegularTradingHours():
    current_time = datetime.now(timezone(Constants.NYC_TIMEZONE))
    
    # Check if today is a weekday (0=Monday, 6=Sunday)
    if current_time.weekday() >= 5:
        return False
    
    # Check time
    market_open_time = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close_time = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open_time <= current_time <= market_close_time

def standardBeginDateFor(end_date, bar_type):

    if (bar_type == Constants.ONE_MIN_BAR) or (bar_type == Constants.TWO_MIN_BAR) or (bar_type == Constants.THREE_MIN_BAR):
        begin_date = end_date - relativedelta(minutes=180)
        if begin_date.time() > time(20, 0) or begin_date.time() < time(4, 0):
            begin_date = begin_date - relativedelta(hours=8)
    elif bar_type == Constants.FIVE_MIN_BAR:
        begin_date = end_date - relativedelta(days=3)
    elif bar_type == Constants.FIFTEEN_MIN_BAR:
        begin_date = end_date - relativedelta(days=5)
    elif bar_type == Constants.HOUR_BAR or bar_type == Constants.FOUR_HOUR_BAR: #we don't fetch 4 hour bars, only in the form of hourly
        begin_date = end_date - relativedelta(days=7)
    elif bar_type == Constants.DAY_BAR:
        begin_date = end_date - relativedelta(days=700)
    elif bar_type == "1 week":
        begin_date = end_date - relativedelta(days=100)
    else:
        begin_date = end_date - relativedelta(days=1)

    return begin_date


def stringRange(req_range):
    if req_range is None:
        return "Empty range"
    return f"from: {req_range[0].strftime('%Y-%m-%d %H:%M:%S')} to {req_range[1].strftime('%Y-%m-%d %H:%M:%S')}"


def dateToReadableString(date):
    return date.strftime(Constants.READABLE_DATE_FORMAT)


def floatFromString(str_flt, default=0.0):
    try:
        return float(str_flt)
    except ValueError:
        return default


def getLowsHighsCount(stock_frame):

    lows, highs = getFilteredArrays(stock_frame, count=50)

    last_high = highs[-1]
    last_low = lows[-1]
    
        #up stair count
    increasing_low_mask = lows >= np.roll(lows, 1)  #we do a shifted comparison
    increasing_low_rev = increasing_low_mask[::-1]  #its easier to look at the first than the last, so we reverse
    increasing_low_indices = np.where(np.logical_not(increasing_low_rev)) #we want the indices of the False values as they indicate transitions
    if len(increasing_low_indices[0]) == 0: increasing_low_count = 0
    else: increasing_low_count = increasing_low_indices[0][0] + 1
    low_move = 100*(last_high-lows[-increasing_low_count])/lows[-increasing_low_count]
    from_low_move = {'start': lows[-increasing_low_count], 'level': last_low, 'apex': last_high, 'move': low_move, 'count': increasing_low_count}

        #down stair count (seems a bit repetitive, should just be one function taking either <= or >=)
    decreasing_high_mask = highs <= np.roll(highs, 1)
    decreasing_high_rev = decreasing_high_mask[::-1]
    decreasing_high_indices = np.where(np.logical_not(decreasing_high_rev))
    if len(decreasing_high_indices[0]) == 0: decreasing_high_count = 0
    else: decreasing_high_count = decreasing_high_indices[0][0] + 1
    high_move = 100*(last_low-highs[-decreasing_high_count])/highs[-decreasing_high_count]
    from_high_move = {'start': highs[-decreasing_high_count], 'level': last_high, 'apex': last_low, 'move': high_move, 'count': decreasing_high_count}

    inner_bar_index = np.where(np.logical_not(np.logical_and(decreasing_high_rev, increasing_low_rev)))
    if len(inner_bar_index[0]) == 0: inner_bar_count = 0
    else: inner_bar_count = inner_bar_index[0][0]
    inner_bar_specs = {'count': inner_bar_count}

    return from_low_move, from_high_move, inner_bar_specs


def getFilteredArrays(stock_frame, count):
    lows = stock_frame[Constants.LOW].to_numpy()[-count:]
    highs = stock_frame[Constants.HIGH].to_numpy()[-count:]

    return lows, highs

def greatherThan(value_1, value_2): return value_1 > value_2
def smallerThan(value_1, value_2): return value_1 < value_2 


def addEMAColumns(stock_frame, for_periods=[12, 26], from_index=None):
    column_names, ema_columns = getEMAColumns(stock_frame, for_periods, from_index)
    stock_frame[column_names] = np.column_stack(ema_columns)
    return stock_frame


def getEMAColumns(stock_frame, periods, from_index):

    columns = []
    column_names = []
    for period in periods:
        emas = pd.Series.ewm(stock_frame[Constants.CLOSE], alpha=2/(1+period)).mean() #, alpha=1/(1+period)
        smoothed_ema_sma = emas.rolling(window=5).mean()
        column_names.append('ema_' + str(period))
        columns.append(emas.to_numpy())
    return column_names, columns


def addRSIsEMAs(stock_frame, from_index=None):
    updated_indices, up_emas, down_emas = getUpDownEMAColumns(stock_frame, from_index)
    
    up_emas = up_emas.to_numpy()
    down_emas = down_emas.to_numpy()
    rsi = calculateRSIfromEMAs(up_emas, down_emas)
    
    stock_frame.loc[updated_indices, ['up_ema', 'down_ema', 'rsi']] = np.column_stack([up_emas, down_emas, rsi])
    
        #we want to remove any NaNs, not sure if this is still necesarry 
    if len(stock_frame['rsi']) != 0:
        stock_frame['rsi'] = stock_frame['rsi'].ffill()
        stock_frame['rsi'] = stock_frame['rsi'].round(1)

    return stock_frame


def calculateRSIfromEMAs(up_emas, down_emas):
    RS = (up_emas/down_emas)
    rsi = 100 - 100/(1+RS)
    return rsi


def getUpDownEMAColumns(stock_frame, from_index=None):

        #if have calculated EMAs before we just want to supplement what's there
    up_ema_column_exists = ('up_ema' in stock_frame.columns) and (stock_frame.iloc[0]['up_ema'] == 0.001)
    down_ema_column_exists = ('down_ema' in stock_frame.columns) and (stock_frame.iloc[0]['down_ema'] == 0.001)
    if up_ema_column_exists and down_ema_column_exists:
        return calculateUpDownEMAsFromIndex(stock_frame, from_index)
    else:
        return calculateUpDownEMAsFromScratch(stock_frame)


def calculateUpDownEMAsFromScratch(stock_frame):
    closes = stock_frame[Constants.CLOSE]
    indices = stock_frame.index
    up_emas, down_emas = calculateUpDownEMAs(closes)
    return indices, up_emas, down_emas


def calculateUpDownEMAs(closes, period=14):

        #we need up and down movements to calculate emas
    ups, downs = getUpsAndDownsSeries(closes)
        #pandas provides the fastest way to calculate emas
    up_emas = pd.Series.ewm(ups, alpha=1/period).mean()
    up_emas.iloc[:14] = 0.001     #we don't want the initial NaN, we also don't want zero, because it doesnt divide
    down_emas = pd.Series.ewm(downs, alpha=1/period).mean()
    down_emas.iloc[:14] = 0.001   #we don't want the initial NaN

    return up_emas, down_emas
    

def calculateUpDownEMAsFromIndex(stock_frame, from_index):
    
        #we only want to recalculate those emas that are necesarry
    alpha = 1/14
    recalc_size = min(100, len(stock_frame))

    integer_index = getStartRecalcIndex(stock_frame, from_index)
    if integer_index < 10:
        return calculateUpDownEMAsFromScratch(stock_frame)
    else:
            #we need up and down movements to calculate emas
        last_closes = stock_frame.iloc[max(0,(integer_index-recalc_size)):][Constants.CLOSE]
        ups, downs = getUpsAndDownsSeries(last_closes)
            #pandas provides the fastest way to calculate emas
        up_emas = pd.Series.ewm(ups, alpha=alpha).mean()
        down_emas = pd.Series.ewm(downs, alpha=alpha).mean()

        return last_closes.index[recalc_size:], up_emas[recalc_size:], down_emas[recalc_size:]


def getStartRecalcIndex(stock_frame, from_index):
    
      #at the least we want to recalculate the last two values
    indexer = len(stock_frame)-2

      #if we have a from index we want to see if we need to go further back
    if from_index is not None:
        try:
            from_int_index = stock_frame.index.get_loc(from_index)
            indexer = min(indexer, from_int_index)
        except KeyError:
            print(f"FROM INDEX not found {from_index}")
      
        
        #finally we want to make sure there are no NaNs that may need recomputing
    first_up_nan = stock_frame['up_ema'].isna().idxmax()
    first_down_nan = stock_frame['down_ema'].isna().idxmax()
    if first_up_nan < first_down_nan:
        smaller_selection = stock_frame.index < first_up_nan
    else:
        smaller_selection = stock_frame.index < first_down_nan

    if len(smaller_selection) > 0:

        true_value_set = np.where(smaller_selection)[0]
        if len(true_value_set) > 0:
            from_int_index = true_value_set.max()
            indexer = min(indexer, from_int_index)

    return indexer
# def calculateEMAsFrom(stock_frame, from_index):
    
#         #we only want to recalculate those emas that are necesarry
#     alpha = 1/14
#     integer_index = getStartRecalcIndex(stock_frame, from_index)
    
#     if integer_index < 10:
#         return calculateEMAsFromScratch(stock_frame)
#     else:
#             #we need to go back one more close to determine ups and downs
#         last_closes = stock_frame.iloc[(integer_index-1):][Constants.CLOSE]
#         ups, downs = getUpsAndDownsNumpy(last_closes)
        
#         ups = ups[1:]   #and cut off again
#         up_emas = stock_frame['up_ema'].to_numpy()
#         updatable_up_emas = up_emas[(integer_index-1):]

#         for up_index in range(len(ups)):
#             updatable_up_emas[up_index+1] = ups[up_index] * alpha + (1 - alpha) * updatable_up_emas[up_index]

#         downs = downs[1:]   #and cut off again
#         down_emas = stock_frame['down_ema'].to_numpy()
#         updatable_down_emas = down_emas[(integer_index-1):]

#         for down_index in range(len(downs)):
#             updatable_down_emas[down_index+1] = downs[down_index] * alpha + (1 - alpha) * updatable_down_emas[down_index]

#         return last_closes.index, updatable_up_emas, updatable_down_emas


def getTradingHours(bar_type, regular_hours):
    if regular_hours:
        if bar_type == Constants.HOUR_BAR:            
            start_time = '09:00:00'
            end_time = '15:59:30'
        else:
            start_time = '09:30:00'
            end_time = '15:59:00'
    else:
        start_time = '04:00:00'
        end_time = '19:59:00'
        
    return start_time, end_time


def getUpsAndDownsNumpy(closes):
    diffs = closes.diff()

    ups = diffs.to_numpy(copy=True)
    downs = diffs.to_numpy(copy=True)
    ups[ups < 0] = 0
    downs[downs > 0] = 0
    downs *= -1

    return ups, downs


def getUpsAndDownsSeries(closes):
    diffs = closes.diff()

    ups = diffs.copy()
    downs = diffs.copy()
    ups[ups < 0] = 0
    downs[downs > 0] = 0
    downs *= -1

    return ups, downs

# def getEma(prices, days=14, counter=0):
#     if len(prices) > days and counter < 150:
#         counter += 1
#         alpha = 1/days
#         return prices[-1] * alpha + (1 - alpha) * getEma(prices[:-1], days, counter)
#     else:
#         return prices.mean()


# def calculateNextEMA(last_price, previous_ema, period=14):

#     return last_price * alpha + (1 - alpha) * previous_ema


def getExpirationString(expiration_date):
    datetime_obj = datetime.strptime(expiration_date, '%Y%m%d')
    return datetime_obj.date().strftime("%d %B %Y")


def getDaysTillExpiration(expiration_date):
    #TODO This one is called an aweful lot
    datetime_obj = datetime.strptime(expiration_date, '%Y%m%d').date()
    today = datetime.now(utc).date()
    return (datetime_obj - today).days




def calculateCorrelation(frame_1, frame_2):
    r = np.corrcoef(np.vstack((frame_1, frame_2)))

    return r[1,0]


def findNearest(any_array, value):
    np_array = np.asarray(any_array)
    np_array = np.nan_to_num(np_array, nan=np.inf)
    idx = (np.abs(np_array - value)).argmin()
    closest_value = np_array[idx]
    return idx, closest_value

