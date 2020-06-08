import pywren_ibm_cloud as pywren
from tp.dataclayObjectManager import DataclayObjectManager 
from tp.v3TP import traj_pred_v2

from tp.mytrace import timeConsumed


def _printResults(ids, dm):
    for oid in ids:
        print('Object Id= %s Prediction= %s' % (oid, dm.getResult(oid)))

def traj_pred_v2_wrapper(oid):
    dm = DataclayObjectManager(alias="GEIC")
    obj = dm.getUpdatedObject(oid)

    # calculate trajectory by v2
    fx, fy, ft = traj_pred_v2(obj)

    print("v_id: " + str(oid) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft))

    dm.storeResult(oid, fx, fy)
    return fx

def run(params=[]):

    timeConsumed("start")   #TODO: to be removed. needed for debugging

    pw = pywren.function_executor()

    timeConsumed("pw_executor")   #TODO: to be removed. needed for debugging

    dm = DataclayObjectManager(alias="GEIC")

    timeConsumed("DataclayVehicleManager")   #TODO: to be removed. needed for debugging

    limit = None   #TODO: to be removed. needed for debugging
    if 'LIMIT' in params:  #TODO: to be removed. needed for debugging
        limit = int(params['LIMIT'])  #TODO: to be removed. needed for debugging

    ids = dm.getVehiclesIDs(limit=limit)   #TODO: to be removed. needed for debugging

    timeConsumed("dm.getVehiclesIDs")

    pw.map(traj_pred_v2_wrapper, ids, extra_env = {'PRE_RUN': 'dataclay.api.init'})

    timeConsumed("pw.map")

    pw.get_result(download_results=False, WAIT_DUR_SEC=0.025)

    timeConsumed("pw.get_result")
    
    _printResults(ids[:1], dm)
    timeConsumed("printResults")

    return {"finished": "true"}

if __name__ == '__main__':
    run()
