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

def fetchVMCredentials(vm_name):
    command = text("""
        SELECT * FROM v_ms WHERE "vm_name" = :vm_name
        """)
    params = {'vm_name': vm_name}
    with ENGINE.connect() as conn:
        vm_info = cleanFetchedSQL(conn.execute(command, **params).fetchone())
        # Decode password
        conn.close()
        return vm_info

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

def main():
    vms = fetchAllVms()
    test = True
    print ("Monitor script running...")

    for vm in vms:
        if not test:
            break
        vmObject = getVM(vm['vm_name'])
        # Check to see if VM is running
        vm_state = CCLIENT.virtual_machines.instance_view(
            resource_group_name = os.environ['VM_GROUP'], 
            vm_name = vm['vm_name']
        )
        # Compare with database and update if there's a disreptancy
        dbVm = fetchVMCredentials(vm['vm_name'])
        state = 'NOT_RUNNING_UNAVAILABLE'
        update = False
        if 'running' in vm_state.statuses[1].code:
            if not dbVm['state']:
                # Check login to figure out availability
                if not dbVm['username']:
                    state = 'RUNNING_AVAILABLE'
                else:
                    state = 'RUNNING_AVAILABLE' if getMostRecentActivity(dbVm.username)['action'] == 'logoff' else 'RUNNING_UNAVAILABLE'
                update = True
                print("Initializing VM state for " + vm['vm_name'] + " to " + state)
            elif dbVm['state'].startswith('NOT_RUNNING'):
                state = 'RUNNING_UNAVAILABLE' if 'UNAVAILABLE' in dbVm['state'] else 'RUNNING_AVAILABLE'
                update = True
                print("Updating VM state for " + vm['vm_name'] + " to " + state)
        else:
            if not dbVm['state']:
                # Check login to figure out availability
                if not dbVm['username']:
                    state = 'NOT_RUNNING_AVAILABLE'
                else:
                    state = 'NOT_RUNNING_AVAILABLE' if getMostRecentActivity(dbVm.username)['action'] == 'logoff' else 'NOT_RUNNING_UNAVAILABLE'
                update = True
                print("Initializing VM state for " + vm['vm_name'] + " to " + state)
            elif dbVm['state'].startswith('RUNNING'):
                state = 'NOT_RUNNING_UNAVAILABLE' if 'UNAVAILABLE' in dbVm['state'] else 'NOT_RUNNING_AVAILABLE'
                update = True
                print("Updating VM state for " + vm['vm_name'] + " to " + state)
        
        if update:
            updateVMState(vm['vm_name'], state)

        # Automatically power off VMs on standby
        # print(vm_state)
        # test = False
    #while True:

main()