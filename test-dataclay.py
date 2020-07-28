from tp.v3TP import traj_pred_v2, QUAD_REG_MIN
from tp.dataclayObjectManager import DataclayObjectManager

if __name__ == '__main__':
    dm = DataclayObjectManager(alias="GEIC")
    oids = dm.getVehiclesIDs()

    for oid in oids:
        obj = dm.getUpdatedObject(oid)
        if not obj:
            continue

        # predict if has a minimum amount of data
        if len(obj._dqx) > QUAD_REG_MIN:
            # calculate trajectory by v2
            fx, fy, ft = traj_pred_v2(obj)
            dm.storeResult(obj, fx, fy, ft)

    for v_id in oids:
        res = dm.getResult(v_id)
        if res:
            print('Object Id= %s Prediction= %s' % (oid, dm.getResult(oid)))
