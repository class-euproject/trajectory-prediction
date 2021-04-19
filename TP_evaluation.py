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
# Created on 19 Mar 2021
# @author: Jorge Montero - ATOS
#

from tp.v3TP import quad_reg
import sys
import math
from math import sqrt
import numpy as np


# store X,Y,timestamp coordinates and types of each object
stored_traj_x = {}
stored_traj_y = {}
stored_t = {}
stored_types = {}

# generate the whole trajectory for each object based on the log file
def generate_trajectories(infile):

    content = str()
    with open(infile) as f:
        content = f.read().splitlines() 

    for line in content:

        fields = line.split()
        frame = fields[1]
        v_id = fields[9]
        
        traj_x = float(fields[4])
        if v_id in stored_traj_x.keys():
            v_stored_traj_x = stored_traj_x[v_id]
            v_stored_traj_x.append(traj_x)
            stored_traj_x[v_id] = v_stored_traj_x
        else:
            v_stored_traj_x = []
            v_stored_traj_x.append(traj_x)
            stored_traj_x[v_id] = v_stored_traj_x

        traj_y = float(fields[5])
        if v_id in stored_traj_y.keys():
            v_stored_traj_y = stored_traj_y[v_id]
            v_stored_traj_y.append(traj_y)
            stored_traj_y[v_id] = v_stored_traj_y
        else:
            v_stored_traj_y = []
            v_stored_traj_y.append(traj_y)
            stored_traj_y[v_id] = v_stored_traj_y

        t = int(fields[2])
        if v_id in stored_t.keys():
            v_stored_t = stored_t[v_id]
            v_stored_t.append(t)
            stored_t[v_id] = v_stored_t
        else:
            v_stored_t = []
            v_stored_t.append(t)
            stored_t[v_id] = v_stored_t

        v_type = fields[3]
        if not v_id in stored_types.keys():
            v_stored_type = v_type
            stored_types[v_id] = v_stored_type


# Haversine function to get the distance between the real position and the predicted one.
# This function will be used in the error function
def Haversine(coord1,coord2):
    '''
    use the haversine class to calculate the distance between
    two lon/lat coordnate pairs.
    output distance available in kilometers, meters, miles, and feet.
    example usage: Haversine([lon1,lat1],[lon2,lat2])
    
    '''
    lon1,lat1=coord1
    lon2,lat2=coord2

    R=6371000 # radius of Earth in meters
    phi_1=math.radians(lat1)
    phi_2=math.radians(lat2)

    delta_phi=math.radians(lat2-lat1)
    delta_lambda=math.radians(lon2-lon1)

    a=math.sin(delta_phi/2.0)**2+\
       math.cos(phi_1)*math.cos(phi_2)*\
       math.sin(delta_lambda/2.0)**2
    c=2*math.atan2(math.sqrt(a),math.sqrt(1-a))

    return R*c # output distance in meters


# Use the zip function to help us generate n-grams for any combination of historical and predicted points
def generate_ngrams(s, n):
    return list(zip(*[s[i:] for i in range(n)]))

# Define the error function to be evaluated based on the Haversine output and the RMSE error
def RMSE_HAV(true_lat,true_lon,pred_lat,pred_lon):
    summ = 0
    for i in range(0,len(true_lat)):
        dist = Haversine([true_lon[i],true_lat[i]],[pred_lon[i],pred_lat[i]])
        #print(dist)
        summ = summ + (dist*dist)
    rmse = sqrt(summ/len(true_lat))
    return rmse


# TP evaluation: RMSE based on Haversine distance using the quad_reg function for v3TP   
def traj_pred_RMSE(v_ids,ths,tps):

    print("RMSE (historical points, predicted points): RMSE value")
    
    v0_X = []
    v0_Y = []
    v0_T = []
    for v_id in v_ids:
        v0_X.extend(stored_traj_x[v_id])
        v0_Y.extend(stored_traj_y[v_id])
        v0_T.extend(stored_t[v_id])

    for th in ths:
        print()
        for tp in tps:
            
            tp_X_real = []
            tp_X_pred = []
            tp_Y_real = []
            tp_Y_pred = []
            
            v_X = generate_ngrams(v0_X, th+tp)
            v_Y = generate_ngrams(v0_Y, th+tp)
            v_T = generate_ngrams(v0_T, th+tp)

            for i in range(0, len(v_T)):

                # set historical timestamps from the n-gram with 'th' size
                vct_t = v_T[i][:th] 
                transformed_timestamps = []
                initial_timestamp = math.floor(vct_t[0]/1000)

                for actual_timestamp in vct_t:
                    transformed_timestamps.append(actual_timestamp/1000 - initial_timestamp)
                vct_x = transformed_timestamps

                vct_y = v_X[i][:th]

                # set the predicted timestamp as the second part of n-gram with 'tp' size
                vct_xp = list()
                ft = v_T[i][th:]
                last_t = vct_x[-1]

                for actual_timestamp in ft:
                    vct_xp.append(actual_timestamp/1000 - initial_timestamp)


                # if all 'x' and 'y' values are the same, the object is stopped
                # return same value for predictions
                if (all(dqx_elem == v_X[i][:th][0] for dqx_elem in v_X[i][:th])) and (all(dqy_elem == v_Y[i][:th][0] for dqy_elem in v_Y[i][:th])):
                    fx = [v_X[i][:th][0]] * tp
                    fy = [v_Y[i][:th][0]] * tp

                # if not, calculate x' and y'
                else:
                    # 1a. calculate x'
                    fx = quad_reg(vct_x, vct_y, vct_xp)

                    # 2. find fy
                    vct_y = v_Y[i][:th]
                    # calculate y'
                    fy = quad_reg(vct_x, vct_y, vct_xp)

                # Add this n-gram predictions to the whole object to get later the full RMSE
                tp_X_real.extend(v_X[i][th:])
                tp_X_pred.extend(fx)
                tp_Y_real.extend(v_Y[i][th:])
                tp_Y_pred.extend(fy)
                
            if tp_X_real:
                rmse = RMSE_HAV(tp_X_real,tp_Y_real,tp_X_pred,tp_Y_pred)
                print("RMSE ("+str(th)+","+str(tp)+"): "+str(rmse))
            else:
                print("RMSE ("+str(th)+","+str(tp)+") not enough data")


                
def main():

    if len(sys.argv) != 3:
        print("You should run it as:")
        print("python TP_evaluation.py <workflow.log> <objectIDs (comma separated or 'all')>")
        exit(0)

    # historical points of each trajectory
    ths = [5,10,20,30,40,50]
    # points to predict
    tps = [1,5,10,20,30]

    # read the file and store the trajectory for each object
    infile = sys.argv[1]
    generate_trajectories(infile)

    # set all the objects or a list of objects to calculate the RMSE
    if sys.argv[2] == "all":
        objects_eval = stored_traj_x.keys()
    else:
        objects_eval = sys.argv[2].split(",")

    for object_eval in objects_eval:
        print("ID: "+object_eval)
        print("TYPE: "+stored_types[object_eval])
        traj_pred_RMSE([object_eval],ths,tps)
        print("\n-------------------------\n")

if __name__ == '__main__':
    main()
