import utils as H
from Patient import *
from Waiting_Place import *
from Serve_Place import *
from utils.package import *
from utils import parser

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
        self.Patient_arrive_blood = []
        self.Patient_served_blood = []
        self.Walk_in_arrive_blood = []
        self.Walk_in_served_blood = []
        self.Patient_arrive_scan = []
        self.Patient_served_scan = []
        self.Walk_in_arrive_scan = []
        self.Walk_in_served_scan = []
        self.Save = [[],[],[]]

        # For simulator
        self.now_step = 0.0
        self.sim_end = H.SIM_END
        ## servers
        self.net = [[Doctor(self, trans_prob = trans_prob) for _ in range(num_node[0])], 
                    [Blood_Service(self) for _ in range(num_node[1])], 
                    [Scan_Service(self) for _ in range(num_node[2])]]
        ## waiting place
        self.waiting_place = [Doctor_Place(self,  0, True, p_showup, walk_in_rate), 
                              Waiting_Place(self, 1, True, arrival_rate_blood), 
                              Waiting_Place(self, 2, True, arrival_rate_scan)]
        self.walk_time = walk_time

    def record_queue(self):
        H.WALK_IN_ARRIVAL += sim.waiting_place[0].Walk_in_times
        H.WALK_IN_SERVED += sim.waiting_place[0].Walk_in_served_times
        H.REVISIT_ARRIVAL += sim.waiting_place[0].Revisit_times
        H.REVISIT_SERVED += sim.waiting_place[0].Revisit_served_times
        H.COMBINE_ARRIVAL += sim.waiting_place[0].Arrive_times
        H.COMBINE_SERVED += sim.waiting_place[0].Served_times
        # ----------------------------------------------------- #
        H.BLOOD_ARRIVAL += sim.waiting_place[1].Arrival_time
        H.BLOOD_SERVED += sim.waiting_place[1].Served_time
        # ----------------------------------------------------- #
        H.SCAN_ARRIVAL += sim.waiting_place[2].Arrival_time
        H.SCAN_SERVED += sim.waiting_place[2].Served_time
        
    # core function: to define the relations or processes and to run the whole simulator.
    def run(self):
        while self.now_step < H.SIM_END:
            # get next event
            self.now_step, service_type, service_id = self.next_event()
            if self.now_step >= H.SIM_END: 
                break

            # the patient leave the waiting place and will be served.
            patient = self.waiting_place[service_type].send_patient() # policy 2: balance walk-in and revisit queue

            before_State = patient.isRevisit() 
            patient = self.net[service_type][service_id].work(patient)
            
            # transport
            TO = None
            if before_State and service_type == 0: # before: revisit patient; now: served by doctor; so: go home 
                TO = 2019 # GO HOME
            else:
                if len(patient.checklist) == 0: # no check item to be done
                    if len(patient.check_list) == 0: # do not need to do some check
                        TO = 2020 # GO HOME directly
                    else: # he/she has finished all check items
                        TO = 0 # GO DOCTOR (revisit)
                        if patient.time[0, -1] == self.net[0][0].id: # this doctor's patient?
                            last = self.argmax_report_time(patient) # which test is later
                            complete_time = patient.time[last, 3] + self.walk_time[last, 0] # must walk for report
                            patient.time[-1, 0] = complete_time # decide when to see the doctor, arrival time
                            self.waiting_place[TO].add_patient(patient, True) # push to the doctor queue
                        else: 
                            TO = 2000 # GO OTHER DOCTOR
                else: # still have some test
                    TO = patient.checklist.pop(0) # next test
                    patient.time[TO, 0] = patient.time[service_type, 2] + self.walk_time[service_type, TO] # arrive time
                    self.waiting_place[TO].add_patient(patient) # push to the queue
        
        # For statistics
#        doctor_cost = self.net[0][0].cost()
#        H.IDLE_COST.append(doctor_cost[0])
#        H.OVERTIME_COST.append(doctor_cost[1])

    # get the next event 
    def next_event(self):
        service_type, service_id = None, None
        current = H.SIM_END
        for i in range(len(self.net)):
            expected_time = self.waiting_place[i].next_patient()
            for j in range(len(self.net[i])):
                temp = max(expected_time, self.net[i][j].finish_time)
                if temp < current:
                    service_type, service_id = i, j
                    current = temp
        return current, service_type, service_id

    # to find the lastest report
    def argmax_report_time(self, patient):
        idx = None
        M = -1
        for i in range(1, len(patient.time[:-1, 3])):
            if patient.time[i, 3] is not None and patient.time[i, 3] > M:
                M = patient.time[i, 3]
                idx = i
        assert M >= 0
        return idx



if __name__ == "__main__":
    data_root = "{}_{}_{}".format(args.dataroot, args.policy, args.ri)
    mkdir_ifmiss(data_root)

    # +++++++++++++++++++++++++++++++++++++++
    mc = args.mc

    # Run simulator (only two rows)
    sim = Simulation()
    sim.run()


    # print(sim.net[0][0].realization)
    H.waste_time(sim)
    H.utility_measure(sim, mc)

    fig, axs = plt.subplots(1,1, figsize=(20, 5))
#    plt.plot(sim.net[0][0].realization,'co')
    # plt.axvline(x=H.WORK_END/H.SLOT, color='k',linestyle='dashed', linewidth=2)
    # plt.axvline(x=H.EARLY_T/H.SLOT, ymin=0,ymax=4, color='k',linestyle='dashed', linewidth=2)
    plt.annotate('No New Scheduled\n (Slot {})'.format(int(H.EARLY_T/H.SLOT)),xy=(H.EARLY_T/H.SLOT,0), xytext=(H.EARLY_T/H.SLOT,0.3),fontsize=12,
             arrowprops=dict(facecolor='black',shrink=0.01))
    plt.annotate('No New Visit\n (Slot {})'.format(int(H.WORK_END/H.SLOT)),xy=(H.WORK_END/H.SLOT,0), xytext=(H.WORK_END/H.SLOT,0.3),fontsize=12,
             arrowprops=dict(facecolor='black',shrink=0.01))
    work_during = np.mean(np.array(H.OVERTIME_COST))+H.WORK_END
    xlim = (0,200)
    # plt.axvline(x=(work_during)/H.SLOT, color='#d46061', linewidth=1)
#    plt.annotate('End \n (Slot {})'.format(int((work_during)/H.SLOT)),xy=((work_during)/H.SLOT,0), xytext=((work_during)/H.SLOT,0.3),fontsize=12,
#             arrowprops=dict(facecolor='black',shrink=0.01))
    plt.xlim(xlim)
    plt.ylim(-0.2,4.2)
    plt.yticks(np.array([0,1,2,3,4]), ('idle','Scheduled','Scheduled(Re)', 'Walk-In',  'Walk-In(Re)'), fontsize=18)
    plt.savefig(data_root+'/realization_day1.png')
    plt.close()
    xy,y,xz,z = H.get_doctor_queue(sim.waiting_place[0].Arrive_times, 
                                    sim.waiting_place[0].Served_times, 
                                    sim.waiting_place[0].Revisit_times, 
                                    sim.waiting_place[0].Revisit_served_times)
    x1,y1 = H.get_service_queue(sim.waiting_place[1].Arrival_time,  sim.waiting_place[1].Served_time)
    x2,y2 = H.get_service_queue(sim.waiting_place[2].Arrival_time,  sim.waiting_place[2].Served_time)

    queue1  = pd.DataFrame({'Day{}'.format(0): H.discretetize(x1,y1)})
    queue2  = pd.DataFrame({'Day{}'.format(0): H.discretetize(x2,y2)})
    walkin_queue  = pd.DataFrame({'Day{}'.format(0): H.discretetize(xy,y)})
    revisit_queue = pd.DataFrame({'Day{}'.format(0): H.discretetize(xz,z)})

    for i in range(1, mc):
        sim = Simulation()
        sim.run()
        # print(sim.net[0][0].realization)
        H.waste_time(sim)

        # 1) Utility Measure
        H.utility_measure(sim,i)

        # 2) Queue Length
        xy,y,xz,z = H.get_doctor_queue(sim.waiting_place[0].Arrive_times, 
                                       sim.waiting_place[0].Served_times, 
                                       sim.waiting_place[0].Revisit_times, 
                                       sim.waiting_place[0].Revisit_served_times)
        x1,y1 = H.get_service_queue(sim.waiting_place[1].Arrival_time,  sim.waiting_place[1].Served_time)
        x2,y2 = H.get_service_queue(sim.waiting_place[2].Arrival_time,  sim.waiting_place[2].Served_time)
        
        queue1 = queue1.join(pd.DataFrame({'Day{}'.format(i): H.discretetize(x1,y1)}))
        queue2 = queue2.join(pd.DataFrame({'Day{}'.format(i): H.discretetize(x2,y2)}))
        walkin_queue  = walkin_queue.join(pd.DataFrame({'Day{}'.format(i): H.discretetize(xy,y)}))
        revisit_queue = revisit_queue.join(pd.DataFrame({'Day{}'.format(i): H.discretetize(xz,z)}))
    
    queue1.join(pd.DataFrame({'AVG':queue1.mean(axis=1).tolist()}))
    queue2.join(pd.DataFrame({'AVG':queue2.mean(axis=1).tolist()}))
    walkin_queue.join(pd.DataFrame({'AVG':walkin_queue.mean(axis=1).tolist()}))
    revisit_queue.join(pd.DataFrame({'AVG':revisit_queue.mean(axis=1).tolist()}))

    plt.plot(walkin_queue.mean(axis=1).tolist())
    plt.plot(revisit_queue.mean(axis=1).tolist())
    plt.xlim(xlim)
    plt.legend(['walkin queue', 'revisit queue'], loc='upper left')
    plt.savefig(data_root+'/plot_MC{}_{}_{}.png'.format(mc,args.policy,args.ri))
    plt.close()

    plt.plot(queue1.mean(axis=1).tolist())
    plt.xlim(xlim)
    plt.legend(['Blood queue'], loc='upper left')
    plt.savefig(data_root+'/plot-blood-MC{}_{}_{}.png'.format(mc,args.policy,args.ri))
    plt.close()

    plt.plot(queue2.mean(axis=1).tolist())
    plt.xlim(xlim)
    plt.legend(['Scan queue'], loc='upper left')
    plt.savefig(data_root+'/plot-scan-MC{}_{}_{}.png'.format(mc,args.policy,args.ri))
    plt.close()

    H.utility_measure_mc(sim,mc,data_root)

    with open(data_root+"/result_{}_{}.txt".format(args.policy,args.ri),"w") as f:
#        print("schedule waiting:",[round(np.mean(lst),3) for lst in H.WASTE[0]], file=f)
#        print("schedule count:",[len(lst)/mc for lst in H.WASTE], file=f)

        print("walk-in waiting", [round(np.mean(lst),3) for lst in H.WASTE], file=f)
        print("walk-in count", [len(lst)/mc for lst in H.WASTE], file=f)

        print("idle cost:", np.mean(np.array(H.IDLE_COST)), end=', ', file=f)
        print("overtime cost:", np.mean(np.array(H.OVERTIME_COST)), file=f)
#
#    print("schedule waiting:",[round(np.mean(lst),3) for lst in H.WASTE[0]])
#    print("schedule count:",[len(lst)/mc for lst in H.WASTE[0]])

    print("walk-in waiting", [round(np.mean(lst),3) for lst in H.WASTE])
    print("walk-in count", [len(lst)/mc for lst in H.WASTE])

#    print("idle cost:", np.mean(np.array(H.IDLE_COST)), end=', ')
#    print("overtime cost:", np.mean(np.array(H.OVERTIME_COST)))
