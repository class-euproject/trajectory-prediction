from tp.v3TP import Vehicle, QUAD_REG_MIN, QUAD_REG_LEN, P_QUAD_REG_MIN, P_QUAD_REG_LEN, V_QUAD_REG_MIN, V_QUAD_REG_LEN, traj_pred_v3
from tp.fileBasedObjectManager import FileBasedObjectManager
from collections import deque
import sys

def main():

    workflow_log = sys.argv[2]

    reg_offset = int(sys.argv[3]) # how many points to predict
    range_mil = int(sys.argv[4]) # milliseconds between points

    p_reg_len = P_QUAD_REG_LEN # pedestrians max len
    p_reg_min = P_QUAD_REG_MIN # ped min len
    v_reg_len = V_QUAD_REG_LEN # vehicle max len
    v_reg_min = V_QUAD_REG_MIN # v min len

    if len(sys.argv) == 9:
        p_reg_len = int(sys.argv[5])
        p_reg_min = int(sys.argv[6])
        v_reg_len = int(sys.argv[7])
        v_reg_min = int(sys.argv[8])

    dm = FileBasedObjectManager(path=sys.argv[1],filename=workflow_log)

    content = dm.getFileContent()

    for line in content:

        fields = line.split()

        frame = fields[1]
        ttamp = fields[2]

        reg_len = QUAD_REG_LEN
        reg_min = QUAD_REG_MIN
        v_type = int(fields[3]) # pedestrian, vehicle, ...
        if v_type == 0:
            reg_len = p_reg_len
            reg_min = p_reg_min
        elif v_type == 1:
            reg_len = v_reg_len
            reg_min = v_reg_min
        else:
            reg_len = v_reg_len
            reg_min = v_reg_min

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

        if len(dqx) > reg_len:
            dqx.popleft()
            dqy.popleft()
            dqt.popleft()

        #for i in range(len(dqx)):
        #    dqx[i] = round(dqx[i],7)
        #    dqy[i] = round(dqy[i],7)

        v = Vehicle(dqx, dqy, dqt)
        dm.storeVehicle(v_id, v)

        # predict if has a minimum amount of data
        if len(dqx) >= reg_min:
            # calculate trajectory by v3
            fx, fy, ft = traj_pred_v3(dqx, dqy, dqt, reg_offset, range_mil)
            dm.storeResult(frame, v_id, fx, fy, ft)
            #raw_out = "frame: " + str(frame) + " v_id: " + str(v_id) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft)
            fx_str = ','.join(str(e) for e in fx)
            fy_str = ','.join(str(e) for e in fy)
            ft_str = ','.join(str(e) for e in ft)
            raw_out = str(frame)+" "+str(ttamp)+" "+str(v_id)+" "+fx_str+" "+fy_str+" "+ft_str
            dm.storeRawResult(raw_out)
            print(raw_out)

    # get the final results
    #res = dm.getResult()
    #print(res)

    # store in a local file
    dm.createResultsFile()

if __name__ == '__main__':
    main()
