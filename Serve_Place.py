import utils as H
from utils.package import *
from utils import parser
args = parser.parse_args()

class Serve_Place(object):
    def __init__(self, env, service_type, service_id):
        self.service_type = service_type
        self.id = service_id
        self.finish_time = 0
        self.busy_times = [0,0] 
        self.start_stamps = []
        self.end_stamps = []
        self.env = env
        
    def work(self, patient):
        patient.time[self.service_type,1] = self.env.now_step # service start time 
        if self.service_type == 1: 
            serve_time  = np.random.uniform(args.blood_service_rate[0],args.blood_service_rate[1])
            report_time = random.sample(args.blood_report_time,1)[0]
        elif self.service_type == 2:
            serve_time = random.sample(args.scan_service_rate,1)[0]
            report_time = 0

        patient.time[self.service_type,2] = self.env.now_step + serve_time 
        patient.time[self.service_type,3] = self.env.now_step + serve_time + report_time 
        patient.time[self.service_type,-1] = self.id

        self.start_stamps.append(patient.time[self.service_type,2])
        self.end_stamps.append(patient.time[self.service_type,3])

        if patient.time[0,0] != None:
            self.busy_times[0] += serve_time
        else: 
            self.busy_times[1] += serve_time

        self.finish_time = self.env.now_step + serve_time
        self.env.Save[self.service_type].append(patient)
        return patient
    
class Blood_Service(Serve_Place):
    ID_generate = 0 
    def __init__(self,env):
        super().__init__(env, 1, Blood_Service.ID_generate)
        Blood_Service.ID_generate += 1
    
class Scan_Service(Serve_Place):
    ID_generate = 0 
    def __init__(self,env):
        super().__init__(env, 2, Scan_Service.ID_generate)
        Scan_Service.ID_generate += 1

class Doctor(object):
    ID_generate = 0 
    def __init__(self, env, trans_prob):
        self.service_type = 0
        self.id = Doctor.ID_generate
        self.finish_time = 0
        self.serve_time = H.SLOT
        Doctor.ID_generate += 1
        self.trans_prob = trans_prob
        self.env = env
        self.realization = np.zeros(int(env.sim_end/5)) #11*60*1/5
        
    def work(self, patient):
        # [1 schedule 2 walkin 3 schedule-R 4 walkin-R]
        slot = int(self.env.now_step // 5)
        # print('Service Begin',self.env.now_step)
        if not patient.isRevisit():
            self.realization[slot] = 1 if patient.schedule == True else 3
            # print('First Come',patient.schedule, patient.id)
            patient.time[self.service_type,1]  = self.env.now_step
            patient.time[self.service_type,2]  = self.env.now_step + self.serve_time
            patient.time[self.service_type,-1] = self.id
            self.finish_time = self.env.now_step + self.serve_time
            patient.checklist = self.__check_list().copy()
            patient.check_list = patient.checklist.copy()
            self.env.Save[self.service_type].append(patient)
            patient.revisit = True
        else:
            self.realization[slot] = 2 if patient.schedule == True else 4
            # print('Revisit',patient.schedule, patient.id, patient.time[0,2])
            patient.time[-1,1] = self.env.now_step
            patient.time[-1,2] = self.env.now_step + self.serve_time
            patient.time[-1,-1] = self.id
            self.finish_time = self.env.now_step + self.serve_time
            self.env.Save[self.service_type].append(patient)
        # print(slot, self.realization[slot])
        return patient
    
    def __check_list(self):
        L = []
        for i in range(len(self.trans_prob)):
            if H.Generator.Bernoulli(self.trans_prob[i]):
                L.append(i+1)
        return L
            
    def idle_cost(self):
        num = np.sum(self.realization==0)
        return num