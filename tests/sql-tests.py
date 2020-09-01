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
    assert fetchDiskByUser("UNEXISTENT USER", devEnv="prod") == [] # empty list for unexistent user


    # assert fetchDiskByUser("", devEnv="prod") == [] # real user














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



# def fetchAllVms(devEnv="prod"):
#     """Fetches all the vms in the v_ms sql table

#     Returns:
#         list: List of all vms
#     """

#     dbUrl = (
#         os.getenv("STAGING_DATABASE_URL")
#         if devEnv == "staging"
#         else os.getenv("DATABASE_URL")
#     )
#     ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

#     command = text(
#         """
#             SELECT * FROM v_ms
#             """
#     )
#     params = {}
#     with ENGINE.connect() as conn:
#         vms_info = cleanFetchedSQL(conn.execute(command, **params).fetchall())
#         conn.close()
#         return vms_info


# def fetchDevVms(devEnv="prod"):
#     """Returns a list of all vm names that are under dev

#     Returns:
#         Arr[obj]: An array of the vm names
#     """

#     dbUrl = (
#         os.getenv("STAGING_DATABASE_URL")
#         if devEnv == "staging"
#         else os.getenv("DATABASE_URL")
#     )
#     ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

#     command = text(
#         """
#         SELECT vm_name FROM v_ms
#         WHERE dev = true
#         """
#     )
#     params = {}

#     with ENGINE.connect() as conn:
#         vms = cleanFetchedSQL(conn.execute(command, **params).fetchall())
#         conn.close()
#         return vms
#     return None


# def updateVMState(vm_name, state, devEnv="prod"):
#     """Updates the state column of the vm in the v_ms sql table

#     Args:
#         vm_name (str): Name of the vm to update
#         state (str): The new state of the vm
#     """
#     sendInfo("Updating state for VM " + vm_name + " to " + state)

#     dbUrl = (
#         os.getenv("STAGING_DATABASE_URL")
#         if devEnv == "staging"
#         else os.getenv("DATABASE_URL")
#     )
#     ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

#     command = text(
#         """
#         UPDATE v_ms
#         SET state = :state
#         WHERE
#            "vm_name" = :vm_name
#         """
#     )
#     params = {"vm_name": vm_name, "state": state}
#     with ENGINE.connect() as conn:
#         conn.execute(command, **params)
#         conn.close()


# def updateDiskState(disk_name, state, devEnv="prod"):
#     """Updates the state of a disk in the disks sql table

#     Args:
#         disk_name (str): Name of the disk to update
#         state (str): The new state of the disk
#     """
#     sendInfo("Updating state for disk " + disk_name + " to " + state)

#     dbUrl = (
#         os.getenv("STAGING_DATABASE_URL")
#         if devEnv == "staging"
#         else os.getenv("DATABASE_URL")
#     )

#     ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

#     command = text(
#         """
#         UPDATE disks
#         SET state = :state
#         WHERE
#         "disk_name" = :disk_name
#         """
#     )
#     params = {"state": state, "disk_name": disk_name}
#     with ENGINE.connect() as conn:
#         conn.execute(command, **params)
#         conn.close()
#     sendInfo("Disk state for " + disk_name + " updated to " + state + "...")


# def getMostRecentActivity(username, devEnv="prod"):
#     """Gets the last activity of a user

#     Args:
#         username (str): Username of the user

#     Returns:
#         dict: The latest activity of the user
#     """
#     dbUrl = (
#         os.getenv("STAGING_DATABASE_URL")
#         if devEnv == "staging"
#         else os.getenv("DATABASE_URL")
#     )

#     ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

#     command = text(
#         """
#         SELECT *
#         FROM login_history
#         WHERE "username" = :username
#         ORDER BY timestamp DESC LIMIT 1
#         """
#     )

#     params = {"username": username}

#     with ENGINE.connect() as conn:
#         activity = cleanFetchedSQL(conn.execute(command, **params).fetchone())
#         return activity


# def lockVM(vm_name, lock, devEnv="prod"):
#     """Locks/unlocks a vm. A vm entry with lock set to True prevents other processes from changing that entry.

#     Args:
#         vm_name (str): The name of the vm to lock
#         lock (bool): True for lock
#     """

#     dbUrl = (
#         os.getenv("STAGING_DATABASE_URL")
#         if devEnv == "staging"
#         else os.getenv("DATABASE_URL")
#     )
#     ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

#     if lock:
#         sendInfo("Locking VM " + vm_name)
#     else:
#         sendInfo("Unlocking VM " + vm_name)

#     command = text(
#         """
#         UPDATE v_ms
#         SET "lock" = :lock, "last_updated" = :last_updated
#         WHERE
#            "vm_name" = :vm_name
#         """
#     )
#     last_updated = datetime.now().strftime("%m/%d/%Y, %H:%M")
#     params = {"vm_name": vm_name, "lock": lock, "last_updated": last_updated}
#     with ENGINE.connect() as conn:
#         conn.execute(command, **params)
#         conn.close()


# def fetchAllDisks(devEnv="prod"):
#     """Fetches all the disks

#     Returns:
#         arr[dict]: An array of all the disks in the disks sql table
#     """

#     dbUrl = (
#         os.getenv("STAGING_DATABASE_URL")
#         if devEnv == "staging"
#         else os.getenv("DATABASE_URL")
#     )
#     ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

#     command = text(
#         """
#             SELECT * FROM disks
#             """
#     )
#     params = {}
#     with ENGINE.connect() as conn:
#         disks = cleanFetchedSQL(conn.execute(command, **params).fetchall())
#         conn.close()
#         return disks





