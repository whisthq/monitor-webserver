from app.helpers.sql import (
    cleanFetchedSQL,
    reportError,
    fetchAllVms,
    getVM,
    updateVMState,
    getMostRecentActivity,
    lockVM,
    fetchAllDisks,
    deleteDiskFromTable,
    deleteVmFromTable,
    getVMLocationState,
    addReportTable,
    getLogons
)








def test_getLogons():
    assert(isinstance( getLogons('06-01-2020, 11:11:11', 'logon'), int))
    assert(isinstance( getLogons('06-01-2020, 11:11:11', 'logoff'), int))
