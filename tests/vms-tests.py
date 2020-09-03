from app.helpers.vms import (
    checkDev,
    waitForWinlogon,
    sendVMStartCommand,
    deallocVm,
    fractalVMStart,
    getVM,
    createVMParameters,
    createVM,
    getIP,
    updateVMIP,
    updateVMLocation,
    updateVMOS,
    fetchVMCredentials,
    lockVMAndUpdate,
    genHaiku,
    genVMName,
    createNic,
)


def test_checkDev():
    assert checkDev("dev-nv6") == True  # Nick's VM


def test_waitForWinlogon():
    # can't really be unit tested
    assert True


def test_sendVMStartCommand():
    # can't really be unit tested
    assert True


def test_deallocVm():
    # can't really be unit tested
    assert True


def test_fractalVMStart():
    # can't really be unit tested
    assert True


def test_getVM():
    assert getVM("dev-nv6") != None  # Nick's VM


def test_createVMParameters():
    # can't really be unit tested
    assert True


def test_createVM():
    # can't really be unit tested
    assert True


def test_getIP():
    assert isinstance(getIP(getVM("dev-nv6")), str)  # Nick's VM


def test_updateVMIP():
    # can't really be unit tested
    assert True


def test_updateVMLocation():
    # can't really be unit tested
    assert True


def test_updateVMOS():
    # can't really be unit tested
    assert True


def test_fetchVMCredentials():
    assert isinstance(
        fetchVMCredentials("dev-nv6"),
        dict,
    )  # Nick's VM


def test_lockVMAndUpdate():
    # can't really be unit tested
    assert True


def test_genHaiku():
    assert isinstance(genHaiku(1), list)
    assert isinstance(genHaiku(5), list)
    assert isinstance(genHaiku(15), list)


def test_genVMName():
    assert isinstance(genVMName(), str)


def test_createNic():
    # can't really be unit tested
    assert True
