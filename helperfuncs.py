from imports import *

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
        service (str): The name of the service in which the erorr occured
    """
    error = traceback.format_exc()
    errorTime = datetime.utcnow().strftime("%m-%d-%Y, %H:%M:%S")
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
    sendInfo("Automatically updating state for VM " + vm_name + " to " + state)
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


def getMostRecentActivity(username):
    """Gets the last activity of a user

    Args:
        username (str): Username of the user

    Returns:
        str: The latest activity of the user
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
    last_updated = datetime.utcnow().strftime("%m/%d/%Y, %H:%M")
    params = {"vm_name": vm_name, "lock": lock, "last_updated": last_updated}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def genHaiku(n):
    """Generates an array of haiku names (no more than 15 characters) using haikunator

    Args:
        n (int): Length of the array to generate

    Returns:
        arr: An array of haikus
    """
    haikunator = Haikunator()
    haikus = [
        haikunator.haikunate(delimiter="") + str(np.random.randint(0, 10000))
        for _ in range(0, n)
    ]
    haikus = [haiku[0 : np.min([15, len(haiku)])] for haiku in haikus]
    return haikus


def genVMName():
    """Generates a unique name for a vm

    Returns:
        str: The generated name
    """
    with ENGINE.connect() as conn:
        oldVMs = [cell[0] for cell in list(conn.execute('SELECT "vm_name" FROM v_ms'))]
        vmName = genHaiku(1)[0]
        while vmName in oldVMs:
            vmName = genHaiku(1)[0]
        return vmName


def createNic(name, location, tries):
    """Creates a network id

    Args:
        name (str): Name of the vm
        location (str): The azure region
        tries (int): The current number of tries

    Returns:
        dict: The network id object
    """
    vnetName, subnetName, ipName, nicName = (
        name + "_vnet",
        name + "_subnet",
        name + "_ip",
        name + "_nic",
    )
    try:
        async_vnet_creation = NCLIENT.virtual_networks.create_or_update(
            os.getenv("VM_GROUP"),
            vnetName,
            {
                "location": location,
                "address_space": {"address_prefixes": ["10.0.0.0/16"]},
            },
        )
        async_vnet_creation.wait()

        # Create Subnet
        async_subnet_creation = NCLIENT.subnets.create_or_update(
            os.getenv("VM_GROUP"),
            vnetName,
            subnetName,
            {"address_prefix": "10.0.0.0/24"},
        )
        subnet_info = async_subnet_creation.result()

        # Create public IP address
        public_ip_addess_params = {
            "location": location,
            "public_ip_allocation_method": "Static",
        }
        creation_result = NCLIENT.public_ip_addresses.create_or_update(
            os.getenv("VM_GROUP"), ipName, public_ip_addess_params
        )

        public_ip_address = NCLIENT.public_ip_addresses.get(
            os.getenv("VM_GROUP"), ipName
        )

        # Create NIC
        async_nic_creation = NCLIENT.network_interfaces.create_or_update(
            os.getenv("VM_GROUP"),
            nicName,
            {
                "location": location,
                "ip_configurations": [
                    {
                        "name": ipName,
                        "public_ip_address": public_ip_address,
                        "subnet": {"id": subnet_info.id},
                    }
                ],
            },
        )

        return async_nic_creation.result()
    except Exception as e:
        if tries < 5:
            # print(e)
            print("Trying again for createNic")
            time.sleep(3)
            return createNic(name, location, tries + 1)
        else:
            return None


def createVMParameters(vmName, nic_id, vm_size, location, operating_system="Windows"):
    """Adds a vm entry to the SQL database

    Parameters:
    vmName (str): The name of the VM to add
    nic_id (str): The vm's network interface ID
    vm_size (str): The type of vm in terms of specs(default is NV6)
    location (str): The Azure region of the vm
    operating_system (str): The operating system of the vm (default is 'Windows')

    Returns:
    dict: Parameters that will be used in Azure sdk
   """

    with ENGINE.connect() as conn:
        oldUserNames = [
            cell[0] for cell in list(conn.execute('SELECT "username" FROM v_ms'))
        ]
        userName = genHaiku(1)[0]
        while userName in oldUserNames:
            userName = genHaiku(1)

        vm_reference = (
            {
                "publisher": "MicrosoftWindowsDesktop",
                "offer": "Windows-10",
                "sku": "rs5-pro",
                "version": "latest",
            }
            if operating_system == "Windows"
            else {
                "publisher": "Canonical",
                "offer": "UbuntuServer",
                "sku": "18.04-LTS",
                "version": "latest",
            }
        )

        command = text(
            """
            INSERT INTO v_ms("vm_name", "disk_name")
            VALUES(:vmName, :disk_name)
            """
        )
        params = {"vmName": vmName, "username": userName, "disk_name": None}
        with ENGINE.connect() as conn:
            conn.execute(command, **params)
            conn.close()

            return {
                "params": {
                    "location": location,
                    "os_profile": {
                        "computer_name": vmName,
                        "admin_username": os.getenv("VM_GROUP"),
                        "admin_password": os.getenv("VM_PASSWORD"),
                    },
                    "hardware_profile": {"vm_size": vm_size},
                    "storage_profile": {
                        "image_reference": {
                            "publisher": vm_reference["publisher"],
                            "offer": vm_reference["offer"],
                            "sku": vm_reference["sku"],
                            "version": vm_reference["version"],
                        },
                        "os_disk": {
                            "os_type": operating_system,
                            "create_option": "FromImage",
                        },
                    },
                    "network_profile": {"network_interfaces": [{"id": nic_id,}]},
                },
                "vm_name": vmName,
            }


def getIP(vm):
    """Gets the IP address for a vm

    Args:
        vm (str): The name of the vm

    Returns:
        str: The ipv4 address
    """
    ni_reference = vm.network_profile.network_interfaces[0]
    ni_reference = ni_reference.id.split("/")
    ni_group = ni_reference[4]
    ni_name = ni_reference[8]

    net_interface = NCLIENT.network_interfaces.get(ni_group, ni_name)
    ip_reference = net_interface.ip_configurations[0].public_ip_address
    ip_reference = ip_reference.id.split("/")
    ip_group = ip_reference[4]
    ip_name = ip_reference[8]

    public_ip = NCLIENT.public_ip_addresses.get(ip_group, ip_name)
    return public_ip.ip_address


def updateVMIP(vm_name, ip):
    """Updates the ip address of a vm

    Args:
        vm_name (str): The name of the vm to update
        ip (str): The new ipv4 address
    """
    command = text(
        """
        UPDATE v_ms
        SET ip = :ip
        WHERE
           "vm_name" = :vm_name
        """
    )
    params = {"ip": ip, "vm_name": vm_name}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def updateVMLocation(vm_name, location):
    """Updates the location of the vm entry in the v_ms sql table

    Args:
        vm_name (str): Name of vm of interest
        location (str): The new region of the vm
    """
    command = text(
        """
        UPDATE v_ms
        SET location = :location
        WHERE
           "vm_name" = :vm_name
        """
    )
    params = {"vm_name": vm_name, "location": location}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def fetchVMCredentials(vm_name):
    """Fetches a vm from the v_ms sql table

    Args:
        vm_name (str): The name of the vm to fetch

    Returns:
        dict: An object respresenting the respective row in the table
    """
    command = text(
        """
        SELECT * FROM v_ms WHERE "vm_name" = :vm_name
        """
    )
    params = {"vm_name": vm_name}
    with ENGINE.connect() as conn:
        vm_info = cleanFetchedSQL(conn.execute(command, **params).fetchone())
        # Decode password
        conn.close()
        return vm_info


def createVM(vm_size, location, operating_system):
    """Creates a windows vm of size vm_size in Azure region location

	Args:
		vm_size (str): The size of the vm to create
		location (str): The Azure region

	Returns:
		dict: The dict representing the vm in the v_ms sql table
	"""
    sendInfo(
        "Creating VM of size {}, location {}, operating system {}".format(
            vm_size, location, operating_system
        ),
    )

    vmName = genVMName()
    nic = createNic(vmName, location, 0)
    if not nic:
        sendError("Nic does not exist, aborting")
        return
    vmParameters = createVMParameters(
        vmName, nic.id, vm_size, location, operating_system
    )
    async_vm_creation = CCLIENT.virtual_machines.create_or_update(
        os.environ["VM_GROUP"], vmParameters["vm_name"], vmParameters["params"]
    )
    sendDebug( "Waiting on async_vm_creation")
    async_vm_creation.wait()

    time.sleep(10)

    async_vm_start = CCLIENT.virtual_machines.start(
        os.environ["VM_GROUP"], vmParameters["vm_name"]
    )
    sendDebug("Waiting on async_vm_start")
    async_vm_start.wait()

    time.sleep(30)

    sendInfo("The VM created is called {}".format(vmParameters["vm_name"]))

    fractalVMStart(vmParameters["vm_name"], needs_winlogon=False)

    time.sleep(30)

    extension_parameters = (
        {
            "location": location,
            "publisher": "Microsoft.HpcCompute",
            "vm_extension_name": "NvidiaGpuDriverWindows",
            "virtual_machine_extension_type": "NvidiaGpuDriverWindows",
            "type_handler_version": "1.2",
        }
        if operating_system == "Windows"
        else {
            "location": location,
            "publisher": "Microsoft.HpcCompute",
            "vm_extension_name": "NvidiaGpuDriverLinux",
            "virtual_machine_extension_type": "NvidiaGpuDriverLinux",
            "type_handler_version": "1.2",
        }
    )

    async_vm_extension = CCLIENT.virtual_machine_extensions.create_or_update(
        os.environ["VM_GROUP"],
        vmParameters["vm_name"],
        extension_parameters["vm_extension_name"],
        extension_parameters,
    )

    sendDebug( "Waiting on async_vm_extension")
    async_vm_extension.wait()

    vm = getVM(vmParameters["vm_name"])
    vm_ip = getIP(vm)
    updateVMIP(vmParameters["vm_name"], vm_ip)
    updateVMState(vmParameters["vm_name"], "RUNNING_AVAILABLE")
    updateVMLocation(vmParameters["vm_name"], location)
    updateVMOS(vmParameters["vm_name"], operating_system)

    sendInfo( "SUCCESS: VM {} created and updated".format(vmName))

    return fetchVMCredentials(vmParameters["vm_name"])

def fractalVMStart(vm_name, needs_restart=False, needs_winlogon=True, s=None):
    """Bullies Azure into actually starting the vm by repeatedly calling sendVMStartCommand if necessary (big brain thoughts from Ming)

    Args:
        vm_name (str): Name of the vm to start
        needs_restart (bool, optional): Whether the vm needs to restart after. Defaults to False.
        ID (int, optional): Unique papertrail logging id. Defaults to -1.

    Returns:
        int: 1 for success, -1 for failure
    """
    sendInfo(
        "Begin repeatedly calling sendVMStartCommand for vm {}".format(vm_name)
    )

    started = False
    start_attempts = 0

    # We will try to start/restart the VM and wait for it three times in total before giving up
    while not started and start_attempts < 3:
        start_command_tries = 0

        # First, send a basic start or restart command. Try six times, if it fails, give up
        if s:
            s.update_state(
                state="PENDING",
                meta={"msg": "Cloud PC successfully received boot request."},
            )

        while (
            sendVMStartCommand(vm_name, needs_restart, needs_winlogon, s=s) < 0
            and start_command_tries < 6
        ):
            time.sleep(10)
            start_command_tries += 1

        if start_command_tries >= 6:
            return -1

        wake_retries = 0

        # After the VM has been started/restarted, query the state. Try 12 times for the state to be running. If it is not running,
        # give up and go to the top of the while loop to send another start/restart command
        vm_state = CCLIENT.virtual_machines.instance_view(
            resource_group_name=os.getenv("VM_GROUP"), vm_name=vm_name
        )

        # Success! VM is running and ready to use
        if "running" in vm_state.statuses[1].code:
            updateVMState(vm_name, "RUNNING_AVAILABLE")
            sendInfo("Running found in status of VM {}".format(vm_name))
            started = True
            return 1

        while not "running" in vm_state.statuses[1].code and wake_retries < 12:
            sendWarning(
                "VM state is currently in state {}, sleeping for 5 seconds and querying state again".format(
                    vm_state.statuses[1].code
                ),
            )
            time.sleep(5)
            vm_state = CCLIENT.virtual_machines.instance_view(
                resource_group_name=os.getenv("VM_GROUP"), vm_name=vm_name
            )

            # Success! VM is running and ready to use
            if "running" in vm_state.statuses[1].code:
                updateVMState(vm_name, "RUNNING_AVAILABLE")
                sendInfo(
                    "VM {} is running. State is {}".format(
                        vm_name, vm_state.statuses[1].code
                    ),
                )
                started = True
                return 1

            wake_retries += 1

        start_attempts += 1

    return -1


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
def getVMLocationState(location, state, os=None):
    """Gets all vms in location with availability state

    Args:
        location (str): The Azure region to look in
        state (str): The state to look for (ie "RUNNING_AVAILABLE", "DEALLOCATED")

    Returns:
        array: An array of all vms that satisfy the query
    """

    nowTime = datetime.utcnow().timestamp()

    if os:
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
    

    
    params = {"location": location, "timestamp": nowTime, "state": state, "os": os}
    with ENGINE.connect() as conn:
        vms = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return vms


def addReportTable(ts, deallocVm, totalDealloc, logons, logoffs, vms, users):
    command = text(
        """
        INSERT INTO status_report("timestamp", "deallocated_vms", "total_vms_deallocated", "logons", "logoffs", "number_users_eastus", "number_vms_eastus", "number_users_southcentralus", "number_vms_southcentralus", "number_users_northcentralus", "number_vms_northcentralus") 
        VALUES(:timestamp, :deallocated_vms, :total_vms_deallocated, :logons, :logoffs, :number_users_eastus, :number_vms_eastus, :number_users_southcentralus, :number_vms_southcentralus, :number_users_northcentralus, :number_vms_northcentralus)
        """
    )
    params = {
        "timestamp": ts,
        "deallocated_vms": deallocVm,
        "total_vms_deallocated": totalDealloc,
        "logons": logons,
        "logoffs": logoffs,
        "number_users_eastus": users["eastus"],
        "number_vms_eastus": vms["eastus"],
        "number_users_southcentralus": users["southcentralus"],
        "number_vms_southcentralus": vms["southcentralus"],
        "number_users_northcentralus": users["northcentralus"],
        "number_vms_northcentralus": vms["northcentralus"],
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

def lockVMAndUpdate(
    vm_name, state, lock, temporary_lock, change_last_updated, verbose, ID=-1
):
    MAX_LOCK_TIME = 10

    session = Session()

    command = text(
        """
        UPDATE v_ms SET state = :state, lock = :lock
        WHERE vm_name = :vm_name
        """
    )

    if temporary_lock:
        temporary_lock = min(MAX_LOCK_TIME, temporary_lock)
        temporary_lock = shiftUnixByMinutes(dateToUnix(getToday()), temporary_lock)

        command = text(
            """
            UPDATE v_ms SET state = :state, lock = :lock, temporary_lock = :temporary_lock
            WHERE vm_name = :vm_name
            """
        )

    params = {
        "vm_name": vm_name,
        "state": state,
        "lock": lock,
        "temporary_lock": temporary_lock,
    }

    session.execute(command, params)
    session.commit()
    session.close()
    
# Logging
class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True


syslog = SysLogHandler(address=(os.getenv("LOGGER_URL"), 44138))
syslog.addFilter(ContextFilter())

format = "%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] [MONITOR]: %(message)s"

formatter = logging.Formatter(format, datefmt="%b %d %H:%M:%S")
syslog.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(syslog)
logger.setLevel(logging.INFO)


def sendDebug(log, papertrail=True):
    """Logs debug messages

    Args:
        log (str): The message
        papertrail (bool, optional): Whether or not to send to papertrail. Defaults to True.
    """
    if papertrail:
        logger.debug(log)
    print(log)


def sendInfo(log, papertrail=True):
    """Logs info messages

    Args:
        log (str): The message
        papertrail (bool, optional): Whether or not to send to papertrail. Defaults to True.
    """
    if papertrail:
        logger.info(log)
    print(log)


def sendError(log, papertrail=True):
    """Logs errors

    Args:
        log (str): The message
        papertrail (bool, optional): Whether or not to send to papertrail. Defaults to True.
    """
    if papertrail:
        logger.error(log)
    print(log)


def sendCritical(log, papertrail=True):
    """Logs critical errors

    Args:
        log (str): The message
        papertrail (bool, optional): Whether or not to send to papertrail. Defaults to True.
    """
    if papertrail:
        logger.critical(log)
    print(log)

