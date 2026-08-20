#!/usr/bin/env python3
from __future__ import annotations
import itertools
import math
from math import factorial
import numpy as np

VARS=('tangent_DESI_sigma','normal_DESI_sigma','omega_b','tau','n_s','logA')
AUX=VARS[2:]
N=4
ALL=tuple(range(N))
CANONICAL_PARTITION=((0,2),(1,3))

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

def conditional_system(C,delta):
    Ctt=C[:2,:2]
    Cto=C[:2,2:]
    Cot=C[2:,:2]
    Coo=C[2:,2:]
    inv=np.linalg.inv(Ctt)
    S=Coo-Cot@inv@Cto
    S=(S+S.T)/2
    r=delta[2:]-Cot@inv@delta[:2]
    sd=np.sqrt(np.diag(S))
    if np.any(sd<=0):
        raise RuntimeError('non-positive conditional scale')
    z=r/sd
    T=S/np.outer(sd,sd)
    T=(T+T.T)/2
    eig=np.linalg.eigvalsh(T)
    if eig[0] <= 0 or not np.all(np.isfinite(eig)):
        raise RuntimeError(f'non-positive conditional correlation eigenvalue: {eig}')
    return z,T,eig

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

def set_partitions(items=ALL):
    items=tuple(items)
    if not items:
        return [tuple()]
    first=items[0]
    rest=set_partitions(items[1:])
    out=set()
    for part in rest:
        # New singleton block.
        blocks=[tuple(b) for b in part]+[(first,)]
        canon=tuple(sorted((tuple(sorted(b)) for b in blocks),key=lambda b:(b[0],len(b),b)))
        out.add(canon)
        # Insert into each existing block.
        for j in range(len(part)):
            blocks=[tuple(b) for b in part]
            blocks[j]=tuple(sorted(blocks[j]+(first,)))
            canon=tuple(sorted((tuple(sorted(b)) for b in blocks),key=lambda b:(b[0],len(b),b)))
            out.add(canon)
    return sorted(out,key=lambda p:(len(p),tuple(len(b) for b in p),p))

PARTITIONS=tuple(set_partitions())

def partition_id(partition):
    return 'P'+str(PARTITIONS.index(partition)+1).zfill(2)

def partition_string(partition):
    return '|'.join('+'.join(AUX[i] for i in block) for block in partition)

def size_signature(partition):
    return '+'.join(str(len(b)) for b in sorted(partition,key=lambda b:(-len(b),b)))

def respecting_orders(partition):
    out=set()
    for block_order in itertools.permutations(partition):
        within=[list(itertools.permutations(block)) for block in block_order]
        for combo in itertools.product(*within):
            out.add(tuple(i for seq in combo for i in seq))
    return sorted(out)

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

def owen_for_partition(vals,partition):
    orders=respecting_orders(partition)
    marg=permutation_marginals(vals,orders)
    return np.mean(marg,axis=0),marg,orders

def partition_catalog_rows():
    rows=[]
    for p in PARTITIONS:
        rows.append({
            'partition_id':partition_id(p),
            'partition':partition_string(p),
            'block_count':len(p),
            'block_size_signature':size_signature(p),
            'respecting_order_count':len(respecting_orders(p)),
            'is_HTS62_canonical_partition':p==CANONICAL_PARTITION,
            'is_all_singletons':len(p)==N,
            'is_single_all_variable_block':len(p)==1,
        })
    return rows

def directed_partition_audit(edge,etype,boundary,burn,source_label,target_label,A,B,direction):
    delta=B['mean']-A['mean']
    z,T,eig=conditional_system(A['cov'],delta)
    vals=all_game_values(T,z)
    total=vals[tuple(sorted(ALL))]
    if total<=0:
        raise RuntimeError('non-positive conditional distance')
    shapley=exact_shapley(vals)
    sshare=shapley/total
    variable_rows=[]
    block_rows=[]
    partition_rows=[]
    top_set=set()
    effs=[]
    top_shares=[]
    max_coal_shift=0.0
    max_close=0.0
    max_recon=0.0
    min_marg=1e300
    share_matrix=[]
    canonical_top=None
    canonical_share=None
    canonical_max_shift=None
    for p in PARTITIONS:
        pid=partition_id(p)
        owen,marg,orders=owen_for_partition(vals,p)
        oshare=owen/total
        share_matrix.append(oshare)
        top=int(np.argmax(oshare))
        top_set.add(AUX[top])
        eff=float(1/np.sum(oshare*oshare))
        effs.append(eff)
        top_shares.append(float(oshare[top]))
        max_shift=float(np.max(np.abs(oshare-sshare)))
        max_coal_shift=max(max_coal_shift,max_shift)
        close=float(np.sum(owen)-total)
        max_close=max(max_close,abs(close))
        min_marg=min(min_marg,float(np.min(marg)))
        for i,name in enumerate(AUX):
            block_index=next(j for j,b in enumerate(p) if i in b)
            variable_rows.append({
                'edge':edge,'direction':direction,'edge_type':etype,
                'burn_fraction_per_chain':burn,'source_contract':source_label,
                'target_contract':target_label,'partition_id':pid,
                'partition':partition_string(p),'variable':name,
                'block_index':block_index+1,
                'unrestricted_shapley_share':float(sshare[i]),
                'partition_owen_share':float(oshare[i]),
                'owen_minus_shapley_share':float(oshare[i]-sshare[i]),
            })
        for j,block in enumerate(p):
            block_sum=float(np.sum(owen[list(block)]))
            # Exact coalition Shapley in the quotient game, computed from the two-stage order average.
            block_rows.append({
                'edge':edge,'direction':direction,'edge_type':etype,
                'burn_fraction_per_chain':burn,'source_contract':source_label,
                'target_contract':target_label,'partition_id':pid,
                'partition':partition_string(p),'block_index':j+1,
                'block_variables':'+'.join(AUX[i] for i in block),
                'block_owen_distance_squared':block_sum,
                'block_owen_share':block_sum/total,
            })
        recon=abs(sum(r['block_owen_distance_squared'] for r in block_rows
                      if r['edge']==edge and r['direction']==direction
                      and r['burn_fraction_per_chain']==burn and r['partition_id']==pid)-total)
        max_recon=max(max_recon,recon)
        pr={
            'edge':edge,'direction':direction,'edge_type':etype,
            'interpretation_boundary':boundary,'burn_fraction_per_chain':burn,
            'source_contract':source_label,'target_contract':target_label,
            'partition_id':pid,'partition':partition_string(p),
            'block_count':len(p),'block_size_signature':size_signature(p),
            'respecting_order_count':len(orders),
            'is_HTS62_canonical_partition':p==CANONICAL_PARTITION,
            'top_owen_variable':AUX[top],
            'top_owen_share':float(oshare[top]),
            'effective_variable_count_owen':eff,
            'max_abs_owen_minus_shapley_share':max_shift,
            'owen_closure_error':close,
            'minimum_respecting_order_marginal_contribution':float(np.min(marg)),
        }
        partition_rows.append(pr)
        if p==CANONICAL_PARTITION:
            canonical_top=AUX[top]
            canonical_share=float(oshare[top])
            canonical_max_shift=max_shift
    M=np.asarray(share_matrix,float)
    ranges=np.max(M,axis=0)-np.min(M,axis=0)
    max_range=float(np.max(ranges))
    summary={
        'edge':edge,'direction':direction,'edge_type':etype,
        'interpretation_boundary':boundary,'burn_fraction_per_chain':burn,
        'source_contract':source_label,'target_contract':target_label,
        'conditional4d_distance_squared':total,
        'conditional4d_mahalanobis':math.sqrt(total),
        'unrestricted_top_variable':AUX[int(np.argmax(sshare))],
        'unrestricted_top_share':float(np.max(sshare)),
        'canonical_partition_top_variable':canonical_top,
        'canonical_partition_top_share':canonical_share,
        'canonical_partition_max_abs_shift_from_shapley':canonical_max_shift,
        'partition_unique_top_variable_count':len(top_set),
        'partition_top_variable_set':','.join(sorted(top_set)),
        'partition_top_share_min':float(min(top_shares)),
        'partition_top_share_max':float(max(top_shares)),
        'partition_top_share_range':float(max(top_shares)-min(top_shares)),
        'partition_effective_count_min':float(min(effs)),
        'partition_effective_count_max':float(max(effs)),
        'partition_effective_count_range':float(max(effs)-min(effs)),
        'max_variable_owen_share_range_across_partitions':max_range,
        'max_abs_partition_owen_minus_shapley_share':max_coal_shift,
        'minimum_respecting_order_marginal_contribution':min_marg,
        'max_owen_closure_error':max_close,
        'max_partition_block_reconciliation_error':max_recon,
        'min_conditional_correlation_eigenvalue':float(eig[0]),
        'conditional_correlation_condition_number':float(eig[-1]/eig[0]),
    }
    if (summary['partition_unique_top_variable_count']>1
        or summary['max_variable_owen_share_range_across_partitions']>0.15
        or summary['partition_effective_count_range']>0.50):
        summary['partition_sensitivity_classification']='COALITION_PARTITION_SENSITIVE'
    else:
        summary['partition_sensitivity_classification']='COALITION_PARTITION_STABLE'
    return summary,partition_rows,variable_rows,block_rows
