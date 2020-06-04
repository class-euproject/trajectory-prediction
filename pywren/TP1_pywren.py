# -*- coding: utf-8 -*-
#import pdb

import sys
import numpy as np
from collections import deque
import math
import pywren_ibm_cloud as pywren
from dataclay.api import init, finish
#used for the import 
init()
#used to be added for the jobrunner method 
#from Cars_ns13.classes import Car, Cars

#cars = Cars.get_by_alias('masa_cars13')
from CityNS.classes import *

eventsDC = GlobalEventsInCar.get_by_alias("GEIC")


QUAD_REG_LEN = 20
QUAD_REG_OFFSET = 10


class Vehicle:

    _dqx = deque()
    _dqy = deque()
    _dqt = deque()
    
    def __init__(self, dqx, dqy, dqt):
        
        self._dqx = dqx
        self._dqy = dqy
        self._dqt = dqt
        

#def traj_pred(dqx, dqy, dqt):
def traj_pred(v):
    
    #
    # 1. find fx
    #

    # we are assuming constant time stamps here, which might be fine for our 
    # synthetic data for the demo, but should really be using the actual
    # timestamps
    vct_x = [i for i in range(20)]
    #    vct_t = list(v._dqt)

    # the y vector is the x positions for this calculation of fx
    vct_y = list(v._dqx)

    # quad_reg finds the quadratic equation using least-squares (*** spiros TODO: put link in the actual function)
    # that fits the given values of x: timestamps, y: values of x
    # the returned value is 
    x, fx = quad_reg(vct_x, vct_y, QUAD_REG_LEN+QUAD_REG_OFFSET-1)

    # need to check R2 (rename it to RSquared) and if it's reasonable...
    # ... let's say > 0.8?, then proceed, otherwise...??? lots of outliers?

    #
    # 2. find fy
    #   

    # xy vectors from file:
    vct_x = list(v._dqx)
    vct_y = list(v._dqy)

    # see if can use quad_reg or fit_circle: (*** spiros TODO: explain why fit_circle might be needed)
    if min(vct_x) <= fx <= max(vct_x):
        fy = circle_fit(vct_x, vct_y, fx)
    else:
        fx, fy = quad_reg(vct_x, vct_y, fx)

    return fx, fy


def circle_fit(vct_x, vct_y, xin):

    x_bar = sum(vct_x)/len(vct_x)
    y_bar = sum(vct_y)/len(vct_y)

    u = list() 
    v = list()

    u = [vct_x[i] - x_bar for i in range(len(vct_x))]
    v = [vct_y[i] - y_bar for i in range(len(vct_y))]

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

    b = -2 * y_c
    xdiff = xin - x_c
    c = y_c * y_c - R * R + xdiff * xdiff
    sr = b * b - 4 * c

    yout1 = 0.0 
    yout2 = 0.0

    if sr < 0:
        return quad_reg(vct_x, vct_y, xin)  # get y from x
    else:
        yout1 = (-b + math.sqrt(b * b - 4 * c)) / 2
        yout2 = (-b - math.sqrt(b * b - 4 * c)) / 2

    if min(vct_y) <= yout1 <= max(vct_y):
        return yout1
    else:
        return yout2


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
    x_prime = np.linalg.solve(A, b)

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

    R2 = 1 - SSE/SST;
    
    fx = z
    fy = a * fx**2 + b * fx + c
    
    print("SSE = ", SSE)
    print("SST = ", SST)
    print("R2 = ", R2)
    print("fx = ", fx) 
    return fx, fy


def my_function(x):

    #read file and call quad_reg() on every window of 20 points
    #while file open:
    #content = str()
    #with open(infile) as f:
    #    content = f.read().splitlines() 
    print(sys.getdefaultencoding())
    mylist = eventsDC.eventsById.get(x)
    #TODO fix pickle bug in demo env dataclay 2dev7
    #mylist_c = mylist.dc_clone(recursive=True)
    for c in mylist.events:
        print(c)
    #content = content.splitlines()
    #print(content)
    dqx = deque()
    dqy = deque()
    dqt = deque()

    ##mylist = eventsDC.eventsById.get(x)
    ##print(mylist)
    ##mylist_c = mylist.dc_clone(recursive=True)
    ##for c in mylist_c.events:
    ##    print(c)

    #print(cars)
    #car = cars.get_by_id('1')
    #print("Car Speed= ", car.speed)
#    return str(cars)
    #return car.speed 
#    pdb.set_trace()
     
    if not (len(mylist.events) > QUAD_REG_LEN):
        return x
    try:
        for event in mylist.events:
            dqx.append(float(event.pos.lon))#float(fields[fields.index('loc_x')+1]))
            dqy.append(float(event.pos.lat))#float(fields[fields.index('loc_y')+1]))
            dqt.append(0)#int(event.dt.timestamp()))#int(fields[fields.index('t')+1]))
            if len(dqx) > QUAD_REG_LEN:
                dqx.popleft()
                dqy.popleft()
                dqt.popleft()

                v = Vehicle(dqx, dqy, dqt)
                fx, fy = traj_pred(v)
    #            fy = traj_pred(dqx, dqy, dqt)
                print(fy)
    except Exception as e:
        return '%s=Err'% (x, )

    p = '%f %f'% (fx, fy)
    print(p) 
    eventsDC.add_prediction(int(x), p)
    return p

    #    calcVehiclePos(last20) // returns the position of the vehicle after 10 timestamps, prediction
    #       ...or can call it TC(last20), or TrajectoryPrediction(last20)
    #    // 1) calls quad_reg(last20) to calculate pos x' after 10 timestamps
    #    // 2) if x' not within range of ncurrent xs, call quad_reg(last20) to calculate y' after 10 timestamps at x'
    #    // 3) else, call fit_circle(last20) to calcualte y' after 10 timestamps at x'
    #    // 4) return (x', y')
    #    



if __name__ == '__main__':
    
    iterdata = eventsDC.eventsById.keys()
    #iterdata = list(iterdata)[0:2]

    iterdata1 = []
    #print(len(iterdata))
    #l = 0
    for oid in iterdata:
        ll = eventsDC.eventsById.get(oid)
        size = len(ll.events)
#        print("%s %d" % (oid, size))
        if size > 20:
            iterdata1.append(oid)
#    print(len(iterdata1))

    iterdata = iterdata1[0:10]
#    print(len(iterdata)) 
#    for oid in iterdata:
#        print(oid)

    #print("size > 20: %d" % l)

    #iterdata1 = iterdata.dc_clone()
    #print(iterdata)
    #print(eventsdc.eventsbyid)

    ##mylist = eventsDC.eventsById.get('1867975069')
    #print(mylist)
    #print("---------------------------")

    ##mylist_c = mylist.dc_clone(recursive=True)
    ##print(mylist_c)
    ##for e in mylist_c.events:
    ##    print(e)    

    #iterdata = ['1350490027', '1967513926']
    #iterdata = [[car1,'1350490027'], [car2, '1967513926'], [car2, '1967513926'], [car2, '1967513926'], [car2, '1967513926']]
    eventsDC.tpById = {}
    #print(eventsDC.tpById)
    config = {
          'pywren': {'runtime': 'sadek_pywren_dc_demo_1.0', 'storage_bucket': 'pywren-sadekj', 'storage_prefix': 'pywren.jobs'},
          #'pywren': {'storage_bucket': 'pywren-sadekj', 'storage_prefix': 'pywren.jobs'},
          'ibm_cf': {'endpoint': 'https://192.168.7.40:31001',
                     'namespace': '_',
                     'api_key': '23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP',
                    },
          'ibm_cos': {'endpoint': 'http://192.168.131.155:9000',
                      'access_key': 'admin',
                      'secret_key': 'admin1234',
                      }}
    import time
    pw = pywren.ibm_cf_executor(config=config)
    for i in range(10):
        start = time.time()
        pw.map(my_function, iterdata)
        res = pw.get_result()
        #print(len(res))
        #for r in res:
        #    print(r)
        #print(len(eventsDC.tpById))
        for k, v in eventsDC.tpById.items():
            print('Object Id= %d Prediction= %s' % (k,v))
        end = time.time()
        #print(end-start)

    
    finish()

#if __name__ == '__main__':
    
#    main()
    
