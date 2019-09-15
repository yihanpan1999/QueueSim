import utils as H
from utils.utils import *
from Patient import Patient

class Waiting_Place(object):
    def __init__(self, env, PlaceType, GENERATE=False, lamda_or_patients=list()):
        self.Arrival_time = []
        self.Served_time = []
        self.env = env 
        self.WaitingQ = queue.PriorityQueue()
        self.PlaceType = PlaceType 
        if GENERATE: 
            patients = self.__generate_external(lamda_or_patients)
        else:
            patients = lamda_or_patients            
        self.__add_external(patients)

    def __generate_external(self, lamda):
        now = 0
        patients = []
        while now < H.SIM_CLOSE:
            now += H.Generator.Exponential(lamda)
            patients.append(Patient(self.env, self.PlaceType, arrive_time=now))
        return patients
    
    def add_patient(self, patient):
        self.Arrival_time.append(patient.time[self.PlaceType, 0])
        self.WaitingQ.put((patient.time[self.PlaceType, 0], patient)) 
        
    def __add_external(self, patients):
        for patient in patients:
            self.add_patient(patient)

    def next_patient(self):
        if self.WaitingQ.empty():
            return H.SIM_END
        else:
            return max(self.WaitingQ.queue[0][0], self.env.now_step)
        
    def send_patient(self):
        if self.WaitingQ.empty() or self.WaitingQ.queue[0][0] > self.env.now_step:
            return None
        else:
            patient = self.WaitingQ.get()[1]
            self.Served_time.append(self.env.now_step)
            return patient
    
class Doctor_Place(object):
    def __init__(self, env, PlaceType, GENERATE=False, prob_or_patients=list(), walk_in_rate=None):

        self.Walk_in_times = [] # walk in queue + 1
        self.Walk_in_served_times = [] # walk in queue - 1
        self.Revisit_times = [] # revisit queue + 1
        self.Revisit_served_times = [] # revisit queue - 1
        self.Arrive_times = []
        self.Served_times = []
        self.last_patient = 0  # 0:revisit 1: walkin

        self.env = env
        self.Idel_times = []
        self.Busy_times = [[],[],[],[]]

        if GENERATE:
            patients = self.__generate_schedule(prob_or_patients,H.POLICY)
        else:
            patients = prob_or_patients
        self.Schedule = patients    
        self.WaitingQ = queue.PriorityQueue()

        self.PlaceType = 0 
        for patient in patients:
            self.add_patient(patient,patient.revisit)

        self.walk_in_rate = walk_in_rate
        self.walkin = queue.Queue() 
        
        walkin_patients = patients = self.__generate_walkin(walk_in_rate)
        for patient in walkin_patients:
            self.add_walkin(patient)

        self.revisit = queue.PriorityQueue()
    
    def __generate_walkin(self, lamda):
        now = 0
        walkin_patients = []
        while now < H.EARLY_T:
            now += H.Generator.Exponential(lamda)
            walkin_patients.append(Patient(self.env, self.PlaceType, arrive_time=now))
            self.Walk_in_times.append(now)
            self.Arrive_times.append(now)
        return walkin_patients

    def add_walkin(self, patient):
        self.walkin.put(patient)

    def __generate_schedule(self, p, policy):
        policy = H.POLICY
        patients = []
        i = 0
        while i < H.EARLY_T:
            if policy == 'random':
                if H.Generator.Bernoulli(p):
                    patients.append(Patient(self.env, arrive_time=i, schedule=True))      
            elif policy == 'first_slots':
                if i < H.EARLY_T / 2:
                    patients.append(Patient(self.env, arrive_time=i, schedule=True))
            elif policy == 'first_half':
                if i % 60 < 30:
                    patients.append(Patient(self.env, arrive_time=i, schedule=True))
            elif policy == 'adaptive':
                time = i // 60 +1
                if (i % 60) < (65-5*2*time):
                    patients.append(Patient(self.env, arrive_time=i, schedule=True))
            elif policy == 'human':
                pass
            i += H.SLOT
        return patients
        
    def add_patient(self, patient, revisit=False):
        if revisit:
            self.Revisit_times.append(patient.time[-1,0])
            self.Arrive_times.append(patient.time[-1,0])

            self.revisit.put((patient.time[-1, 0], patient))
        else:
            self.WaitingQ.put((patient.time[self.PlaceType, 0], patient)) 

    def next_patient(self):
        revisit = self.revisit.queue[0][0] if not self.revisit.empty() else H.SIM_END
        scheduled = self.WaitingQ.queue[0][0] if not self.WaitingQ.empty() else H.SIM_END
        if len(self.walkin.queue) == 0:
            time = max(self.env.now_step, min(scheduled, H.Ceil_Slot(revisit)))
        else:
            time = max(self.env.now_step, min(scheduled, H.Ceil_Slot(self.walkin.queue[0].time[0,0]), H.Ceil_Slot(revisit)))
        return time 

    def send_patient(self):
        if (not self.WaitingQ.empty()) and self.WaitingQ.queue[0][0] <= self.env.now_step:
            assert self.WaitingQ.queue[0][0] == self.env.now_step
            patient = self.WaitingQ.get()[1]
            self.Busy_times[0].append(self.env.now_step)
            return patient

        else:
            if (not self.revisit.empty()) and H.Ceil_Slot(self.revisit.queue[0][0]) <= self.env.now_step:
                self.Revisit_served_times.append(self.env.now_step)
                self.Served_times.append(self.env.now_step)
                
                patient = self.revisit.get()[1]
                if patient in self.Schedule:
                    self.Busy_times[1].append(self.env.now_step)
                else: 
                    self.Busy_times[2].append(self.env.now_step)
                return patient

            elif (not self.walkin.empty()) and H.Ceil_Slot(self.walkin.queue[0].time[0,0]) <= self.env.now_step:
                self.Walk_in_served_times.append(self.env.now_step)
                self.Served_times.append(self.env.now_step)

                patient = self.walkin.get()
                self.Busy_times[3].append(self.env.now_step)
                return patient

            else:
                assert False
                return None, None   

    def send_patient_2(self):
        if (not self.WaitingQ.empty()) and self.WaitingQ.queue[0][0] <= self.env.now_step:
            assert self.WaitingQ.queue[0][0] == self.env.now_step
            patient = self.WaitingQ.get()[1]
            self.Busy_times[0].append(self.env.now_step)
            return patient

        else:
            if (not self.walkin.empty()) and H.Ceil_Slot(self.walkin.queue[0].time[0,0]) <= self.env.now_step and \
                (not self.revisit.empty()) and H.Ceil_Slot(self.revisit.queue[0][0]) <= self.env.now_step:

                # if have longer revisit queue, serve revisit
                if len(self.walkin.queue) < len(self.revisit.queue):
                    self.Revisit_served_times.append(self.env.now_step)
                    self.Served_times.append(self.env.now_step)
                    
                    patient = self.revisit.get()[1]
                    if patient in self.Schedule:
                        self.Busy_times[1].append(self.env.now_step)
                    else: 
                        self.Busy_times[2].append(self.env.now_step)
                    return patient   
                else:  
                    self.Walk_in_served_times.append(self.env.now_step)
                    self.Served_times.append(self.env.now_step)

                    patient = self.walkin.get()
                    self.Busy_times[3].append(self.env.now_step)
                    return patient 

            elif (not self.revisit.empty()) and H.Ceil_Slot(self.revisit.queue[0][0]) <= self.env.now_step:
                self.Revisit_served_times.append(self.env.now_step)
                self.Served_times.append(self.env.now_step)
                
                patient = self.revisit.get()[1]
                if patient in self.Schedule:
                    self.Busy_times[1].append(self.env.now_step)
                else: 
                    self.Busy_times[2].append(self.env.now_step)
                return patient

            elif (not self.walkin.empty()) and H.Ceil_Slot(self.walkin.queue[0].time[0,0]) <= self.env.now_step:
                self.Walk_in_served_times.append(self.env.now_step)
                self.Served_times.append(self.env.now_step)

                patient = self.walkin.get()
                self.Busy_times[3].append(self.env.now_step)
                return patient

            else:
                assert False
                return None, None  


    #one walkin, one revisit
    def send_patient_3(self):  
        if (not self.WaitingQ.empty()) and self.WaitingQ.queue[0][0] <= self.env.now_step:
            assert self.WaitingQ.queue[0][0] == self.env.now_step
            patient = self.WaitingQ.get()[1]
            self.Busy_times[0].append(self.env.now_step)
            return patient

        else:
            if (not self.walkin.empty()) and H.Ceil_Slot(self.walkin.queue[0].time[0,0]) <= self.env.now_step and \
                (not self.revisit.empty()) and H.Ceil_Slot(self.revisit.queue[0][0]) <= self.env.now_step:

                if self.last_patient == 0:
                    self.Walk_in_served_times.append(self.env.now_step)
                    self.Served_times.append(self.env.now_step)
                    patient = self.walkin.get()
                    self.Busy_times[3].append(self.env.now_step)
                    self.last_patient = 1
                    return patient

                else:
                    self.Revisit_served_times.append(self.env.now_step)
                    self.Served_times.append(self.env.now_step)
                    
                    patient = self.revisit.get()[1]
                    if patient in self.Schedule:
                        self.Busy_times[1].append(self.env.now_step)
                    else: 
                        self.Busy_times[2].append(self.env.now_step)
                    self.last_patient =0
                    return patient

            elif (not self.revisit.empty()) and H.Ceil_Slot(self.revisit.queue[0][0]) <= self.env.now_step:
                self.Revisit_served_times.append(self.env.now_step)
                self.Served_times.append(self.env.now_step)
                
                patient = self.revisit.get()[1]
                if patient in self.Schedule:
                    self.Busy_times[1].append(self.env.now_step)
                else: 
                    self.Busy_times[2].append(self.env.now_step)
                self.last_patient = 0
                return patient

            elif (not self.walkin.empty()) and H.Ceil_Slot(self.walkin.queue[0].time[0,0]) <= self.env.now_step:
                self.Walk_in_served_times.append(self.env.now_step)
                self.Served_times.append(self.env.now_step)

                patient = self.walkin.get()
                self.Busy_times[3].append(self.env.now_step)
                self.last_patient = 1
                return patient

            else:
                assert False
                return None, None  



    #first serve revisit, when walkin line >= 8, serve walkin
    def send_patient_4(self):   
        if (not self.WaitingQ.empty()) and self.WaitingQ.queue[0][0] <= self.env.now_step:
            assert self.WaitingQ.queue[0][0] == self.env.now_step
            patient = self.WaitingQ.get()[1]
            self.Busy_times[0].append(self.env.now_step)
            return patient
        
        else:
            if (not self.walkin.empty()) and H.Ceil_Slot(self.walkin.queue[0].time[0,0]) <= self.env.now_step and \
                (not self.revisit.empty()) and H.Ceil_Slot(self.revisit.queue[0][0]) <= self.env.now_step:

                if len(self.walkin.queue) < 8:
                    self.Revisit_served_times.append(self.env.now_step)
                    self.Served_times.append(self.env.now_step)
                    
                    patient = self.revisit.get()[1]
                    if patient in self.Schedule:
                        self.Busy_times[1].append(self.env.now_step)
                    else: 
                        self.Busy_times[2].append(self.env.now_step)
                    return patient   
                else:  
                    self.Walk_in_served_times.append(self.env.now_step)
                    self.Served_times.append(self.env.now_step)

                    patient = self.walkin.get()
                    self.Busy_times[3].append(self.env.now_step)
                    return patient 

            elif (not self.revisit.empty()) and H.Ceil_Slot(self.revisit.queue[0][0]) <= self.env.now_step:
                self.Revisit_served_times.append(self.env.now_step)
                self.Served_times.append(self.env.now_step)
                
                patient = self.revisit.get()[1]
                if patient in self.Schedule:
                    self.Busy_times[1].append(self.env.now_step)
                else: 
                    self.Busy_times[2].append(self.env.now_step)
                return patient

            elif (not self.walkin.empty()) and H.Ceil_Slot(self.walkin.queue[0].time[0,0]) <= self.env.now_step:
                self.Walk_in_served_times.append(self.env.now_step)
                self.Served_times.append(self.env.now_step)

                patient = self.walkin.get()
                self.Busy_times[3].append(self.env.now_step)
                return patient

            else:
                assert False
                return None, None  

            


                    
                    
            

