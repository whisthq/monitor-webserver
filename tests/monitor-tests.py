from app.monitor import (
    monitorVMs,
    monitorLogins,
    monitorDisks,
    manageRegions,
    monitorThread,
    reportThread,
)


def test_monitorVMs():

    assert sendDebug("TEST LOG", papertrail=False) == None


def test_monitorLogins():
    assert sendInfo("TEST LOG", papertrail=False) == None


def test_monitorDisks():
    assert sendError("TEST LOG", papertrail=False) == None


def test_manageRegions():
    assert sendCritical("TEST LOG", papertrail=False) == None


def test_monitorThread():
    assert sendCritical("TEST LOG", papertrail=False) == None


def test_reportThread():
    assert sendCritical("TEST LOG", papertrail=False) == None
