import utils as H
from utils.package import *
from utils import parser
import numpy as np
args = parser.parse_args()

class Serve_Place(object):
    '''
    This class, Serve_Place, is to model the service process in the service (blood or ultrasound) in the real world.
    '''
    def __init__(self, env, service_type, service_id):
        # For simulator
        self.env = env # contain the whole info of the simulator

        # For statistics
        self.busy_times = [0,0] # to calculate the busy time and idle time
        self.start_stamps = []
        self.end_stamps = []

        # For modeling the service
        self.service_type = service_type # 1 is blood test, 2 is ultrasound
        self.id = service_id # to identify
        self.finish_time = 0 # when the recent service will be over 

    # to serve a patient, and return the patient with many time stamps
    def work(self, patient):
        # serve and record, for simulator
        patient.time[self.service_type,1] = self.env.now_step # record service start time 
        if self.service_type == 1: 
            serve_time  = np.random.uniform(args.blood_service_rate[0], args.blood_service_rate[1])
            report_time = random.sample(args.blood_report_time,1)[0]
        elif self.service_type == 2:
            serve_time = random.sample(args.scan_service_rate,1)[0]
            report_time = 0
        patient.time[self.service_type,2] = self.env.now_step + serve_time # record service end time
        patient.time[self.service_type,3] = self.env.now_step + serve_time + report_time # record service report time
        patient.time[self.service_type,-1] = self.id # record service id
        ## for finding next event
        self.finish_time = self.env.now_step + serve_time

        # For statistics
        self.start_stamps.append(patient.time[self.service_type, 1])
        self.end_stamps.append(patient.time[self.service_type, 2])
        if patient.time[0,0] != None:   # not external patients
            self.busy_times[0] += serve_time
        else:  # external patients
            self.busy_times[1] += serve_time
        self.env.Save[self.service_type].append(patient)

        return patient
    
class Blood_Service(Serve_Place):
    '''
    This class, Blood_Service, is to model the service process in the blood service in the real world.
    This is a subclass of Serve_Place, just to define the type and id.
    '''
    ID_generate = 0 
    def __init__(self,env):
        super().__init__(env, 1, Blood_Service.ID_generate)
        Blood_Service.ID_generate += 1
    
class Scan_Service(Serve_Place):
    '''
    This class, Scan_Service, is to model the service process in the ultrasound service in the real world.
    This is a subclass of Scan_Service, just to define the type and id.
    '''
    ID_generate = 0 
    def __init__(self,env):
        super().__init__(env, 2, Scan_Service.ID_generate)
        Scan_Service.ID_generate += 1

class Doctor(object):
    '''
    This class, Doctor, is to model the doctor in the clinic in the real world.
    '''
    ID_generate = 0 
    def __init__(self, env, trans_prob):
        # For simulator
        self.env = env # contain the whole info of the simulator

        # For statistics
        ## which types of patients are served at each slot
#        self.realization = np.zeros(int(np.ceil(env.sim_end/H.SLOT)), dtype=int) #11*60*1/5 
        # 1:schedule  2:schedule-revisit  3:walkin  4:walkin-revisit
        
        # For modeling the service
        self.service_type = 0
        self.id = Doctor.ID_generate
        Doctor.ID_generate += 1
        self.finish_time = 0 # when the recent service will be over 
#        self.serve_time = H.SLOT # a fixed time
        self.trans_prob = trans_prob # the probability to do some check
        
    def work(self, patient):
#        slot = int(self.env.now_step // H.SLOT) # how many slots are there opening
        # print('Service Begin',self.env.now_step)
        if not patient.isRevisit(): # new patient
            # For simulator
            service_time = np.random.normal(7, 2)
            patient.time[self.service_type, 1]  = self.env.now_step # service start time
            patient.time[self.service_type, 2]  = self.env.now_step + service_time # service end time
            patient.time[self.service_type, -1] = self.id # service id
            ## the check items which the patient need to be served
            patient.checklist = self.__check_list().copy() 
            patient.check_list = patient.checklist.copy()
            patient.revisit = True # change state
            ## predict time to revisit based on the checklist and env
#            patient.scheduled_revisit_time = self.scheduled_revisit_time(patient)
            ## for finding next event
            self.finish_time = self.env.now_step + service_time # service end time

            # For statistics
#            self.realization[slot] = 1 if patient.schedule == True else 3 # record the type of patient at this slot
            # print('First Come',patient.schedule, patient.id)
            self.env.Save[self.service_type].append(patient)

        else: # revisit patient
            # For simulator
            service_time = np.random.normal(7, 2)
            patient.time[-1,1] = self.env.now_step # service start time
            patient.time[-1,2] = self.env.now_step + service_time # service end time
            patient.time[-1,-1] = self.id # service id
            ## for finding next event
            self.finish_time = self.env.now_step + service_time

            # For statistics
            self.env.Save[self.service_type].append(patient)
#            self.realization[slot] = 2 if patient.schedule == True else 4 # record the type of patient at this slot
            # print('Revisit',patient.schedule, patient.id, patient.time[0,2])
        # print(slot, self.realization[slot])
        return patient

    # trivial policy to predict
    def scheduled_revisit_time(self, patient):
        # t = check_end_time
        # t = min(check_end_time + 60, H.EARLY_T+30)
        # t = H.EARLY_T + check_end_time*H.SLOT
        # t = check_end_time//60+30
        t = self.finish_time + H.riDELAY
        return t
    
    # generate the checklist, based on trans_prob
    def __check_list(self):
        L = []
        for i in range(len(self.trans_prob)):
            if H.Generator.Bernoulli(self.trans_prob[i]):
                L.append(i+1)
        return L
            
    # calculate the idle time cost and overtime cost
    def cost(self):
        idx = H.WORK_END // H.SLOT
        idle = np.sum(self.realization[:idx]==0) * H.SLOT
        overtime = np.max(np.nonzero(self.realization)[0][-1] * H.SLOT + H.SLOT - H.WORK_END, 0)
        return idle, overtime
