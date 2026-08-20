#!/usr/bin/env python3
from __future__ import annotations
import itertools
import math
from math import factorial
import numpy as np

VARS=('tangent_DESI_sigma','normal_DESI_sigma','omega_b','tau','n_s','logA')
AUX=VARS[2:]
BLOCKS={'BARYON_TILT':(0,2),'TAU_AMPLITUDE':(1,3)}
ANGLES=(0,15,30,45,60,75,90)
N=4
ALL=tuple(range(N))

def wmean_matrix(X,w):
    return np.sum(X*w[:,None],axis=0)/float(np.sum(w))

def wcov_matrix(X,w):
    sw=float(np.sum(w))
    m=wmean_matrix(X,w)
    Z=X-m
    C=(Z*w[:,None]).T@Z/sw
    return m,(C+C.T)/2

def kish(w):
    return float(np.sum(w)**2/np.sum(w*w))

def endpoint_detail(d,w,ids):
    X=np.column_stack([np.asarray(d[k],float) for k in VARS])
    w=np.asarray(w,float)
    ids=np.asarray(ids,object)
    m,C=wcov_matrix(X,w)
    vals=np.linalg.eigvalsh(C)
    if vals[0] <= 0 or not np.all(np.isfinite(vals)):
        raise RuntimeError(f'non-positive 6D covariance eigenvalue: {vals}')
    return {'X':X,'w':w,'ids':ids,'mean':m,'cov':C}

def subset_detail(D,mask):
    X=D['X'][mask]
    w=D['w'][mask]
    ids=D['ids'][mask]
    return endpoint_detail({k:X[:,i] for i,k in enumerate(VARS)},w,ids)

def support_rows(label,burn,D):
    out=[]
    sw=float(np.sum(D['w']))
    for ch in sorted(set(D['ids'])):
        m=D['ids']==ch
        ww=D['w'][m]
        out.append({
            'contract':label,'burn_fraction_per_chain':burn,'chain_file':ch,
            'row_count':int(np.sum(m)),'weight_sum':float(np.sum(ww)),
            'weight_share':float(np.sum(ww)/sw),
            'kish_effective_rows':kish(ww),
        })
    return out

def conditional_raw(C,delta):
    Ctt=C[:2,:2]
    Cto=C[:2,2:]
    Cot=C[2:,:2]
    Coo=C[2:,2:]
    inv=np.linalg.inv(Ctt)
    S=Coo-Cot@inv@Cto
    S=(S+S.T)/2
    r=delta[2:]-Cot@inv@delta[:2]
    vals=np.linalg.eigvalsh(S)
    if vals[0] <= 0 or not np.all(np.isfinite(vals)):
        raise RuntimeError(f'non-positive conditional covariance eigenvalue: {vals}')
    return r,S

def standardize(r,S):
    sd=np.sqrt(np.diag(S))
    if np.any(sd<=0):
        raise RuntimeError('non-positive transformed conditional scale')
    z=r/sd
    T=S/np.outer(sd,sd)
    T=(T+T.T)/2
    vals=np.linalg.eigvalsh(T)
    if vals[0] <= 0 or not np.all(np.isfinite(vals)):
        raise RuntimeError(f'non-positive transformed correlation eigenvalue: {vals}')
    return z,T,vals

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

def coalition_orders():
    out=[]
    block_names=('BARYON_TILT','TAU_AMPLITUDE')
    for block_order in itertools.permutations(block_names):
        within=[list(itertools.permutations(BLOCKS[b])) for b in block_order]
        for first in within[0]:
            for second in within[1]:
                out.append(tuple(first+second))
    return out

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

def block_shapley(vals):
    b=tuple(sorted(BLOCKS['BARYON_TILT']))
    a=tuple(sorted(BLOCKS['TAU_AMPLITUDE']))
    total=vals[tuple(sorted(ALL))]
    bm=vals[b]
    am=vals[a]
    return .5*(bm+(total-am)), .5*(am+(total-bm))

def rotation(theta_deg):
    th=math.radians(theta_deg)
    return np.array([[math.cos(th),-math.sin(th)],
                     [math.sin(th), math.cos(th)]],float)

def standardized_rotation_raw_transform(Sraw,theta_b,theta_a):
    D=np.diag(np.sqrt(np.diag(Sraw)))
    Di=np.diag(1/np.sqrt(np.diag(Sraw)))
    R=np.eye(4)
    Rb=rotation(theta_b)
    Ra=rotation(theta_a)
    bi=list(BLOCKS['BARYON_TILT'])
    ai=list(BLOCKS['TAU_AMPLITUDE'])
    R[np.ix_(bi,bi)]=Rb
    R[np.ix_(ai,ai)]=Ra
    return D@R@Di

def physical_amplitude_transform():
    L=np.eye(4)
    # New fourth coordinate is logA_eff = logA - 2*tau.
    L[3,1]=-2.0
    return L

def transformed_allocation(r,S,L,coordinate_names):
    rt=L@r
    St=L@S@L.T
    z,T,eig=standardize(rt,St)
    vals=all_game_values(T,z)
    total=vals[tuple(sorted(ALL))]
    phi=exact_shapley(vals)
    owen=np.mean(permutation_marginals(vals,coalition_orders()),axis=0)
    shb,sha=block_shapley(vals)
    if total<=0:
        raise RuntimeError('non-positive conditional distance')
    sshare=phi/total
    oshare=owen/total
    top_s=int(np.argmax(sshare))
    top_o=int(np.argmax(oshare))
    return {
        'conditional4d_distance_squared':total,
        'conditional4d_mahalanobis':math.sqrt(total),
        'min_transformed_correlation_eigenvalue':float(eig[0]),
        'condition_number':float(eig[-1]/eig[0]),
        'shapley_closure_error':float(np.sum(phi)-total),
        'owen_closure_error':float(np.sum(owen)-total),
        'baryon_tilt_block_share':float(shb/total),
        'tau_amplitude_block_share':float(sha/total),
        'top_shapley_coordinate':coordinate_names[top_s],
        'top_shapley_share':float(sshare[top_s]),
        'top_owen_coordinate':coordinate_names[top_o],
        'top_owen_share':float(oshare[top_o]),
        'effective_variable_count_shapley':float(1/np.sum(sshare*sshare)),
        'effective_variable_count_owen':float(1/np.sum(oshare*oshare)),
        'minimum_marginal_contribution':float(min(np.min(permutation_marginals(vals,list(itertools.permutations(ALL)))),
                                                  np.min(permutation_marginals(vals,coalition_orders())))),
        '_phi':phi,'_owen':owen,'_sshare':sshare,'_oshare':oshare,
    }

def directed_rotation_audit(edge,etype,boundary,burn,source_label,target_label,A,B,direction):
    delta=B['mean']-A['mean']
    r,S=conditional_raw(A['cov'],delta)
    identity=np.eye(4)
    original=transformed_allocation(r,S,identity,list(AUX))
    grid=[]
    coords=[]
    top_names=set()
    top_share_values=[]
    eff_values=[]
    max_total_error=0.0
    max_block_error=0.0
    min_eig=1e300
    max_cond=0.0
    min_marg=1e300
    max_close=0.0
    for tb in ANGLES:
        for ta in ANGLES:
            L=standardized_rotation_raw_transform(S,tb,ta)
            names=(f'B1_rot{tb}',f'A1_rot{ta}',f'B2_rot{tb}',f'A2_rot{ta}')
            q=transformed_allocation(r,S,L,names)
            grid.append({
                'edge':edge,'direction':direction,'edge_type':etype,
                'burn_fraction_per_chain':burn,'source_contract':source_label,
                'target_contract':target_label,'baryon_rotation_deg':tb,
                'tau_amplitude_rotation_deg':ta,
                **{k:v for k,v in q.items() if not k.startswith('_')},
            })
            for i,name in enumerate(names):
                coords.append({
                    'edge':edge,'direction':direction,'burn_fraction_per_chain':burn,
                    'baryon_rotation_deg':tb,'tau_amplitude_rotation_deg':ta,
                    'coordinate_index':i+1,'coordinate_name':name,
                    'fixed_block':'BARYON_TILT' if i in BLOCKS['BARYON_TILT'] else 'TAU_AMPLITUDE',
                    'shapley_share':float(q['_sshare'][i]),
                    'owen_share':float(q['_oshare'][i]),
                })
            top_names.add(q['top_shapley_coordinate'])
            top_share_values.append(q['top_shapley_share'])
            eff_values.append(q['effective_variable_count_shapley'])
            max_total_error=max(max_total_error,abs(q['conditional4d_distance_squared']-original['conditional4d_distance_squared']))
            max_block_error=max(max_block_error,
                                abs(q['baryon_tilt_block_share']-original['baryon_tilt_block_share']),
                                abs(q['tau_amplitude_block_share']-original['tau_amplitude_block_share']))
            min_eig=min(min_eig,q['min_transformed_correlation_eigenvalue'])
            max_cond=max(max_cond,q['condition_number'])
            min_marg=min(min_marg,q['minimum_marginal_contribution'])
            max_close=max(max_close,abs(q['shapley_closure_error']),abs(q['owen_closure_error']))
    phys=transformed_allocation(
        r,S,physical_amplitude_transform(),
        ('omega_b','tau','n_s','logA_minus_2tau')
    )
    summary={
        'edge':edge,'direction':direction,'edge_type':etype,
        'interpretation_boundary':boundary,'burn_fraction_per_chain':burn,
        'source_contract':source_label,'target_contract':target_label,
        'conditional4d_mahalanobis':original['conditional4d_mahalanobis'],
        'original_top_shapley_variable':original['top_shapley_coordinate'],
        'original_top_shapley_share':original['top_shapley_share'],
        'original_effective_variable_count':original['effective_variable_count_shapley'],
        'rotation_grid_top_share_min':float(min(top_share_values)),
        'rotation_grid_top_share_max':float(max(top_share_values)),
        'rotation_grid_top_share_range':float(max(top_share_values)-min(top_share_values)),
        'rotation_grid_effective_count_min':float(min(eff_values)),
        'rotation_grid_effective_count_max':float(max(eff_values)),
        'rotation_grid_effective_count_range':float(max(eff_values)-min(eff_values)),
        'rotation_grid_unique_top_coordinate_count':len(top_names),
        'max_total_distance_invariance_error':max_total_error,
        'max_block_share_invariance_error':max_block_error,
        'minimum_transformed_correlation_eigenvalue':min_eig,
        'maximum_transformed_condition_number':max_cond,
        'minimum_permutation_marginal_contribution':min_marg,
        'max_allocation_closure_error':max_close,
        'physical_amplitude_top_shapley_coordinate':phys['top_shapley_coordinate'],
        'physical_amplitude_top_shapley_share':phys['top_shapley_share'],
        'physical_amplitude_effective_variable_count':phys['effective_variable_count_shapley'],
        'physical_amplitude_baryon_tilt_block_share':phys['baryon_tilt_block_share'],
        'physical_amplitude_tau_amplitude_block_share':phys['tau_amplitude_block_share'],
    }
    if summary['rotation_grid_top_share_range']>0.15 or summary['rotation_grid_effective_count_range']>0.50 or summary['rotation_grid_unique_top_coordinate_count']>1:
        summary['reparameterization_classification']='BLOCK_ROBUST_VARIABLE_ALLOCATION_BASIS_SENSITIVE'
    else:
        summary['reparameterization_classification']='VARIABLE_ALLOCATION_ROTATION_STABLE'
    return summary,grid,coords
