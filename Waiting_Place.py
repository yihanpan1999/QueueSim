import utils as H
from utils.utils import *
from Patient import Patient

class Waiting_Place(object):
    '''
    This class, Waiting_Place, is to model the waiting room in the service in the real world.
    '''
    def __init__(self, env, PlaceType, GENERATE=False, lamda_or_patients=list()):
        # For simulator
        self.env = env # contain the whole info of the simulator

        # For statistics, to record some important time
        self.Arrival_time = []
        self.Served_time = []

        # For modeling the service
        self.PlaceType = PlaceType # to identify blood or ultrasound
        self.WaitingQ = queue.PriorityQueue() # only have a queue.

        # Add external patients intially
        if GENERATE: # Generate by lambda (input is lambda)
            patients = self.__generate_external(lamda_or_patients)
        else: # input is patients
            patients = lamda_or_patients
        self.__add_external(patients)



    # Generate by lambda (Exponential Distribution)
    # Generate in advance, so static
    def __generate_external(self, lamda):
        now = H.Generator.Exponential(lamda)
        patients = []
        while now < H.SIM_CLOSE:
            patients.append(Patient(self.env, self.PlaceType, arrive_time=now))
            now += H.Generator.Exponential(lamda)
        return patients
    
    # push a patient into the queue
    def add_patient(self, patient):
        self.Arrival_time.append(patient.time[self.PlaceType, 0])
        self.WaitingQ.put((patient.time[self.PlaceType, 0], patient)) 
        
    # push external patients generated in advance
    def __add_external(self, patients):
        for patient in patients:
            self.add_patient(patient)

    # This is to tell the simulator when is the next active time or the completed time of one patient.
    def next_patient(self):
        if self.WaitingQ.empty():
            return H.SIM_END
        else:
            return max(self.WaitingQ.queue[0][0], self.env.now_step)
        
    # One patient is over, and he/she need to leave the service.
    def send_patient(self):
        if self.WaitingQ.empty() or self.WaitingQ.queue[0][0] > self.env.now_step:
            return None
        else:
            patient = self.WaitingQ.get()[1]
            self.Served_time.append(self.env.now_step)
            return patient
    
class Doctor_Place(object):
    '''
    This class, Doctor_Place, is to model the waiting room in the service in the real world.
    Class Doctor_Place is similar to Class Waiting_Place.
    '''
    def __init__(self, env, PlaceType, GENERATE=False, prob_or_patients=list(), walk_in_rate=None):
        # For simulator
        self.env = env # contain the whole info of the simulator

        # For statistics, to record some important time
        self.Arrive_times = []
        self.Served_times = []
        self.Revisit_times = [] # revisit queue + 1
        self.Revisit_served_times = [] # revisit queue - 1
        self.last_patient = 0  # 0:revisit 1: walkin
        
#        self.Idle_times = []
        self.Busy_times = [[],[]] # [[walkin], [walkin-revisit]]

        # For modeling the service
        self.PlaceType = 0  # to identify, doctor is 0
        ## have 3 queues, different types have different queue
#        self.WaitingQ = queue.PriorityQueue() 
        self.walkin = queue.Queue() 
        self.revisit = queue.PriorityQueue()

        # Add external patients intially
        ## Scheduled patients
#        if GENERATE: # Generate by appointment policy
#            patients = self.__generate_schedule(prob_or_patients, H.POLICY)
#        else: # input is patients
#            patients = prob_or_patients
#        self.Schedule = patients  
#        for patient in patients:
#            self.add_patient(patient, patient.revisit)
        ## Walk-in patients
        self.walk_in_rate = walk_in_rate
        walkin_patients = self.__generate_walkin(walk_in_rate)
        for patient in walkin_patients:
            self.add_walkin(patient)
   
    # Generate by lambda (Exponential Distribution)
    # Generate in advance, so static
    def __generate_walkin(self, rate):
        now = H.Generator.Exponential(max(rate))
        walkin_patients = []
        while now < H.EARLY_T:
            if H.Generator.Bernoulli(rate[int(now//60)]/max(rate)):   # Thinning
                walkin_patients.append(Patient(self.env, self.PlaceType, arrive_time=now))
                self.Arrive_times.append(now)
            now += H.Generator.Exponential(max(rate))
        return walkin_patients

    # push walk-in patients into the queue
    def add_walkin(self, patient):
        self.walkin.put(patient)

    # Generate by appointment policy
    # Generate in advance, so static
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
        
    # push a patient into the queue
    def add_patient(self, patient, revisit=False):
        if revisit:
            # record
            self.Revisit_times.append(patient.time[-1,0])
            self.Arrive_times.append(patient.time[-1,0])
            # action
            self.revisit.put((patient.time[-1, 0], patient))
        else:
            self.WaitingQ.put((patient.time[self.PlaceType, 0], patient)) 

    # This is to tell the simulator when is the next active time or the completed time of one patient.
    def next_patient(self):
        if not self.revisit.empty():
            revisit = self.revisit.queue[0][0]
        else:
            revisit = H.SIM_END 
#        if not self.WaitingQ.empty():
#            scheduled = self.WaitingQ.queue[0][0]
#        else:
#            scheduled = H.SIM_END
        if len(self.walkin.queue) == 0:
            time = max(self.env.now_step, revisit)
        else:
            time = max(self.env.now_step, min(self.walkin.queue[0].time[0,0], revisit))
        return time 

    # One patient is over, and he/she needs to leave the service.
    def send_patient(self):
        switch = {1: self.send_patient_1, 2:self.send_patient_2, 3:self.send_patient_3, 4:self.send_patient_4}
        try:
            return switch[args.policy]()
        except:
            assert False
            return None, None 

    def send_patient_1(self):
        if (not self.revisit.empty()) and self.revisit.queue[0][0] <= self.env.now_step:
            self.Revisit_served_times.append(self.env.now_step)
            self.Served_times.append(self.env.now_step)
            patient = self.revisit.get()[1]
            self.Busy_times[1].append(self.env.now_step)
            return patient

        elif (not self.walkin.empty()) and self.walkin.queue[0].time[0,0] <= self.env.now_step:
            self.Served_times.append(self.env.now_step)
            patient = self.walkin.get()
            self.Busy_times[0].append(self.env.now_step)
            return patient

        else:
            assert False
            return None, None  
        
#        if (not self.WaitingQ.empty()) and self.WaitingQ.queue[0][0] <= self.env.now_step:
#            assert self.WaitingQ.queue[0][0] == self.env.now_step
#            patient = self.WaitingQ.get()[1]
#            self.Busy_times[0].append(self.env.now_step)
#            return patient
#
#        else:
#            if (not self.revisit.empty()) and H.Ceil_Slot(self.revisit.queue[0][0]) <= self.env.now_step:
#                self.Revisit_served_times.append(self.env.now_step)
#                self.Served_times.append(self.env.now_step)
#                
#                patient = self.revisit.get()[1]
#                if patient in self.Schedule:
#                    self.Busy_times[1].append(self.env.now_step)
#                else: 
#                    self.Busy_times[2].append(self.env.now_step)
#                return patient
#
#            elif (not self.walkin.empty()) and H.Ceil_Slot(self.walkin.queue[0].time[0,0]) <= self.env.now_step:
#                self.Walk_in_served_times.append(self.env.now_step)
#                self.Served_times.append(self.env.now_step)
#
#                patient = self.walkin.get()
#                self.Busy_times[3].append(self.env.now_step)
#                return patient
#
#            else:
#                assert False
#                return None, None   

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



    # first serve revisit, when walkin line >= 8, serve walkin
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

            


                    
                    
            

