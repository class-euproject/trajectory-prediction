from dataclay.api import init, finish
from collections import deque

import os 

init()

from CityNS.classes import *
from tp.v3TP import QUAD_REG_LEN, Vehicle

import pywren_ibm_cloud as pywren
from tp.dataclayObjectManager import DataclayObjectManager 
from tp.v3TP import traj_pred_v2

from tp.mytrace import timeConsumed


def _printResults(ids, dm):
    for oid in ids:
        print('Object Id= %s obj.trajectory_px = %s' % (oid, dm.getResult(oid)))

def traj_pred_v2_wrapper(oid):
    dm = DataclayObjectManager(alias="GEIC")
    obj, vehicle = dm.getUpdatedObject(oid)
    
    # calculate trajectory by v2
    fx, fy, ft = traj_pred_v2(vehicle)

    print("v_id: " + str(oid) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft))

    dm.storeResult(obj, fx, fy, ft)
    return fx

def run(params=[]):

    timeConsumed("start")   #TODO: to be removed. needed for debugging

    pw = pywren.function_executor()

    timeConsumed("pw_executor")   #TODO: to be removed. needed for debugging
    alias = "GEIC"
    if 'ALIAS' in params:  #TODO: to be removed. needed for debugging
        alias = params['ALIAS']

    dm = DataclayObjectManager(alias=alias)

#    timeConsumed("DataclayVehicleManager")   #TODO: to be removed. needed for debugging

#    eventsS = EventsSnapshot.get_by_alias(alias="GEIC")
#    objectsIds = eventsS.get_objects_refs()

#    print("params: %s" % params)
    limit = 20   #TODO: to be removed. needed for debugging
    if 'LIMIT' in params:  #TODO: to be removed. needed for debugging
        limit = int(params['LIMIT'])  #TODO: to be removed. needed for debugging
#        objectsIds = objectsIds[:limit]

    ids = dm.getVehiclesIDs(limit=limit)   #TODO: to be removed. needed for debugging

    timeConsumed("dm.getVehiclesIDs")

#    import pdb;pdb.set_trace()
    pw.map(traj_pred_v2_wrapper, ids, extra_env = {'PRE_RUN': 'dataclay.api.init'})

    timeConsumed("pw.map")

    pw.get_result(download_results=False, WAIT_DUR_SEC=0.015)

    timeConsumed("pw.get_result")
    
    _printResults(ids, dm)
    timeConsumed("printResults")

    return {"finished": "true"}

if __name__ == '__main__':
    run(params={"LIMIT": 20})
