#!/usr/bin/env python3
from __future__ import annotations
import math
import numpy as np

VARS=('tangent_DESI_sigma','normal_DESI_sigma','omega_b','tau','n_s','logA')
AUX=VARS[2:]

def wmean_matrix(X,w):
    return np.sum(X*w[:,None],axis=0)/float(np.sum(w))

def wcov_matrix(X,w):
    sw=float(np.sum(w)); m=wmean_matrix(X,w); Z=X-m
    C=(Z*w[:,None]).T@Z/sw
    return m,(C+C.T)/2

def kish(w):
    return float(np.sum(w)**2/np.sum(w*w))

def endpoint_detail(d,w,ids):
    X=np.column_stack([np.asarray(d[k],float) for k in VARS])
    w=np.asarray(w,float); ids=np.asarray(ids,object)
    m,C=wcov_matrix(X,w)
    sd=np.sqrt(np.diag(C))
    if np.any(~np.isfinite(sd)) or np.any(sd<=0):
        raise RuntimeError('non-positive endpoint scale')
    R=(C/np.outer(sd,sd)); R=(R+R.T)/2
    eig=np.linalg.eigvalsh(R)
    if np.any(~np.isfinite(eig)) or eig[0]<=0:
        raise RuntimeError(f'non-positive 6D correlation eigenvalue: {eig}')
    return {'X':X,'w':w,'ids':ids,'mean':m,'cov':C,'sd':sd,'corr':R,'eig':eig,
            'condition_number':float(eig[-1]/eig[0])}

def endpoint_row(label,burn,D):
    r={'contract':label,'burn_fraction_per_chain':burn,'row_count':len(D['w']),
       'weight_sum':float(np.sum(D['w'])),'kish_effective_rows':kish(D['w']),
       'min_correlation_eigenvalue':float(D['eig'][0]),
       'max_correlation_eigenvalue':float(D['eig'][-1]),
       'correlation_condition_number':D['condition_number']}
    for i,k in enumerate(VARS):
        r[f'mean_{k}']=float(D['mean'][i]); r[f'sd_{k}']=float(D['sd'][i])
    return r

def support_rows(label,burn,D):
    out=[]; sw=float(np.sum(D['w']))
    for ch in sorted(set(D['ids'])):
        m=D['ids']==ch; ww=D['w'][m]
        out.append({'contract':label,'burn_fraction_per_chain':burn,'chain_file':ch,
                    'row_count':int(np.sum(m)),'weight_sum':float(np.sum(ww)),
                    'weight_share':float(np.sum(ww)/sw),'kish_effective_rows':kish(ww)})
    return out

def subset_detail(D,mask):
    X=D['X'][mask]; w=D['w'][mask]; ids=D['ids'][mask]
    return endpoint_detail({k:X[:,i] for i,k in enumerate(VARS)},w,ids)

def _decompose(delta_raw,C):
    sd=np.sqrt(np.diag(C)); R=C/np.outer(sd,sd); R=(R+R.T)/2
    eig=np.linalg.eigvalsh(R)
    if eig[0]<=0: raise RuntimeError(f'non-positive correlation eigenvalue: {eig}')
    dz=delta_raw/sd
    Rtt=R[:2,:2]; Rto=R[:2,2:]; Rot=R[2:,:2]; Roo=R[2:,2:]
    invR=np.linalg.inv(R); invT=np.linalg.inv(Rtt)
    S=Roo-Rot@invT@Rto; S=(S+S.T)/2
    seig=np.linalg.eigvalsh(S)
    if seig[0]<=0: raise RuntimeError(f'non-positive conditional eigenvalue: {seig}')
    resid=dz[2:]-Rot@invT@dz[:2]
    d2full=float(dz@invR@dz)
    d2tn=float(dz[:2]@invT@dz[:2])
    d2cond=float(resid@np.linalg.inv(S)@resid)
    uz=resid/np.sqrt(np.diag(S))
    return {'d2_full':d2full,'d2_tn':d2tn,'d2_cond':d2cond,
            'closure':d2full-d2tn-d2cond,
            'residual_fraction_d2':float(d2cond/d2full) if d2full>0 else 0.0,
            'corr_condition_number':float(eig[-1]/eig[0]),
            'conditional_condition_number':float(seig[-1]/seig[0]),
            'min_corr_eigenvalue':float(eig[0]),'min_conditional_eigenvalue':float(seig[0]),
            'conditional_residual':resid,'conditional_univariate_z':uz}

def directed_metric(edge,edge_type,boundary,burn,source_label,target_label,A,B,direction):
    delta=B['mean']-A['mean']
    q=_decompose(delta,A['cov'])
    r={'edge':edge,'direction':direction,'edge_type':edge_type,
       'interpretation_boundary':boundary,'burn_fraction_per_chain':burn,
       'source_contract':source_label,'target_contract':target_label,
       'full6d_mahalanobis':math.sqrt(max(q['d2_full'],0)),
       'tn2d_mahalanobis':math.sqrt(max(q['d2_tn'],0)),
       'conditional4d_mahalanobis':math.sqrt(max(q['d2_cond'],0)),
       'full6d_distance_squared':q['d2_full'],'tn2d_distance_squared':q['d2_tn'],
       'conditional4d_distance_squared':q['d2_cond'],
       'conditional_fraction_full_distance_squared':q['residual_fraction_d2'],
       'decomposition_closure_error':q['closure'],
       'source_correlation_condition_number':q['corr_condition_number'],
       'conditional_correlation_condition_number':q['conditional_condition_number'],
       'source_min_correlation_eigenvalue':q['min_corr_eigenvalue'],
       'conditional_min_eigenvalue':q['min_conditional_eigenvalue']}
    for i,k in enumerate(VARS): r[f'delta_{k}']=float(delta[i])
    for i,k in enumerate(AUX):
        r[f'conditional_residual_standardized_{k}']=float(q['conditional_residual'][i])
        r[f'conditional_univariate_z_{k}']=float(q['conditional_univariate_z'][i])
    j=int(np.argmax(np.abs(q['conditional_univariate_z'])))
    r['largest_abs_conditional_univariate_z_parameter']=AUX[j]
    r['largest_abs_conditional_univariate_z']=float(abs(q['conditional_univariate_z'][j]))
    return r
