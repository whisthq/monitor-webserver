from app.logger import *

def test_sendDebug():
    assert sendDebug("TEST LOG", papertrail=False) == "TEST LOG"
    
def test_sendInfo():
    assert sendInfo("TEST LOG", papertrail=False) == "TEST LOG"

def test_sendError():
    assert sendError("TEST LOG", papertrail=False) == "TEST LOG"

def test_sendCritical():
    assert sendCritical("TEST LOG", papertrail=False) == "TEST LOG"
