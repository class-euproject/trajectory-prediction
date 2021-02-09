from dataclay.api import init, finish
from collections import deque

init()

from CityNS.classes import DKB, uuid
from tp.v3TP import QUAD_REG_LEN, QUAD_REG_MIN

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
            self.KB.cloud_backend_id = self.backend_id
            self.KB.make_persistent(alias="DKB")

    def getAllObjects(self):
        '''
        allObjects = self.KB.get_objects(events_length_max=QUAD_REG_LEN, events_length_min=QUAD_REG_MIN)

        for j in range(len(allObjects)):
            obj = allObjects[j]
            for i in range(len(obj[5][0])):
              obj[5][0][i] = round(obj[5][0][i], 14)
            for i in range(len(obj[5][1])):
              obj[5][1][i] = round(obj[5][1][i], 14)
            allObjects[j] = obj


        print('===========')

        for obj in allObjects:
            for i in range(len(obj[5][0])):
                print(obj[5][0][i])
            for i in range(len(obj[5][1])):
                print(obj[5][1][i])
        print('======+=====')
        return allObjects
        '''
        return self.KB.get_objects(events_length_max=QUAD_REG_LEN, events_length_min=QUAD_REG_MIN)
    
    def getObject(self, oid):
        obj_id, class_id = oid.split(":")
        obj_id = uuid.UUID(obj_id)
        class_id = uuid.UUID(class_id)
        return getRuntime().get_object_by_id(obj_id, hint=self.backend_id, class_id=class_id)

    def storeResult(self, obj, fx, fy, ft, tp_timestamp, frame_tp):
        obj.add_prediction(fx,fy,ft, tp_timestamp, frame_tp)

    def getResult(self, oid):
        obj = self.getObject(oid)
        return obj.trajectory_px, obj.trajectory_py, obj.trajectory_pt
