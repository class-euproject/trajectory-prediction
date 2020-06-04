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


QUAD_REG_LEN = 20 # max amount of trajectory points to manage
QUAD_REG_OFFSET = 5 # how many points to predict
QUAD_REG_MIN = 5 # min amount of trajectory points to start predicting
PRED_RANGE_MIL = 1000 # range for predicted points in milliseconds 


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
            if len(dqx) > QUAD_REG_MIN:
                dqx.popleft()
                dqy.popleft()
                dqt.popleft()

                v = Vehicle(dqx, dqy, dqt)
                # calculate trajectory by v2 method
                fx, fy, ft = traj_pred_v2(v)
                print("x: " + str(fx) + " y: " + str(fy) + " t: " + str(ft)) 

    except Exception as e:
        return '%s=Err'% (x, )

    p = '%f %f %f'% (fx, fy, ft)
    print(p) 
    eventsDC.add_prediction(int(x), p)
    return p



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
    
