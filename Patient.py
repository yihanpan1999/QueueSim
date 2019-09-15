import utils as H
from utils.package import *

class Patient(object):
    ID_generate = 0 
    def __init__(self, env, select = 0, arrive_time = None, schedule=False):
        self.id = str(Patient.ID_generate).zfill(H.DIGITS) 
        Patient.ID_generate += 1
        self.schedule = schedule
        self.env = env
        self.env.all_patient.append(self)
        self.revisit = False

        self.time = np.full((H.NUM_STEP, 5), None)
        self.time[select, 0] = arrive_time
        self.scheduled_revisit_time = None

        self.check_list = [] 
        self.checklist =  [] 
        
    def __lt__(self, a):
        return True
    
    def isRevisit(self):
        return self.revisit

    # when to revisit
    def policy(self, ri, early_time):
        return max(ri, early_time)
    