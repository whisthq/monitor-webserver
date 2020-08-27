from .imports import *


def dateToUnix(date):
    """Converts a date to rounded Unix format

    Args:
        date (float): POSIX timestamp as float
    """
    return round(date.timestamp())  # rounds to 0 digits by default


def getToday():
    """Retrieve today's date as a POSIX timestamp float

    Args:
        N/A
    """
    aware = datetime.now()
    return aware


def shiftUnixByMinutes(utc, num_minutes):
    """Shift Unix timestamp by num_minutes

    Args:
        utc (int): Unix timestamp as integer
        num_minutes (int): Number of minutes to shift by
    """
    date = unixToDate(utc)
    return round(dateToUnix(date + relativedelta(minutes=num_minutes)))


def unixToDate(utc):
    """Convert Unix timestamp to POSIX datetime format

    Args:
        utc (int): Unix timestamp to convert to POSIX datetime
    """
    return datetime.fromtimestamp(utc)
