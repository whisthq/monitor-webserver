from app.logger import sendDebug, sendInfo, sendError, sendCritical


def test_sendDebug():
    assert sendDebug("TEST LOG", upload_logs_to_cloud=False) == None


def test_sendInfo():
    assert sendInfo("TEST LOG", upload_logs_to_cloud=False) == None


def test_sendError():
    assert sendError("TEST LOG", upload_logs_to_cloud=False) == None


def test_sendCritical():
    assert sendCritical("TEST LOG", upload_logs_to_cloud=False) == None
