#!/usr/bin/env python3
import numpy as np
import hts60_metric as g

def main():
    rng=np.random.default_rng(60); n=14000
    M=np.array([[1,0,0,0,0,0],[.35,1,0,0,0,0],[.2,.1,1,0,0,0],
                [.1,.2,.4,1,0,0],[.2,-.1,.2,.3,1,0],[-.1,.2,.3,.4,.2,1]],float)
    X=rng.normal(size=(n,6))@M.T
    w=np.exp(rng.normal(0,.12,n)); ids=np.array([f'CLASS.{i%6+1}.txt' for i in range(n)],object)
    A=g.endpoint_detail({k:X[:,i] for i,k in enumerate(g.VARS)},w,ids)
    Y=X+np.array([.4,-.2,.2,.25,-.35,.15])
    B=g.endpoint_detail({k:Y[:,i] for i,k in enumerate(g.VARS)},w,ids)
    s,m=g.directed_modes('E','TEST','boundary',.3,'A','B',A,B,'FORWARD')
    assert abs(sum(r['mode_distance_squared_contribution'] for r in m)-s['conditional4d_distance_squared'])<1e-10
    assert abs(sum(r['mode_fraction_conditional_distance_squared'] for r in m)-1)<1e-10
    assert 1<=s['effective_contributing_mode_count']<=4
    assert len(g.endpoint_mode_rows('A',.3,A))==4
    assert len(g.support_rows('A',.3,A))==6
    print('HTS60 SELFTEST PASS')
if __name__=='__main__':main()
