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


import os
import sys
import numpy as np
from collections import deque
import math


QUAD_REG_LEN = 20 # max amount of trajectory points to manage
QUAD_REG_MIN = 5 # min amount of trajectory points to start predicting

# max amount of trajectory points to manage per class
QUAD_REG_LEN_DICT = {
    "person":50,
    "car":40,
    "truck":40,
    "bus":40,
    "motor":40,
    "bike":40,
    "rider":50,
    "train":40
}

# min amount of trajectory points to start predicting per class
QUAD_REG_MIN_DICT = {
    "person":20,
    "car":10,
    "truck":10,
    "bus":10,
    "motor":10,
    "bike":10,
    "rider":20,
    "train":10
}

QUAD_REG_OFFSET = 5 # how many points to predict
PRED_RANGE_MIL = 1000 # range for predicted points in milliseconds 
PRECISION = 9


class Vehicle:

    _dqx = None #deque() Currently there no need to instantiate queue as it is passed in constructor
    _dqy = None #deque()
    _dqt = None #deque()
    
    def __init__(self, dqx, dqy, dqt):
        self._dqx = dqx
        self._dqy = dqy
        self._dqt = dqt
        

def traj_pred_v3(dqx, dqy, dqt,
                 reg_offset=QUAD_REG_OFFSET,
                 range_mil=PRED_RANGE_MIL):
    
    #
    # 1. find fx
    #
    
    # assuming not constant time stamps here, is necessary to
    # transform timestamps to small integers starting at 0 (each unit is 1 second)
    # to be used correctly in next formulas
    vct_t = list(dqt)
    transformed_timestamps = []
    initial_timestamp = math.floor(vct_t[0]/1000)
    
    #print(vct_t[0])
    #print(initial_timestamp)
    
    for actual_timestamp in vct_t:
        transformed_timestamps.append(actual_timestamp/1000 - initial_timestamp)
    vct_x = transformed_timestamps
    
    # the y vector is the x positions for this calculation of fx
    vct_y = list(dqx)

    # quad_reg finds the quadratic equation using least-squares 
    # that fits the given values of x: timestamps, y: values of x
    # the returned value is 
    #fx = quad_reg(vct_x, vct_y, QUAD_REG_LEN+QUAD_REG_OFFSET-1)
    
    # generate array of timestamps to predict and original predicted timestamps
    vct_xp = list()
    ft = list()
    last_t = vct_x[-1]
    
    for i in range(1,reg_offset+1):
        vct_xp.append(last_t + i*(range_mil/1000))
        ft.append(vct_t[-1] + i*range_mil)    
    
    
    # if all 'x' and 'y' values are the same, the object is stopped
    # return same value for predictions
    if (all(dqx_elem == dqx[0] for dqx_elem in dqx)) and (all(dqy_elem == dqy[0] for dqy_elem in dqy)):
        fx = [dqx[-1]] * reg_offset
        fy = [dqy[-1]] * reg_offset
    
    # if not, calculate x' and y'
    else:
        # 1a. calculate x'
        fx = quad_reg(vct_x, vct_y, vct_xp)
    
        # need to check R2 (rename it to RSquared) and if it's reasonable...
        # ... let's say > 0.8?, then proceed, otherwise...??? lots of outliers?

        #
        # 2. find fy
        #   

        # the y vector is the y positions for this calculation of fx
        vct_y = list(dqy)
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
    
    #SSE = 0.0
    #SST = 0.0
    
    #y_ave = np.average(vy)
    
    #i = 0
    #while i < len(vx):
    #    SST += (vy[i] - y_ave)**2
    #    SSE += (vy[i] - a*vx[i]**2 - b*vx[i] - c)**2
    #    i += 1

    #R2 = 1 - SSE/SST
    
    #print("SSE = ", SSE)
    #print("SST = ", SST)
    #print("R2 = ", R2)
    
    
    # loop to predict multiple values
    fy = list()
    for x in z:    
        fx = x
        fy.append(a * fx**2 + b * fx + c)
        
    return fy
