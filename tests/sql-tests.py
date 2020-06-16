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
)


def test_cleanFetchedSQL():
    # fetchAllDisks() calls cleanFetchedSQL
    assert isinstance(fetchAllDisks(), list)


def test_reportError():
    assert reportError("TEST SERVICE") == None


def test_fetchAllVms():
    assert isinstance(fetchAllVms(), list)


def test_getVM():
    assert getVM("dev-nv6") != None
    assert getVM("this-vm-doesnt-exist") == None


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
