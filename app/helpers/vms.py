from app.imports import *
from app.logger import *

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

def sendVMStartCommand(vm_name, needs_restart, needs_winlogon):
    """Starts a vm

    Args:
        vm_name (str): The name of the vm to start
        needs_restart (bool): Whether the vm needs to restart after
        ID (int, optional): Unique papertrail logging id. Defaults to -1.

    Returns:
        int: 1 for success, -1 for fail
    """
    sendInfo("Sending VM start command for vm {}".format(vm_name))

    try:

        def boot_if_necessary(vm_name, needs_restart, ID, s=s):
            power_state = "PowerState/deallocated"
            vm_state = CCLIENT.virtual_machines.instance_view(
                resource_group_name=os.getenv("VM_GROUP"), vm_name=vm_name
            )

            try:
                power_state = vm_state.statuses[1].code
            except Exception as e:
                sendCritical(str(e))
                pass

            if "stop" in power_state or "dealloc" in power_state:
                sendInfo(
                    "VM {} currently in state {}. Setting Winlogon to False".format(
                        vm_name, power_state
                    ),
                )
                vmReadyToConnect(vm_name, False)

                sendInfo("Starting VM {}".format(vm_name))
                lockVMAndUpdate(
                    vm_name,
                    "STARTING",
                    True,
                    temporary_lock=12,
                    change_last_updated=True,
                    verbose=False,
                )

                async_vm_start = CCLIENT.virtual_machines.start(
                    os.environ.get("VM_GROUP"), vm_name
                )

                createTemporaryLock(vm_name, 12)

                sendInfo( async_vm_start.result(timeout = 180))

                if s:
                    s.update_state(
                        state="PENDING",
                        meta={"msg": "Your cloud PC was started successfully."},
                    )

                sendInfo( "VM {} started successfully".format(vm_name))

            if needs_restart:
                sendInfo(
                    "VM {} needs to restart. Setting Winlogon to False".format(vm_name),
                )
                vmReadyToConnect(vm_name, False)

                lockVMAndUpdate(
                    vm_name,
                    "RESTARTING",
                    True,
                    temporary_lock=12,
                    change_last_updated=True,
                    verbose=False,
                )

                async_vm_restart = CCLIENT.virtual_machines.restart(
                    os.environ.get("VM_GROUP"), vm_name
                )

                createTemporaryLock(vm_name, 12)

                sendInfo(async_vm_restart.result())
                sendInfo( "VM {} restarted successfully".format(vm_name))

        def checkFirstTime(disk_name):
            session = Session()
            command = text(
                """
                SELECT * FROM disks WHERE "disk_name" = :disk_name
                """
            )
            params = {"disk_name": disk_name}

            disk_info = cleanFetchedSQL(session.execute(command, params).fetchone())

            if disk_info:
                session.commit()
                session.close()
                return disk_info["first_time"]

            session.commit()
            session.close()

            return False

        def changeFirstTime(disk_name, first_time=False):
            session = Session()
            command = text(
                """
                UPDATE disks SET "first_time" = :first_time WHERE "disk_name" = :disk_name
                """
            )
            params = {"disk_name": disk_name, "first_time": first_time}

            session.execute(command, params)
            session.commit()
            session.close()

        disk_name = fetchVMCredentials(vm_name)["disk_name"]
        first_time = checkFirstTime(disk_name)
        num_boots = 1 if not first_time else 2

        if first_time:
            print("First time! Going to boot {} times".format(str(num_boots)))

        for i in range(0, num_boots):
            lockVMAndUpdate(
                vm_name,
                "ATTACHING",
                True,
                temporary_lock=None,
                change_last_updated=True,
                verbose=False,
            )

            if i == 1:
                needs_restart = True

            boot_if_necessary(vm_name, needs_restart)
            lockVMAndUpdate(
                vm_name,
                "RUNNING_AVAILABLE",
                False,
                temporary_lock=None,
                change_last_updated=True,
                verbose=False,
            )

            if s:
                s.update_state(
                    state="PENDING",
                    meta={
                        "msg": "Logging you into your cloud PC. This should take less than two minutes."
                    },
                )

            winlogon = waitForWinlogon(vm_name)
            while winlogon < 0:
                boot_if_necessary(vm_name, True)
                winlogon = waitForWinlogon(vm_name)

            if i == 1:
                changeFirstTime(disk_name)
                time.sleep(60)

                lockVMAndUpdate(
                    vm_name,
                    "RUNNING_AVAILABLE",
                    False,
                    temporary_lock=3,
                    change_last_updated=True,
                    verbose=False,
                )

        return 1
    except Exception as e:
        sendCritical(str(e))
        return -1

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