# -*- coding: utf-8 -*-
"""
This file is to simulate the patient flow using a single-server queue in doctor place.

"""
import utils as H
from Patient import *
from Waiting_Place import *
from Serve_Place import *
from utils.package import *
from utils import parser
import numpy as np
import matplotlib.pyplot as plt

args = parser.parse_args()
p_showup           = args.p_showup
walk_in_rate       = args.walk_in_rate
arrival_rate_blood = args.arrival_rate_blood
arrival_rate_scan  = args.arrival_rate_scan
num_node           = args.num_node
trans_prob         = args.trans_prob
walk_time          = H.walk_time

class Simulation(object):
    '''
    This class, Simulation, is to define the relations or processes and to run the whole simulator.
    '''
    def __init__(self, num_node=num_node, trans_prob=trans_prob, walk_time=walk_time):
        # For statistics
        self.all_patient = []
        self.Save = [[],[],[]]

        # For simulator
        self.now_step = 0.0
        self.sim_end = H.SIM_END
        ## servers
        self.net = Doctor(self, trans_prob = trans_prob)
        ## waiting place
        self.waiting_place = Doctor_Place(self,  0, True, p_showup, walk_in_rate)
        
    # core function: to define the relations or processes and to run the whole simulator.
    def run(self):
        while self.now_step < H.SIM_END:
            # get next event
            self.now_step = self.next_event()
            if self.now_step >= H.SIM_END: 
                break

            patient = self.waiting_place.walkin.get()
            patient = self.net.work(patient)

            # Go home after service (no revisit)

    # get the next event 
    def next_event(self):
        if self.waiting_place.walkin.empty():
            current = H.SIM_END
        else:
            if 300 < self.waiting_place.walkin.queue[0].time[0,0] < 420:
                self.net.finish_time = 420
            current = max(self.waiting_place.walkin.queue[0].time[0,0], self.net.finish_time)
        return current

if __name__ == "__main__":
    data_root = "{}_{}_{}".format(args.dataroot, args.policy, args.ri)
    mkdir_ifmiss(data_root)

    # +++++++++++++++++++++++++++++++++++++++
    mc = args.mc
    waiting_time = []
    total_time = []
    count = []
    
    # Run simulator 
    for i in range(100):
        sim = Simulation()
        sim.run()
        for patient in sim.all_patient:
            waiting_time.append(int(round(patient.time[0][1]-patient.time[0][0])))
            total_time.append(int(round(patient.time[0][2]-patient.time[0][0])))

    # don't remove 0 waiting time
    for i in range(0, max(waiting_time) + 1):
        count.append(waiting_time.count(i)/len(waiting_time))
      
    print(count)
    X = [i for i in range(len(count))]    
    plt.bar(X, count, 1, color = "blue")
    plt.savefig("waiting_all.png")
    
    
    
    
#    # remove 0 waiting time
#    for i in range(1, max(waiting_time) + 1):
#        count.append(waiting_time.count(i)/(len(waiting_time)-waiting_time.count(0)))
#      
#    print(count) 
#    X = [i for i in range(1, max(waiting_time) + 1)]    
#    print(X)
#    plt.bar(X, count, 1, color = "blue")
#    plt.savefig("waiting_except0.png")
    
    
    
    
#    # total time
#    for i in range(min(total_time), max(total_time) + 1):
#        count.append(total_time.count(i)/len(total_time))
#      
#    print(count)
#    X = [i for i in range(len(count))]    
#    plt.bar(X, count, 1, color = "blue")
#    plt.savefig("total.png")
    
# +++++++++++++++++++++++++++++++++++++++   waiting time for each hour  
#    
#    mc = args.mc
#    
#    # Run simulator
#    i = 10
#    waiting_time = []
#    total_time = []
#    count = []
#    for j in range(100):
#        sim = Simulation()
#        sim.run()
#        for patient in sim.all_patient:
#            if patient.time[0][0] // 60 == i:
#                waiting_time.append(int(round(patient.time[0][1]-patient.time[0][0])))
#                total_time.append(int(round(patient.time[0][2]-patient.time[0][0])))
#
#    for k in range(0, max(waiting_time) + 1):
#        count.append(waiting_time.count(k)/len(waiting_time))
#
#    print(i+7, count)
#    X = [a for a in range(len(count))]    
#    plt.bar(X, count, 1, color = "blue")
#    plt.title(str(i+7)+"-"+str(i+8))
#    plt.savefig("waiting"+str(i+7)+"-"+str(i+8)+".png")     
