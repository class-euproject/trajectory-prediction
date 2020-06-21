from dataclay.api import init, finish
from collections import deque

import os 

init()

from CityNS.classes import *
from tp.v3TP import QUAD_REG_LEN, Vehicle

import pywren_ibm_cloud as pywren
#from tp.dataclayObjectManager import DataclayObjectManager 
from tp.v3TP import traj_pred_v2

from tp.mytrace import timeConsumed


def _printResults(ids):
    for oid in ids:
        print('Object Id= %s obj.trajectory_px = %s' % (oid, Object.get_by_alias(oid).trajectory_px))

def traj_pred_v2_wrapper(oid):
#    EventsSnapshot.get_by_alias(alias ="GEIC")
    obj = Object.get_by_alias(oid)
    dqx,dqy,_dqt = obj.get_events_history()
    
    dqt = deque([int(numeric_string) for numeric_string in _dqt])
    
#    dm = DataclayObjectManager(alias="GEIC")
#    obj = dm.getUpdatedObject(oid)

    # calculate trajectory by v2
    fx, fy, ft = traj_pred_v2(Vehicle(dqx,dqy,dqt))

    print("v_id: " + str(oid) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft))

    obj.add_prediction(fx,fy,ft)
#    dm.storeResult(oid, fx, fy, ft)
    return fx

def run(params=[]):

    timeConsumed("start")   #TODO: to be removed. needed for debugging

    pw = pywren.function_executor()

    timeConsumed("pw_executor")   #TODO: to be removed. needed for debugging

#    dm = DataclayObjectManager(alias="GEIC")

#    timeConsumed("DataclayVehicleManager")   #TODO: to be removed. needed for debugging

    eventsS = EventsSnapshot.get_by_alias(alias="GEIC")
    objectsIds = eventsS.get_objects_refs()

    print("params: %s" % params)
    limit = None   #TODO: to be removed. needed for debugging
    if 'LIMIT' in params:  #TODO: to be removed. needed for debugging
        limit = int(params['LIMIT'])  #TODO: to be removed. needed for debugging
        objectsIds = objectsIds[:limit]


#    ids = dm.getVehiclesIDs(limit=limit)   #TODO: to be removed. needed for debugging

    timeConsumed("dm.getVehiclesIDs")

#    import pdb;pdb.set_trace()
    pw.map(traj_pred_v2_wrapper, objectsIds, extra_env = {'PRE_RUN': 'dataclay.api.init'})

    timeConsumed("pw.map")

    pw.get_result(download_results=False, WAIT_DUR_SEC=0.025)

    timeConsumed("pw.get_result")
    
    _printResults(objectsIds)
    timeConsumed("printResults")

    return {"finished": "true"}

if __name__ == '__main__':
    run()
