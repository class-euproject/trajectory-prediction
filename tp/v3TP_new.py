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
# @author: Adrian Arroyo - ATOS
#


import os
import sys
import numpy as np
from collections import deque
import math
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import cv2

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
GEO_MOD =  [10.9258325726001146449562, 0.0000012929374284312734, 0.0000000000000000000000, 44.6595471971102497832362, 0.0000000000000000000000, -0.0000008796952010381291]
GEO_OWEN = [-78.9316336640000031366071, 0.0000010000000000000000, 0.0000000000000000000000, 35.0315191749999996773113, 0.0000000000000000000000, -0.0000010000000000000000]

IMAT_DICT = {'20939': np.array( [[ 1.0312843e+00 , 1.9871530e-01, -7.8963071e+03], \
                                    [-7.3551707e-02,  7.9373951e-04,  5.6017670e+02], \
                                    [-8.3895675e-06, -2.2179075e-04,  1.1082504e+00]]),
                 '2405': np.array(  [[ 1.4855428e-01, -3.1246930e-01,  1.1134888e+02], \
                                    [ 2.0982297e-02, -3.2458495e-02,  2.0829369e+01], \
                                    [-1.6552572e-04, -2.7494816e-04,  6.0363925e-01]]),
                 '6310': np.array(  [[ 1.71662995e+00,  3.33694227e-01, -4.35023052e+03], \
                                    [-5.09825344e-02,  4.15920917e-02,  1.52769839e+01], \
                                    [ 3.55175312e-04, -4.63087247e-04,  1.27697288e+00]]),
                 '634': np.array(   [[ 4.9490247e+00, -1.7986463e-01, -1.4399846e+04], \
                                    [ 4.2591566e-01, -2.8731579e-01, -7.1679822e+02], \
                                    [ 1.4120782e-03, -1.4354429e-03, -4.4839436e-01]]),
                 '637': np.array(   [[-1.39837170e+00,  8.17328274e-01,  1.69785229e+03], \
                                    [-1.11902215e-01,  8.78771693e-02,  1.62084751e+01], \
                                    [-2.97075341e-04,  6.94441842e-04, -1.41250253e+00]]),
                '6311': np.array(   [[ 4.6438417e+00,  2.7147813e+00, -2.1480926e+04], \
                                    [ 1.3239883e+00, -1.2577654e-01, -5.4419595e+03], \
                                    [ 6.2101847e-03, -1.1107889e-03, -2.4130587e+01]]),
                '6312': np.array(   [[-3.7839601e+00,  4.5093307e+00 , 1.0689723e+04], \
                                    [-2.5738266e-01,  1.5883133e+00 ,-7.4461774e+02], \
                                    [-5.0236052e-04,  7.9181716e-03 ,-5.9862475e+00]]),
                '6313': np.array(   [[-2.9730530e+00, -1.8050245e+00,  1.3747679e+04], \
                                    [-8.1895161e-01,  1.2549882e-01,  2.9976626e+03], \
                                    [-4.5699980e-03,  1.3139079e-03,  1.6950178e+01]]),
                '6314': np.array(   [[ 1.2576976e+00, -3.7231266e+00, -1.3202415e+03], \
                                    [-4.7465152e-01, -8.3026093e-01,  2.5384727e+03], \
                                    [-2.8526296e-03, -4.3438966e-03 , 1.5666543e+01]]),
                '6315': np.array(   [[ 1.4574182e+00,  1.9768994e+00, -8.9676152e+03] ,\
                                    [ 9.5025852e-02,  2.5807818e-02, -4.7650812e+02], \
                                    [ 7.8109716e-04,  7.0775590e-05, -2.7684593e+00]]),
                '10218': np.array(  [[-4.6705031e-01, -4.1387053e+00,  2.0901955e+04], \
                                    [ 1.2866619e-01, -8.2636952e-02, -4.8830710e+02], \
                                    [-8.1619096e-04, -3.2475838e-04,  7.7563605e+00]]),
                '20932': np.array(  [[ 1.2776829e-01, -5.8261555e-02, -5.8179095e+02], \
                                    [ 1.5170943e-02 ,-7.1426108e-03,-7.0920525e+01], \
                                    [ 1.1285656e-05, -8.3504325e-05 , 3.0716157e-01]]),
                '20936': np.array(  [[ 8.7396008e-01 ,-2.2188594e+00 , 2.2125654e+03], \
                                    [-1.3522908e-01, -4.1281156e-02 , 9.5611444e+02], \
                                    [-1.0041756e-03, -8.1070681e-04,  9.8019505e+00]]),
                '20937': np.array(  [[-3.6492407e-02,  3.7385684e-02,  1.0984574e+02], \
                                    [ 9.9460303e-04, -9.3211461e-04, -5.8030586e+00], \
                                    [ 6.5231002e-06,  2.8232673e-05 ,-1.4919072e-01]]),
                '20940': np.array(  [[-1.0171498e+00, -7.0630664e-01,  1.0245919e+04], \
                                    [ 8.5871615e-02,  2.8988831e-02, -6.1519476e+02], \
                                    [-1.6709240e-04,  1.6546916e-04,  3.8814998e-01]])        

                }


QUAD_REG_OFFSET = 8 # how many points to predict
PRED_RANGE_MIL = 500 # range for predicted points in milliseconds 
PRECISION = 9
REGRESSION_DEGREES = 1 # number of degrees of the polynomials to use in the regression process (linear: 1, quadratic: 2, etc.)
REGRESSION_METHOD = "numpy" # type of method to use to compute reggression. Valid are: "numpy" or "sklearn"

class Vehicle:

    _dqx = None #deque() Currently there no need to instantiate queue as it is passed in constructor
    _dqy = None #deque()
    _dqt = None #deque()
    
    def __init__(self, dqx, dqy, dqt):
        self._dqx = dqx
        self._dqy = dqy
        self._dqt = dqt
        

def traj_pred_v3(dqx, dqy, dqt, w, h,source_id,
                 reg_offset=QUAD_REG_OFFSET,
                 range_mil=PRED_RANGE_MIL
                 ):
    threshold_mov=0.5
    reg_method = 'numpy'
    reg_deg = 1
    static = False
    
    try:
        InvProjMat = IMAT_DICT[source_id] 
    except (KeyError):
        source_id = '0'
    
    #InvProjMat = IMAT_DICT[source_id]
     
    #print(InvProjMat)
    if (source_id == '2405'):
        adfGeoTransform = np.array(GEO_OWEN)
    else:
        adfGeoTransform = np.array(GEO_MOD)
    
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
    
    # check if static object based on boxes sizes
    if (source_id != '0'):
        static = is_object_static (dqx[-1],dqy[-1],w,h,threshold_mov,dqx,dqy,InvProjMat, adfGeoTransform)
    
    # if all 'x' and 'y' values are the same, the object is stopped
    # return same value for predictions
    if ((all(dqx_elem == dqx[0] for dqx_elem in dqx)) and (all(dqy_elem == dqy[0] for dqy_elem in dqy)) or static):
        fx = [dqx[-1]] * reg_offset
        fy = [dqy[-1]] * reg_offset

    # if not, calculate x' and y'
    else:
        # if (source_id == '' | source_id == '' | source_id == '' |):
        # reg_deg = 2
        # 1a. calculate x'
        #if reg_method == "numpy":
        fx = numpy_poly_reg(vct_x, vct_y, vct_xp, reg_deg)
        #elif reg_method == "sklearn":
        #    fx = sklearn_poly_reg(vct_x, vct_y, vct_xp, reg_deg)
        
    
        # need to check R2 (rename it to RSquared) and if it's reasonable...
        # ... let's say > 0.8?, then proceed, otherwise...??? lots of outliers?

        #
        # 2. find fy
        #   

        # the y vector is the y positions for this calculation of fx
        vct_y = list(dqy)
        # vct_x (timestamps) and vct_xp (predicted timestamps) are the same
    
        # calculate y'
        #if reg_method == "numpy":
        fy = numpy_poly_reg(vct_x, vct_y, vct_xp, reg_deg)
        #elif reg_method == "sklearn":
        #    fy = sklearn_poly_reg(vct_x, vct_y, vct_xp, reg_deg)
    
    # now the output is 3 arrays for timestamps, x and y positions
    return fx, fy, ft

def numpy_poly_reg(vx, vy, z, degrees):
    """Computes the polynomial regression of vx and vy, according to the number of degrees 
        of the polynomials using numpy and least squares. Then, predicts the next values 
        according to input timestamps (z).

        Args:
            vx (list): x-axis input data for regression.
            vy (list): y-axis input data for regression.
            z (list): Input data (timestamps) for prediction.
            degrees (int): number of degrees of the fitting polynomials of the regression.
            
        Returns:
            fy: predicted fy according to input z
    """
    # This will compute the regression using least squares. From the returned object, we can get the coefficients.
    reg = np.polynomial.polynomial.Polynomial.fit(vx, vy, deg=degrees)

    fy = list()
    for fx in z:    
        computed_fy = 0.0
        for i in range(degrees+1):
            # Coefficients are in reverse order (for 2 degrees: coef[0]=c, coef[1]=b, coef[2]=a): y = a*x^2 + b*x + c
            computed_fy += reg.convert().coef[i] * fx**i
        fy.append(computed_fy)
        
    return fy

def sklearn_poly_reg(vx, vy, z, degrees):
    """Computes the polynomial regression of vx and vy, according to the number of degrees 
        of the polynomials using scikit learn. Then, predicts the next values according to 
        input timestamps (z).

        Args:
            vx (list): x-axis input data for regression.
            vy (list): y-axis input data for regression.
            z (list): Input data (timestamps) for prediction.
            degrees (int): number of degrees of the fitting polynomials of the regression.
            
        Returns:
            fy: predicted fy according to input z
    """
    # This is the polynomial.
    poly = PolynomialFeatures(degree = degrees)
    # Transform input data
    vx_poly = poly.fit_transform(np.array(vx).reshape(-1, 1))
    # Fit polynomial to input data = compute polynomial equation
    poly.fit(vx_poly, vy)
    # This will do the regression using scikit learn. 
    reg = LinearRegression()
    reg.fit(vx_poly, vy)

    fy = list()
    for fx in z:    
        computed_fy = reg.predict(poly.fit_transform(np.array(fx).reshape(-1, 1)))
        fy.append(computed_fy[0])
        
    return fy

# First version: quadratic regression (2 degrees: quadratic)
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
