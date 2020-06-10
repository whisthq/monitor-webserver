from app import *

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


def reportError(service):
    """"Logs an error message with datetime, service name, and traceback in log.txt file. Also send an error log to papertrail

    Args:
        service (str): The name of the service in which the error occured
    """
    error = traceback.format_exc()
    errorTime = datetime.now(datetime.timezone.utc).strftime("%m-%d-%Y, %H:%M:%S")
    msg = "ERROR for " + service + ": " + error

    # Log error in log.txt
    # file = open("log.txt", "a")
    # file.write(errorTime + " " + msg)
    # file.close()

    # Send log to Papertrail
    sendError(msg)

    # Send error email to logs@fractalcomputers.com
    # title = 'Error in monitoring service: [' + service + ']'
    # message = error + "\n Occured at " + errorTime
    # internal_message = SendGridMail(
    #     from_email='jonathan@fractalcomputers.com',
    #     to_emails=['logs@fractalcomputers.com'],
    #     subject=title,
    #     html_content=message
    # )
    # try:
    #     sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
    #     response = sg.send(internal_message)
    # except:
    #     file = open("log.txt", "a")
    #     file.write(datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S') +
    #                " ERROR while reporting error: " + traceback.format_exc())
    #     file.close()


def fetchAllVms():
    """Fetches all the vms in the v_ms sql table

    Returns:
        list: List of all vms
    """
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


def getVM(vm_name):
    """Fetches a vm object from Azure sdk

    Args:
        vm_name (str): Name of the vm to look for

    Returns:
        VirtualMachine: The virtual machine object (https://docs.microsoft.com/en-us/rest/api/compute/virtualmachines/get#virtualmachine)
    """
    try:
        virtual_machine = CCLIENT.virtual_machines.get(os.getenv("VM_GROUP"), vm_name)
        return virtual_machine
    except:
        return None


def updateVMState(vm_name, state):
    """Updates the state column of the vm in the v_ms sql table

    Args:
        vm_name (str): Name of the vm to update
        state (str): The new state of the vm
    """
    sendInfo("Updating state for VM " + vm_name + " to " + state)
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


def updateDiskState(disk_name, state):
    """Updates the state of a disk in the disks sql table

    Args:
        disk_name (str): Name of the disk to update
        state (str): The new state of the disk
    """
    sendInfo("Updating state for disk " + disk_name + " to " + state)
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


def getMostRecentActivity(username):
    """Gets the last activity of a user

    Args:
        username (str): Username of the user

    Returns:
        dict: The latest activity of the user
    """
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


def lockVM(vm_name, lock):
    """Locks/unlocks a vm. A vm entry with lock set to True prevents other processes from changing that entry.

    Args:
        vm_name (str): The name of the vm to lock
        lock (bool): True for lock
    """

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
    last_updated = datetime.now(datetime.timezone.utc).strftime("%m/%d/%Y, %H:%M")
    params = {"vm_name": vm_name, "lock": lock, "last_updated": last_updated}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def fetchAllDisks():
    """Fetches all the disks

    Returns:
        arr[dict]: An array of all the disks in the disks sql table
    """
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


def deleteDiskFromTable(disk_name):
    """Deletes a disk from the disks sql table

    Args:
        disk_name (str): The name of the disk to delete
    """
    command = text(
        """
        DELETE FROM disks WHERE "disk_name" = :disk_name 
        """
    )
    params = {"disk_name": disk_name}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def deleteVmFromTable(vm_name):
    """Deletes a vm from the v_ms sql table

    Args:
        vm_name (str): The name of the vm to delete
    """
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
def getVMLocationState(location, state, operatingSys=None):
    """Gets all vms in location with availability state

    Args:
        location (str): The Azure region to look in
        state (str): The state to look for (ie "RUNNING_AVAILABLE", "DEALLOCATED")

    Returns:
        array: An array of all vms that satisfy the query
    """

    nowTime = datetime.now(datetime.timezone.utc).timestamp()

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


def addReportTable(ts, totalDealloc, logons, logoffs, vms, users, liveUsers):
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


def getLogons(timestamp, action):
    """Counts the number of times users have done an action action, since timestamp

    Args:
        timestamp (str): The datetime formatted as mm-dd-yyyy, hh:mm:ss in 24h format
        action (str): ['logoff', 'logon']

    Returns:
        int: The # of actions
    """
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
