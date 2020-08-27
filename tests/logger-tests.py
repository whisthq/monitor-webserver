from app.logger import sendDebug, sendInfo, sendError, sendCritical


def test_sendDebug():
    assert sendDebug("TEST LOG") == None


def test_sendInfo():
    assert sendInfo("TEST LOG") == None


def test_sendError():
    assert sendError("TEST LOG") == None
