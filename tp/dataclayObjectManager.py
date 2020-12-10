from dataclay.api import init, finish
from collections import deque

init()

from CityNS.classes import *
from tp.v3TP import QUAD_REG_LEN, QUAD_REG_MIN, Vehicle, PRECISION
from geolib import geohash

import multiprocessing
from multiprocessing.pool import ThreadPool as Pool



class DataclayObjectManager:
    KB = None
    
    def __init__(self, alias="DKB"):
        self.KB = DKB.get_by_alias(alias)

    def _convert_object_to_tuple(self, obj):
        dqx,dqy,_dqt = obj.get_events_history()
        if len(dqx) >= QUAD_REG_MIN:
            dqt = deque([int(numeric_string) for numeric_string in _dqt])
            return (str(obj.id_object), dqx, dqy, dqt)

    def getAllObjectsTuples(self, limit=None):
        objects = self.KB.get_objects()
        res = []
        for obj in objects:
            dqx,dqy,_dqt = obj.get_events_history()
            if len(dqx) >= QUAD_REG_MIN:
                dqt = deque([int(numeric_string) for numeric_string in _dqt])
                res.append((str(obj.id_object), dqx, dqy, dqt))
                if len(res) == limit:
                    break;
        return res

    def getAllObjectsTuplesAsync(self, limit=None):
        objects = self.KB.get_objects()
        pool = Pool(8)
        return pool.map(self._convert_object_to_tuple, objects[:limit])

    def getObject(self, oid):
        return Object.get_by_alias(oid)

    def storeResult(self, obj, fx, fy, ft):
        obj.add_prediction(fx,fy,ft)

    def getResult(self, oid):
        obj = self.getObject(oid)
        return obj.trajectory_px, obj.trajectory_py, obj.trajectory_pt

    def getUpdatedObject(self, oid):
        obj = Object.get_by_alias(oid)
        dqx,dqy,_dqt = obj.get_events_history()

        if len(dqx) < QUAD_REG_MIN:
            print("Object: " + str(oid) + " data amount " + str(len(dqx)) + " not sufficient for Vehicle object initialization")
            return None

        dqt = deque([int(numeric_string) for numeric_string in _dqt])

        return Vehicle(dqx, dqy, dqt)
