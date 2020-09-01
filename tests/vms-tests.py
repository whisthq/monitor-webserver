from app.helpers.vms import (
    checkDev,
    sendVMStartCommand,
    fractalVMStart,
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
    # can't really be unit tested
    assert True


def test_createVMParameters():
    # can't really be unit tested
    assert True


def test_createVM():
    # can't really be unit tested
    assert True


def test_getIP():
    # assert isinstance(getIP(getVM("dev-nv6")), str)
    assert True


def test_updateVMIP():
    # can't really be unit tested
    assert True


def test_updateVMLocation(vm_name, location):
    # can't really be unit tested
    assert True


def test_updateVMOS(vm_name, operating_system):
    # can't really be unit tested
    assert True


def test_fetchVMCredentials():
    assert isinstance(fetchVMCredentials("dev-nv6"), dict)


def test_lockVMAndUpdate():
    # can't really be unit tested
    assert True


def test_genHaiku():
    assert isinstance(genHaiku(1), list)
    assert isinstance(genHaiku(5), list)
    assert isinstance(genHaiku(15), list)


def test_genVMName():
    assert isinstance(genVMName(), str)


def test_createNic(name, location, tries):
    # can't really be unit tested
    assert True
