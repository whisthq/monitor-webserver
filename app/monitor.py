from app.imports import *
from app.helpers.sql import *
from app.helpers.vms import *

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

# Threshold for min number of available VMs per region and OS
REGION_THRESHOLD = {
    "staging": {"Windows": 0, "Linux": 0},
    "prod": {"Windows": 1, "Linux": 0},
}
# The regions we care about
REGIONS = ["eastus", "northcentralus", "southcentralus"]
# The operating systems we care about
VM_OS = ["Windows", "Linux"]

# Report variables
timesDeallocated = 0

# Nightime shutoff
TEST_SHUTOFF = False


def monitorVMs(devEnv):
    """Deallocates any VM that has been running for over 30 minutes while user has been logged off

    Args:
        staging (bool): Whether to monitor staging or prod db
    """
    sendDebug("Monitoring " + devEnv + " VMs...")
    azureGroup = (
        os.getenv("STAGING_GROUP") if devEnv == "staging" else os.getenv("VM_GROUP")
    )

    global timesDeallocated
    freeVmsByRegion = {}
    for region in REGIONS:
        regionVms = getVMLocationState(
            location=region, state="RUNNING_AVAILABLE", devEnv=devEnv
        )
        if not regionVms:
            freeVmsByRegion[region] = 0
        else:
            freeVmsByRegion[region] = len(regionVms)

    vms = fetchAllVms(devEnv)

    azureVms = []
    for azureVm in CCLIENT.virtual_machines.list(resource_group_name=azureGroup):
        azureVms.append(azureVm.name)

    for vm in vms:
        try:
            if vm["vm_name"] not in azureVms:
                deleteVmFromTable(vm["vm_name"], devEnv)
                sendInfo("Deleted nonexistent VM " + vm["vm_name"] + " from database")
            else:
                # Update the database vm state
                # Get VM state
                vm_state = CCLIENT.virtual_machines.instance_view(
                    resource_group_name=azureGroup, vm_name=vm["vm_name"]
                )
                # Compare with database and update if there's a disreptancy
                power_state = vm_state.statuses[1].code

                if "stopped" in power_state:
                    if vm["state"] != "STOPPED":
                        updateVMState(vm["vm_name"], "STOPPED", devEnv)
                    if vm["lock"]:
                        lockVM(vm["vm_name"], False)
                elif "deallocated" in power_state:
                    if vm["state"] != "DEALLOCATED":
                        updateVMState(vm["vm_name"], "DEALLOCATED", devEnv)
                    if vm["lock"]:
                        lockVM(vm["vm_name"], False)
                if not vm["lock"]:
                    if "starting" in power_state:
                        if vm["state"] != "STARTING":
                            updateVMState(vm["vm_name"], "STARTING", devEnv)
                    elif "stopping" in power_state:
                        if vm["state"] != "STOPPING":
                            updateVMState(vm["vm_name"], "STOPPING", devEnv)
                    elif "deallocating" in power_state:
                        if vm["state"] != "DEALLOCATING":
                            updateVMState(vm["vm_name"], "DEALLOCATING", devEnv)

                # Automatically deallocate VMs on standby
                if "running" in vm_state.statuses[1].code:
                    shutdown = False
                    if not vm["username"] or not vm["state"]:
                        shutdown = True

                    if not vm["last_updated"]:
                        shutdown = True
                    else:
                        lastActive = datetime.strptime(
                            vm["last_updated"], "%m/%d/%Y, %H:%M"
                        )
                        now = datetime.now()
                        if (
                            timedelta(minutes=30) <= now - lastActive
                            and vm["state"] == "RUNNING_AVAILABLE"
                        ):
                            shutdown = True

                    if vm["lock"]:
                        shutdown = False

                    if vm["dev"]:
                        shutdown = False

                    if vm["state"] is not None and vm["state"].endswith("ING"):
                        shutdown = False

                    if (
                        vm["location"] in freeVmsByRegion
                        and freeVmsByRegion[vm["location"]]
                        <= REGION_THRESHOLD[devEnv][vm["os"]]
                    ):
                        shutdown = False

                    if shutdown:
                        print(shutdown)
                        deallocVm(vm["vm_name"], devEnv)
                        if devEnv == "prod":
                            timesDeallocated += 1

        except:
            reportError("VM monitor for VM " + vm["vm_name"])
            # vm_state = CCLIENT.virtual_machines.instance_view(
            #     resource_group_name=os.environ['VM_GROUP'],
            #     vm_name=vm['vm_name']
            # )
            # print(vm_state)


def monitorDisks(devEnv):
    """Deletes nonexistent disks from table, and deletes disks marked as TO_BE_DELETED

    Args:
        staging (bool): Whether to monitor staging or prod db
    """
    sendDebug("Monitoring " + devEnv + " disks...")

    azureGroup = (
        os.getenv("STAGING_GROUP") if devEnv == "staging" else os.getenv("VM_GROUP")
    )
    dbDisks = fetchAllDisks(devEnv)

    azureDisks = []
    disks = CCLIENT.disks.list(resource_group_name=azureGroup)
    for disk in disks:
        azureDisks.append(disk.name)

    print("group: " + azureGroup)
    print("polisheddisk202_OsDisk_1_b2ec7e4c866d4b78ad0a870160e27ca9" in azureDisks)

    for dbDisk in dbDisks:
        try:
            if dbDisk["disk_name"] not in azureDisks:
                deleteDiskFromTable(dbDisk["disk_name"], devEnv)
                sendInfo(
                    "Deleted nonexistent disk "
                    + dbDisk["disk_name"]
                    + " from "
                    + devEnv
                    + " database"
                )
            elif not dbDisk["disk_name"].startswith("crimsonbonus543"):
                delete = False
                if dbDisk["state"] == "TO_BE_DELETED":
                    os_disk = CCLIENT.disks.get(azureGroup, dbDisk["disk_name"])
                    vm_name = os_disk.managed_by
                    if (
                        not vm_name
                    ):  # Disk is not attached to VM, go ahead and delete it.
                        if not dbDisk["delete_date"]:
                            delete = True
                        else:
                            expiryTime = datetime.strptime(
                                dbDisk["delete_date"], "%m/%d/%Y, %H:%M"
                            )
                            now = datetime.now()
                            if now > expiryTime:
                                delete = True

                if delete:
                    sendInfo(
                        "Automatically deleting Disk " + dbDisk["disk_name"] + "..."
                    )
                    async_disk_delete = CCLIENT.disks.delete(
                        azureGroup, dbDisk["disk_name"]
                    )
                    async_disk_delete.wait()

                    deleteDiskFromTable(dbDisk["disk_name"], devEnv)

                    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))

                    # Send email to support@fractalcomputers.com
                    title = "Automatically deleted disk for " + dbDisk["username"]
                    message = (
                        "The monitor webserver has automatically deleted disk "
                        + dbDisk["disk_name"]
                        + " for user "
                        + dbDisk["username"]
                    )
                    internal_message = SendGridMail(
                        from_email="noreply@fractalcomputers.com",
                        to_emails=["support@fractalcomputers.com"],
                        subject=title,
                        html_content=message,
                    )
                    response = sg.send(internal_message)

                    # Send email to user
                    currPath = os.path.abspath(os.path.dirname(sys.argv[0]))
                    path = os.path.join(currPath, "templates/disk_deleted.txt")
                    with open(path, "r") as template:
                        templateData = template.read()

                    title = "Your cloud PC has automatically been deleted"
                    internal_message = SendGridMail(
                        from_email="noreply@fractalcomputers.com",
                        to_emails=[dbDisk["username"]],
                        subject=title,
                        html_content=templateData,
                    )
                    response = sg.send(internal_message)

        except:
            reportError("Disk monitor for disk " + dbDisk["disk_name"])


def manageRegions(devEnv):
    """Increases available VMs for a region if the # of available VMs dips below a threshold

    Args:
        staging (bool): Whether to monitor staging or prod db
    """
    sendDebug("Monitoring " + devEnv + " regions...")
    azureGroup = (
        os.getenv("STAGING_GROUP") if devEnv == "staging" else os.getenv("VM_GROUP")
    )

    # TODO: Add region support
    for operatingSystem in VM_OS:
        if REGION_THRESHOLD[devEnv][operatingSystem] > 0:
            for location in REGIONS:
                try:
                    availableVms = getVMLocationState(
                        location, "RUNNING_AVAILABLE", operatingSystem, devEnv
                    )
                    if (
                        not availableVms
                        or len(availableVms) < REGION_THRESHOLD[devEnv][operatingSystem]
                    ):
                        deallocVms = getVMLocationState(
                            location, "DEALLOCATED", operatingSystem, devEnv
                        )
                        vmToAllocate = None
                        if deallocVms:
                            for vm in deallocVms:
                                # Get VM state
                                vm_state = CCLIENT.virtual_machines.instance_view(
                                    resource_group_name=azureGroup,
                                    vm_name=vm["vm_name"],
                                )
                                if "deallocated" in vm_state.statuses[1].code:
                                    vmToAllocate = vm["vm_name"]
                                    break

                        if vmToAllocate:  # Reallocate from VMs
                            sendInfo(
                                "Reallocating VM "
                                + vmToAllocate
                                + " in region "
                                + location
                                + " with os "
                                + operatingSystem
                            )
                            async_vm_alloc = CCLIENT.virtual_machines.start(
                                azureGroup, vmToAllocate
                            )
                            lockVM(vmToAllocate, True)
                            updateVMState(vm["vm_name"], "STARTING", devEnv)
                            async_vm_alloc.wait()
                            updateVMState(vm["vm_name"], "RUNNING_AVAILABLE", devEnv)
                            lockVM(vmToAllocate, False)
                        else:
                            sendInfo(
                                "Creating VM in region "
                                + location
                                + " with os "
                                + operatingSystem
                            )
                            createVM(
                                "standard_NV6_promo", location, operatingSystem, devEnv
                            )
                except:
                    reportError("Region monitor error for region " + location)


def nightToggle(devEnv):
    """Shuts off dev vms and region management between times EST 1am -> 7am in prod db
    """
    # TODO: Add support for both dbs
    global TEST_SHUTOFF

    if 5 <= datetime.utcnow().hour <= 11:
        if not TEST_SHUTOFF:
            sendInfo("Shutting off dev vms and region management for night time")
            for system in REGION_THRESHOLD:
                REGION_THRESHOLD[devEnv][system] = 0
            vms = fetchDevVms(devEnv)
            for vm in vms:
                deallocVm(vm["vm_name"], devEnv)
            TEST_SHUTOFF = True
    elif TEST_SHUTOFF:
        sendInfo("Resuming region management")
        REGION_THRESHOLD[devEnv]["Windows"] = 1
        TEST_SHUTOFF = False


def monitorThread():
    while True:
        nightToggle("prod")
        monitorVMs("prod")
        manageRegions("prod")
        # monitorLogins()
        monitorDisks("prod")
        time.sleep(10)


def stagingMonitorThread():
    while True:
        monitorVMs("staging")
        manageRegions("staging")
        monitorDisks("staging")
        time.sleep(10)


def reportThread():
    global timesDeallocated
    while True:
        timesDeallocated = 0
        time.sleep(60 * 60)

        timestamp = int(time.time())
        vmByRegion = {
            "eastus": {"available": 0, "unavailable": 0, "deallocated": 0},
            "southcentralus": {"available": 0, "unavailable": 0, "deallocated": 0},
            "northcentralus": {"available": 0, "unavailable": 0, "deallocated": 0},
        }
        users = {
            "eastus": 0,
            "southcentralus": 0,
            "northcentralus": 0,
        }
        liveUsers = 0
        oneHourAgo = (datetime.now() - timedelta(hours=1)).strftime(
            "%m-%d-%Y, %H:%M:%S"
        )
        logons = getLogons(oneHourAgo, "logon")["count"]
        logoffs = getLogons(oneHourAgo, "logoff")["count"]
        vms = fetchAllVms()
        for vm in vms:
            if vm["location"] in REGIONS:
                if "DEALLOCATED" in vm["state"]:
                    vmByRegion[vm["location"]]["deallocated"] += 1
                elif "RUNNING_AVAILABLE" in vm["state"]:
                    vmByRegion[vm["location"]]["available"] += 1
                elif "RUNNING_UNAVAILABLE" in vm["state"]:
                    vmByRegion[vm["location"]]["unavailable"] += 1
                    liveUsers += 1
                if vm["username"]:
                    users[vm["location"]] += 1

        try:
            addReportTable(
                timestamp,
                timesDeallocated,
                logons,
                logoffs,
                vmByRegion,
                users,
                liveUsers,
            )
            sendInfo("Generated hourly report")
        except:
            reportError("Report gen")


if __name__ == "__main__":
    t1 = threading.Thread(target=monitorThread)
    t2 = threading.Thread(target=reportThread)
    t3 = threading.Thread(target=stagingMonitorThread)

    # Reset log file
    # open("log.txt", "w").close()

    t1.start()
    t2.start()
    t3.start()
