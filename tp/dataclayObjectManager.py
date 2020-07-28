from dataclay.api import init, finish
from collections import deque

init()

from CityNS.classes import *
from tp.v3TP import QUAD_REG_LEN, Vehicle

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
        print("-------------aaaaaaaaaaaaaaaaa--------------")
        obj = Object.get_by_alias(oid)
        dqx,dqy,_dqt = obj.get_events_history()
        dqt = deque([int(numeric_string) for numeric_string in _dqt])

        return obj, Vehicle(dqx, dqy, dqt)
