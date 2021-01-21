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
        print('Object = %s \nObject TRAJECTORY = %s' % (objTuple, dm.getResult(objTuple[0])))

def traj_pred_v2_wrapper(objects_chunk):
    print(" = ==================in traj_pred_v2_wrapper ===============")
    print(" with input: " + str(objects_chunk))
    dm = DataclayObjectManager()
    
    for objectTuple in objects_chunk:
      # calculate trajectory by v2
      fx, fy, ft = traj_pred_v3(objectTuple[5][0], objectTuple[5][1], objectTuple[5][2])

      print("v_id: " + str(objectTuple[0]) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft))

      obj = dm.getObject(objectTuple[0])
      dm.storeResult(obj, fx, fy, ft)
    return {}

def run(params=[]):

    print("params: %s" % params)

    timeConsumed("start")   #TODO: to be removed. needed for debugging

    fexec = lithops.FunctionExecutor()

    timeConsumed("lithops executor")   #TODO: to be removed. needed for debugging
    if 'ALIAS' not in params:  #TODO: to be removed. needed for debugging
        print("Params %s missing ALIAS parameter" % params)
        exit()

    limit = None
    if 'LIMIT' in params and params['LIMIT'] != None:  #TODO: to be removed. needed for debugging
        limit = int(params['LIMIT'])

    alias = params['ALIAS']

    print("ALIAS: %s" % alias)

    chunk_size = 1
    if 'CHUNK_SIZE' in params and params['CHUNK_SIZE'] != None:
        chunk_size =  int(params['CHUNK_SIZE'])

    dm = DataclayObjectManager(alias=alias)
    timeConsumed("DataclayObjectManager")

    allObjectsTuples = dm.getAllObjects()[:limit]
    timeConsumed("dm.getAllObjects: %d " % len(allObjectsTuples))

    def chunker(seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))

    if allObjectsTuples:

        kwargs = []
        for objects_chunk in chunker(allObjectsTuples, chunk_size):
            kwargs.append({'objects_chunk': objects_chunk})

        fexec.map(traj_pred_v2_wrapper, kwargs, extra_env = {'__LITHOPS_LOCAL_EXECUTION': True, 'PRE_RUN': 'dataclay.api.init'})

        timeConsumed("fexec.map")

        fexec.wait(download_results=False, WAIT_DUR_SEC=0.015)

        timeConsumed("pw.get_result")
    
    _printResults(allObjectsTuples, dm)
    timeConsumed("printResults")

    return {"finished": "true"}

if __name__ == '__main__':
    limit = None
    chunk_size = 1
    if len(sys.argv) > 1:
        chunk_size = sys.argv[1]
    if len(sys.argv) > 2:
        limit = sys.argv[2]
    run(params={"CHUNK_SIZE" : chunk_size, "LIMIT": limit, "ALIAS" : "DKB"})
