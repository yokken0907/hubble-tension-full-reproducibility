#!/usr/bin/env python3
from __future__ import annotations
import itertools
import math
from math import factorial
import numpy as np

VARS=('tangent_DESI_sigma','normal_DESI_sigma','omega_b','tau','n_s','logA')
AUX=VARS[2:]
BLOCKS={'BARYON_TILT':(0,2),'TAU_AMPLITUDE':(1,3)}
VAR_TO_BLOCK={0:'BARYON_TILT',2:'BARYON_TILT',1:'TAU_AMPLITUDE',3:'TAU_AMPLITUDE'}
N=4
ALL=tuple(range(N))

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
    m,C=wcov_matrix(X,w); sd=np.sqrt(np.diag(C))
    if np.any(~np.isfinite(sd)) or np.any(sd<=0):
        raise RuntimeError('non-positive endpoint scale')
    R=C/np.outer(sd,sd); R=(R+R.T)/2
    vals=np.linalg.eigvalsh(R)
    if vals[0]<=0 or not np.all(np.isfinite(vals)):
        raise RuntimeError(f'non-positive 6D correlation eigenvalue: {vals}')
    return {'X':X,'w':w,'ids':ids,'mean':m,'cov':C,'sd':sd,'corr':R,
            'eig':vals,'condition_number':float(vals[-1]/vals[0])}

def subset_detail(D,mask):
    X=D['X'][mask]; w=D['w'][mask]; ids=D['ids'][mask]
    return endpoint_detail({k:X[:,i] for i,k in enumerate(VARS)},w,ids)

def conditional_system(C):
    sd=np.sqrt(np.diag(C))
    R=C/np.outer(sd,sd); R=(R+R.T)/2
    Rtt=R[:2,:2]; Rto=R[:2,2:]; Rot=R[2:,:2]; Roo=R[2:,2:]
    S=Roo-Rot@np.linalg.inv(Rtt)@Rto; S=(S+S.T)/2
    csd=np.sqrt(np.diag(S))
    if np.any(csd<=0):
        raise RuntimeError('non-positive conditional scale')
    T=S/np.outer(csd,csd); T=(T+T.T)/2
    vals=np.linalg.eigvalsh(T)
    if vals[0]<=0 or not np.all(np.isfinite(vals)):
        raise RuntimeError(f'non-positive conditional correlation eigenvalue: {vals}')
    return {'R':R,'Rtt':Rtt,'Rot':Rot,'S':S,'csd':csd,'T':T,
            'eigvals':vals,'condition_number':float(vals[-1]/vals[0])}

def support_rows(label,burn,D):
    out=[]; sw=float(np.sum(D['w']))
    for ch in sorted(set(D['ids'])):
        m=D['ids']==ch; ww=D['w'][m]
        out.append({'contract':label,'burn_fraction_per_chain':burn,'chain_file':ch,
                    'row_count':int(np.sum(m)),'weight_sum':float(np.sum(ww)),
                    'weight_share':float(np.sum(ww)/sw),
                    'kish_effective_rows':kish(ww)})
    return out

def game_value(T,z,S):
    S=tuple(sorted(S))
    if not S:
        return 0.0
    idx=np.asarray(S,int)
    M=T[np.ix_(idx,idx)]
    q=z[idx]
    return float(q@np.linalg.inv(M)@q)

def all_game_values(T,z):
    vals={}
    for r in range(N+1):
        for S in itertools.combinations(ALL,r):
            vals[S]=game_value(T,z,S)
    return vals

def exact_shapley(vals):
    phi=np.zeros(N,float)
    den=factorial(N)
    for i in ALL:
        others=[j for j in ALL if j!=i]
        for r in range(N):
            coeff=factorial(r)*factorial(N-r-1)/den
            for S in itertools.combinations(others,r):
                phi[i]+=coeff*(vals[tuple(sorted(S+(i,)))]-vals[tuple(sorted(S))])
    return phi

def permutation_marginals(vals,orders):
    rows=[]
    for order in orders:
        S=()
        contrib=np.zeros(N,float)
        for i in order:
            S2=tuple(sorted(S+(i,)))
            contrib[i]=vals[S2]-vals[tuple(sorted(S))]
            S=S2
        rows.append(contrib)
    return np.asarray(rows,float)

def all_orders():
    return list(itertools.permutations(ALL))

def coalition_orders():
    out=[]
    block_names=('BARYON_TILT','TAU_AMPLITUDE')
    for block_order in itertools.permutations(block_names):
        within=[list(itertools.permutations(BLOCKS[b])) for b in block_order]
        for first in within[0]:
            for second in within[1]:
                out.append(tuple(first+second))
    return out

def block_shapley(vals):
    b=tuple(sorted(BLOCKS['BARYON_TILT']))
    a=tuple(sorted(BLOCKS['TAU_AMPLITUDE']))
    total=vals[tuple(sorted(ALL))]
    bm=vals[b]; am=vals[a]
    shb=.5*(bm+(total-am))
    sha=.5*(am+(total-bm))
    return shb,sha

def classify(summary):
    if not summary['top_variable_agreement']:
        return 'COALITION_SENSITIVE'
    if summary['max_abs_owen_minus_shapley_share']>0.15:
        return 'COALITION_SENSITIVE'
    if summary['max_order_range_fraction']>0.50:
        return 'ORDER_SENSITIVE'
    if summary['top_shapley_share']>=0.60:
        return summary['top_shapley_variable'].upper()+'_DOMINANT'
    return 'MIXED_VARIABLE'

def directed_variable_allocation(edge,etype,boundary,burn,source_label,target_label,A,B,direction):
    delta=B['mean']-A['mean']; dz=delta/A['sd']
    Q=conditional_system(A['cov'])
    resid=dz[2:]-Q['Rot']@np.linalg.inv(Q['Rtt'])@dz[:2]
    z=resid/Q['csd']; T=Q['T']
    vals=all_game_values(T,z)
    total=vals[tuple(sorted(ALL))]
    phi=exact_shapley(vals)
    allm=permutation_marginals(vals,all_orders())
    coalm=permutation_marginals(vals,coalition_orders())
    owen=np.mean(coalm,axis=0)
    shb,sha=block_shapley(vals)
    closure=float(np.sum(phi)-total)
    oclosure=float(np.sum(owen)-total)
    brecon_b=float(np.sum(owen[list(BLOCKS['BARYON_TILT'])])-shb)
    brecon_a=float(np.sum(owen[list(BLOCKS['TAU_AMPLITUDE'])])-sha)
    min_marginal=float(min(np.min(allm),np.min(coalm)))
    if total>0:
        sshare=phi/total; oshare=owen/total
        eff_s=float(1/np.sum(sshare*sshare))
        eff_o=float(1/np.sum(oshare*oshare))
        ranges=(np.max(allm,axis=0)-np.min(allm,axis=0))/total
    else:
        sshare=np.zeros(N); oshare=np.zeros(N); eff_s=eff_o=0.0; ranges=np.zeros(N)
    top_s=int(np.argmax(sshare)); top_o=int(np.argmax(oshare))
    summary={
        'edge':edge,'direction':direction,'edge_type':etype,
        'interpretation_boundary':boundary,'burn_fraction_per_chain':burn,
        'source_contract':source_label,'target_contract':target_label,
        'conditional4d_distance_squared':total,
        'conditional4d_mahalanobis':math.sqrt(max(total,0)),
        'top_shapley_variable':AUX[top_s],
        'top_shapley_share':float(sshare[top_s]),
        'top_owen_variable':AUX[top_o],
        'top_owen_share':float(oshare[top_o]),
        'top_variable_agreement':bool(top_s==top_o),
        'effective_variable_count_shapley':eff_s,
        'effective_variable_count_owen':eff_o,
        'max_abs_owen_minus_shapley_share':float(np.max(np.abs(oshare-sshare))),
        'max_order_range_fraction':float(np.max(ranges)),
        'minimum_permutation_marginal_contribution':min_marginal,
        'shapley_closure_error':closure,
        'owen_closure_error':oclosure,
        'baryon_tilt_block_reconciliation_error':brecon_b,
        'tau_amplitude_block_reconciliation_error':brecon_a,
        'baryon_tilt_block_shapley_share':float(shb/total) if total>0 else 0.0,
        'tau_amplitude_block_shapley_share':float(sha/total) if total>0 else 0.0,
    }
    summary['variable_pattern_classification']=classify(summary)
    variables=[]
    for i,name in enumerate(AUX):
        variables.append({
            'edge':edge,'direction':direction,'edge_type':etype,
            'burn_fraction_per_chain':burn,'source_contract':source_label,
            'target_contract':target_label,'variable':name,
            'fixed_block':VAR_TO_BLOCK[i],
            'conditional_residual_coordinate':float(z[i]),
            'unrestricted_shapley_distance_squared':float(phi[i]),
            'unrestricted_shapley_share':float(sshare[i]) if total>0 else 0.0,
            'owen_distance_squared':float(owen[i]),
            'owen_share':float(oshare[i]) if total>0 else 0.0,
            'owen_minus_shapley_share':float(oshare[i]-sshare[i]) if total>0 else 0.0,
            'all_order_marginal_mean':float(np.mean(allm[:,i])),
            'all_order_marginal_std':float(np.std(allm[:,i])),
            'all_order_marginal_min':float(np.min(allm[:,i])),
            'all_order_marginal_max':float(np.max(allm[:,i])),
            'all_order_range_fraction':float(ranges[i]) if total>0 else 0.0,
            'coalition_order_marginal_mean':float(np.mean(coalm[:,i])),
            'coalition_order_marginal_std':float(np.std(coalm[:,i])),
            'coalition_order_marginal_min':float(np.min(coalm[:,i])),
            'coalition_order_marginal_max':float(np.max(coalm[:,i])),
        })
    return summary,variables

def vector_from_rows(rows,key):
    d={r['variable']:float(r[key]) for r in rows}
    return np.array([d[k] for k in AUX],float)
