from imports import *
from helperfuncs import *

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

# Threshold for min number of available VMs per region
REGION_THRESHOLD = 1
# The regions we care about
REGIONS = ["eastus", "northcentralus", "southcentralus"]

# Report variables
timesDeallocated = 0


# Deallocates any VM that has been running for over 30 minutes while user has been logged off


def monitorVMs():
    sendDebug("Monitoring VMs...")

    global timesDeallocated
    freeVmsByRegion = {}
    for region in REGIONS:
        regionVms = getVMLocationState(region, "available")
        if not regionVms:
            freeVmsByRegion[region] = 0
        else:
            freeVmsByRegion[region] = len(regionVms)

    vms = fetchAllVms()

    azureVms = []
    for azureVm in CCLIENT.virtual_machines.list_all():
        azureVms.append(azureVm.name)

    for vm in vms:
        try:
            if vm["vm_name"] not in azureVms:
                deleteVmFromTable(vm["vm_name"])
                sendInfo("Deleted nonexistent VM " + vm["vm_name"] + " from database")
            else:
                # Get VM state
                vm_state = CCLIENT.virtual_machines.instance_view(
                    resource_group_name=os.getenv("VM_GROUP"), vm_name=vm["vm_name"]
                )
                # Compare with database and update if there's a disreptancy
                power_state = vm_state.statuses[1].code
                if "starting" in power_state:
                    if vm["state"] != "STARTING":
                        updateVMState(vm["vm_name"], "STARTING")
                elif "stopping" in power_state:
                    if vm["state"] != "STOPPING":
                        updateVMState(vm["vm_name"], "STOPPING")
                elif "deallocating" in power_state:
                    if vm["state"] != "DEALLOCATING":
                        updateVMState(vm["vm_name"], "DEALLOCATING")
                elif "stopped" in power_state:
                    if vm["state"] != "STOPPED":
                        updateVMState(vm["vm_name"], "STOPPED")
                    if vm["lock"]:
                        lockVM(vm["vm_name"], False)
                elif "deallocated" in power_state:
                    if vm["state"] != "DEALLOCATED":
                        updateVMState(vm["vm_name"], "DEALLOCATED")
                    if vm["lock"]:
                        lockVM(vm["vm_name"], False)
                elif "running" not in power_state:
                    sendError(
                        "State "
                        + power_state
                        + " incompatible with VM "
                        + vm["vm_name"]
                    )

                # Automatically deallocate VMs on standby
                if "running" in vm_state.statuses[1].code:
                    shutdown = False
                    if not vm["username"]:
                        shutdown = True

                    if not vm["last_updated"]:
                        shutdown = True
                    else:
                        lastActive = datetime.strptime(
                            vm["last_updated"], "%m/%d/%Y, %H:%M"
                        )
                        now = datetime.utcnow()
                        if (
                            timedelta(minutes=30) <= now - lastActive
                            and vm["state"] == "RUNNING_AVAILABLE"
                        ):
                            shutdown = True

                    if vm["lock"]:
                        shutdown = False

                    if vm["dev"] and vm["os"] != "Linux":
                        shutdown = False

                    if vm["state"].endswith("ING"):
                        shutdown = False

                    if (
                        vm["location"] in freeVmsByRegion
                        and freeVmsByRegion[vm["location"]] <= REGION_THRESHOLD
                    ):
                        shutdown = False

                    if shutdown:
                        sendInfo(
                            "Automatically deallocating VM " + vm["vm_name"] + "..."
                        )
                        async_vm_deallocate = CCLIENT.virtual_machines.deallocate(
                            os.getenv("VM_GROUP"), vm["vm_name"]
                        )

                        lockVM(vm["vm_name"], True)
                        updateVMState(vm["vm_name"], "DEALLOCATING")
                        async_vm_deallocate.wait()
                        updateVMState(vm["vm_name"], "DEALLOCATED")
                        lockVM(vm["vm_name"], False)
                        timesDeallocated += 1

        except:
            reportError("VM monitor for VM " + vm["vm_name"])
            # vm_state = CCLIENT.virtual_machines.instance_view(
            #     resource_group_name=os.environ['VM_GROUP'],
            #     vm_name=vm['vm_name']
            # )
            # print(vm_state)


# Checks for disreptancies between VM availability and the user's login history


def monitorLogins():
    sendDebug("Monitoring user logins...")
    vms = fetchAllVms()
    for vm in vms:
        try:
            state = "NOT_RUNNING_UNAVAILABLE"
            update = False
            userActivity = getMostRecentActivity(vm["username"])
            if userActivity:
                if userActivity["action"] == "logoff" and "UNAVAILABLE" in vm["state"]:
                    state = vm["state"]
                    state = state[0 : state.rfind("_") + 1] + "AVAILABLE"
                    update = True
                elif (
                    userActivity["action"] == "logon"
                    and "UNAVAILABLE" not in vm["state"]
                ):
                    state = vm["state"]
                    state = state[0 : state.rfind("_") + 1] + "UNAVAILABLE"
                    update = True
            if update:
                updateVMState(vm["vm_name"], state)
                sendInfo("Updating state for VM " + vm["vm_name"] + " to " + state)
        except:
            reportError("Login monitor for VM " + vm["vm_name"])


# Monitors disks in db, and deletes any that have state set as TO_BE_DELETED


def monitorDisks():
    sendDebug("Monitoring disks...")

    dbDisks = fetchAllDisks()

    azureDisks = []
    disks = CCLIENT.disks.list(resource_group_name=os.getenv("VM_GROUP"))
    for disk in disks:
        azureDisks.append(disk.name)

    for dbDisk in dbDisks:
        try:
            if dbDisk["disk_name"] not in azureDisks:
                deleteDiskFromTable(dbDisk["disk_name"])
                sendInfo(
                    "Deleted nonexistent disk " + dbDisk["disk_name"] + " from database"
                )
            else:
                delete = False
                if dbDisk["state"] == "TO_BE_DELETED":
                    os_disk = CCLIENT.disks.get(
                        os.getenv("VM_GROUP"), dbDisk["disk_name"]
                    )
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
                            now = datetime.utcnow()
                            if now > expiryTime:
                                delete = True

                if delete:
                    sendInfo(
                        "Automatically deleting Disk " + dbDisk["disk_name"] + "..."
                    )
                    async_disk_delete = CCLIENT.disks.delete(
                        os.getenv("VM_GROUP"), dbDisk["disk_name"]
                    )
                    async_disk_delete.wait()

                    deleteDiskFromTable(dbDisk["disk_name"])

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


# Increases available VMs for a region if the # of available VMs dips below a threshold


def manageRegions():
    sendDebug("Monitoring regions...")
    for location in REGIONS:
        try:
            availableVms = getVMLocationState(location, "available")
            if not availableVms or len(availableVms) < REGION_THRESHOLD:
                unavailableVms = getVMLocationState(location, "unavailable")
                vmToAllocate = None
                if unavailableVms:
                    for vm in unavailableVms:
                        # Get VM state
                        vm_state = CCLIENT.virtual_machines.instance_view(
                            resource_group_name=os.getenv("VM_GROUP"),
                            vm_name=vm["vm_name"],
                        )
                        if "deallocated" in vm_state.statuses[1].code:
                            vmToAllocate = vm["vm_name"]
                            break

                if vmToAllocate:  # Reallocate from VMs
                    sendInfo(
                        "Reallocating VM " + vmToAllocate + " in region " + location
                    )
                    async_vm_alloc = CCLIENT.virtual_machines.start(
                        os.getenv("VM_GROUP"), vmToAllocate
                    )
                    lockVM(vmToAllocate, True)
                    updateVMState(vm["vm_name"], "STARTING")
                    async_vm_alloc.wait()
                    updateVMState(vm["vm_name"], "RUNNING_AVAILABLE")
                    lockVM(vmToAllocate, False)
                else:
                    sendInfo("Creating VM in region " + location)
                    createVM("Standard_NV6_Promo", location)
        except:
            reportError("Region monitor error for region " + location)


def monitorThread():
    while True:
        monitorVMs()
        manageRegions()
        # monitorLogins()
        monitorDisks()
        time.sleep(10)


def reportThread():
    global timesDeallocated
    while True:
        timesDeallocated = 0
        time.sleep(60 * 60)

        timestamp = datetime.utcnow().strftime("%m-%d-%Y, %H:%M:%S")
        vmByRegion = {
            "eastus": 0,
            "southcentralus": 0,
            "northcentralus": 0,
        }
        users = {
            "eastus": 0,
            "southcentralus": 0,
            "northcentralus": 0,
        }
        oneHourAgo = (datetime.utcnow() - timedelta(hours=1)).strftime(
            "%m-%d-%Y, %H:%M:%S"
        )
        logons = getLogons(oneHourAgo, "logon")["count"]
        logoffs = getLogons(oneHourAgo, "logoff")["count"]
        deallocatedVms = 0
        vms = fetchAllVms()
        for vm in vms:
            if "NOT_RUNNING" in vm["state"]:
                deallocatedVms += 1

            if vm["location"] == "eastus":
                vmByRegion["eastus"] += 1
                if vm["username"]:
                    users["eastus"] += 1
            elif vm["location"] == "southcentralus":
                vmByRegion["southcentralus"] += 1
                if vm["username"]:
                    users["southcentralus"] += 1
            elif vm["location"] == "northcentralus":
                vmByRegion["northcentralus"] += 1
                if vm["username"]:
                    users["northcentralus"] += 1

        try:
            addReportTable(
                timestamp,
                deallocatedVms,
                timesDeallocated,
                logons,
                logoffs,
                vmByRegion,
                users,
            )
            sendInfo("Generated hourly report")
        except:
            reportError("Report gen")


if __name__ == "__main__":
    t1 = threading.Thread(target=monitorThread)
    t2 = threading.Thread(target=reportThread)

    # Reset log file
    # open("log.txt", "w").close()

    t1.start()
    t2.start()
