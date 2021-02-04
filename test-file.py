from tp.v3TP import Vehicle, QUAD_REG_MIN, QUAD_REG_LEN, traj_pred_v3
from tp.fileBasedObjectManager import FileBasedObjectManager
from collections import deque
import sys
import cv2
import numpy as np
#from osgeo import gdal

def GPS2Pixel(lat, lon, InvProjMat, adfGeoTransform):
    x = (lon - adfGeoTransform[0]) / adfGeoTransform[1]
    y = (lat - adfGeoTransform[3]) / adfGeoTransform[5]

    mapPixels = np.array([[[x, y]]], dtype='float32')
    imgPixels = cv2.perspectiveTransform(mapPixels, InvProjMat)

    # print("At GPS2Pixel: ("+str(lat)+","+str(lon)+")->("+str(imgPixels[0][0][0])+","+str(imgPixels[0][0][1])+")")
    return int(imgPixels[0][0][0]), int(imgPixels[0][0][1])

def generate_transformation_da(ProjMat_file,GeoTransform_file):
        
    with open(ProjMat_file) as f:
        rows_pj = [line.split() for line in f]
    ProjMat = np.array(rows_pj, dtype = 'float32')
    InvProjMat = np.linalg.inv(ProjMat)
            
    with open(GeoTransform_file) as f:
        rows_gt = [line.split() for line in f]
    adfGeoTransform = np.array(rows_gt[0], dtype = 'float32')
        
    return ProjMat, InvProjMat, adfGeoTransform

def compute_maxmin_coord(coord, assoc_coord):

    max1 = max(coord)
    maxi = [i for i, j in enumerate(coord) if j == max1]             
    max_assoc_coord = deque()
    for i in maxi: max_assoc_coord.append(assoc_coord[i])
    max2 = max(max_assoc_coord)

    min1 = min(coord)
    mini = [i for i, j in enumerate(coord) if j == min1]             
    min_assoc_coord = deque()
    for i in mini: min_assoc_coord.append(assoc_coord[i])
    min2 = min(min_assoc_coord)

    return max1, max2, min1, min2

def is_object_static (traj_x, traj_y,w,h,thr_box,dqx,dqy,InvProjMat, adfGeoTransform):

    thr_x, thr_y = w*thr_box, h*thr_box

    center_bb = GPS2Pixel(traj_x,traj_y,InvProjMat, adfGeoTransform)
    x1, x2, y1, y2 = center_bb[0] - thr_x, center_bb[0] + thr_x, center_bb[1] - thr_y, center_bb[1] + thr_y


    maxlat, maxlat_lon, minlat, minlat_lon = compute_maxmin_coord(dqx, dqy)
    maxlon, maxlon_lat, minlon, minlon_lat = compute_maxmin_coord(dqy, dqx)

    pixel_maxlat = GPS2Pixel(maxlat, maxlat_lon, InvProjMat, adfGeoTransform) 
    pixel_maxlon = GPS2Pixel(maxlon_lat, maxlon, InvProjMat, adfGeoTransform) 
    pixel_minlat = GPS2Pixel(minlat, minlat_lon, InvProjMat, adfGeoTransform) 
    pixel_minlon = GPS2Pixel(minlon_lat, minlon, InvProjMat, adfGeoTransform) 
                                 
    # print(pixel_maxlat)
    # print(pixel_maxlon)
    # print(pixel_minlat)
    # print(pixel_minlon)
    # print(x1, y1, x2, y2)
    # print(" ")
                
    return ((x1<=pixel_maxlat[0]<=x2) and (x1<=pixel_maxlon[0]<=x2) and (x1<=pixel_minlat[0]<=x2) and (x1<=pixel_minlon[0]<=x2) and (y1<=pixel_maxlat[1]<=y2) and (y1<=pixel_maxlon[1]<=y2) and (y1<=pixel_minlat[1]<=y2) and (y1<=pixel_minlon[1]<=y2))

def main():

    ProjMat_file = sys.argv[2]
    GeoTransform_file = sys.argv[3]
    workflow_log = sys.argv[4]
    threshold_mov = float(sys.argv[5])

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

        if len(dqx) > QUAD_REG_LEN:
            dqx.popleft()
            dqy.popleft()
            dqt.popleft()
        
        v = Vehicle(dqx, dqy, dqt)
        dm.storeVehicle(v_id, v)

        for i in range(len(dqx)):
            dqx[i] = round(dqx[i],7)
            dqy[i] = round(dqy[i],7)

        # predict if has a minimum amount of data
        if len(dqx) >= QUAD_REG_MIN:

            #static = (1 == 0)
            #if(v_id == "2406_9"):
            static = is_object_static (traj_x,traj_y,w,h,threshold_mov,dqx,dqy,InvProjMat, adfGeoTransform)

            # calculate trajectory by v3
            fx, fy, ft = traj_pred_v3(dqx, dqy, dqt,static)

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
