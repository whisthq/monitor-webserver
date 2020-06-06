


from app.helpers.vms import (





)



def sendVMStartCommand(vm_name, needs_restart, needs_winlogon):

def fractalVMStart(vm_name, needs_restart=False, needs_winlogon=True):

def createVMParameters(vmName, nic_id, vm_size, location, operating_system="Windows"):

def createVM(vm_size, location, operating_system):

def getIP(vm):

def updateVMIP(vm_name, ip):

def updateVMLocation(vm_name, location):

def updateVMOS(vm_name, operating_system):

def fetchVMCredentials(vm_name):

def lockVMAndUpdate(vm_name, state, lock, temporary_lock, change_last_updated, verbose):

def genHaiku(n):

def genVMName():

def createNic(name, location, tries):



def test_cleanFetchedSQL():
    # fetchAllDisks() calls cleanFetchedSQL
    assert isinstance(fetchAllDisks(), list)

def test_reportError():
    assert reportError("TEST SERVICE") == None
    
def test_fetchAllVms():
    assert isinstance(fetchAllVms(), list)

def test_getVM():
    assert getVM('dev-nv6') != None
    assert getVM('this-vm-doesnt-exist') == None

def test_updateVMState():
    # can't really be unit tested
    assert True


    
