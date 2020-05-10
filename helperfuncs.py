from imports import *

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


def cleanFetchedSQL(out):
    if out:
        is_list = isinstance(out, list)
        if is_list:
            return [dict(row) for row in out]
        else:
            return dict(out)
    return None

# Logs error in file and emails to logs@fractalcomputers.com


def reportError(service):
    error = traceback.format_exc()
    errorTime = datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S')
    msg = "ERROR for " + service + ": " + error

    # Log error in log.txt
    file = open("log.txt", "a")
    file.write(errorTime + " " + msg)
    file.close()

    # Send log to Papertrail
    sendError(msg)

    # Send error email to logs@fractalcomputers.com
    title = 'Error in monitoring service: [' + service + ']'
    message = error + "\n Occured at " + errorTime
    internal_message = SendGridMail(
        from_email='jonathan@fractalcomputers.com',
        to_emails=['logs@fractalcomputers.com'],
        subject=title,
        html_content=message
    )
    try:
        sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
        response = sg.send(internal_message)
    except:
        file = open("log.txt", "a")
        file.write(datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S') +
                   " ERROR while reporting error: " + traceback.format_exc())
        file.close()


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
    sendInfo("Automatically updating state for VM " + vm_name + " to " + state)
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
    if lock:
        sendInfo("Locking VM " + vm_name)
    else:
        sendInfo("Unlocking VM " + vm_name)

    command = text("""
        UPDATE v_ms
        SET "lock" = :lock, "last_updated" = :last_updated
        WHERE
           "vm_name" = :vm_name
        """)
    last_updated = datetime.utcnow().strftime('%m/%d/%Y, %H:%M')
    params = {'vm_name': vm_name, 'lock': lock, 'last_updated': last_updated}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def genHaiku(n):
    haikunator = Haikunator()
    haikus = [haikunator.haikunate(
        delimiter='') + str(np.random.randint(0, 10000)) for _ in range(0, n)]
    haikus = [haiku[0: np.min([15, len(haiku)])] for haiku in haikus]
    return haikus


def genVMName():
    with ENGINE.connect() as conn:
        oldVMs = [cell[0]
                  for cell in list(conn.execute('SELECT "vm_name" FROM v_ms'))]
        vmName = genHaiku(1)[0]
        while vmName in oldVMs:
            vmName = genHaiku(1)[0]
        return vmName


def createNic(name, location, tries):
    vnetName, subnetName, ipName, nicName = name + \
        '_vnet', name + '_subnet', name + '_ip', name + '_nic'
    try:
        async_vnet_creation = NCLIENT.virtual_networks.create_or_update(
            os.environ['VM_GROUP'],
            vnetName,
            {
                'location': location,
                'address_space': {
                    'address_prefixes': ['10.0.0.0/16']
                }
            }
        )
        async_vnet_creation.wait()

        # Create Subnet
        async_subnet_creation = NCLIENT.subnets.create_or_update(
            os.environ['VM_GROUP'],
            vnetName,
            subnetName,
            {'address_prefix': '10.0.0.0/24'}
        )
        subnet_info = async_subnet_creation.result()

        # Create public IP address
        public_ip_addess_params = {
            'location': location,
            'public_ip_allocation_method': 'Static'
        }
        creation_result = NCLIENT.public_ip_addresses.create_or_update(
            os.environ['VM_GROUP'],
            ipName,
            public_ip_addess_params
        )

        public_ip_address = NCLIENT.public_ip_addresses.get(
            os.environ['VM_GROUP'],
            ipName)

        # Create NIC
        async_nic_creation = NCLIENT.network_interfaces.create_or_update(
            os.environ['VM_GROUP'],
            nicName,
            {
                'location': location,
                'ip_configurations': [{
                    'name': ipName,
                    'public_ip_address': public_ip_address,
                    'subnet': {
                        'id': subnet_info.id
                    }
                }]
            }
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


def createVMParameters(vmName, nic_id, vm_size, location):
    with ENGINE.connect() as conn:
        oldUserNames = [cell[0] for cell in list(
            conn.execute('SELECT "username" FROM v_ms'))]
        userName = genHaiku(1)[0]
        while userName in oldUserNames:
            userName = genHaiku(1)

        vm_reference = {
            'publisher': 'MicrosoftWindowsDesktop',
            'offer': 'Windows-10',
            'sku': 'rs5-pro',
            'version': 'latest'
        }

        command = text("""
            INSERT INTO v_ms("vm_name", "username", "disk_name") 
            VALUES(:vmName, :username, :disk_name)
            """)
        params = {'vmName': vmName, 'username': userName, 'disk_name': None}
        with ENGINE.connect() as conn:
            conn.execute(command, **params)
            conn.close()
            return {'params': {
                'location': location,
                'os_profile': {
                    'computer_name': vmName,
                    'admin_username': os.getenv('VM_GROUP'),
                    'admin_password': os.getenv('VM_PASSWORD')
                },
                'hardware_profile': {
                    'vm_size': vm_size
                },
                'storage_profile': {
                    'image_reference': {
                        'publisher': vm_reference['publisher'],
                        'offer': vm_reference['offer'],
                        'sku': vm_reference['sku'],
                        'version': vm_reference['version']
                    },
                    'os_disk': {
                        'os_type': 'Windows',
                        'create_option': 'FromImage',
                        'caching': 'ReadOnly'
                    }
                },
                'network_profile': {
                    'network_interfaces': [{
                        'id': nic_id,
                    }]
                },
            }, 'vm_name': vmName}


def getIP(vm):
    ni_reference = vm.network_profile.network_interfaces[0]
    ni_reference = ni_reference.id.split('/')
    ni_group = ni_reference[4]
    ni_name = ni_reference[8]

    net_interface = NCLIENT.network_interfaces.get(ni_group, ni_name)
    ip_reference = net_interface.ip_configurations[0].public_ip_address
    ip_reference = ip_reference.id.split('/')
    ip_group = ip_reference[4]
    ip_name = ip_reference[8]

    public_ip = NCLIENT.public_ip_addresses.get(ip_group, ip_name)
    return public_ip.ip_address


def updateVMIP(vm_name, ip):
    command = text("""
        UPDATE v_ms
        SET ip = :ip
        WHERE
           "vm_name" = :vm_name
        """)
    params = {'ip': ip, 'vm_name': vm_name}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def updateVMLocation(vm_name, location):
    command = text("""
        UPDATE v_ms
        SET location = :location
        WHERE
           "vm_name" = :vm_name
        """)
    params = {'vm_name': vm_name, 'location': location}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


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


def createVM(vm_size, location):
    vmName = genVMName()
    nic = createNic(vmName, location, 0)
    if not nic:
        return
    vmParameters = createVMParameters(vmName, nic.id, vm_size, location)
    async_vm_creation = CCLIENT.virtual_machines.create_or_update(
        os.environ['VM_GROUP'], vmParameters['vm_name'], vmParameters['params'])
    async_vm_creation.wait()

    extension_parameters = {
        'location': location,
        'publisher': 'Microsoft.HpcCompute',
        'vm_extension_name': 'NvidiaGpuDriverWindows',
        'virtual_machine_extension_type': 'NvidiaGpuDriverWindows',
        'type_handler_version': '1.2'
    }

    async_vm_extension = CCLIENT.virtual_machine_extensions.create_or_update(os.environ['VM_GROUP'],
                                                                             vmParameters['vm_name'], 'NvidiaGpuDriverWindows', extension_parameters)
    async_vm_extension.wait()

    async_vm_start = CCLIENT.virtual_machines.start(
        os.environ['VM_GROUP'], vmParameters['vm_name'])
    async_vm_start.wait()

    vm = getVM(vmParameters['vm_name'])
    vm_ip = getIP(vm)
    updateVMIP(vmParameters['vm_name'], vm_ip)
    updateVMState(vmParameters['vm_name'], 'RUNNING_AVAILABLE')
    updateVMLocation(vmParameters['vm_name'], location)

    return fetchVMCredentials(vmParameters['vm_name'])


def fetchAllDisks():
    command = text("""
            SELECT * FROM disks
            """)
    params = {}
    with ENGINE.connect() as conn:
        disks = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return disks


def deleteDiskFromTable(disk_name):
    command = text("""
        DELETE FROM disks WHERE "disk_name" = :disk_name 
        """)
    params = {'disk_name': disk_name}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


def deleteVmFromTable(vm_name):
    command = text("""
        DELETE FROM v_ms WHERE "vm_name" = :vm_name 
        """)
    params = {'vm_name': vm_name}
    with ENGINE.connect() as conn:
        conn.execute(command, **params)
        conn.close()


# Gets all VMs from database with specified location and state


def getVMLocationState(location, state):
    # This is a bad way of doing things, hopefully this can be changed if we update the database schema
    if(state == "available"):  # Get VMs that are "available" for users to use
        command = text("""
        SELECT * FROM v_ms WHERE ("location" = :location AND "state" = 'RUNNING_AVAILABLE' AND "dev" = 'false')
        """)
    elif (state == "unavailable"):  # Get deallocated VMs (not running)
        command = text("""
        SELECT * FROM v_ms WHERE ("location" = :location AND "dev" = 'false' AND "state" = 'DEALLOCATED')
        """)
    params = {'location': location}
    with ENGINE.connect() as conn:
        vms = cleanFetchedSQL(conn.execute(command, **params).fetchall())
        conn.close()
        return vms


def addReportTable(ts, deallocVm, totalDealloc, logons, logoffs, vms, users):
    command = text("""
        INSERT INTO status_report("timestamp", "deallocated_vms", "total_vms_deallocated", "logons", "logoffs", "number_users_eastus", "number_vms_eastus", "number_users_southcentralus", "number_vms_southcentralus", "number_users_northcentralus", "number_vms_northcentralus") 
        VALUES(:timestamp, :deallocated_vms, :total_vms_deallocated, :logons, :logoffs, :number_users_eastus, :number_vms_eastus, :number_users_southcentralus, :number_vms_southcentralus, :number_users_northcentralus, :number_vms_northcentralus)
        """)
    params = {"timestamp": ts,
              "deallocated_vms": deallocVm,
              "total_vms_deallocated": totalDealloc,
              "logons": logons,
              "logoffs": logoffs,
              "number_users_eastus": users['eastus'],
              "number_vms_eastus": vms['eastus'],
              "number_users_southcentralus": users['southcentralus'],
              "number_vms_southcentralus": vms['southcentralus'],
              "number_users_northcentralus": users['northcentralus'],
              "number_vms_northcentralus": vms['northcentralus']}
    with ENGINE.connect() as conn:
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

# Logging


class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True


syslog = SysLogHandler(address=(os.environ['LOGGER_URL'], 44138))
syslog.addFilter(ContextFilter())

format = '%(asctime)s %(hostname)s YOUR_APP: %(message)s'
formatter = logging.Formatter(format, datefmt='%b %d %H:%M:%S')
syslog.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(syslog)
logger.setLevel(logging.INFO)


def sendInfo(log, papertrail=True):
    if papertrail:
        logger.info('[MONITOR] INFO: {}'.format(log))
    print('[MONITOR] INFO: {}'.format(log))


def sendError(log, papertrail=True):
    if papertrail:
        logger.error('[MONITOR] ERROR: {}'.format(log))
    print('[MONITOR] ERROR: {}'.format(log))


def sendCritical(log, papertrail=True):
    if papertrail:
        logger.critical('[MONITOR] CRITICAL: {}'.format(log))
    print('[MONITOR] CRITICAL: {}'.format(log))
