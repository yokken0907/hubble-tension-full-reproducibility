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
    R=C/np.outer(sd,sd); R=(R+R.T)/2
    eig=np.linalg.eigvalsh(R)
    if np.any(~np.isfinite(eig)) or eig[0]<=0:
        raise RuntimeError(f'non-positive 6D correlation eigenvalue: {eig}')
    return {'X':X,'w':w,'ids':ids,'mean':m,'cov':C,'sd':sd,'corr':R,'eig':eig,
            'condition_number':float(eig[-1]/eig[0])}

def subset_detail(D,mask):
    X=D['X'][mask]; w=D['w'][mask]; ids=D['ids'][mask]
    return endpoint_detail({k:X[:,i] for i,k in enumerate(VARS)},w,ids)

def support_rows(label,burn,D):
    out=[]; sw=float(np.sum(D['w']))
    for ch in sorted(set(D['ids'])):
        m=D['ids']==ch; ww=D['w'][m]
        out.append({'contract':label,'burn_fraction_per_chain':burn,'chain_file':ch,
                    'row_count':int(np.sum(m)),'weight_sum':float(np.sum(ww)),
                    'weight_share':float(np.sum(ww)/sw),'kish_effective_rows':kish(ww)})
    return out

def conditional_basis(C):
    sd=np.sqrt(np.diag(C))
    R=C/np.outer(sd,sd); R=(R+R.T)/2
    Rtt=R[:2,:2]; Rto=R[:2,2:]; Rot=R[2:,:2]; Roo=R[2:,2:]
    invT=np.linalg.inv(Rtt)
    S=Roo-Rot@invT@Rto; S=(S+S.T)/2
    csd=np.sqrt(np.diag(S))
    if np.any(csd<=0): raise RuntimeError('non-positive conditional scale')
    T=S/np.outer(csd,csd); T=(T+T.T)/2
    vals,vecs=np.linalg.eigh(T)
    if vals[0]<=0 or not np.all(np.isfinite(vals)):
        raise RuntimeError(f'non-positive conditional-correlation eigenvalue: {vals}')
    # Deterministic sign: largest absolute loading is positive.
    for j in range(vecs.shape[1]):
        k=int(np.argmax(np.abs(vecs[:,j])))
        if vecs[k,j] < 0: vecs[:,j]*=-1
    return {'R':R,'Rtt':Rtt,'Rot':Rot,'Rto':Rto,'S':S,'csd':csd,
            'T':T,'eigvals':vals,'eigvecs':vecs,
            'condition_number':float(vals[-1]/vals[0])}

def endpoint_mode_rows(label,burn,D):
    B=conditional_basis(D['cov']); out=[]
    for j in range(4):
        v=B['eigvecs'][:,j]
        dom=int(np.argmax(np.abs(v)))
        r={'contract':label,'burn_fraction_per_chain':burn,
           'mode_index_ascending_eigenvalue':j+1,
           'conditional_correlation_eigenvalue':float(B['eigvals'][j]),
           'dominant_loading_parameter':AUX[dom],
           'dominant_abs_loading':float(abs(v[dom]))}
        for i,k in enumerate(AUX): r[f'loading_{k}']=float(v[i])
        out.append(r)
    return out

def directed_modes(edge,etype,boundary,burn,source_label,target_label,A,B,direction):
    delta=B['mean']-A['mean']; sd=A['sd']; dz=delta/sd
    Q=conditional_basis(A['cov'])
    resid=dz[2:]-Q['Rot']@np.linalg.inv(Q['Rtt'])@dz[:2]
    zc=resid/Q['csd']
    vals=Q['eigvals']; vecs=Q['eigvecs']
    amp=vecs.T@zc/np.sqrt(vals)
    contrib=amp*amp
    d2=float(np.sum(contrib))
    inv=float(zc@np.linalg.inv(Q['T'])@zc)
    closure=d2-inv
    if d2>0:
        frac=contrib/d2
        eff=float(1/np.sum(frac*frac))
    else:
        frac=np.zeros(4); eff=0.0
    order=np.argsort(contrib)[::-1]
    summary={
        'edge':edge,'direction':direction,'edge_type':etype,
        'interpretation_boundary':boundary,'burn_fraction_per_chain':burn,
        'source_contract':source_label,'target_contract':target_label,
        'conditional4d_distance_squared':d2,
        'conditional4d_mahalanobis':math.sqrt(max(d2,0)),
        'mode_decomposition_closure_error':closure,
        'conditional_mode_condition_number':Q['condition_number'],
        'top1_mode_fraction':float(frac[order[0]]) if d2>0 else 0.0,
        'top2_mode_fraction':float(frac[order[0]]+frac[order[1]]) if d2>0 else 0.0,
        'effective_contributing_mode_count':eff,
        'top_contribution_mode_index_ascending_eigenvalue':int(order[0]+1),
        'top_mode_dominant_parameter':AUX[int(np.argmax(np.abs(vecs[:,order[0]])))],
    }
    modes=[]
    for rank,j in enumerate(order,1):
        v=vecs[:,j]; dom=int(np.argmax(np.abs(v)))
        r={'edge':edge,'direction':direction,'edge_type':etype,
           'burn_fraction_per_chain':burn,'source_contract':source_label,
           'target_contract':target_label,'contribution_rank':rank,
           'mode_index_ascending_eigenvalue':int(j+1),
           'conditional_correlation_eigenvalue':float(vals[j]),
           'signed_mahalanobis_mode_amplitude':float(amp[j]),
           'mode_distance_squared_contribution':float(contrib[j]),
           'mode_fraction_conditional_distance_squared':float(frac[j]) if d2>0 else 0.0,
           'dominant_loading_parameter':AUX[dom],
           'dominant_abs_loading':float(abs(v[dom]))}
        for i,k in enumerate(AUX): r[f'loading_{k}']=float(v[i])
        modes.append(r)
    return summary,modes

def mode_vector_from_summary(summary):
    return np.array([summary['top1_mode_fraction'],summary['top2_mode_fraction'],
                     summary['effective_contributing_mode_count']],float)
