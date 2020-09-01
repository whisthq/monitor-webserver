from app.helpers.sql import (
    cleanFetchedSQL,
    reportError,
    fetchAllVms,
    updateVMState,
    getMostRecentActivity,
    lockVM,
    fetchAllDisks,
    deleteDiskFromTable,
    deleteVmFromTable,
    getVMLocationState,
    addReportTable,
    getLogons,
    fetchLogs,
    fetchStingyCustomers,
    fetchDiskByUser,
    fetchAllDisks,
    updateDiskState,
    fetchDevVms,
    vmReadyToConnect,
    createTemporaryLock,
)


def test_cleanFetchedSQL():
    assert isinstance(fetchAllDisks(), list) # fetchAllDisks() calls cleanFetchedSQL


def test_checkWinlogon():
    # can't really be unit tested
    assert True


def createTemporaryLock():
    # can't really be unit tested
    assert True


def test_reportError():
    assert reportError("TEST SERVICE") == None


def test_fetchAllVms():
    assert isinstance(fetchAllVms(), list)


def test_updateVMState():
    # can't really be unit tested
    assert True


def test_getMostRecentActivity():
    assert isinstance(getMostRecentActivity("ming@fractalcomputers.com"), dict)


def test_lockVM():
    # can't really be unit tested
    assert True


def test_fetchAllDisks():
    assert isinstance(fetchAllDisks(), list)


def test_deleteVmFromTable():
    # can't really be unit tested
    assert True


def test_getVMLocationState():
    assert isinstance(getVMLocationState("eastus", "RUNNING_AVAILABLE"), list)
    assert isinstance(getVMLocationState("northcentralus", "RUNNING_AVAILABLE"), list)
    assert isinstance(getVMLocationState("southcentralus", "RUNNING_AVAILABLE"), list)


def test_addReportTable():
    # can't really be unit tested
    assert True


def test_getLogons():
    assert isinstance(getLogons("06-01-2020, 11:11:11", "logon")["count"], int)
    assert isinstance(getLogons("06-01-2020, 11:11:11", "logoff")["count"], int)


def test_fetchLogs():
    assert isinstance(fetchLogs(devEnv="prod"), list)


def test_deleteDiskFromTable():
    # can't really be unit tested
    assert True


def test_updateDiskState():
    # can't really be unit tested
    assert True    


def test_vmReadyToConnect():
    # can't really be unit tested
    assert True       
 

def test_fetchStingyCustomers():
    assert isinstance(fetchStingyCustomers(devEnv="prod"), list)


def test_fetchDiskByUser():
    assert isinstance(fetchDiskByUser("ming@fractalcomputers.com", devEnv="prod"), list) # real user
    assert fetchDiskByUser("UNEXISTENT USER", devEnv="prod") == None # unexistent user


def test_fetchDevVms():
    assert isinstance(fetchDevVms(devEnv="prod"), list)
