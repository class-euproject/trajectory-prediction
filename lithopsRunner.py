from dataclay.api import init, finish

import time

init()

from CityNS.classes import *

import lithops

from tp.dataclayObjectManager import DataclayObjectManager 
from tp.v3TP import traj_pred_v3

from tp.mytrace import timeConsumed


def _printResults(allObjectsTuples, dm):
    for objTuple in allObjectsTuples:
        print('Object Id= %s obj.trajectory_px = %s' % (objTuple[0], dm.getResult(objTuple[0])))

def traj_pred_v2_wrapper(objectTuple):
    print(" = ==================in traj_pred_v2_wrapper ===============")
    print(" with input: " + str(objectTuple))
    
    # calculate trajectory by v2
    fx, fy, ft = traj_pred_v3(objectTuple[1], objectTuple[2], objectTuple[3])

    print("v_id: " + str(objectTuple[0]) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft))

    dm = DataclayObjectManager()
    obj = dm.getObject(objectTuple[0])

    dm.storeResult(obj, fx, fy, ft)
    return fx

def run(params=[]):

    print("params: %s" % params)

    timeConsumed("start")   #TODO: to be removed. needed for debugging

    fexec = lithops.FunctionExecutor()

    timeConsumed("lithops executor")   #TODO: to be removed. needed for debugging
    if 'ALIAS' not in params:  #TODO: to be removed. needed for debugging
        print("Params %s missing ALIAS parameter" % params)
        exit()

    limit = None
    if 'LIMIT' in params:  #TODO: to be removed. needed for debugging
        limit = int(params['LIMIT'])

    alias = params['ALIAS']

    print("ALIAS: %s" % alias)

    dm = DataclayObjectManager(alias=alias)
    timeConsumed("DataclayObjectManager")

#    import pdb;pdb.set_trace()
    allObjectsTuples = dm.getAllObjectsTuples(limit=limit)   #TODO: to be removed. needed for debugging

    timeConsumed("dm.getVehiclesIDs")

    fexec.map(traj_pred_v2_wrapper, allObjectsTuples, extra_env = {'__LITHOPS_LOCAL_EXECUTION': True, 'PRE_RUN': 'dataclay.api.init'})

    timeConsumed("fexec.map")

    fexec.wait(download_results=False, WAIT_DUR_SEC=0.015)

    timeConsumed("pw.get_result")
    
#    _printResults(allObjectsTuples, dm)
    timeConsumed("printResults")

    return {"finished": "true"}

if __name__ == '__main__':
    params = {"ALIAS" : "DKB"}
    if len(sys.argv) > 1:
        params['LIMIT'] = sys.argv[1]
    run(params=params)
