from pytz import timezone, utc

from dataHandling.Constants import Constants
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, time, date

def getCurrentUtcTime():
    return datetime.now(utc).replace(microsecond=0)


def getLocalizedDt(dt, time_zone):
    localized_tz = timezone(time_zone)
    return localized_tz.localize(dt)


def convertToUtcTimestamp(dt_localized):
    dt_utc = dt_localized.astimezone(utc)
    return int(dt_utc.timestamp())


def todayDT():
	return datetime.combine(date.today(), time(0,0,0))


def dtFromDate(date):
	return datetime.combine(date, time(0, 0,0))


def utcLocalize(date_time_obj):
	return utc.localize(date_time_obj)



def utcDtFromIBString(date_string):

    # Split the string into date, time, and timezone parts
    date_time_part, tz_part = date_string.rsplit(' ', 1)

    # Combine the date and time parts and convert to a datetime object
    date_time = datetime.strptime(date_time_part, "%Y%m%d %H:%M:%S")

    # Localize the datetime object to the specified timezone
    tz = timezone(tz_part)
    date_time = tz.localize(date_time)

    # Convert to UTC
    utc_time = date_time.astimezone(timezone('UTC'))

    return utc_time


def barStartTime(time_index, bar_type):
    return time_index
    # if bar_type == Constants.FIVE_MIN_BAR or bar_type == Constants.FIFTEEN_MIN_BAR or bar_type == Constants.HOUR_BAR or bar_type == Constants.FOUR_HOUR_BAR:
    #     return time_index
    # elif bar_type == Constants.DAY_BAR:
    #     return time_index + relativedelta(minutes=570)


def barEndTime(time_index, bar_type,):
    return time_index + relativedelta(minutes=MINUTES_PER_BAR[bar_type])
    
    # if bar_type == Constants.FIVE_MIN_BAR or bar_type == Constants.FIFTEEN_MIN_BAR or bar_type == Constants.HOUR_BAR or bar_type == Constants.FOUR_HOUR_BAR:
    #     return time_index + relativedelta(minutes=self.bar_minutes[bar_type])
    # elif bar_type == Constants.DAY_BAR:
    #     return time_index + relativedelta(minutes=960)


def subtract_days(count):
    return int((datetime.utcnow() - relativedelta(days=count)).timestamp())

def subtract_weeks(count):
    return int((datetime.utcnow() - relativedelta(weeks=count)).timestamp())

def subtract_months(count):
    return int((datetime.utcnow() - relativedelta(months=count)).timestamp())




def dateFromString(date_string, sep=' '):
    return datetime.strptime(date_string, f"%Y%m%d{sep}%H:%M:%S")

# def dateFromStringTZ(date_string):
#     return datetime.strptime(date_string, Constants.TIME_FORMAT)

def dateToString(date):
    return date.strftime(Constants.TIME_FORMAT_NO_TZ)


def pdDateFromIBString(date_string, bar_type, instrument_tz):

    if bar_type == Constants.DAY_BAR:
        date_time = pd.to_datetime(date_string, format="%Y%m%d")
        date_time = date_time.tz_localize(instrument_tz)
    else:
        dt_part, tz_part = date_string.rsplit(' ', 1)
        date_time = pd.to_datetime(dt_part, format="%Y%m%d %H:%M:%S")
        date_time = date_time.tz_localize(tz_part)
    
    return date_time, int(date_time.astimezone(utc).timestamp())

