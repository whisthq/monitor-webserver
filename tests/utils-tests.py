from app.utils import (
    dateToUnix,
    getToday,
    shiftUnixByMinutes,
    unixToDate,
)

import datetime


def test_dateToUnix():
    assert isinstance(dateToUnix(getToday()), int)


def test_getToday():
    assert isinstance(getToday(), datetime.date)


def test_shiftUnixByMinutes():
    assert isinstance(
        shiftUnixByMinutes(dateToUnix(getToday()), 60),
        int,
    )


def test_unixToDate():
    assert isinstance(
        unixToDate(dateToUnix(getToday())),
        datetime.date,
    )
