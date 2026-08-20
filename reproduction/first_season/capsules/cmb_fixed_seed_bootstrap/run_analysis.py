#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,csv,json,math
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import chi2,norm

def write(path,rows):
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys:keys.append(k)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rows)

def cv(r):return np.array([[r.cov_Omega_m_Omega_m,r.cov_Omega_m_q],[r.cov_Omega_m_q,r.cov_q_q]],float)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--moments',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--bootstrap-draws',type=int,default=1000);ap.add_argument('--seed',type=int,default=10199);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(a.moments,sep='\t');D=df[df.kind=='DESI'].iloc[0];C=df[df.kind=='CMB'].reset_index(drop=True);n=len(C)
    muD=np.array([D.Omega_m,D.q_Mpc]);CD=cv(D);A=np.diag([100.,1.])
    d=np.concatenate([A@(np.array([r.Omega_m,r.q_Mpc])-muD) for _,r in C.iterrows()])
    S=np.zeros((2*n,2*n))
    for i,ri in C.iterrows():
        for j,rj in C.iterrows():S[2*i:2*i+2,2*j:2*j+2]=A@(CD if i!=j else cv(ri)+CD)@A.T
    Si=np.linalg.inv(S)
    models={'ALL_EQUAL':[0,0,0],'PLANCK_SPT_EQUAL_ACT_SEPARATE':[0,0,1],'PLANCK_ACT_EQUAL_SPT_SEPARATE':[0,1,0],'SPT_ACT_EQUAL_PLANCK_SEPARATE':[0,1,1],'ALL_SEPARATE':[0,1,2]}
    def fit(y,groups):
        labs=sorted(set(groups));mp={g:k for k,g in enumerate(labs)};G=len(labs)
        def solve(t,details=False):
            u=np.array([math.cos(t),math.sin(t)]);X=np.zeros((2*n,G))
            for i,g in enumerate(groups):X[2*i:2*i+2,mp[g]]=u
            M=X.T@Si@X;b=np.linalg.solve(M,X.T@Si@y);r=y-X@b;v=float(r@Si@r)
            return (v,u,b,np.linalg.inv(M)) if details else v
        grid=np.linspace(0,math.pi,181);vals=np.array([solve(t) for t in grid]);k=int(vals.argmin());lo=grid[max(0,k-2)];hi=grid[min(len(grid)-1,k+2)]
        o=minimize_scalar(solve,bounds=(lo,hi),method='bounded',options={'xatol':1e-13});val,u,b,V=solve(o.x,True)
        raw=np.linalg.inv(A)@u
        if raw[0]<0:raw=-raw;b=-b
        slope01=.01*raw[1]/raw[0];scale=raw[0]/.01
        return {'chi2':val,'dof':2*n-(G+1),'p':float(chi2.sf(val,2*n-(G+1))),'slope01':float(slope01),'b':b*scale,'V':V*scale*scale,'us':u}
    fits={k:fit(d,g) for k,g in models.items()}
    model_rows=[];amp_rows=[]
    for name,f in fits.items():
        model_rows.append({'model':name,'chi2':f['chi2'],'dof':f['dof'],'p':f['p'],'equivalent_sigma':float(norm.isf(f['p']/2)),'delta_q_Mpc_per_plus_0p01_Omega_m':f['slope01'],'free_amplitude_groups':len(set(models[name]))})
        for i,b in enumerate(f['b']):amp_rows.append({'model':name,'group_index':i,'amplitude_per_0p01_Omega_m_step':b,'fixed_at_profiled_direction_sigma':math.sqrt(f['V'][i,i])})
    specs=[('ALL_EQUAL','PLANCK_SPT_EQUAL_ACT_SEPARATE',1,'ACT_SEPARATE_FROM_PLANCK_SPT'),('PLANCK_SPT_EQUAL_ACT_SEPARATE','ALL_SEPARATE',1,'PLANCK_SEPARATE_FROM_SPT_WITH_ACT_SEPARATE'),('ALL_EQUAL','ALL_SEPARATE',2,'ANY_AMPLITUDE_DIFFERENCE')]
    tests=[]
    for null,alt,dd,label in specs:
        q=fits[null]['chi2']-fits[alt]['chi2'];p=float(chi2.sf(q,dd));tests.append({'test':label,'null_model':null,'alternative_model':alt,'delta_chi2':q,'delta_dof':dd,'asymptotic_p':p,'asymptotic_equivalent_sigma':float(norm.isf(p/2))})
    def fitted_mean(f,groups):
        labs=sorted(set(groups));mp={g:k for k,g in enumerate(labs)};raw=np.array([1.,f['slope01']/.01]);u=A@raw;u=u/np.linalg.norm(u);scale=(np.linalg.inv(A)@u)[0]/.01;bb=f['b']/scale;mu=np.zeros(2*n)
        for i,g in enumerate(groups):mu[2*i:2*i+2]=u*bb[mp[g]]
        return mu
    rng=np.random.default_rng(a.seed);L=np.linalg.cholesky(S);mu0=fitted_mean(fits['ALL_EQUAL'],models['ALL_EQUAL']);mu1=fitted_mean(fits['PLANCK_SPT_EQUAL_ACT_SEPARATE'],models['PLANCK_SPT_EQUAL_ACT_SEPARATE']);obs={r['test']:r['delta_chi2'] for r in tests};cnt={k:0 for k in obs}
    for _ in range(a.bootstrap_draws):
        y=mu0+L@rng.standard_normal(2*n);f0=fit(y,models['ALL_EQUAL']);f1=fit(y,models['PLANCK_SPT_EQUAL_ACT_SEPARATE']);f2=fit(y,models['ALL_SEPARATE'])
        cnt['ACT_SEPARATE_FROM_PLANCK_SPT']+=int(f0['chi2']-f1['chi2']>=obs['ACT_SEPARATE_FROM_PLANCK_SPT']-1e-12);cnt['ANY_AMPLITUDE_DIFFERENCE']+=int(f0['chi2']-f2['chi2']>=obs['ANY_AMPLITUDE_DIFFERENCE']-1e-12)
        y=mu1+L@rng.standard_normal(2*n);f1=fit(y,models['PLANCK_SPT_EQUAL_ACT_SEPARATE']);f2=fit(y,models['ALL_SEPARATE']);cnt['PLANCK_SEPARATE_FROM_SPT_WITH_ACT_SEPARATE']+=int(f1['chi2']-f2['chi2']>=obs['PLANCK_SEPARATE_FROM_SPT_WITH_ACT_SEPARATE']-1e-12)
    for r in tests:
        p=(cnt[r['test']]+1)/(a.bootstrap_draws+1);r['bootstrap_draws']=a.bootstrap_draws;r['bootstrap_p']=p;r['bootstrap_equivalent_sigma']=float(norm.isf(p/2))
    write(a.out/'02_PROFILED_AMPLITUDE_MODELS.tsv',model_rows);write(a.out/'03_MODEL_AMPLITUDES.tsv',amp_rows);write(a.out/'04_NESTED_MODEL_TESTS.tsv',tests);write(a.out/'05_PROFILED_DIRECTION_STABILITY.tsv',[{'model':k,'delta_q_Mpc_per_plus_0p01_Omega_m':v['slope01']} for k,v in fits.items()])
    (a.out/'06_MACHINE_READABLE_RESULTS.json').write_text(json.dumps({'classification':'HTV101_PROFILED_CMB_AMPLITUDE_HIERARCHY_COMPLETE_WITH_SCOPE','tests':tests,'limits':['Gaussian moments','shared DESI covariance included','CMB cross-covariance zero','bootstrap conditional on fitted model']},indent=2)+'\n')
    print(json.dumps({'model_rows':len(model_rows),'amplitude_rows':len(amp_rows),'test_rows':len(tests),'bootstrap_draws':a.bootstrap_draws},indent=2))
if __name__=='__main__':main()
