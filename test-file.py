# Trajectory Prediction application
# CLASS Project: https://class-project.eu/

#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Created on 8 Jun 2020
# @author: Jorge Montero - ATOS
#

from tp.v3TP_new import Vehicle, QUAD_REG_MIN_DICT, QUAD_REG_LEN_DICT, traj_pred_v3
from tp.fileBasedObjectManager import FileBasedObjectManager
from collections import deque
import sys
import numpy as np

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
    
    workflow_log = sys.argv[2]

    reg_offset = int(sys.argv[3]) # how many points to predict
    range_mil = int(sys.argv[4]) # milliseconds between points

    ProjMat_file = sys.argv[5]
    GeoTransform_file = sys.argv[6]
    threshold_mov = float(sys.argv[7])
    reg_degree = int(sys.argv[8])

    dm = FileBasedObjectManager(path=sys.argv[1],filename=workflow_log)

    content = dm.getFileContent()

    # Generate matrices
    ProjMat, InvProjMat, adfGeoTransform = generate_transformation_da(ProjMat_file, GeoTransform_file)

    it = 0
    for line in content:
        print('Processing: %.2f' %(100*it/len(content)), end="\r")
        it=it+1
        fields = line.split()

        frame = int(fields[1])
        ttamp = fields[2]

        v_type = fields[3] # pedestrian, vehicle, ...

        reg_len = QUAD_REG_LEN_DICT[v_type]
        reg_min = QUAD_REG_MIN_DICT[v_type]
        
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

        w,h=float(fields[12]), float(fields[13])

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
            #fx, fy, ft = traj_pred_v3(dqx, dqy, dqt, reg_offset, range_mil)

            #if (v_id == "2804_103"):
                #print("Frame: "+str(frame)+" TP input:", dqx, dqy, dqt)
                #print("HERE: " +str(frame))
            #fx, fy, ft = traj_pred_v3(dqx, dqy, dqt,w,h,InvProjMat,adfGeoTransform,reg_offset,range_mil,threshold_mov)
            
            workflow_log_number = workflow_log.split('.')[0]
            fx, fy, ft = traj_pred_v3(dqx, dqy, dqt, w, h, workflow_log_number,
                                      reg_offset, range_mil)

            dm.storeResult(frame, v_id, v_type, fx, fy, ft)
            
            #raw_out = "frame: " + str(frame) + " v_id: " + str(v_id) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft)
            fx_str = ','.join(str(e) for e in fx)
            fy_str = ','.join(str(e) for e in fy)
            ft_str = ','.join(str(e) for e in ft)
            raw_out = str(frame)+" "+str(ttamp)+" "+str(v_id)+" "+fx_str+" "+fy_str+" "+ft_str
            dm.storeRawResult(raw_out)
            #print(raw_out)
            visual_out = ' '.join(str(e) for e in fields[0:14])+" "+str(frame-1)+" "+str(ttamp)+" "+fx_str+" "+fy_str+" "+ft_str
            dm.storeVisualResult(visual_out)
        else:
            visual_out = ' '.join(str(e) for e in fields[0:14])+" -1 -1 0,0,0,0,0 0,0,0,0,0 0,0,0,0,0"
            dm.storeVisualResult(visual_out)
        
    # get the final results
    #res = dm.getResult()
    #print(res)

    # store in a local file
    dm.createResultsFile()
    

if __name__ == '__main__':
    main()
