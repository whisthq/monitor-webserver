from .imports import *


def dateToUnix(date):
    return round(date.timestamp())


def getToday():
    aware = datetime.now()
    return aware
