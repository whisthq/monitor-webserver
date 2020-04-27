from imports import *
from helperfuncs import *

# Create db engine object
ENGINE = sqlalchemy.create_engine(
    os.environ['DATABASE_URL'], echo=False, pool_pre_ping=True)

# Get Azure clients
subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
credentials = ServicePrincipalCredentials(
    client_id=os.environ['AZURE_CLIENT_ID'],
    secret=os.environ['AZURE_CLIENT_SECRET'],
    tenant=os.environ['AZURE_TENANT_ID']
)
RCLIENT = ResourceManagementClient(credentials, subscription_id)
CCLIENT = ComputeManagementClient(credentials, subscription_id)
NCLIENT = NetworkManagementClient(credentials, subscription_id)

# Report variables
timesDeallocated = 0


# Deallocates any VM that has been running for over 30 minutes while user has been logged off


def monitorVMs():
    vms = fetchAllVms()
    global timesDeallocated
    print("Monitoring VMs...")

    for vm in vms:
        try:
            # Get VM state
            vm_state = CCLIENT.virtual_machines.instance_view(
                resource_group_name=os.environ['VM_GROUP'],
                vm_name=vm['vm_name']
            )

            # Compare with database and update if there's a disreptancy
            state = 'NOT_RUNNING_UNAVAILABLE'
            update = False
            if 'running' in vm_state.statuses[1].code:
                if not vm['state']:
                    # Check login to figure out availability
                    if not vm['username']:
                        state = 'RUNNING_AVAILABLE'
                    else:
                        state = 'RUNNING_AVAILABLE' if getMostRecentActivity(
                            vm['username'])['action'] == 'logoff' else 'RUNNING_UNAVAILABLE'
                    update = True
                    print("Initializing VM state for " +
                          vm['vm_name'] + " to " + state)
                elif vm['state'].startswith('NOT_RUNNING'):
                    state = 'RUNNING_UNAVAILABLE' if 'UNAVAILABLE' in vm[
                        'state'] else 'RUNNING_AVAILABLE'
                    update = True
                    print("Updating VM state for " +
                          vm['vm_name'] + " to " + state)
            else:
                if not vm['state']:
                    # Check login to figure out availability
                    if not vm['username']:
                        state = 'NOT_RUNNING_AVAILABLE'
                    else:
                        state = 'NOT_RUNNING_AVAILABLE' if getMostRecentActivity(
                            vm['username'])['action'] == 'logoff' else 'NOT_RUNNING_UNAVAILABLE'
                    update = True
                    print("Initializing VM state for " +
                          vm['vm_name'] + " to " + state)
                elif vm['state'].startswith('RUNNING'):
                    state = 'NOT_RUNNING_UNAVAILABLE' if 'UNAVAILABLE' in vm[
                        'state'] else 'NOT_RUNNING_AVAILABLE'
                    update = True
                    print("Updating VM state for " +
                          vm['vm_name'] + " to " + state)

            if update:
                updateVMState(vm['vm_name'], state)

            # Automatically deallocate VMs on standby
            if 'running' in vm_state.statuses[1].code:
                shutdown = False
                if not vm['username']:
                    shutdown = True
                else:
                    userActivity = getMostRecentActivity(vm['username'])
                    if not userActivity:
                        shutdown = True
                    elif userActivity['action'] == 'logoff':
                        now = datetime.utcnow()
                        logoffTime = datetime.strptime(
                            userActivity['timestamp'], '%m-%d-%Y, %H:%M:%S')
                        #print(logoffTime.strftime('%m-%d-%Y, %H:%M:%S'))
                        if timedelta(minutes=30) <= now - logoffTime:
                            shutdown = True

                if vm['lock']:
                    shutdown = False

                if vm['dev']:
                    shutdown = False

                if vm['last_updated'] and shutdown:
                    lastActive = datetime.strptime(
                        vm['last_updated'], '%m/%d/%Y, %H:%M')
                    now = datetime.utcnow()
                    if timedelta(minutes=30) >= now - lastActive:
                        shutdown = False

                if shutdown:
                    print("Automatically deallocating VM " +
                          vm['vm_name'] + "...")
                    async_vm_deallocate = CCLIENT.virtual_machines.deallocate(
                        os.environ['VM_GROUP'],
                        vm['vm_name']
                    )
                    lockVM(vm['vm_name'], True)
                    async_vm_deallocate.wait()
                    lockVM(vm['vm_name'], False)
                    timesDeallocated += 1

        except:
            reportError("VM monitor for VM " + vm['vm_name'])
            # vm_state = CCLIENT.virtual_machines.instance_view(
            #     resource_group_name=os.environ['VM_GROUP'],
            #     vm_name=vm['vm_name']
            # )
            # print(vm_state)

# Checks for disreptancies between VM availability and the user's login history


def monitorLogins():
    print("Monitoring user logins...")
    vms = fetchAllVms()
    for vm in vms:
        try:
            state = 'NOT_RUNNING_UNAVAILABLE'
            update = False
            userActivity = getMostRecentActivity(vm['username'])
            if userActivity:
                if userActivity['action'] == 'logoff' and 'UNAVAILABLE' in vm['state']:
                    state = vm['state']
                    state = state[0:state.rfind('_') + 1] + "AVAILABLE"
                    update = True
                elif userActivity['action'] == 'logon' and 'UNAVAILABLE' not in vm['state']:
                    state = vm['state']
                    state = state[0:state.rfind('_') + 1] + "UNAVAILABLE"
                    update = True
            if update:
                updateVMState(vm['vm_name'], state)
                print("Updating state for VM " +
                      vm['vm_name'] + " to " + state)
        except:
            reportError("Login monitor for VM " + vm['vm_name'])

# Monitors disks in db, and deletes any that have state set as TO_BE_DELETED


def monitorDisks():
    print("Monitoring disks...")
    disks = fetchAllDisks()
    for disk in disks:
        try:
            if disk['state'] == "TO_BE_DELETED":
                print("Automatically deleting Disk " +
                      disk['disk_name'] + "...")
                async_disk_delete = CCLIENT.disks.delete(
                    os.environ['VM_GROUP'],
                    disk['disk_name']
                )
                async_disk_delete.wait()
                deleteDiskFromTable(disk['disk_name'])
        except:
            reportError("Disk monitor for disk " + disk['disk_name'])

# Increases available VMs for a region if the # of available VMs dips below a threshold


def manageRegions():
    theshold = 1
    locations = ["eastus", "northcentralus", "southcentralus"]
    for location in locations:
        availableVms = getVMLocationState(location, "available")
        if len(availableVms) < theshold:
            unavailableVms = getVMLocationState(location, "unavailable")
            vmToAllocate = None
            for vm in unavailableVms:
                # Get VM state
                vm_state = CCLIENT.virtual_machines.instance_view(
                    resource_group_name=os.environ['VM_GROUP'],
                    vm_name=vm['vm_name']
                )
                if 'deallocated' in vm_state.statuses[1].code:
                    vmToAllocate = vm['vm_name']
                    break

            if vmToAllocate:  # Reallocate from VMs
                print("Reallocating VM " +
                      unavailableVms[0]['vm_name'] + " in region " + location)
                async_vm_alloc = CCLIENT.virtual_machines.start(
                    os.environ['VM_GROUP'],
                    vmToAllocate
                )
                async_vm_alloc.wait()
            else:
                print("Creating VM " +
                      unavailableVms[0]['vm_name'] + " in region " + location)
                createVM("Standard_NV6_Promo", location)


def monitorThread():
    while True:
        monitorVMs()
        monitorLogins()
        monitorDisks()
        time.sleep(5)


def reportThread():
    global timesDeallocated
    while True:
        timesDeallocated = 0
        time.sleep(60*60)

        timestamp = datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S')
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
        oneHourAgo = (datetime.utcnow() - timedelta(hours=1)
                      ).strftime('%m-%d-%Y, %H:%M:%S')
        logons = getLogons(oneHourAgo, 'logon')['count']
        logoffs = getLogons(oneHourAgo, 'logoff')['count']
        deallocatedVms = 0
        vms = fetchAllVms()
        for vm in vms:
            if "NOT_RUNNING" in vm['state']:
                deallocatedVms += 1

            if vm['location'] == "eastus":
                vmByRegion['eastus'] += 1
                if vm['username']:
                    users['eastus'] += 1
            elif vm['location'] == "southcentralus":
                vmByRegion['southcentralus'] += 1
                if vm['username']:
                    users['southcentralus'] += 1
            elif vm['location'] == "northcentralus":
                vmByRegion['northcentralus'] += 1
                if vm['username']:
                    users['northcentralus'] += 1

        try:
            addReportTable(timestamp, deallocatedVms,
                           timesDeallocated, logons, logoffs, vmByRegion, users)
            print("Generated hourly report")
        except:
            reportError("Report gen")


if __name__ == "__main__":
    t1 = threading.Thread(target=monitorThread)
    t2 = threading.Thread(target=reportThread)

    # Reset log file
    open('log.txt', 'w').close()

    t1.start()
    t2.start()
