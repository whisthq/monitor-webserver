from .imports import *


def dateToUnix(date):
    """Converts a date to rounded Unix format

    Args:
        date (float): POSIX timestamp as float

    Returns:
        int: Unix timestamp as integer
    """
    return round(date.timestamp())  # rounds to 0 digits by default


def getToday():
    """Retrieve today's date as a POSIX timestamp float

    Args:
        N/A

    Returns:
        float: Today's POSIX timestamp as float
    """
    aware = datetime.now()
    return aware


def shiftUnixByMinutes(utc, num_minutes):
    """Shift Unix timestamp by num_minutes

    Args:
        utc (int): Unix timestamp as integer
        num_minutes (int): Number of minutes to shift by

    Returns:
        int: Unix date format shifted by num_minutes
    """
    date = unixToDate(utc)
    return round(dateToUnix(date + relativedelta(minutes=num_minutes)))


def unixToDate(utc):
    """Convert Unix timestamp to POSIX datetime format

    Args:
        utc (int): Unix timestamp to convert to POSIX datetime

    Returns:
        float: POSIX datetime format
    """
    return datetime.fromtimestamp(utc)
