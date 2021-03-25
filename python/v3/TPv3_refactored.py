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
# Created on 4 Jun 2020
# @author: Jorge Montero - ATOS
#


import os
import sys
import numpy as np
from collections import deque
import math


QUAD_REG_LEN = 20 # max amount of trajectory points to manage
QUAD_REG_OFFSET = 5 # how many points to predict
QUAD_REG_MIN = 5 # min amount of trajectory points to start predicting
PRED_RANGE_MIL = 200 # range for predicted points in milliseconds 

vehicles = {} # store vehicles as many could be processed at the same time



class Vehicle:

    _dqx = deque()
    _dqy = deque()
    _dqt = deque()
    
    def __init__(self, dqx, dqy, dqt):
        
        self._dqx = dqx
        self._dqy = dqy
        self._dqt = dqt
        

#def traj_pred(dqx, dqy, dqt):
def traj_pred_v2(v):
    
    #
    # 1. find fx
    #
    
    # assuming not constant time stamps here, is necessary to
    # transform timestamps to small integers starting at 0 (each unit is 1 second)
    # to be used correctly in next formulas
    vct_t = list(v._dqt)    
    transformed_timestamps = []
    initial_timestamp = math.floor(vct_t[0]/1000)
    
    #print(vct_t[0])
    #print(initial_timestamp)
    
    for actual_timestamp in vct_t:
        transformed_timestamps.append(actual_timestamp/1000 - initial_timestamp)
    vct_x = transformed_timestamps
    
    # the y vector is the x positions for this calculation of fx
    vct_y = list(v._dqx)

    # quad_reg finds the quadratic equation using least-squares 
    # that fits the given values of x: timestamps, y: values of x
    # the returned value is 
    #fx = quad_reg(vct_x, vct_y, QUAD_REG_LEN+QUAD_REG_OFFSET-1)
    
    # generate array of timestamps to predict and original predicted timestamps
    vct_xp = list()
    ft = list()
    last_t = vct_x[-1]
    
    for i in range(1,QUAD_REG_OFFSET+1):
        vct_xp.append(last_t + i*(PRED_RANGE_MIL/1000))
        ft.append(vct_t[-1] + i*PRED_RANGE_MIL)    
    
    # calculate x'
    fx = quad_reg(vct_x, vct_y, vct_xp)
    
    # need to check R2 (rename it to RSquared) and if it's reasonable...
    # ... let's say > 0.8?, then proceed, otherwise...??? lots of outliers?

    #
    # 2. find fy
    #   

    # the y vector is the y positions for this calculation of fx
    vct_y = list(v._dqy)
    # vct_x (timestamps) and vct_xp (predicted timestamps) are the same
    
    # calculate y'
    fy = quad_reg(vct_x, vct_y, vct_xp)
    
    # now the output is 3 arrays for timestamps, x and y positions
    return fx, fy, ft


def quad_reg(vx, vy, z):

    sum_xi2_by_yi = 0.0 
    sum_xi_by_yi = 0.0 
    sum_yi = 0.0
    sum_xi = 0.0 
    sum_xi2 = 0.0 
    sum_xi3 = 0.0 
    sum_xi4 = 0.0
    
    i = 0
    while i < len(vx):
        sum_xi += vx[i];
        sum_xi2 += vx[i]**2
        sum_xi3 += vx[i]**3
        sum_xi4 += vx[i]**4
        sum_yi += vy[i]
        sum_xi_by_yi += vx[i] * vy[i];
        sum_xi2_by_yi += vx[i]**2 * vy[i];
        i += 1

    A = np.array([[sum_xi4, sum_xi3, sum_xi2], [sum_xi3, sum_xi2, sum_xi], [sum_xi2, sum_xi, len(vx)]])
    b = np.array([sum_xi2_by_yi, sum_xi_by_yi, sum_yi])
    try:
        x_prime = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        x_prime = np.linalg.lstsq(A, b)[0] # for singular matrix exceptions

    a = x_prime[0]
    b = x_prime[1]
    c = x_prime[2]
    
    SSE = 0.0
    SST = 0.0
    
    y_ave = np.average(vy)
    
    i = 0
    while i < len(vx):
        SST += (vy[i] - y_ave)**2
        SSE += (vy[i] - a*vx[i]**2 - b*vx[i] - c)**2
        i += 1

    R2 = 1 - SSE/SST
    
    #print("SSE = ", SSE)
    #print("SST = ", SST)
    #print("R2 = ", R2)
    
    
    # loop to predict multiple values
    fy = list()
    for x in z:    
        fx = x
        fy.append(a * fx**2 + b * fx + c)
        
    return fy






# load/store functions will work with the class "Vehicle"

# load an object from minio using the v_id
def load_object_minio(v_id):
    vehicle = function_from_minio(v_id) # TODO: minio function
    return vehicle

# store a Vehicle object in minio
def store_object_minio(v):
    function_to_minio(v) # TODO: minio function
    



# add data (x,y,t) to a vehicle object
# using using the variable QUAD_REG_LEN as threshold
def add_data_to_object(v, x, y, t, threshold):
    dqx = v._dqx
    dqy = v._dqy
    dqt = v._dqt

    dqx.append(x)
    dqy.append(y)
    dqt.append(t)
    
    # remove data using the variable QUAD_REG_LEN
    if len(dqx) > threshold:
        dqx.popleft()
        dqy.popleft()
        dqt.popleft()

    v = Vehicle(dqx, dqy, dqt)
    
    return v



# do something (store, append, ...) with the vehicle object and its predictions
def something_with_predictions(v, fx, fy, ft):
    # store only the latest predictions in minio??


# calculate the predictions for a vehicle object using QUAD_REG_MIN as threshold
def object_prediction(v, threshold):
    # predict if has a minimum amount of data
    if len(v._dqx) > threshold: 
        # calculate trajectory by v2 method
        fx, fy, ft = traj_pred_v2(v)
        print("v_id: " + str(v_id) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft))

        something_with_predictions(v, fx, fy, ft)
    



# manage the event coming from dataclay and return the data to be processed
def get_data_from_event():
    # TODO
    # return object id, coordinates, and timestamp
    return v_id,x,y,t



    
# main using minio functions
def main():
    
    v_id,x,y,t = get_data_from_event() # TODO
    
    v = load_object_minio(v_id)
    
    v = add_data_to_object(v, x, y, t, QUAD_REG_LEN)
    
    store_object_minio(v)
    
    object_prediction(v, QUAD_REG_MIN)



if __name__ == '__main__':
    
    main()


