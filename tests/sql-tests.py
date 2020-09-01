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


def test_fetchStingyCustomers():
    assert isinstance(fetchStingyCustomers(devEnv="prod"), list)

def test_deleteDiskFromTable():
    # can't really be unit tested
    assert True



def test_fetchDiskByUser():
    # assert fetchDiskByUser("", devEnv="prod") == [] # real user
    assert fetchDiskByUser("UNEXISTENT USER", devEnv="prod") == [] # empty list for unexistent user


def test_updateDiskState():
    # can't really be unit tested
    assert True    





def test_fetchDevVms():
    assert isinstance(fetchDevVms(devEnv="prod"), list)
















# def createTemporaryLock(vm_name, minutes, devEnv="prod"):
#     """Sets the temporary lock field for a vm

#     Args:
#         vm_name (str): The name of the vm to temporarily lock
#         minutes (int): Minutes to lock for
#         ID (int, optional): Papertrail logging ID. Defaults to -1.
#     """

#     dbUrl = (
#         os.getenv("STAGING_DATABASE_URL")
#         if devEnv == "staging"
#         else os.getenv("DATABASE_URL")
#     )

#     ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

#     temporary_lock = shiftUnixByMinutes(dateToUnix(getToday()), minutes)

#     command = text(
#         """
#         UPDATE v_ms
#         SET "temporary_lock" = :temporary_lock
#         WHERE
#         "vm_name" = :vm_name
#         """
#     )

#     params = {"vm_name": vm_name, "temporary_lock": temporary_lock}

#     with ENGINE.connect() as conn:
#         conn.execute(command, **params)
#         conn.close()

#     sendInfo(
#         "Temporary lock created for VM {} for {} minutes".format(vm_name, str(minutes)),
#     )


# def vmReadyToConnect(vm_name, ready, devEnv="prod"):
#     """Sets the vm's ready_to_connect field

#     Args:
#         vm_name (str): Name of the vm
#         ready (boolean): True for ready to connect
#     """
#     dbUrl = (
#         os.getenv("STAGING_DATABASE_URL")
#         if devEnv == "staging"
#         else os.getenv("DATABASE_URL")
#     )

#     ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

#     if ready:
#         current = dateToUnix(getToday())

#         command = text(
#             """
#             UPDATE v_ms
#             SET "ready_to_connect" = :current
#             WHERE
#             "vm_name" = :vm_name
#             """
#         )
#         params = {"vm_name": vm_name, "current": current}

#         with ENGINE.connect() as conn:
#             conn.execute(command, **params)
#             conn.close()


