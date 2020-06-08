from dataclay.api import init, finish
from collections import deque

init()

from CityNS.classes import *
from tp.v3TP import QUAD_REG_LEN, Vehicle

class DataclayObjectManager:
    eventsDC = None
    
    def __init__(self, alias="GEIC"):
        self.eventsDC = GlobalEventsInCar.get_by_alias(alias)

    def getVehiclesIDs(self, limit=None):
        allIDs = self.eventsDC.eventsById.keys()
        filteredIDs = []

        for oid in allIDs:
            obj = self.getVehicleByID(oid)
            if len(obj.events) > QUAD_REG_LEN:
                filteredIDs.append(oid)
                self.eventsDC.add_prediction(int(oid), 'None None')

            if len(filteredIDs) == limit:    #TODO: to be removed. needed for debugging
                break
            
        return filteredIDs 

    def getVehicleByID(self, oid):
        return self.eventsDC.eventsById.get(oid)

    def storeResult(self, oid, fx, fy, ft):
        px = [str(x) for x in fx]
        py = [str(y) for y in fy]
        pt = [str(t) for t in ft]
        pp = ['(' + x + "," + y + "," + t +')' for x in px for y in py for t in pt]
        pp = ', '.join(pp)

        self.eventsDC.add_prediction(int(oid), pp)

    def getResult(self, oid):
        return self.eventsDC.tpById.get(int(oid))

    def getUpdatedObject(self, oid):
        events = self.getVehicleByID(oid).events
        print (f"events num: {len(events)}")

        if not (len(events) > QUAD_REG_LEN):
            raise Exception(f'Shouldn\'t happen, number of object events {len(events)} is less than required {QUAD_REG_LEN}')
        
        dqx = deque()
        dqy = deque()
        dqt = deque()
    
        for event in events:
            dqx.append(float(event.pos.lon))
            dqy.append(float(event.pos.lat))
            dqt.append(int(event.dt))
            if len(dqx) > QUAD_REG_LEN:
                dqx.popleft()
                dqy.popleft()
                dqt.popleft()

        return Vehicle(dqx, dqy, dqt)
