from app.utils import (
    dateToUnix,
    getToday,
    shiftUnixByMinutes,
    unixToDate,
)


def test_dateToUnix(date):
    assert isinstance(dateToUnix(getToday()), int)


def test_getToday():
    assert isinstance(getToday(), datetime.date)


def test_shiftUnixByMinutes(utc, num_minutes):
    assert shiftUnixByMinutes(dateToUnix(getToday()), 60) == (
        int(dateToUnix(getToday())) + 60
    )


def test_unixToDate(utc):
    assert isinstance(unixToDate(dateToUnix(getToday())), datetime.date)
