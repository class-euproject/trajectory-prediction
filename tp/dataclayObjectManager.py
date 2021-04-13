from dataclay.api import init, finish
from collections import deque
init()
from tp.v3TP import QUAD_REG_LEN_DICT, QUAD_REG_MIN_DICT
from dataclay import getRuntime
from dataclay.api import get_backend_id_by_name
from CityNS.classes import uuid
from CityNS.classes import DKB

class DataclayObjectManager:
    KB = None
    
    def __init__(self, alias="DKB"):
        print("in DataclayObjectManager.__init__")
        self.backend_id = get_backend_id_by_name("DS1")
        try:
            self.KB = DKB.get_by_alias(alias)
        except Exception:
            self.KB = DKB()
            self.KB.cloud_backend_id = self.backend_id
            self.KB.make_persistent(alias="DKB")

    def getAllObjects(self):
        import pdb;pdb.set_trace()
        return self.KB.get_objects(events_length_max=QUAD_REG_LEN_DICT, events_length_min=QUAD_REG_MIN_DICT)
    
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
