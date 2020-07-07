from app.imports import *
from app.logger import *
from app.utils import *

# Create db engine object
ENGINE = sqlalchemy.create_engine(
    os.getenv("DATABASE_URL"), echo=False, pool_pre_ping=True
)

# Get Azure clients
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
credentials = ServicePrincipalCredentials(
    client_id=os.getenv("AZURE_CLIENT_ID"),
    secret=os.getenv("AZURE_CLIENT_SECRET"),
    tenant=os.getenv("AZURE_TENANT_ID"),
)
RCLIENT = ResourceManagementClient(credentials, subscription_id)
CCLIENT = ComputeManagementClient(credentials, subscription_id)
NCLIENT = NetworkManagementClient(credentials, subscription_id)


def cleanFetchedSQL(out):
    """Takes the result of a sql fetch query, and returns it as a list or dictionary

    Args:
        out (obj): The sqlalchemy return

    Returns:
        dict, list: Data in dict or list format
    """
    if out:
        is_list = isinstance(out, list)
        if is_list:
            return [dict(row) for row in out]
        else:
            return dict(out)
    return None


def checkWinlogon(vm_name, devEnv="prod"):
    """Checks if a vm is ready to connect

    Args:
        vm_name (str): Name of the vm to check

    Returns:
        bool: True if vm is ready to connect
    """
    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )

    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
        SELECT * FROM v_ms WHERE "vm_name" = :vm_name
        """
    )
    params = {"vm_name": vm_name}

    with ENGINE.connect() as conn:
        vm = cleanFetchedSQL(conn.execute(command, **params).fetchone())
        conn.close()
        if vm:
            return dateToUnix(getToday()) - vm["ready_to_connect"] < 10
        return None


def createTemporaryLock(vm_name, minutes, devEnv="prod"):
    """Sets the temporary lock field for a vm

    Args:
        vm_name (str): The name of the vm to temporarily lock
        minutes (int): Minutes to lock for
        ID (int, optional): Papertrail logging ID. Defaults to -1.
    """

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )

    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    temporary_lock = shiftUnixByMinutes(dateToUnix(getToday()), minutes)

    command = text(
        """
        UPDATE v_ms
        SET "temporary_lock" = :temporary_lock
        WHERE
        "vm_name" = :vm_name
        """
    )

    params = {"vm_name": vm_name, "temporary_lock": temporary_lock}

    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()

    sendInfo(
        "Temporary lock created for VM {} for {} minutes".format(vm_name, str(minutes)),
    )


def vmReadyToConnect(vm_name, ready, devEnv="prod"):
    """Sets the vm's ready_to_connect field

    Args:
        vm_name (str): Name of the vm
        ready (boolean): True for ready to connect
    """
    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )

    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    if ready:
        current = dateToUnix(getToday())

        command = text(
            """
            UPDATE v_ms
            SET "ready_to_connect" = :current
            WHERE
            "vm_name" = :vm_name
            """
        )
        params = {"vm_name": vm_name, "current": current}

        with ENGINE.connect() as conn:
            conn.execute(command, **params)
            conn.close()


def reportError(service):
    """"Logs an error message with datetime, service name, and traceback in log.txt file. Also send an error log to papertrail

    Args:
        service (str): The name of the service in which the error occured
    """
    error = traceback.format_exc()
    errorTime = datetime.now().strftime("%m-%d-%Y, %H:%M:%S")
    msg = "ERROR for " + service + ": " + error

    # Log error in log.txt
    # file = open("log.txt", "a")
    # file.write(errorTime + " " + msg)
    # file.close()

    # Send log to Papertrail
    sendError(msg)


def fetchAllVms(devEnv="prod"):
    """Fetches all the vms in the v_ms sql table

    Returns:
        list: List of all vms
    """

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
            SELECT * FROM v_ms
            """
    )
    params = {}
    with ENGINE.connect() as conn:
        vms_info = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return vms_info


def fetchDevVms(devEnv="prod"):
    """Returns a list of all vm names that are under dev

    Returns:
        Arr[obj]: An array of the vm names
    """

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
        SELECT vm_name FROM v_ms
        WHERE dev = true
        """
    )
    params = {}

    with ENGINE.connect() as conn:
        vms = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return vms
    return None


def updateVMState(vm_name, state, devEnv="prod"):
    """Updates the state column of the vm in the v_ms sql table

    Args:
        vm_name (str): Name of the vm to update
        state (str): The new state of the vm
    """
    sendInfo("Updating state for VM " + vm_name + " to " + state)

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
        UPDATE v_ms
        SET state = :state
        WHERE
           "vm_name" = :vm_name
        """
    )
    params = {"vm_name": vm_name, "state": state}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def updateDiskState(disk_name, state, devEnv="prod"):
    """Updates the state of a disk in the disks sql table

    Args:
        disk_name (str): Name of the disk to update
        state (str): The new state of the disk
    """
    sendInfo("Updating state for disk " + disk_name + " to " + state)

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )

    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
        UPDATE disks
        SET state = :state
        WHERE
        "disk_name" = :disk_name
        """
    )
    params = {"state": state, "disk_name": disk_name}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def getMostRecentActivity(username, devEnv="prod"):
    """Gets the last activity of a user

    Args:
        username (str): Username of the user

    Returns:
        dict: The latest activity of the user
    """
    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )

    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
        SELECT *
        FROM login_history
        WHERE "username" = :username
        ORDER BY timestamp DESC LIMIT 1
        """
    )

    params = {"username": username}

    with ENGINE.connect() as conn:
        activity = cleanFetchedSQL(conn.execute(command, **params).fetchone())
        return activity


def lockVM(vm_name, lock, devEnv="prod"):
    """Locks/unlocks a vm. A vm entry with lock set to True prevents other processes from changing that entry.

    Args:
        vm_name (str): The name of the vm to lock
        lock (bool): True for lock
    """

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    if lock:
        sendInfo("Locking VM " + vm_name)
    else:
        sendInfo("Unlocking VM " + vm_name)

    command = text(
        """
        UPDATE v_ms
        SET "lock" = :lock, "last_updated" = :last_updated
        WHERE
           "vm_name" = :vm_name
        """
    )
    last_updated = datetime.now().strftime("%m/%d/%Y, %H:%M")
    params = {"vm_name": vm_name, "lock": lock, "last_updated": last_updated}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def fetchAllDisks(devEnv="prod"):
    """Fetches all the disks

    Returns:
        arr[dict]: An array of all the disks in the disks sql table
    """

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
            SELECT * FROM disks
            """
    )
    params = {}
    with ENGINE.connect() as conn:
        disks = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return disks


def deleteDiskFromTable(disk_name, devEnv="prod"):
    """Deletes a disk from the disks sql table

    Args:
        disk_name (str): The name of the disk to delete
    """
    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
        DELETE FROM disks WHERE "disk_name" = :disk_name 
        """
    )
    params = {"disk_name": disk_name}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def deleteVmFromTable(vm_name, devEnv="prod"):
    """Deletes a vm from the v_ms sql table

    Args:
        vm_name (str): The name of the vm to delete
    """

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
        DELETE FROM v_ms WHERE "vm_name" = :vm_name 
        """
    )
    params = {"vm_name": vm_name}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


# Gets all VMs from database with specified location and state and OS
def getVMLocationState(location, state, operatingSys=None, devEnv="prod"):
    """Gets all vms in location with availability state

    Args:
        staging (bool): Whether or not to use the staging db
        location (str): The Azure region to look in
        state (str): The state to look for (ie "RUNNING_AVAILABLE", "DEALLOCATED")

    Returns:
        array: An array of all vms that satisfy the query
    """
    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    nowTime = datetime.now().timestamp()

    if operatingSys:
        command = text(
            """
            SELECT * 
            FROM v_ms 
            WHERE ("location" = :location AND "state" = :state AND "dev" = 'false' AND "os" = :os)
            AND ("temporary_lock" IS NULL OR "temporary_lock" < :timestamp)
            """
        )
    else:
        command = text(
            """
            SELECT * 
            FROM v_ms 
            WHERE ("location" = :location AND "state" = :state AND "dev" = 'false')
            AND ("temporary_lock" IS NULL OR "temporary_lock" < :timestamp)
            """
        )

    params = {
        "location": location,
        "timestamp": nowTime,
        "state": state,
        "os": operatingSys,
    }

    with ENGINE.connect() as conn:
        vms = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return vms


def addReportTable(
    ts, totalDealloc, logons, logoffs, vms, users, liveUsers, devEnv="prod"
):
    """Counts statistics of the whole Fractal system
    
    Args:
        ts (str): The datetime formatted as mm-dd-yyyy, hh:mm:ss in 24h format
        totalDealloc (int): Total number of deallocs since timestamp
        logons (int): Total number of logons since timestamp
        logoffs (int): Total number of logoffs since timestamp
        vms (int): Total number of VMs across the whole system
        users (int): Total number of users across the whole system
        liveUsers (int): Total number of users currently logged on
    """
    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
        INSERT INTO status_report("timestamp", "total_vms_deallocated", "logons", "logoffs", "users_online", "number_users_eastus", "number_users_southcentralus", "number_users_northcentralus", "eastus_available", "eastus_unavailable", "eastus_deallocated", "northcentralus_available", "northcentralus_unavailable", "northcentralus_deallocated", "southcentralus_available", "southcentralus_unavailable", "southcentralus_deallocated") 
        VALUES(:timestamp, :total_vms_deallocated, :logons, :logoffs, :users_online, :number_users_eastus, :number_users_southcentralus, :number_users_northcentralus, :eastus_available, :eastus_unavailable, :eastus_deallocated, :northcentralus_available, :northcentralus_unavailable, :northcentralus_deallocated, :southcentralus_available, :southcentralus_unavailable, :southcentralus_deallocated)
        """
    )
    params = {
        "timestamp": ts,
        "total_vms_deallocated": totalDealloc,
        "logons": logons,
        "logoffs": logoffs,
        "users_online": liveUsers,
        "number_users_eastus": users["eastus"],
        "number_users_southcentralus": users["southcentralus"],
        "number_users_northcentralus": users["northcentralus"],
        "eastus_available": vms["eastus"]["available"],
        "eastus_unavailable": vms["eastus"]["unavailable"],
        "eastus_deallocated": vms["eastus"]["deallocated"],
        "northcentralus_available": vms["northcentralus"]["available"],
        "northcentralus_unavailable": vms["northcentralus"]["unavailable"],
        "northcentralus_deallocated": vms["northcentralus"]["deallocated"],
        "southcentralus_available": vms["southcentralus"]["available"],
        "southcentralus_unavailable": vms["southcentralus"]["unavailable"],
        "southcentralus_deallocated": vms["southcentralus"]["deallocated"],
    }
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def getLogons(timestamp, action, devEnv="prod"):
    """Counts the number of times users have done an action action, since timestamp

    Args:
        timestamp (str): The datetime formatted as mm-dd-yyyy, hh:mm:ss in 24h format
        action (str): ['logoff', 'logon']

    Returns:
        int: The # of actions
    """

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
        SELECT COUNT(*)
        FROM login_history
        WHERE "action" = :action AND "timestamp" > :timestamp
        """
    )

    params = {"timestamp": timestamp, "action": action}

    with ENGINE.connect() as conn:
        activity = cleanFetchedSQL(conn.execute(command, **params).fetchone())
        return activity


def fetchExpiredLogs(expiry, devEnv="prod"):
    """Fetches all the logs

    Returns:
        arr[dict]: An array of all the logs in the logs sql table
    """

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
            SELECT * FROM logs
            WHERE last_updated < :expiry
            """
    )
    params = {"expiry": expiry}
    with ENGINE.connect() as conn:
        logs = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return logs


def fetchStingyCustomers(devEnv="prod"):
    aWeekAgo = dateimte.timestamp(datetime.now() - datetime.timedelta(days=7))

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )
    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    command = text(
        """
            SELECT username FROM customers
            WHERE paid = false AND trial_end < :expiry
        """
    )
    params = {"expiry": aWeekAgo}
    with ENGINE.connect() as conn:
        customers = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return customers
