import glob
import pickle
import matplotlib.pyplot as plt
import numpy as np
import jackknife as jk
from scipy.optimize import curve_fit

class Data:
    def __init__(self, Nt, cutoff, block_size):
        self.Nt = Nt
        self.cutoff = cutoff
        self.block_size = block_size
        # Stores the trajectory number for debugging purposes
        self.trajs = {}
        # Save the acceptance rates
        self.accept_rates = {}
        # Stores the average phi^2 for each trajectory
        self.psq_list={}
        # Stores the average values of each phi_i for each trajectory
        self.phi_list={}
        #
        self.timeslices={}
        #
        self.fields={}
        self.momentums={}
        self.forces={}
        #
        self.delta_actions_M = {}
        self.actions_M = {}
        self.delta_actions_L = {}
        self.actions_L = {}
        self.delta_actions_t_FV = {}
        self.actions_t_FV = {}
        self.delta_actions_t_TV = {}
        self.actions_t_TV = {}
    
    def get_t_TV(self, sf):
        return int(self.get_param(sf, "measurements").split("x")[1]) - 2*int(self.get_param(sf, "tfull")) - int(self.get_param(sf, "tFV"))
    
    def get_param(self, sf, param):
        if(param=="tTV"):
            return self.get_t_TV(sf)
        return sf.split(param)[1].split("_")[1]
    
    def replace_param(self, sf, param, val):
        a = sf.split("_")
        a[a.index(param)+1] = str(val)
        return "_".join(a)
    
    def replace_params(self, sf, params, values):
        rtn = []
        for v in values:
            s = sf
            for p in range(len(params)):
                s = self.replace_param(s, params[p], v[p])
            rtn.append(s)
        return rtn
    
    def remove_date(self, sf):
        a = sf.split("_")
        for i in range(len(a)):
            if len(a[i].split("-"))==3:
                a[i] = "*"
        return "_".join(a)
    
    def get_sfs_list(self, sfs, profile):
        if(profile=="*"):
            return sfs
        rtn = []
        profile = profile.split("_")
        for sf in sfs:
            a = sf.split("_")
            append = True
            for i in range(len(a)):
                if(profile[i]=="*"):
                    continue
                elif(a[i]!=profile[i]):
                    append = False
                    break
            if(append):
                rtn.append(sf)
        return rtn
    
    def get_M_L_blocks(self, Ms, Ls, profile):
        sfs_M = self.replace_params(profile, ["M", "L"], [[M, 1.0] for M in Ms])
        sfs_L = self.replace_params(profile, ["M", "L"], [[1.0, L] for L in Ls])
        delta_actions_M = [jk.get_jackknife_blocks(np.exp(self.delta_actions_M[sfs_M[i]][str(Ms[i+1])][self.cutoff:]), self.block_size)
                           for i in range(len(Ms)-1)]
        delta_actions_L = [jk.get_jackknife_blocks(np.exp(self.delta_actions_L[sfs_L[i]][str(Ls[i+1])][self.cutoff:]), self.block_size)
                           for i in range(len(Ls)-1)]
        return delta_actions_M + delta_actions_L
    
    def calc_ratio(self, delta_actions, N_Ms):
        ratio = 1.0
        for i in range(len(delta_actions)):
            if(i<N_Ms):
                ratio *= np.mean(delta_actions[i])
            else:
                ratio /= np.mean(delta_actions[i])
        return ratio
    
    def calc_gamma(self, R, Ebar, delta_E, t_full, dt):
        return R*(2*np.pi)**0.5/delta_E * np.exp(-Ebar**2/2/delta_E**2)/(t_full*dt)**2
    
    def calc_gamma_blocks(self, Ms, Ls, profile_ML, profile_tFV, der=1):
        t_full = int(self.get_param(profile_ML,"tfull"))
        dt = float(self.get_param(profile_ML, "dt"))
        t_FV = int(self.get_param(profile_ML,"tFV"))
        ml_blocks = self.get_M_L_blocks(Ms, Ls, profile_ML)
        R_blocks = jk.super_jackknife_combine_blocks(ml_blocks, lambda x: self.calc_ratio(x, len(Ms)-1))
        Ebar_blocks = self.get_Ebar_blocks(self.replace_params(profile_ML,["M","L"],[[1.0,0.0]])[0])
        #
        sfs = self.get_sfs_list(list(self.delta_actions_t_FV), profile_tFV)
        sfs.sort(key=lambda x: float(self.get_param(x, "tFV")))
        if der==0:
            sf1 = self.replace_param(profile_tFV,"tFV",t_FV)
            sf2 = list(filter(lambda x: int(self.get_param(x,"tFV"))>t_FV, sfs))[0]
        elif der==1:
            sf1 = list(filter(lambda x: int(self.get_param(x,"tFV"))<t_FV, sfs))[-1]
            sf2 = list(filter(lambda x: int(self.get_param(x,"tFV"))>t_FV, sfs))[0]
        else:
            sf1 = list(filter(lambda x: int(self.get_param(x,"tFV"))<t_FV, sfs))[-1]
            sf2 = self.replace_param(profile_tFV,"tFV",t_FV)
        dE_blocks = self.get_Ebar_slope_blocks(sf1, sf2)
        print(f"Calculating dE with t_FV={self.get_param(sf1,'tFV')} and t_FV={self.get_param(sf2,'tFV')}")
        #
        gamma_blocks = jk.super_jackknife_combine_blocks([R_blocks, Ebar_blocks, dE_blocks], lambda x: self.calc_gamma(x[0], x[1], x[2], t_full, dt))
        gamma_mean = self.calc_gamma(np.mean(R_blocks), np.mean(Ebar_blocks), np.mean(dE_blocks), t_full, dt)
        return gamma_mean, gamma_blocks
    
    def calc_gamma_w_errors(self, Ms, Ls, profile_ML, profile_tFV, der=1):
        gamma_mean, gamma_blocks = self.calc_gamma_blocks(Ms, Ls, profile_ML, profile_tFV, der)
        return jk.get_errors_from_blocks(gamma_mean, gamma_blocks)
    
    def calc_gamma_M_L_errors(self, Ms, Ls, profile_ML, profile_tFV, der=1):
        gammas = []
        for i in range(1,len(Ms)-1):
            M = Ms.pop(i)
            gammas.append(self.calc_gamma_blocks(Ms,Ls,profile_ML, profile_tFV, der=1)[0])
            Ms.insert(i,M)
        for i in range(1,len(Ls)-1):
            L = Ls.pop(i)
            gammas.append(self.calc_gamma_blocks(Ms,Ls,profile_ML, profile_tFV, der=1)[0])
            Ls.insert(i,L)
        return gammas
    
    def calc_gamma_dis_errors(self, Ms, Ls, profile_ML, profile_tFV):
        gamma = self.calc_gamma_blocks(Ms,Ls,profile_ML, profile_tFV, der=1)[0]
        fd = self.calc_gamma_blocks(Ms,Ls,profile_ML, profile_tFV, der=2)[0]
        bd = self.calc_gamma_blocks(Ms,Ls,profile_ML, profile_tFV, der=0)[0]
        lerr = min([fd,bd]) - gamma
        uerr = max([fd,bd]) - gamma
        if lerr>0 or uerr<0:
            lerr = max([abs(lerr),abs(uerr)])
            uerr = lerr
        return [abs(lerr), abs(uerr)]
    
    def get_exp_Ebar_blocks(self, sf, delta_t=1):
        t_TV = self.get_t_TV(sf)
        t_FV = int(self.get_param(sf,"tFV"))
        blocks_TV = jk.get_jackknife_blocks(np.exp(self.delta_actions_t_TV[sf][f"{t_TV+delta_t}"][self.cutoff:]), self.block_size)
        blocks_FV = jk.get_jackknife_blocks(np.exp(self.delta_actions_t_FV[sf][f"{t_FV+delta_t}"][self.cutoff:]), self.block_size)
        return np.divide(blocks_FV,blocks_TV)
    
    def get_Ebar_blocks(self, sf, delta_t=1):
        dt = float(self.get_param(sf, "dt"))
        bdiv = np.log(self.get_exp_Ebar_blocks(sf, delta_t))/(dt*delta_t)
        return bdiv
    
    def get_Ebar_E_FV(self, sf, delta_t=1):
        bdiv = self.get_Ebar_blocks(sf, delta_t)
        return jk.get_errors_from_blocks(np.mean(bdiv), bdiv)
    
    def get_Ebar_slope_blocks(self, sf1, sf2, delta_t=1):
        dt_TV = self.get_t_TV(sf2)*float(self.get_param(sf2, "dt")) - self.get_t_TV(sf1)*float(self.get_param(sf2, "dt"))
        bdiv1 = self.get_Ebar_blocks(sf1, delta_t)
        bdiv2 = self.get_Ebar_blocks(sf2, delta_t)
        return ((bdiv1 - bdiv2) / dt_TV)**0.5
    
    def get_Ebar_slope(self, sf1, sf2, delta_t=1):
        bdiv = self.get_Ebar_slope_blocks(sf1, sf2, delta_t)
        return jk.get_errors_from_blocks(np.mean(bdiv), bdiv)
    
    def get_delta_E(self, sf):
        delta_t=1
        delta_t2=2
        t_TV = self.get_t_TV(sf)
        t_FV = int(self.get_param(sf,"tFV"))
        dt = float(self.get_param(sf, "dt"))
        
        blocks_TVa = jk.get_jackknife_blocks(np.exp(self.delta_actions_t_TV[sf][f"{t_TV+delta_t}"][self.cutoff:]), self.block_size)
        blocks_FVa = jk.get_jackknife_blocks(np.exp(self.delta_actions_t_FV[sf][f"{t_FV+delta_t}"][self.cutoff:]), self.block_size)
        
        blocks_TVa2 = jk.get_jackknife_blocks(np.exp(self.delta_actions_t_TV[sf][f"{t_TV+delta_t2}"][self.cutoff:]), self.block_size)
        blocks_FVa2 = jk.get_jackknife_blocks(np.exp(self.delta_actions_t_FV[sf][f"{t_FV+delta_t2}"][self.cutoff:]), self.block_size)
        
        bdiv = np.log(np.divide(blocks_FVa2,blocks_TVa2)/np.divide(blocks_FVa,blocks_TVa)**2.0)**0.5/(dt*delta_t2)
        return jk.get_errors_from_blocks(np.mean(bdiv), bdiv)
    
    def fit_ratios(self, ratios, t_TVs, start_time = -1.0):
        # This integration range is based on the energy distribution after evolving in Euclidean time
        int_range = 1/np.abs(np.min(np.subtract(t_TVs,start_time)))*200
        dE = int_range/1000.0
        E = np.arange(-int_range,int_range,dE)
        dt = 0.2
        
        opt, cov = curve_fit(fit, t_TVs, ratios, sigma=dS_errs, p0=[1.0, 1.0, 1.0], jac=dfit, bounds=((-np.inf,0,0),(np.inf,np.inf,np.inf)))
        print(np.sqrt(np.diag(cov)))

        plt.plot(t_TVs, ratios)
        plt.plot(t_TVs, fit(np.array(t_TVs), opt[0], opt[1],opt[2]))

        #ts = np.array([0, 1, 2, 3])
        #x, ys = integrand(ts,opt[0],opt[1],opt[2])
        #norms = np.ones(len(ts))#Rt(ts,opt[0],opt[1],opt[2])
        #plt.plot(x, ys[0]/norms[0])
        #plt.plot(x, ys[1]/norms[1])
        #plt.plot(x, ys[2]/norms[2])
        #plt.plot(x, ys[3]/norms[3])

        #plt.plot(t_TVs, dfit(np.array(t_TVs), opt[0], opt[1],opt[2]))
        #plt.plot(t_TVs, [0.32e7*corr_tdse[i][0] for i in range(len(corr_tdse))])
        #print(ratios)
        print(opt)
        print(R0(0,opt[0],opt[1])/Rt(np.array([15.0]),opt[0],opt[1],opt[2])[0])
        #print(int_range)
        return opt, fit
    
    def get_fit_ratios_blocks(self, profile_tFV, t_TV, before=2, after=2):
        sfs = self.get_sfs_list(list(self.delta_actions_t_FV), profile_tFV)
        sfs.sort(key=lambda x: float(self.get_param(x, "tFV")))
        
        dS_blocks = []
        t_TVs = []
        
        for sf in sfs:
            dS_blocks.append(self.get_exp_Ebar_blocks(sf))
            t_TVs.append(self.get_t_TV(sf))
        
        blocks = jk.super_jackknife_combine_blocks(dS_blocks_before[-before:]+dS_blocks_after[:after+1], lambda x: self.ratio_fit(x,t_TVs,t_TV))
    
    def plot_mean_path(self, profile="*"):
        #x = np.arange(-5,5,0.1)
        #for t in range(0,self.Nt,int(self.Nt/20)):
        #    plt.plot([min(self.action.V(i,t)*self.Nt/20.0, 200.0) + t for i in x],x)
        sfs = self.get_sfs_list(list(self.timeslices), profile)
        for sf in sfs:
            plt.plot(np.mean(self.timeslices[sf][self.cutoff:],axis=0), label=sf)
    
    def plot_paths(self):
        #x = np.arange(-5,5,0.1)
        #for t in range(0,self.Nt,int(self.Nt/20)):
        #    plt.plot([min(self.action.V(i,t)*self.Nt/20.0, 200.0) + t for i in x],x)
        for sf in self.timeslices:
            i=0
            #plt.plot(self.timeslices[sf][0])
            #plt.show()
            for ts in self.timeslices[sf][:]:
                if (i+1)%100==0: plt.plot(ts)
                if (i+1)%10000==0: plt.show()
                i+=1
    
    def plot_expS(self, delta_action, get_x=float, fact=1.0, label="p", filter_x=lambda x: False):
        expS = []
        expS_errs = []
        x = []
        for k in delta_action:
            if(filter_x(k)): continue
            x.append(get_x(k))
            blocks = jk.get_jackknife_blocks(np.exp(delta_action[k][self.cutoff:]), self.block_size)
            [eS, err] = jk.get_errors_from_blocks(np.mean(blocks), blocks)
            expS.append(eS*fact)
            expS_errs.append(err*fact)
        plt.errorbar(x, expS, yerr=expS_errs, label=label)
        print(x)
        print(expS)
        print(expS_errs)
        return x, expS, expS_errs
    
    def plot_all_expS(self, delta_actions, sfs, param, get_x=float, filter_x=lambda x,y: False, sort=None):
        fact = 1.0
        last_params = []
        last_expS = []
        if(sort==None):
            sort = lambda x: float(self.get_param(x, param))
        sfs.sort(key=sort)
        for sf in sfs:
            print(sf)
            p = float(self.get_param(sf,param))
            if(p in last_params):
                fact = last_expS[last_params.index(p)]
            else:
                print(f"No previous factor found for {param}={p}")
            last_params, last_expS, errs = self.plot_expS(delta_actions[sf], get_x, fact, f"{param}={p}", lambda x: filter_x(x,p))
    
    def plot_expS_vs_M(self):
        sfs = list(filter(lambda x: self.get_param(x,"M")!="1.0", list(self.delta_actions_M)))
        self.plot_all_expS(self.delta_actions_M, sfs, "M")
    
    def plot_expS_vs_L(self):
        sfs = list(filter(lambda x: self.get_param(x,"L")!="1.0", list(self.delta_actions_L)))
        self.plot_all_expS(self.delta_actions_L, sfs, "L")
    
    def plot_expS_vs_t_TV(self, t_limit=[-100,100], sf=""):
        if(sf==""):
            sfs = list(self.delta_actions_t_TV)
        else:
            sfs = [sf]
        self.plot_all_expS(self.delta_actions_t_TV, sfs, "tTV", get_x=int, filter_x=lambda x,x0: (int(x)-x0)<t_limit[0] or (int(x)-x0)>t_limit[1])
    
    def plot_delta_actions_vs_t_FV(self, t_limit=[-100,100], sf=""):
        if(sf==""):
            sfs = list(self.delta_actions_t_FV)
        else:
            sfs = [sf]
        self.plot_all_expS(self.delta_actions_t_FV, sfs, "tFV", get_x=int, filter_x=lambda x,x0: (int(x)-x0)<t_limit[0] or (int(x)-x0)>t_limit[1])
    
    def plot_Ebar_E_FV(self, profile_tFV, delta_t=1):
        sfs = self.get_sfs_list(list(self.delta_actions_t_TV), profile_tFV)
        sfs.sort(key=self.get_t_TV)
        t_TVs = []
        Es = []
        E_errs = []
        for sf in sfs:
            t_TVs.append(self.get_t_TV(sf)*float(self.get_param(sf,"dt")))
            E, err = self.get_Ebar_E_FV(sf, delta_t)
            Es.append(E)
            E_errs.append(err)
        plt.errorbar(t_TVs, Es, yerr=E_errs)
    
    def plot_delta_E(self, profile_tFV):
        sfs = self.get_sfs_list(list(self.delta_actions_t_TV), profile_tFV)
        sfs.sort(key=self.get_t_TV)
        t_TVs = []
        dEs = []
        dE_errs = []
        for sf in sfs:
            t_TVs.append(self.get_t_TV(sf)*float(self.get_param(sf,"dt")))
            dE, err = self.get_delta_E(sf)
            dEs.append(dE)
            dE_errs.append(err)
        plt.errorbar(t_TVs, dEs, yerr=dE_errs)
    
    def plot_Ebar_slope(self, profile_tFV, delta_t=1):
        sfs = self.get_sfs_list(list(self.delta_actions_t_TV), profile_tFV)
        sfs.sort(key=self.get_t_TV)
        t_TVs = []
        dEs = []
        dE_errs = []
        for sf in range(len(sfs)-1):
            t_TVs.append(self.get_t_TV(sfs[sf])*float(self.get_param(sfs[sf],"dt")))
            dE, err = self.get_Ebar_slope(sfs[sf], sfs[sf+1], delta_t)
            dEs.append(dE)
            dE_errs.append(err)
        plt.errorbar(t_TVs, dEs, yerr=dE_errs)
    
    def plot_change_over_mdtime(self, obs, block_size, t_limit=100):
        y = []
        y_err = []
        x = []
        for i in range(int(len(obs)/block_size)):
            x.append(i*block_size)
            blocks = jk.get_jackknife_blocks(obs[i*block_size:(i+1)*block_size], self.block_size)
            [meas, err] = jk.get_errors_from_blocks(np.mean(blocks), blocks)
            y.append(meas)
            y_err.append(err)
        plt.errorbar(x,y,yerr=y_err)
    
    def load(self, save_file):
        files = glob.glob(save_file)
        if len(files):
            for sf in files:
                with open(sf,"rb") as input:
                    data = pickle.load(input)
                    sf = self.remove_date(sf)
                    if(sf in list(self.trajs)):
                        print(f"Already loaded ensemble with same parameters as {sf}")
                        continue
                    self.trajs[sf] = data["trajs"]
                    self.accept_rates[sf] = data["accept_rates"]
                    self.psq_list[sf] = data["psq_list"]
                    self.phi_list[sf] = data["phi_list"]
                    self.timeslices[sf] = data["timeslices"]
                    self.fields[sf] = data["fields"]
                    self.momentums[sf] = data["momentums"]
                    self.forces[sf] = data["forces"]
                    self.delta_actions_M[sf] = data["delta_actions_M"]
                    self.delta_actions_L[sf] = data["delta_actions_L"]
                    self.delta_actions_t_FV[sf] = data["delta_actions_t_FV"]
                    self.delta_actions_t_TV[sf] = data["delta_actions_t_TV"]
                    print(f"Loaded {sf}")
                    print(f"# traj: {len(data['trajs'])}")
                    print(f"Accept rate: {np.mean(data['accept_rates'])}")