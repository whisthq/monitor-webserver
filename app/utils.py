from .imports import *


def dateToUnix(date):
    return round(date.timestamp())


def getToday():
    aware = datetime.now()
    return aware

def shiftUnixByMinutes(utc, num_minutes):
    date = unixToDate(utc)
    return round(dateToUnix(date + relativedelta(minutes=num_minutes)))