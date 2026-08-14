#!/usr/bin/env python3
import numpy as np
import hts63_metric as g

def main():
    rng=np.random.default_rng(63); n=16000
    M=np.array([[1,0,0,0,0,0],[.25,1,0,0,0,0],[.15,.1,1,0,0,0],
                [.1,.2,.35,1,0,0],[.2,-.1,.25,.2,1,0],[-.1,.15,.25,.4,.15,1]],float)
    X=rng.normal(size=(n,6))@M.T
    w=np.exp(rng.normal(0,.12,n))
    ids=np.array([f'CLASS.{i%6+1}.txt' for i in range(n)],object)
    A=g.endpoint_detail({k:X[:,i] for i,k in enumerate(g.VARS)},w,ids)
    Y=X+np.array([.35,-.15,.25,.2,-.4,.15])
    B=g.endpoint_detail({k:Y[:,i] for i,k in enumerate(g.VARS)},w,ids)
    s,v=g.directed_variable_allocation('E','TEST','boundary',.3,'A','B',A,B,'FORWARD')
    assert abs(sum(r['unrestricted_shapley_distance_squared'] for r in v)-s['conditional4d_distance_squared'])<1e-10
    assert abs(sum(r['owen_distance_squared'] for r in v)-s['conditional4d_distance_squared'])<1e-10
    b=sum(r['owen_distance_squared'] for r in v if r['fixed_block']=='BARYON_TILT')
    a=sum(r['owen_distance_squared'] for r in v if r['fixed_block']=='TAU_AMPLITUDE')
    assert abs(b-s['baryon_tilt_block_shapley_share']*s['conditional4d_distance_squared'])<1e-10
    assert abs(a-s['tau_amplitude_block_shapley_share']*s['conditional4d_distance_squared'])<1e-10
    assert min(r['all_order_marginal_min'] for r in v)>-1e-10
    assert 1<=s['effective_variable_count_shapley']<=4
    print('HTS63 SELFTEST PASS')

if __name__=='__main__':
    main()
