from tp.v3TP import Vehicle, QUAD_REG_MIN, QUAD_REG_LEN, traj_pred_v3
from tp.fileBasedObjectManager import FileBasedObjectManager
from collections import deque

def main():

    dm = FileBasedObjectManager(path="tp/data")

    content = dm.getFileContent()

    for line in content:

        fields = line.split()

        frame = fields[1]

        v_id = fields[9]

        dqx = deque()
        dqy = deque()
        dqt = deque()
        if v_id in dm.getVehiclesIDs():
            v = dm.getVehicleByID(v_id)
            dqx = v._dqx
            dqy = v._dqy
            dqt = v._dqt

        traj_x = float(fields[4])
        dqx.append(traj_x)

        traj_y = float(fields[5])
        dqy.append(traj_y)

        t = int(fields[2])
        dqt.append(t)

        if len(dqx) > QUAD_REG_LEN:
            dqx.popleft()
            dqy.popleft()
            dqt.popleft()

        v = Vehicle(dqx, dqy, dqt)
        dm.storeVehicle(v_id, v)

        # predict if has a minimum amount of data
        if len(dqx) > QUAD_REG_MIN:
            # calculate trajectory by v3
            fx, fy, ft = traj_pred_v3(dqx, dqy, dqt)
            dm.storeResult(frame, v_id, fx, fy, ft)

    # get the final results
    res = dm.getResult()
    print(res)

    # store in a local file
    dm.createResultsFile(res)

if __name__ == '__main__':
    main()
