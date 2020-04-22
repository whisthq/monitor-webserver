from imports import *

# Create db engine object
ENGINE = sqlalchemy.create_engine(os.environ['DATABASE_URL'], echo= False, pool_pre_ping = True)

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

def cleanFetchedSQL(out):
    if out:
        is_list = isinstance(out, list)
        if is_list:
            return [dict(row) for row in out]
        else:
            return dict(out)
    return None

def fetchAllVms():
    command = text("""
            SELECT * FROM v_ms
            """)
    params = {}
    with ENGINE.connect() as conn:
        vms_info = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return vms_info

def getVM(vm_name):
    try:
        virtual_machine = CCLIENT.virtual_machines.get(
            os.environ['VM_GROUP'],
            vm_name
        )
        return virtual_machine
    except:
        return None

def updateVMState(vm_name, state):
    command = text("""
        UPDATE v_ms
        SET state = :state
        WHERE
           "vm_name" = :vm_name
        """)
    params = {'vm_name': vm_name, 'state': state}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()

def getMostRecentActivity(username):
    command = text("""
        SELECT *
        FROM login_history
        WHERE "username" = :username
        ORDER BY timestamp DESC LIMIT 1
        """)

    params = {'username': username}

    with ENGINE.connect() as conn:
        activity = cleanFetchedSQL(conn.execute(command, **params).fetchone())
        return activity

def lockVM(vm_name, lock):
    command = text("""
        UPDATE v_ms
        SET "lock" = :lock
        WHERE
           "vm_name" = :vm_name
        """)
    params = {'vm_name': vm_name, 'lock': lock}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()

def monitorVMs():
    vms = fetchAllVms()
    global timesDeallocated
    #print ("Monitoring VMs...")

    for vm in vms:
        try:
            # Get VM state
            vm_state = CCLIENT.virtual_machines.instance_view(
                resource_group_name = os.environ['VM_GROUP'], 
                vm_name = vm['vm_name']
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
                        state = 'RUNNING_AVAILABLE' if getMostRecentActivity(vm['username'])['action'] == 'logoff' else 'RUNNING_UNAVAILABLE'
                    update = True
                    print("Initializing VM state for " + vm['vm_name'] + " to " + state)
                elif vm['state'].startswith('NOT_RUNNING'):
                    state = 'RUNNING_UNAVAILABLE' if 'UNAVAILABLE' in vm['state'] else 'RUNNING_AVAILABLE'
                    update = True
                    print("Updating VM state for " + vm['vm_name'] + " to " + state)
            else:
                if not vm['state']:
                    # Check login to figure out availability
                    if not vm['username']:
                        state = 'NOT_RUNNING_AVAILABLE'
                    else:
                        state = 'NOT_RUNNING_AVAILABLE' if getMostRecentActivity(vm['username'])['action'] == 'logoff' else 'NOT_RUNNING_UNAVAILABLE'
                    update = True
                    print("Initializing VM state for " + vm['vm_name'] + " to " + state)
                elif vm['state'].startswith('RUNNING'):
                    state = 'NOT_RUNNING_UNAVAILABLE' if 'UNAVAILABLE' in vm['state'] else 'NOT_RUNNING_AVAILABLE'
                    update = True
                    print("Updating VM state for " + vm['vm_name'] + " to " + state)
            
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
                        logoffTime = datetime.strptime(userActivity['timestamp'], '%m-%d-%Y, %H:%M:%S')
                        #print(logoffTime.strftime('%m-%d-%Y, %H:%M:%S'))
                        if timedelta(minutes=30) <= now - logoffTime:
                            shutdown = True

                if vm['lock']:
                    shutdown = False

                if shutdown:
                    print("Automatically deallocating VM " + vm['vm_name'] + "...")
                    async_vm_deallocate = CCLIENT.virtual_machines.deallocate(
                        os.environ['VM_GROUP'], 
                        vm['vm_name']
                    )
                    lockVM(vm['vm_name'], True)
                    async_vm_deallocate.wait()
                    lockVM(vm['vm_name'], False)
                    timesDeallocated += 1

        except:
            file = open("log.txt", "a") 
            file.write(datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S') + " ERROR for VM " + vm['vm_name'] + ": " + traceback.format_exc())
            vm_state = CCLIENT.virtual_machines.instance_view(
                resource_group_name = os.environ['VM_GROUP'], 
                vm_name = vm['vm_name']
            )
            print(vm_state)
            file.close()

def monitorLogins():
    #print("Monitoring user logins...")
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
                print("Updating state for VM " + vm['vm_name'] + " to " + state)
        except:
            file = open("log.txt", "a") 
            file.write(datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S') + " ERROR for VM " + vm['vm_name'] + ": " + traceback.format_exc())
            file.close()

def fetchAllDisks():
    command = text("""
            SELECT * FROM disks
            """)
    params = {}
    with ENGINE.connect() as conn:
        disks = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return disks

def monitorDisks():
    #print("Monitoring disks...")
    disks = fetchAllDisks()
    for disk in disks:
        try:
            if disk['state'] == "TO_BE_DELETED":
                print("Automatically deleting Disk " + disk['disk_name'] + "...")
                async_disk_delete = CCLIENT.disks.delete(
                    os.environ['VM_GROUP'], 
                    disk['disk_name']
                    )
                async_disk_delete.wait()
        except:
            file = open("log.txt", "a") 
            file.write(datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S') + " ERROR for disk " + disk['disk_name'] + ": " + traceback.format_exc())
            file.close()

def monitorThread():
    open('log.txt', 'w').close()
    while True:
        monitorVMs()
        monitorLogins()
        monitorDisks()
        time.sleep(5)

def addReportTable(ts, deallocVm, totalDealloc, logons, logoffs, vms, users):
    command = text("""
        INSERT INTO status_report("timestamp", "deallocated_vms", "total_vms_deallocated", "logons", "logoffs", "number_users_eastus", "number_vms_eastus", "number_users_southcentralus", "number_vms_southcentralus", "number_users_northcentralus", "number_vms_northcentralus") 
        VALUES(:userName, :currentTime, :action, :is_user)
        """)
    params = {"timestamp":ts, 
        "deallocated_vms":deallocVm, 
        "total_vms_deallocated":totalDealloc, 
        "logons":logons, 
        "logoffs":logoffs, 
        "number_users_eastus":users['eastus'], 
        "number_vms_eastus":vms['eastus'], 
        "number_users_southcentralus":users['southcentralus'], 
        "number_vms_southcentralus":vms['southcentralus'], 
        "number_users_northcentralus":users['northcentralus'], 
        "number_vms_northcentralus":vms['northcentralus']}
    with engine.connect() as conn:
        conn.execute(command, **params)
        conn.close()

def getLogons(timestamp, action):
    command = text("""
        SELECT COUNT(*)
        FROM login_history
        WHERE "action" = :action AND "timestamp" > :timestamp
        """)

    params = {'timestamp': timestamp, 'action': action}

    with ENGINE.connect() as conn:
        activity = cleanFetchedSQL(conn.execute(command, **params).fetchone())
        return activity

def reportThread():
    while True:
        # Report variables
        timesDeallocated = 0
        time.sleep(60*60)

        timestamp = datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S')
        vmByRegion = {
            "eastus":0,
            "southcentralus":0,
            "northcentralus":0,
        }
        users = {
            "eastus":0,
            "southcentralus":0,
            "northcentralus":0,
        }
        oneHourAgo = ( datetime.utcnow() - timedelta(hours = 1) ).strftime('%m-%d-%Y, %H:%M:%S')
        logons = getLogons(oneHourAgo, 'logon')
        logoffs = getLogons(oneHourAgo, 'logoff')
        deallocatedVms = 0
        vms = fetchAllVms()
        for vm in vms:
            if "NOT_RUNNING" in vm['state']:
                deallocatedVms += 1

            if vm['location'] == "eastus":
                vmByRegion['eastus'] +=1
                if vm['username']:
                    users['eastus'] += 1
            elif vm['location'] == "southcentralus":
                vmByRegion['southcentralus'] +=1
                if vm['username']:
                    users['southcentralus'] += 1
            elif vm['location'] == "northcentralus":
                vmByRegion['northcentralus'] +=1
                if vm['username']:
                    users['northcentralus'] += 1

        try:
            addReportTable(timestamp, deallocatedVms, timesDeallocated, logons, logoffs, vmByRegion, users)
            print("Generated hourly report")
        except:
            file = open("log.txt", "a") 
            file.write(datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S') + " ERROR while generating report: " + traceback.format_exc())
            file.close()

if __name__ == "__main__":
    t1 = threading.Thread(target=monitorThread)
    t2 = threading.Thread(target=reportThread)

    t1.start()
    t2.start()