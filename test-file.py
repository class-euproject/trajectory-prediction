from tp.v3TP import QUAD_REG_MIN, traj_pred_v2
from tp.fileBasedObjectManager import FileBasedObjectManager

def main():

    dm = FileBasedObjectManager(path="python/v3/data2")
    oids = dm.getVehiclesIDs()
    for oid in oids:
        obj = dm.getUpdatedObject(oid)
        if len(obj._dqx) > QUAD_REG_MIN:
            fx, fy, ft = traj_pred_v2(obj)

        # predict if has a minimum amount of data
        if len(obj._dqx) > QUAD_REG_MIN:
            # calculate trajectory by v2
            fx, fy, ft = traj_pred_v2(obj)
            dm.storeResult(oid, (fx, fy, ft))

    for v_id in oids:
        res = dm.getResult(v_id)
        if res:
            print(f"v_id: {v_id} x: {res[0]} y: {res[1]} t: {res[2]}")

if __name__ == '__main__':
    main()
