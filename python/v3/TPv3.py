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


import pdb

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


def circle_fit(vct_x, vct_y, xin):

#    pdb.set_trace()
    
    x_bar = sum(vct_x)/len(vct_x)
    y_bar = sum(vct_y)/len(vct_y)

    u = list()
    v = list()

    u = [vct_x[i] - x_bar for i in range(len(vct_x))]
    v = [vct_y[i] - y_bar for i in range(len(vct_y))]

    # if all values are equal, return the same x,y coordinates
    if (len(np.unique(u)) == 1) or (len(np.unique(v)) == 1):
        fy = list()
        for x in xin:    
            fy.append(vct_x[-1])
        return fy

    S_uu = 0.0;
    S_vv = 0.0;
    S_uuu = 0.0;
    S_vvv = 0.0;
    S_uv = 0.0;
    S_uvv = 0.0;
    S_vuu = 0.0;

    i = 0
    while i < len(vct_x):
        S_uu += u[i] * u[i];
        S_vv += v[i] * v[i];
        S_uuu += u[i] * u[i] * u[i];
        S_vvv += v[i] * v[i] * v[i];
        S_uv += u[i] * v[i];
        S_uvv += u[i] * v[i] * v[i];
        S_vuu += v[i] * u[i] * u[i];
        i += 1

    v_c = (S_uv * (S_uuu + S_uvv) - S_uu * (S_vvv + S_vuu)) / (2 * (S_uv * S_uv - S_uu * S_vv))
    u_c = (0.5 * (S_uuu + S_uvv) - v_c * S_uv) / S_uu
    x_c = u_c + x_bar
    y_c = v_c + y_bar

    a = u_c * u_c + v_c * v_c + (S_uu + S_vv) / len(vct_x)
    R = math.sqrt(a)
    
    
    # loop to predict multiple values
    fy = list()
    for x in xin:        
        b = -2 * y_c
        xdiff = x - x_c
        c = y_c * y_c - R * R + xdiff * xdiff
        sr = b * b - 4 * c

        yout1 = 0.0 
        yout2 = 0.0

        if sr < 0:
            fy.append(quad_reg(vct_x, vct_y, [x])[-1])  # get y from x
        else:
            yout1 = (-b + math.sqrt(b * b - 4 * c)) / 2
            yout2 = (-b - math.sqrt(b * b - 4 * c)) / 2

        if min(vct_y) <= yout1 <= max(vct_y):
            fy.append(yout1)
        else:
            fy.append(yout2)
            
    return fy


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



def main():

    #infile = sys.argv[1]

    #while file open:
    #content = str()
    #with open(infile) as f:
    #    content = f.read().splitlines()


    # read BSC test data
    path = "data2"

    files = []
    for i in range(50,60): # last test files are in a wrong order
        infile = path + "/"+str(i)+".txt"
        if os.path.exists(infile):
            files.append(path + "/"+str(i)+".txt")
    for i in range(0,50):
        infile = path + "/"+str(i)+".txt"
        if os.path.exists(infile):
            files.append(path + "/"+str(i)+".txt")

            
    for infile in files:
        
        content = str()
        with open(infile) as f:
            content = f.read().splitlines() 

        for line in content:

            fields = line.split()

            v_id = fields[7]

            dqx = deque()
            dqy = deque()
            dqt = deque()
            if v_id in vehicles.keys():
                v = vehicles[v_id]
                dqx = v._dqx
                dqy = v._dqy
                dqt = v._dqt


            traj_x = float(fields[3])
            dqx.append(traj_x)

            traj_y = float(fields[4])
            dqy.append(traj_y)

            t = int(fields[1])
            dqt.append(t)


            if len(dqx) > QUAD_REG_LEN:
                dqx.popleft()
                dqy.popleft()
                dqt.popleft()

            v = Vehicle(dqx, dqy, dqt)

            vehicles[v_id] = v


            # predict if has a minimum amount of data
            if len(dqx) > QUAD_REG_MIN:
                
                # calculate trajectory by v2 method
                fx, fy, ft = traj_pred_v2(v)

                print("v_id: " + str(v_id) + " x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft)) 



if __name__ == '__main__':
    
    main()


