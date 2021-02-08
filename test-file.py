from tp.v3TP import Vehicle, QUAD_REG_MIN, QUAD_REG_LEN, traj_pred_v3
from tp.fileBasedObjectManager import FileBasedObjectManager
from collections import deque
import sys
import cv2
import numpy as np
#from osgeo import gdal

def generate_transformation_da(ProjMat_file,GeoTransform_file):
        
    with open(ProjMat_file) as f:
        rows_pj = [line.split() for line in f]
    ProjMat = np.array(rows_pj, dtype = 'float32')
    InvProjMat = np.linalg.inv(ProjMat)
            
    with open(GeoTransform_file) as f:
        rows_gt = [line.split() for line in f]
    adfGeoTransform = np.array(rows_gt[0], dtype = 'float32')
        
    return ProjMat, InvProjMat, adfGeoTransform

def main():

    ProjMat_file = sys.argv[2]
    GeoTransform_file = sys.argv[3]
    workflow_log = sys.argv[4]
    threshold_mov = float(sys.argv[5])

    reg_len = int(sys.argv[6])
    reg_offset = int(sys.argv[7])
    reg_min = int(sys.argv[8])
    range_mil = int(sys.argv[9])
    
    dm = FileBasedObjectManager(path=sys.argv[1],filename=workflow_log)

    content = dm.getFileContent()

    # Generate matrices
    ProjMat, InvProjMat, adfGeoTransform = generate_transformation_da(ProjMat_file, GeoTransform_file)

    for line in content:

        fields = line.split()

        frame = fields[1]
        ttamp = fields[2]

        v_id = fields[9]
        w,h = float(fields[12]), float(fields[13])

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
        
        v = Vehicle(dqx, dqy, dqt)
        dm.storeVehicle(v_id, v)

        for i in range(len(dqx)):
            dqx[i] = round(dqx[i],7)
            dqy[i] = round(dqy[i],7)

        # predict if has a minimum amount of data
        if len(dqx) >= reg_min:

            #static = (1 == 0)
            #if(v_id == "2406_9"):
            #static = is_object_static (traj_x,traj_y,w,h,threshold_mov,dqx,dqy,InvProjMat, adfGeoTransform)

            # calculate trajectory by v3
            fx, fy, ft = traj_pred_v3(dqx, dqy, dqt,w,h,InvProjMat,adfGeoTransform,reg_offset,range_mil,threshold_mov)

            dm.storeResult(frame, v_id, fx, fy, ft)
            #raw_out = "frame: " + str(frame) + " v_id: " + str(v_id) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft)
            fx_str = ','.join(str(e) for e in fx)
            fy_str = ','.join(str(e) for e in fy)
            ft_str = ','.join(str(e) for e in ft)
            raw_out = str(frame)+" "+str(ttamp)+" "+str(v_id)+" "+fx_str+" "+fy_str+" "+ft_str
            dm.storeRawResult(raw_out)

 
    # get the final results
    #res = dm.getResult()
    #print(res)

    # store in a local file
    dm.createResultsFile()

if __name__ == '__main__':
    main()
