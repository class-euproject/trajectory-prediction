from collections import deque
import os
from tp.v3TP import QUAD_REG_LEN, Vehicle

class FileBasedObjectManager:

    vehicles = {}
    results = {}

    def __init__(self, path='.'):
        # read BSC test data
        files = []
        for i in range(50,60): # last test files are in a wrong order
            infile = path + "/"+str(i)+".txt"
            if os.path.exists(infile):
                files.append(path + "/"+str(i)+".txt")
        for i in range(0,50):
            infile = path + "/"+str(i)+".txt"
            if os.path.exists(infile):
                files.append(path + "/"+str(i)+".txt")

        for infile in files:

            content = str()
            with open(infile) as f:
                content = f.read().splitlines()

            for line in content:

                fields = line.split()

                v_id = fields[7]

                dqx = deque()
                dqy = deque()
                dqt = deque()
                if v_id in self.vehicles.keys():
                    v = self.vehicles[v_id]
                    dqx = v._dqx
                    dqy = v._dqy
                    dqt = v._dqt


                traj_x = float(fields[3])
                dqx.append(traj_x)

                traj_y = float(fields[4])
                dqy.append(traj_y)

                t = int(fields[1])
                dqt.append(t)


                if len(dqx) > QUAD_REG_LEN:
                    dqx.popleft()
                    dqy.popleft()
                    dqt.popleft()

                v = Vehicle(dqx, dqy, dqt)
                self.vehicles[v_id] = v

    def getVehiclesIDs(self):
        return self.vehicles.keys()

    def getVehicleByID(self, v_id):
        return self.vehicles[v_id]

    def getUpdatedObject(self, oid):
        return self.getVehicleByID(oid)

    def storeResult(self, oid, result):
        self.results[oid] = result

    def getResult(self, oid):
        if oid in self.results:
            return self.results[oid]
        return None
