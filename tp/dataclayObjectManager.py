from dataclay.api import init, finish
from collections import deque

init()

from CityNS.classes import *
from tp.v3TP import QUAD_REG_LEN, QUAD_REG_MIN, Vehicle

class DataclayObjectManager:
    eventsDC = None
    
    def __init__(self, alias):
        self.eventsDC = EventsSnapshot.get_by_alias(alias)

    def getVehiclesIDs(self, limit=None):
        objectsIds = self.eventsDC.get_objects_refs()

        if limit:  #TODO: to be removed. needed for debugging
            return objectsIds[:limit]

        return objectsIds

    def getVehicleByID(self, oid):
        return Object.get_by_alias(oid)

    def storeResult(self, obj, fx, fy, ft):
        obj.add_prediction(fx,fy,ft)

    def getResult(self, oid):
        obj = Object.get_by_alias(oid)
        return obj.trajectory_px, obj.trajectory_py, obj.trajectory_pt

    def getUpdatedObject(self, oid):
        print("-------------aaaaaaaaaaaaaaaaa1--------------")
        obj = Object.get_by_alias(oid)
        dqx,dqy,_dqt = obj.get_events_history()

        print("dqx: " + str(dqx) + ", dqy: " + str(dqy) + ", _dqt: " + str(_dqt))

        if len(dqx) < QUAD_REG_MIN:
            print("Object: " + str(oid) + " data amount " + str(len(dqx)) + " not sufficient for Vehicle object initialization")
            return None, None

        dqt = deque([int(numeric_string) for numeric_string in _dqt])

        return obj, Vehicle(dqx, dqy, dqt)
