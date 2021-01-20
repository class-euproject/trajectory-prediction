from tp.v3TP import QUAD_REG_MIN, traj_pred_v3
from tp.fileBasedObjectManager import FileBasedObjectManager

def main():

    dm = FileBasedObjectManager(path="tp/data")
    oids = dm.getVehiclesIDs()
    for oid in oids:
        obj = dm.getUpdatedObject(oid)[1]

        # predict if has a minimum amount of data
        if len(obj._dqx) > QUAD_REG_MIN:
            # calculate trajectory by v2
            #fx, fy, ft = traj_pred_v2(obj)
            fx, fy, ft = traj_pred_v3(obj._dqx, obj._dqy, obj._dqt)
            dm.storeResult(oid, fx, fy, ft)

    for v_id in oids:
        res = dm.getResult(v_id)
        if res:
            print(f"v_id: {v_id} x: {res[0]} y: {res[1]} t: {res[2]}")

if __name__ == '__main__':
    main()
