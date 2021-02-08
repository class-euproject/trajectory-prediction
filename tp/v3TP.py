# -*- coding: utf-8 -*-

# /*
#  * Copyright (C) 2019  Atos Spain SA. All rights reserved.
#  *
#  * This file is part of pCEP.
#  *
#  * pCEP is free software: you can redistribute it and/or modify it under the
#  * terms of the Apache License, Version 2.0 (the License);
#  *
#  * http://www.apache.org/licenses/LICENSE-2.0
#  *
#  * The software is provided "AS IS", without any warranty of any kind, express or implied,
#  * including but not limited to the warranties of merchantability, fitness for a particular
#  * purpose and noninfringement, in no event shall the authors or copyright holders be
#  * liable for any claim, damages or other liability, whether in action of contract, tort or
#  * otherwise, arising from, out of or in connection with the software or the use or other
#  * dealings in the software.
#  *
#  * See README file for the full disclaimer information and LICENSE file for full license
#  * information in the project root.
#  *
#  * Authors:  Atos Research and Innovation, Atos SPAIN SA
#  */


import os
import sys
import numpy as np
from collections import deque
import math
import statistics
import cv2
import numpy as np


QUAD_REG_LEN = 50 # max amount of trajectory points to manage
QUAD_REG_OFFSET = 5 # how many points to predict
QUAD_REG_MIN = 10 # min amount of trajectory points to start predicting
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
                 w, h, # last w and h box sizes
                 InvProjMat, adfGeoTransform, # projection matrix and geotransform
                 reg_offset=QUAD_REG_OFFSET,
                 range_mil=PRED_RANGE_MIL,
                 threshold_mov=0.3):
    
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

    # generate array of timestamps to predict and original predicted timestamps
    vct_xp = list()
    ft = list()
    last_t = vct_x[-1]
    
    for i in range(1,reg_offset+1):
        vct_xp.append(last_t + i*(range_mil/1000))
        ft.append(vct_t[-1] + i*range_mil)    

    # check if static object based on boxes sizes
    static = is_object_static (dqx[-1],dqy[-1],w,h,threshold_mov,dqx,dqy,InvProjMat, adfGeoTransform)

    # if all 'x' and 'y' values are the same, or static, the object is stopped
    # return same value for predictions
    if ((all(dqx_elem == dqx[0] for dqx_elem in dqx)) and (all(dqy_elem == dqy[0] for dqy_elem in dqy)) or static):
        fx = [dqx[len(dqx)-1]] * reg_offset
        fy = [dqy[len(dqx)-1]] * reg_offset
    
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


def GPS2Pixel(lat, lon, InvProjMat, adfGeoTransform):
    x = (lon - adfGeoTransform[0]) / adfGeoTransform[1]
    y = (lat - adfGeoTransform[3]) / adfGeoTransform[5]

    mapPixels = np.array([[[x, y]]], dtype='float32')
    imgPixels = cv2.perspectiveTransform(mapPixels, InvProjMat)

    # print("At GPS2Pixel: ("+str(lat)+","+str(lon)+")->("+str(imgPixels[0][0][0])+","+str(imgPixels[0][0][1])+")")
    return int(imgPixels[0][0][0]), int(imgPixels[0][0][1])

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

