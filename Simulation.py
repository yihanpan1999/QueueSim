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
    def __init__(self, num_node=num_node, trans_prob=trans_prob, walk_time=walk_time):

        self.now_step = 0.0
        self.sim_end = H.SIM_END
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

        self.net = [[Doctor(self, trans_prob = trans_prob) for _ in range(num_node[0])], 
                    [Blood_Service(self) for _ in range(num_node[1])], 
                    [Scan_Service(self) for _ in range(num_node[2])]]

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
        
    def run(self):

        while self.now_step < H.SIM_END:
            self.now_step, type, id = self.next()
            
            if self.now_step >= H.SIM_END: 
                break

            patient = self.waiting_place[type].send_patient_4() # policy 2: balance walk-in and revisit queue

            before_State = patient.isRevisit() 
            patient = self.net[type][id].work(patient)
            
            TO = None
            if before_State and type == 0:
                TO = 2019 # GO HOME
            else:
                if len(patient.checklist) == 0:
                    if len(patient.check_list) == 0:
                        TO = 2020 # GO HOME
                    else:
                        TO = 0 # GO DOCTOR
                        if patient.time[0, -1] == self.net[0][0].id: 
                            last = self.argmax_report_time(patient)
                            patient.scheduled_revisit_time = self.scheduled_revisit_time(patient.time[last, 3])
                            patient.time[-1, 0] = patient.policy(patient.scheduled_revisit_time, patient.time[last, 3] + self.walk_time[last, 0])                                     #@# arrive exactly
                            self.waiting_place[TO].add_patient(patient, True)
                        else: 
                            TO = 2000 # GO OTHER DOCTOR
                else:
                    TO = patient.checklist.pop(0)
                    patient.time[TO, 0] = patient.time[type, 2] + self.walk_time[type, TO]
                    self.waiting_place[TO].add_patient(patient)
            
    def next(self):
        type, id = None, None
        m = H.SIM_END
        for i in range(len(self.net)):
            expected_time = self.waiting_place[i].next_patient()
            for j in range(len(self.net[i])):
                temp = max(expected_time, self.net[i][j].finish_time)
                if temp < m:
                    type, id = i, j
                    m = temp
        return m, type, id    
        
    def argmax_report_time(self, patient):
        idx = None
        M = -1
        for i in range(1, len(patient.time[:-1, 3])):
            if patient.time[i, 3] is not None and patient.time[i, 3] > M:
                M = patient.time[i, 3]
                idx = i
        assert M >= 0
        return idx

    def scheduled_revisit_time(self, check_end_time):
        return check_end_time + 30

if __name__ == "__main__":
    data_root = args.dataroot
    mkdir_ifmiss(data_root)

    # +++++++++++++++++++++++++++++++++++++++
    mc = args.mc

    sim = Simulation()
    sim.run()
    # print(sim.net[0][0].realization)
    H.waste_time(sim)
    H.utility_measure(sim,mc)

    fig, axs = plt.subplots(1,1, figsize=(20, 5))
    plt.plot(sim.net[0][0].realization,'co')
    plt.ylim(0.8,4.2)
    plt.yticks(np.array([0,1,2,3,4]), ('idle','Scheduled','Scheduled(Re)', 'Walk-In',  'Walk-In(Re)'), fontsize=18)
    plt.savefig(data_root+'/realization_day1.png')
    plt.close()
    xy,y,xz,z = H.get_doctor_queue(sim.waiting_place[0].Walk_in_times, 
                                    sim.waiting_place[0].Walk_in_served_times, 
                                    sim.waiting_place[0].Revisit_times, 
                                    sim.waiting_place[0].Revisit_served_times)
    x1,y1 = H.get_service_queue(sim.waiting_place[1].Arrival_time,  sim.waiting_place[1].Served_time)
    x2,y2 = H.get_service_queue(sim.waiting_place[2].Arrival_time,  sim.waiting_place[2].Served_time)

    queue1  = pd.DataFrame({'Day{}'.format(0): H.discretetize(x1,y1)})
    queue2  = pd.DataFrame({'Day{}'.format(0): H.discretetize(x2,y2)})
    walkin_queue  = pd.DataFrame({'Day{}'.format(0): H.discretetize(xy,y)})
    revisit_queue = pd.DataFrame({'Day{}'.format(0): H.discretetize(xz,z)})

    for i in range(1,mc):
        sim = Simulation()
        sim.run()
        # print(sim.net[0][0].realization)
        H.waste_time(sim)

        # 1) Utility Measure
        H.utility_measure(sim,i)

        # 2) Queue Length
        xy,y,xz,z = H.get_doctor_queue(sim.waiting_place[0].Walk_in_times, 
                                       sim.waiting_place[0].Walk_in_served_times, 
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
    plt.legend(['walkin queue', 'revisit queue'], loc='upper left')
    plt.savefig(data_root+'/plot_MC{}.png'.format(mc))
    plt.close()

    plt.plot(queue1.mean(axis=1).tolist())
    plt.legend(['Blood queue'], loc='upper left')
    plt.savefig(data_root+'/plot-blood-MC{}.png'.format(mc))
    plt.close()

    plt.plot(queue2.mean(axis=1).tolist())
    plt.legend(['Scan queue'], loc='upper left')
    plt.savefig(data_root+'/plot-scan-MC{}.png'.format(mc))
    plt.close()

    H.utility_measure_mc(sim,mc,data_root)

    print([round(np.mean(lst),3) for lst in H.WASTE[0]])
    print([len(lst)/mc for lst in H.WASTE[0]])

    print([round(np.mean(lst),3) for lst in H.WASTE[1]])
    print([len(lst)/mc for lst in H.WASTE[1]])
