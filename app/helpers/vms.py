from app.imports import *
from app.logger import *
from app.helpers.sql import *
from app.utils import *

# Create db engine object
ENGINE = sqlalchemy.create_engine(
    os.getenv("DATABASE_URL"), echo=False, pool_pre_ping=True
)
Session = sessionmaker(bind=ENGINE, autocommit=False)

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


def checkDev(vm_name):
    """Checks to see if a vm is in dev mode

    Args:
        vm_name (str): Name of vm to check

    Returns:
        bool: True if vm is in dev mode, False otherwise
    """
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
            return vm["dev"]
        return None


def waitForWinlogon(vm_name):
    """Periodically checks and sleeps until winlogon succeeds

    Args:
        vm_name (str): Name of the vm
        ID (int, optional): Unique papertrail logging id. Defaults to -1.

    Returns:
        int: 1 for success, -1 for fail
    """
    ready = checkWinlogon(vm_name)

    num_tries = 0

    if ready:
        sendInfo("VM {} has Winlogoned successfully".format(vm_name))
        return 1

    if checkDev(vm_name):
        sendInfo(
            "VM {} is a DEV machine. Bypassing Winlogon. Sleeping for 50 seconds before returning.".format(
                vm_name
            ),
        )
        time.sleep(50)
        return 1

    while not ready:
        sendWarning("Waiting for VM {} to Winlogon".format(vm_name))
        time.sleep(5)
        ready = checkWinlogon(vm_name)
        num_tries += 1

        if num_tries > 30:
            sendError("Waited too long for winlogon. Sending failure message.")
            return -1

    sendInfo(
        "VM {} has Winlogon successfully after {} tries".format(
            vm_name, str(num_tries)
        ),
    )

    return 1


def sendVMStartCommand(vm_name, needs_restart, needs_winlogon, ID=-1, s=None):
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

        def boot_if_necessary(vm_name, needs_restart, ID=-1, s=s):

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
                if s:
                    s.update_state(
                        state="PENDING",
                        meta={
                            "msg": "Your cloud PC is powered off. Powering on (this could take a few minutes)."
                        },
                    )

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

                sendInfo(async_vm_start.result(timeout=180))

                if s:
                    s.update_state(
                        state="PENDING",
                        meta={"msg": "Your cloud PC was started successfully."},
                    )

                sendInfo("VM {} started successfully".format(vm_name))

                return 1

            if needs_restart:
                if s:
                    s.update_state(
                        state="PENDING",
                        meta={
                            "msg": "Your cloud PC needs to be restarted. Restarting (this will take no more than a minute)."
                        },
                    )

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

                if s:
                    s.update_state(
                        state="PENDING",
                        meta={"msg": "Your cloud PC was restarted successfully."},
                    )

                sendInfo("VM {} restarted successfully".format(vm_name))

                return 1

            return 1

        def checkFirstTime(disk_name):
            command = text(
                """
                SELECT * FROM disks WHERE "disk_name" = :disk_name
                """
            )
            params = {"disk_name": disk_name}

            with ENGINE.connect() as conn:
                disk_info = cleanFetchedSQL(conn.execute(command, **params).fetchone())
                conn.close()
            if disk_info:
                return disk_info["first_time"]

            return False

        def changeFirstTime(disk_name, first_time=False):
            command = text(
                """
                UPDATE disks SET "first_time" = :first_time WHERE "disk_name" = :disk_name
                """
            )
            params = {"disk_name": disk_name, "first_time": first_time}

            with ENGINE.connect() as conn:
                conn.execute(command, **params)
                conn.close()

        if s:
            s.update_state(
                state="PENDING",
                meta={"msg": "Cloud PC started executing boot request."},
            )

        disk_name = fetchVMCredentials(vm_name)["disk_name"]
        first_time = checkFirstTime(disk_name)
        num_boots = 1 if not first_time else 2

        if first_time:
            print("First time! Going to boot {} times".format(str(num_boots)))

        for i in range(0, num_boots):
            if i == 1 and s:
                s.update_state(
                    state="PENDING",
                    meta={
                        "msg": "Since this is your first time logging on, we're running a few extra tests to ensure stability. Please allow a few extra minutes."
                    },
                )
                time.sleep(60)

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

            if s:
                s.update_state(
                    state="PENDING",
                    meta={"msg": "Cloud PC still executing boot request."},
                )

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

            if needs_winlogon:
                winlogon = waitForWinlogon(vm_name)
                while winlogon < 0:
                    boot_if_necessary(vm_name, True)
                    if s:
                        s.update_state(
                            state="PENDING",
                            meta={
                                "msg": "Logging you into your cloud PC. This should take less than two minutes."
                            },
                        )
                    winlogon = waitForWinlogon(vm_name)

                if s:
                    s.update_state(
                        state="PENDING",
                        meta={"msg": "Logged into your cloud PC successfully."},
                    )

                lockVMAndUpdate(
                    vm_name,
                    "RUNNING_AVAILABLE",
                    False,
                    temporary_lock=1,
                    change_last_updated=True,
                    verbose=False,
                )

            if i == 1:
                changeFirstTime(disk_name)

                if s:
                    s.update_state(
                        state="PENDING",
                        meta={
                            "msg": "Running final performance checks. This will take two minutes."
                        },
                    )
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


def fractalVMStart(vm_name, needs_restart=False, needs_winlogon=False):
    """Bullies Azure into actually starting the vm by repeatedly calling sendVMStartCommand if necessary (big brain thoughts from Ming)

    Args:
        vm_name (str): Name of the vm to start
        needs_restart (bool, optional): Whether the vm needs to restart after. Defaults to False.

    Returns:
        int: 1 for success, -1 for failure
    """
    sendInfo("Begin repeatedly calling sendVMStartCommand for vm {}".format(vm_name))

    started = False
    start_attempts = 0

    # We will try to start/restart the VM and wait for it three times in total before giving up
    while not started and start_attempts < 3:
        start_command_tries = 0
        while (
            sendVMStartCommand(vm_name, needs_restart, needs_winlogon) < 0
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
    sendDebug("Waiting on async_vm_creation")
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

    sendDebug("Waiting on async_vm_extension")
    async_vm_extension.wait()

    vm = getVM(vmParameters["vm_name"])
    vm_ip = getIP(vm)
    updateVMIP(vmParameters["vm_name"], vm_ip)
    updateVMState(vmParameters["vm_name"], "RUNNING_AVAILABLE")
    updateVMLocation(vmParameters["vm_name"], location)
    updateVMOS(vmParameters["vm_name"], operating_system)

    sendInfo("SUCCESS: VM {} created and updated".format(vmName))
    vmObj = CCLIENT.virtual_machines.get(
        os.environ["VM_GROUP"], vmParameters["vm_name"]
    )
    disk_name = vmObj.storageProfile.osDisk.name
    updateDiskState(disk_name, "TO_BE_DELETED")
    sendInfo("Marking osDisk of {} to TO_BE_DELETED".format(vmName))

    return fetchVMCredentials(vmParameters["vm_name"])


def getIP(vm):
    """Gets the IP address for a vm

    Args:
        vm (vm object name): The name of the VM to find the IP of

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


def updateVMOS(vm_name, operating_system):
    """Updates the OS of the vm entry in the v_ms sql table
    Args:
        vm_name (str): Name of vm of interest
        operating_system (str): The OSof the vm
    """
    sendInfo("Updating OS for VM {} to {} in SQL".format(vm_name, operating_system))
    command = text(
        """
        UPDATE v_ms
        SET os = :operating_system
        WHERE
        "vm_name" = :vm_name
        """
    )
    params = {"vm_name": vm_name, "operating_system": operating_system}
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


def lockVMAndUpdate(vm_name, state, lock, temporary_lock, change_last_updated, verbose):
    MAX_LOCK_TIME = 10

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
