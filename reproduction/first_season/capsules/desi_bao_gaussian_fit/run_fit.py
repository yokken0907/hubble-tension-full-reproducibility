#!/usr/bin/env python3
"""Re-execute the frozen two-parameter DESI DR2 BAO Gaussian fit."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.stats import chi2 as chi2_dist
C_LIGHT=299792.458

def main():
 p=argparse.ArgumentParser(); p.add_argument('--mean',required=True); p.add_argument('--cov',required=True); p.add_argument('--output',default='actual_output.json'); a=p.parse_args()
 rows=[]
 for line in Path(a.mean).read_text(encoding='utf-8').splitlines():
  if not line.strip() or line.lstrip().startswith('#'): continue
  z,value,quantity=line.split(); rows.append((float(z),float(value),quantity))
 observed=np.array([x[1] for x in rows]); cov=np.loadtxt(a.cov); inv=np.linalg.inv(cov)
 def E(z,om): return math.sqrt(om*(1+z)**3+1-om)
 def model(par):
  om,h0rd=par; pred=[]
  for z,_,q in rows:
   dm=C_LIGHT/h0rd*quad(lambda zp:1/E(zp,om),0,z)[0]; dh=C_LIGHT/h0rd/E(z,om)
   pred.append(dm if q=='DM_over_rs' else dh if q=='DH_over_rs' else (z*dm**2*dh)**(1/3))
  return np.array(pred)
 def stat(par):
  r=observed-model(par); return float(r@inv@r)
 fit=minimize(stat,x0=[0.30,10150.0],method='Nelder-Mead',bounds=[(0.03,0.80),(6000,15000)],options={'maxiter':20000,'xatol':1e-12,'fatol':1e-12})
 best=np.asarray(fit.x); steps=np.array([1e-5,0.1]); jac=np.empty((len(rows),2))
 for i in range(2):
  d=np.zeros(2); d[i]=steps[i]; jac[:,i]=(model(best+d)-model(best-d))/(2*steps[i])
 pcov=np.linalg.inv(jac.T@inv@jac); err=np.sqrt(np.diag(pcov)); dof=len(rows)-2
 out={'omega_m':float(best[0]),'omega_m_sigma':float(err[0]),'H0_rd_km_s':float(best[1]),'H0_rd_sigma_km_s':float(err[1]),'chi2':float(fit.fun),'dof':dof,'PTE':float(chi2_dist.sf(fit.fun,dof))}
 Path(a.output).write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8'); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
