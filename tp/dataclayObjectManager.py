from dataclay.api import init, finish
from collections import deque

init()

from CityNS.classes import *
from tp.v3TP import QUAD_REG_LEN, QUAD_REG_MIN, Vehicle, PRECISION
from geolib import geohash

import multiprocessing
from multiprocessing.pool import ThreadPool as Pool

from dataclay import getRuntime
from dataclay.api import get_backend_id_by_name


class DataclayObjectManager:
    KB = None
    
    def __init__(self, alias="DKB"):
        self.backend_id = get_backend_id_by_name("DS1")
        try:
            self.KB = DKB.get_by_alias(alias)
        except Exception:
            self.KB = DKB()
            self.KB.cloud_backend_id = backend_id
            self.KB.make_persistent(alias="DKB")

    def getAllObjects(self):
        allObjects = self.KB.get_objects()
        res = []
        for obj in allObjects:
            _obj = self.getObject(obj[0])
            self.storeResult(_obj, [], [], [])
            if len(obj[5][0]) >= QUAD_REG_MIN:
                res.append(obj)
        return res
    
    def getObject(self, oid):
        obj_id, class_id = oid.split(":")
        obj_id = uuid.UUID(obj_id)
        class_id = uuid.UUID(class_id)
        return getRuntime().get_object_by_id(obj_id, hint=self.backend_id, class_id=class_id)

    def storeResult(self, obj, fx, fy, ft):
        obj.add_prediction(fx,fy,ft)

    def getResult(self, oid):
        obj = self.getObject(oid)
        return obj.trajectory_px, obj.trajectory_py, obj.trajectory_pt
