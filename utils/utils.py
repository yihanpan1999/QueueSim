from .package import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# plt.style.use('dark_background')
plt.style.use('ggplot')

parser = argparse.ArgumentParser(description='Outpatient Simulation')
parser.add_argument('--dataroot',           type = str,   default = 'first_half')  
parser.add_argument('--policy',           type = int,   default = 1)  
parser.add_argument('--ri',           type = float,   default = 0)  

parser.add_argument('--mc',                 type = int,   default = 100)         # NUMBER OF DAYS
parser.add_argument('--seed',               type = int,   default = 123)        # RANDOM SEED
parser.add_argument('--num_check',          type = int,   default = 2)          # NUMBER OF CHECK ITEMS
parser.add_argument('--close_time',         type = int,   default = 6)          # ALLOWED TIME PERIOD FOR NEW PATIENTS (hrs)
parser.add_argument('--slot_time',          type = int,   default = 5)          # TIME DURATION (5 MINS) OF ONE SLOT (mins)
parser.add_argument('--sim_end',            type = int,   default = 8*60)      # ONE DAY SERVICE TIME (mins)
 
parser.add_argument('--p_showup',           type = float, default = 0.5)        # 30/72 ALL SLOTS ARE OCCUPIRED BY SCHEDULED PEOPLE
parser.add_argument('--walk_in_rate',       type = float, default = [2.92201835/60, 8.15596330/60, 7.71559633/60, 6.61467890/60, 2.98623953/60, 0.51834862/60])  # TIME-VARYING POISSON
parser.add_argument('--arrival_rate_blood', type = float, default = 30/60)      # 30 PATIENTS / 60 MINUTES FOR EXTERNAL BLOOD TEST
parser.add_argument('--arrival_rate_scan',  type = float, default = 20/60)      # 20 PATIENT  / 60 MINUTES FOR EXTERNAL SCAN TEST

parser.add_argument('--num_node',           type = list,  default = [1,2,4])    # DOCTOR: 1, BLOOD: 2, SCAN: 4
# parser.add_argument('--trans_prob',         type = list,  default = [0.8,0.8])  # PROB 
parser.add_argument('--trans_prob', nargs='+', type=float, default = [0.8,0.8])
parser.add_argument('--blood_service_rate', type = list,  default = [2,4])      # UNIFORM(2,4)
parser.add_argument('--blood_report_time',  type = list,  default = [15,30])    # DISCRETE(15,30)
parser.add_argument('--scan_service_rate',  type = list,  default = [3,9,15])   # DISCRETE(3,9,15)

parser.add_argument('--mute',               type = bool,  default = True)
args = parser.parse_args()

# ---------------------------------------- GLOBAL VARIABLE ------------------------------------------------
DIGITS = 5      
POLICY    = args.dataroot
SLOT      = args.slot_time         
SIM_END   = args.sim_end * 4     # ALLOWED MAXIMUM CLOSE TIMEPOINT  
WORK_END = args.sim_end
SIM_CLOSE = args.sim_end - 60  # IDEAL CLOSE TIMEPOINT
EARLY_T   = args.close_time*60 

NUM_CHECK = 2         
NUM_STEP = NUM_CHECK + 2 
walk_time = 2*np.ones([NUM_CHECK+1,NUM_CHECK+1])

# r_i
riDELAY = args.ri

        
# -------------------------------------------------------------------------------------------------------
Name_waiting_place = {0: "Doctor", 1: "Blood", 2: "Scan", 3: "Revisit",
                      2019:"Go Home", 2020:"Go Home", 2000:"Other Doctor"} 
Patient_type = {0:'Schedule'}

# COLOR PRINT OUT
Clear  = "\033[0m" 
Red    = "\033[1;31m"
Green  = "\033[32m"
Yellow = "\033[33m" 
Blue   = "\033[34m"

RAN_SEED = args.seed
random.seed(RAN_SEED)
scipy.random.seed(RAN_SEED)

# ---------------------------------------- Record ------------------------------------------------
MUTE = args.mute
RECORD = True
# -------------------- #
WALK_IN_ARRIVAL = []
WALK_IN_SERVED = []
REVISIT_ARRIVAL = []
REVISIT_SERVED = []
COMBINE_ARRIVAL = []
COMBINE_SERVED = []
# -------------------- #
BLOOD_ARRIVAL = []
BLOOD_SERVED = []
# -------------------- #
SCAN_ARRIVAL = []
SCAN_SERVED = []
# -------------------- #
DOCTOR_UTIL = []
BLOOD_UTIL = []
SCAN_UTIL = []
# -------------------- #
WASTE = [[],[],[],[]]
IDLE_COST = []
OVERTIME_COST= []

# ---------------------------------------- Util functions ------------------------------------------------

def mkdir_ifmiss(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

TEST = []
def discretetize(x,y):
    # x = [0, 28.306141030249545, 43.30614103024955, 45, ...
    # y = [0, 1,                  2,                 1, 0, 1, 2, ...
    slot = [[] for _ in range(SIM_END//5)] # 0-10, 10-20, ... , 650-660, 660-670, 670-680
    slot_final = [0 for _ in range(SIM_END//5)]
    TEST.append(x[-1])
    for i in range(len(x)):
        x_step = x[i]
        idx = int(x_step // 5)
        slot[idx].append(y[i])
    for i in range(SIM_END//5):
        if len(slot[i]) != 0:
            slot_final[i] = np.mean(slot[i])
        else:
            slot_final[i] = slot_final[i-1]
            # print('WARINING',i)
    # pdb.set_trace()
    return slot_final

def get_average_queue(x,y):
    area = 0
    for i in range(len(x)-1):
        time_duration = x[i+1] - x[i]
        length = y[i]
        area += time_duration * length
    return area / x[-1]

def plot_doctor_queue(ax, walk_in_times, walk_in_served_times, revisit_times, revisit_served_times, mc=None):
    max_time = max(walk_in_times+walk_in_served_times+revisit_times+revisit_served_times)
    walk_in_all_times = walk_in_times + walk_in_served_times
    revisit_all_times = revisit_times + revisit_served_times
    y = [0]
    for time in sorted(walk_in_all_times):
        if time in walk_in_times and time in walk_in_served_times:
            y.append(y[-1])
        elif time in walk_in_times:
            y.append(y[-1]+1)
        elif time in walk_in_served_times:
            y.append(y[-1]-1)  
    y.append(y[-1])
    xy = [0]+sorted(walk_in_all_times)+[max_time]
    if mc != None:
        y = [a/mc for a in y]
    ax.step(xy, y, label='Walk In',where='post',linewidth=2)

    z = [0]
    for time in sorted(revisit_all_times):
        if time in revisit_times and time in revisit_served_times:
            z.append(z[-1])
        elif time in revisit_times:
            z.append(z[-1]+1)
        elif time in revisit_served_times:
            z.append(z[-1]-1)     
    z.append(z[-1])
    if mc != None:
        z = [a/mc for a in z]
    xz = [0]+sorted(revisit_all_times)+[max_time]
    ax.step(xz, z, label='Revisit',where='post',linewidth=2)
    # qq = [0]
    # for time in sorted(all_times):
    #     if time in arrival_times and time in served_times:
    #         qq.append(qq[-1])
    #     elif time in arrival_times:
    #         qq.append(qq[-1]+1)
    #     elif time in served_times:
    #         qq.append(qq[-1]-1)     
    # qq.append(qq[-1])
    # if mc != None:
    #     qq = [a/mc for a in qq]
    # xq = [0]+sorted(all_times)+[max_time]
    # ax.step(xq, qq, label='Combined',where='post',linewidth=2)
    ax.axvline(x=SIM_CLOSE, ymin=0, ymax=max(y+z),ls='-',alpha=0.5)
    ax.set_title('Queue Length in Doctor Place is {}-{}'.format(round(calculate_area(xz,z)),round(calculate_area(xy,y))),fontsize=20,weight='bold')
    ax.legend(loc="upper right",fontsize=14)
    ax.set_ylim(None,max(y+z)+2)

def get_doctor_queue(walk_in_times, walk_in_served_times, revisit_times, revisit_served_times):
    max_time = max(walk_in_times+walk_in_served_times+revisit_times+revisit_served_times)
    walk_in_all_times = walk_in_times + walk_in_served_times
    revisit_all_times = revisit_times + revisit_served_times
    y = [0]
    a = sorted(list(set(walk_in_all_times)))
    for time in a:
        if time in walk_in_times and time in walk_in_served_times:
            y.append(y[-1])
        elif time in walk_in_times:
            y.append(y[-1]+1)
        elif time in walk_in_served_times:
            y.append(y[-1]-1)  
    y.append(y[-1])
    xy = [0]+a+[max_time]

    z = [0]
    aa = sorted(list(set(revisit_all_times)))
    for time in aa:
        if time in revisit_times and time in revisit_served_times:
            incre = len([t for t in revisit_times if t == time]) - len([t for t in revisit_served_times if t == time])
            z.append(z[-1]+incre)
        elif time in revisit_times:
            z.append(z[-1]+1)
        elif time in revisit_served_times:
            z.append(z[-1]-1)     
    z.append(z[-1])
    xz = [0]+aa+[max_time]
    return xy,y,xz,z
    
def get_service_queue(arrival_times, served_times):
    max_time = max(arrival_times, served_times)
    times = arrival_times + served_times
    y = [0]
    for time in sorted(times):
        if time in arrival_times and time in served_times:
            y.append(y[-1])
        elif time in arrival_times:
            y.append(y[-1]+1)
        elif time in served_times:
            y.append(y[-1]-1)  
    y.append(y[-1])
    x = [0]+sorted(times)
    return x,y

def plot_service_queue(ax, service_type, arrival_times, served_times, mc=None):
    all_times = arrival_times + served_times

    y = [0]
    if mc == None:
        for time in sorted(all_times):
            if time in arrival_times and time in served_times:
                y.append(y[-1])
            elif time in arrival_times:
                y.append(y[-1]+1)
            elif time in served_times:
                y.append(y[-1]-1)  
    if mc != None:
        i = 0 
        while i < len(sorted(all_times)):
            time = sorted(all_times)[i]
            if time in arrival_times and time in served_times:
                arrival_count = len([idx for idx,t in enumerate(arrival_times) if t == time])
                served_count = len([idx for idx,t in enumerate(served_times) if t == time])
                diff = arrival_count - served_count
                y.extend([y[-1]+diff for _ in range(arrival_count+served_count)])
                i = i + (arrival_count + served_count)
            elif time in arrival_times:
                y.append(y[-1]+1)
                i += 1
            elif time in served_times:
                y.append(y[-1]-1)  
                i += 1
        y = [a/mc for a in y]
    xy = [0]+sorted(all_times)

    df = pd.DataFrame({'Time': xy, 'Queue': y})
    df.to_excel("queue.xls") 


    ax.step(xy, y, label=service_type,linewidth=2)
    ax.axvline(x=SIM_CLOSE, ymin=0, ymax=max(y),ls='-',alpha=0.5)
    ax.set_title('Queue Length in {} is {}'.format(service_type,round(calculate_area(xy,y))),fontsize=20,weight='bold')
    ax.legend(loc="upper right",fontsize=14)
    ax.set_ylim(None,max(y)+2)

def calculate_area(x,y):
    area = 0
    for i in range(len(x)-1):
        duration = x[i+1] - x[i]
        value = y[i]
        area += duration * value
    return area / x[-1]

def doctor_utility_pie(ax, utility, mc=None):

    labels = 'Walk In', 'Revisit (Walk In)', 'Idle Slot'
    explode = (0, 0, 0.1) ## only "explode" the 2nd slice (i.e. 'Revisit')

    if mc == None:
        busy = sum(utility)
        total = int(SIM_CLOSE / SLOT)# normally end at 10 hrs, extra 1 hr in case
        idle =  max(total - busy,0)
        sizes = [util for util in utility] + [idle]
        DOCTOR_UTIL.append(sizes)
    else:
        sizes = utility
        idle = sizes[-1]
    ax.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    ax.set_title("Doctor Utility\n{} - {} - {}".format(round(utility[0]),round(utility[1]),round(idle)))
    ax.legend(labels,loc="upper right",fontsize=10)

def service_pie_utility(ax,servers, arrival_rate, mc=None):
    sizes = [0,0,0]
    explode = (0, 0, 0.1) 
    labels = 'Busy Slot (Clinic)', 'Busy Slot (External)', 'Idle Slot'
    if mc == None:
        for i in range(len(servers)):
            server = servers[i]
            sizes[0]+= server.busy_times[0]
            sizes[1]+= server.busy_times[1]
            sizes[2]+= max(SIM_CLOSE - server.busy_times[0] -server.busy_times[1],0)
            
        size_normalize = [i/len(servers) for i in sizes]

        if server.service_type == 1:
            BLOOD_UTIL.append(size_normalize)
        elif server.service_type == 2:
            SCAN_UTIL.append(size_normalize)  
    else:
        server = servers[0]
        if server.service_type == 1:
            size_normalize = np.mean(BLOOD_UTIL,0)
        elif server.service_type == 2:
            size_normalize = np.mean(SCAN_UTIL,0)
    ax.pie(size_normalize, explode=explode, labels=labels, autopct='%1.1f%%',
            shadow=True, startangle=90)#, textprops={'fontsize': 14, 'weight':'bold'})
    ax.axis('equal') 
    ax.set_title("{} Utility \n{} / {}".format(Name_waiting_place[server.service_type],
                                        round(size_normalize[0]+size_normalize[1]),round(sum(size_normalize))))#,fontsize=20,weight='bold')
    ax.legend(labels,loc="upper right",fontsize=10)

def performance_measure(sim,k):
    fig, axs = plt.subplots(2, 3, figsize=(30, 15))
    plot_doctor_queue(axs[0,0],
                      sim.waiting_place[0].Walk_in_times, 
                      sim.waiting_place[0].Walk_in_served_times, 
                      sim.waiting_place[0].Revisit_times, 
                      sim.waiting_place[0].Revisit_served_times)
                    #   sim.waiting_place[0].Arrive_times,
                    #   sim.waiting_place[0].Served_times)
    plot_service_queue(axs[0,1],Name_waiting_place[1],
                        sim.waiting_place[1].Arrival_time,
                        sim.waiting_place[1].Served_time)
    plot_service_queue(axs[0,2],Name_waiting_place[2],
                    sim.waiting_place[2].Arrival_time,
                    sim.waiting_place[2].Served_time)

    doctor_utility_pie(axs[1,0],[len(a) for a in sim.waiting_place[0].Busy_times])
    service_pie_utility(axs[1,1],sim.net[1],args.arrival_rate_blood)
    service_pie_utility(axs[1,2],sim.net[2],args.arrival_rate_scan)

    plt.suptitle('Day {}'.format(k),fontsize=24, weight='bold')
    plt.savefig('./result_check/Day_{}.png'.format(k))
    plt.close()

def performance_measure_mc(sim,mc):
    fig, axs = plt.subplots(2, 3, figsize=(39, 15))
    plot_doctor_queue(axs[0,0],
                        WALK_IN_ARRIVAL,
                        WALK_IN_SERVED,
                        REVISIT_ARRIVAL,
                        REVISIT_SERVED,
                        mc=mc)
    plot_service_queue(axs[0,1],
                        Name_waiting_place[1],
                        BLOOD_ARRIVAL,
                        BLOOD_SERVED,
                        mc=mc)
    plot_service_queue(axs[0,2],
                       Name_waiting_place[2],
                       SCAN_ARRIVAL,
                       SCAN_SERVED,
                       mc=mc)
    doctor_utility_pie(axs[1,0],np.mean(DOCTOR_UTIL,0),mc)
    service_pie_utility(axs[1,1],sim.net[1],args.arrival_rate_blood,mc)
    service_pie_utility(axs[1,2],sim.net[2],args.arrival_rate_scan,mc)

    plt.suptitle('{} Day Average'.format(mc),fontsize=24, weight='bold')
    plt.savefig('./result_policy2/Day_MC{}.png'.format(mc))
    plt.close()

def utility_measure(sim,k):
    fig, axs = plt.subplots(1, 1)
    doctor_utility_pie(axs, [len(a) for a in sim.waiting_place[0].Busy_times])
    # plt.savefig('utility_DOC_DAY{}.png'.format(k))
    plt.close()

    fig, axs = plt.subplots(1, 1)
    service_pie_utility(axs,sim.net[1],args.arrival_rate_blood)
    # plt.savefig('utility_BLOOD_DAY{}.png'.format(k))
    plt.close()

    fig, axs = plt.subplots(1, 1)
    service_pie_utility(axs,sim.net[2],args.arrival_rate_scan)
    # plt.savefig('utility_SCAN_DAY{}.png'.format(k))
    plt.close()

def utility_measure_mc(sim,mc,dataroot):

    fig, axs = plt.subplots(1, 1)
    doctor_utility_pie(axs,np.mean(DOCTOR_UTIL,0),mc)
    plt.savefig(dataroot+'/utility_DOC_MC{}.png'.format(mc))
    plt.close()

    fig, axs = plt.subplots(1, 1)
    service_pie_utility(axs,sim.net[1],args.arrival_rate_blood,mc)
    plt.savefig(dataroot+'/utility_BLOOD_MC{}.png'.format(mc))
    plt.close()

    fig, axs = plt.subplots(1, 1)
    service_pie_utility(axs,sim.net[2],args.arrival_rate_scan,mc)
    plt.savefig(dataroot+'/utility_SCAN_MC{}.png'.format(mc))
    plt.close()


def subtract(item1, item2):
    if item1 != None and item2 != None:
        return item1 - item2 
    else: 
        return None

def Ceil_Slot(t):
    return math.ceil(t / SLOT) * SLOT

def Visualize(sim):
    col_names = ["patient_id","arrive_time","begin_time","finish_time","None","doctor_id",
                 "blood_arrive_time","blood_begin_time","blood_finish_time","blood_report_time","blood_id",
                 "scan_arrive_time","scan_begin_time","scan_finish_time","scan_report_time","scan_id",
                 "revisit_arrive_time","revisit_begin_time","revisit_finish_time","None","revisit_id"]
    for i in range(3):
        L = sim.Save[i]
        rows_list = []
        for row in L:
            LL = [row.id]
            dict1 = row.time.reshape(-1)
            L1 = dict1.tolist()
            rows_list.append(LL+L1)
        df = pd.DataFrame(rows_list, columns = col_names)
        name = Name_waiting_place[i]
        df.to_csv("./result_check/"+name+".csv")

def pt_patient_stats(sim):
    tb0 = pt.PrettyTable()
    tb1 = pt.PrettyTable()
    tb2 = pt.PrettyTable()
    Service = ['Doctor','Blood','Scan','Revisit']
    tb0.field_names = ['ID','Service','Arrival','Start','End','Report', 'Waiting T','Service T','Total T'] # doctor
    tb1.field_names = ['ID','Service','Arrival','Start','End','Report', 'Waiting T','Service T','Total T'] # blood
    tb2.field_names = ['ID','Service','Arrival','Start','End','Report', 'Waiting T','Service T','Total T'] # scan
    print('Total Created Patient: {}'.format(len(sim.all_patient)))

    for patient in sim.all_patient:
        if patient.time[0][0] == None: # external
            if patient.time[1][0] != None:
                tb1.add_row([patient.id, Service[1], patient.time[1][0],patient.time[1][1],patient.time[1][2],patient.time[1][3],
                            subtract(patient.time[1][1],patient.time[1][0]), subtract(patient.time[1][2],patient.time[1][1]), subtract(patient.time[1][3],patient.time[1][0])])
                            
            elif patient.time[2][0] != None:
                tb2.add_row([patient.id, Service[2], patient.time[2][0],patient.time[2][1],patient.time[2][2],patient.time[2][3],
                            subtract(patient.time[2][1],patient.time[2][0]), subtract(patient.time[2][2],patient.time[2][1]), subtract(patient.time[2][3],patient.time[2][0])])
        
        else:   # patients visit doctors
            for i in range(4):
                if patient.time[i][0] != None:
                    if i == 0 or i == 3:
                        tb0.add_row([patient.id, Service[i], patient.time[i][0],patient.time[i][1],patient.time[i][2],patient.time[i][3],
                        subtract(patient.time[i][1],patient.time[i][0]), subtract(patient.time[i][2],patient.time[i][1]), subtract(patient.time[i][2],patient.time[i][0])])
                    else: 
                        tb0.add_row([patient.id, Service[i], patient.time[i][0],patient.time[i][1],patient.time[i][2],patient.time[i][3],
                        subtract(patient.time[i][1],patient.time[i][0]), subtract(patient.time[i][2],patient.time[i][1]), subtract(patient.time[i][3],patient.time[i][0])])

    path_exp_setting = './result_patient/'
    f = open(path_exp_setting+'prettytable_Patient_Doctor.txt', 'w')
    f.write(tb0.get_string())
    f.close()
    f = open(path_exp_setting+'prettytable_Patient_BloodOnly.txt', 'w')
    f.write(tb1.get_string())
    f.close()
    f = open(path_exp_setting+'prettytable_Patient_ScanOnly.txt', 'w')
    f.write(tb2.get_string())
    f.close()

def waste_time(sim):
    for i, patient in enumerate(sim.all_patient):
        if patient.time[0][0] != None:
            for i in range(4):
                if patient.time[i][2] != None:
                    WASTE[i].append(patient.time[i][1] - patient.time[i][0])

def df_patient_stats(sim):

    ID = []
    Schedule = []
    D_Arrival = []
    D_Start = []
    D_End = []
    B_Arrival = []
    B_Start = []
    B_End = []
    B_Report = []
    S_Arrival = []
    S_Start = []
    S_End = []
    R_Arrival = []
    R_Start = []
    R_End = []
    
    # system_time_schedule = []
    # system_time_walkin = []
    
    for i, patient in enumerate(sim.all_patient):

        # if patient.time[3][2] != None:
        #     if patient.schedule == True:
        #         system_time_schedule.append(patient.time[3][2] - patient.time[0][0])
        #     else:
        #         system_time_walkin.append(patient.time[3][2] - patient.time[0][0])

        ID.append(patient.id)
        Schedule.append(patient.schedule)
        D_Arrival.append(patient.time[0][0])
        D_Start.append(patient.time[0][1])
        D_End.append(patient.time[0][2])

        B_Arrival.append(patient.time[1][0])
        B_Start.append(patient.time[1][1])
        B_End.append(patient.time[1][2])
        B_Report.append(patient.time[1][3])

        S_Arrival.append(patient.time[2][0])
        S_Start.append(patient.time[2][1])
        S_End.append(patient.time[2][2])

        R_Arrival.append(patient.time[3][0])
        R_Start.append(patient.time[3][1])
        R_End.append(patient.time[3][2])

    df = pd.DataFrame({
        'ID':ID,
        'Schedule': Schedule,

        'D_Arrival':D_Arrival,
        'D_Start':D_Start,
        'D_End':D_End,

        'B_Arrival':B_Arrival,
        'B_Start':B_Start,
        'B_End':B_End,
        'B_Report':B_Report,

        'S_Arrival':S_Arrival,
        'S_Start':S_Start,
        'S_End':S_End,

        'R_Arrival':R_Arrival,
        'R_Start':R_Start,
        'R_End':R_End
    })

    df.to_csv('patient_stat.csv',index=False)

class Generator(object):
    def Exponential(self, lamda):
        return random.expovariate(lamda)
    def Bernoulli(self, p):
        return np.random.binomial(1, p)
Generator = Generator()
