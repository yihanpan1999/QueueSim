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

# waiting time 的统计量用这段代码
#    mc = args.mc
#    waiting_time = []
#
#    # Run simulator 
#    for i in range(100):
#        sim = Simulation()
#        sim.run()
#        for patient in sim.all_patient:
#            waiting_time.append(patient.time[0][1]-patient.time[0][0])
#
#    print(np.mean(waiting_time))
#    print(np.median(waiting_time))
#    print(np.std(waiting_time))   
# -------------------------------------------------------------------------
    
# 分时段的 average waiting time 用这段代码 (hour=0代表7点，hour=10代表17点)
    mc = args.mc
    wait_byHour = []

    # Run simulator
    for hour in range(11):
        waiting_time = []
        for i in range(100):
            sim = Simulation()
            sim.run()
            for patient in sim.all_patient:
                if 60*hour < patient.time[0][0] < 60*(hour+1):
                    waiting_time.append(patient.time[0][1]-patient.time[0][0])
        wait_byHour.append(np.mean(waiting_time))

    # plot the figure
    empirical = [21.4580236381505, 16.340242148865443, 19.323295097701134,
                 19.622087877720812, 20.80573309448155, 52.91604257239057, 
                 36.17085924170742, 25.43721169116396, 21.41483412504384, 
                 10.093030293010619, 3.7732421296296303]
    hour = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
    print(wait_byHour)
    plt.plot(hour, wait_byHour)
    plt.plot(hour, empirical)
    plt.legend(["Simulation", "Empirical"], fontsize = 13, loc = "best")
    plt.title("mean waiting time", fontsize = 15)
    plt.savefig("waiting.png")    
#----------------------------------------------------------------------------
    
# waiting time 的柱状图用这段代码 (只看小于60分钟的部分)
#    mc = args.mc
#    waiting_time = []
#    count = []
#
#    # Run simulator 
#    for i in range(100):
#        sim = Simulation()
#        sim.run()
#        for patient in sim.all_patient:
#            waiting_time.append(int(round(patient.time[0][1]-patient.time[0][0])))
#
#    for i in range(0, 60):
#        count.append(waiting_time.count(i)/len(waiting_time))
#      
#    print(count)
#    X = [i for i in range(len(count))]    
#    plt.bar(X, count, 1, color = "blue")
#    plt.title("waiting time distribution", fontsize = 15)
#    plt.savefig("wait_dist.png")
# -------------------------------------------------------------------------    
    
# average queue length 的统计量用这段代码
#    mc = args.mc
#    avg_Qlen = []
#    
#    # Run simulator 
#    for i in range(100):
#        waiting_time = []
#        sim = Simulation()
#        sim.run()
#        for patient in sim.all_patient:
#            waiting_time.append(patient.time[0][1]-patient.time[0][0])
#        avg_Qlen.append(sum(waiting_time)/660)  
#
#    print(np.mean(avg_Qlen))
#    print(np.median(avg_Qlen))
#    print(np.std(avg_Qlen))
#-----------------------------------------------------------------------------
    
# 分时段的 average queue length 用这段代码 (hour=0代表7点，hour=10代表17点)
#    mc = args.mc
#    avg_Qlen_byHour = []
#    
#    # Run simulator 
#    for hour in range(11):
#        avg_Qlen = []
#        for i in range(100):
#            waiting_time = []
#            sim = Simulation()
#            sim.run()
#            for patient in sim.all_patient:
#                if 60*hour < patient.time[0][0] < 60*(hour+1):
#                    waiting_time.append(min(60*(hour+1), patient.time[0][1])-patient.time[0][0])
#            avg_Qlen.append(sum(waiting_time)/60)
#        avg_Qlen_byHour.append(np.mean(avg_Qlen))
#
#    # plot the figure
#    empirical = [1.09, 2.95, 3.08, 3.08, 1.74, 0.51, 1.86, 4.13, 2.8, 1.19, 0.06]
#    hour = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
#    print(avg_Qlen_byHour)
#    plt.plot(hour, avg_Qlen_byHour)
#    plt.plot(hour, empirical)
#    plt.legend(["Simulation", "Empirical"], fontsize = 13, loc = "best")
#    plt.title("mean average queue length", fontsize = 15)
#    plt.savefig("queue.png")
#-----------------------------------------------------------------------------
