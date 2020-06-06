from app.logger import sendDebug, sendInfo, sendError, sendCritical

def test_sendDebug():
    assert sendDebug("TEST LOG", papertrail=False) == None
    
def test_sendInfo():
    assert sendInfo("TEST LOG", papertrail=False) == None

def test_sendError():
    assert sendError("TEST LOG", papertrail=False) == None

def test_sendCritical():
    assert sendCritical("TEST LOG", papertrail=False) == None
