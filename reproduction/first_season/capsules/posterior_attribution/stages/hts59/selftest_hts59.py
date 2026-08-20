#!/usr/bin/env python3
import numpy as np
import hts59_metric as g

def main():
    rng=np.random.default_rng(59); n=12000
    M=np.array([[1,0,0,0,0,0],[.4,1,0,0,0,0],[.2,.1,1,0,0,0],[.1,.2,.3,1,0,0],[.2,-.1,.1,.2,1,0],[-.1,.2,.2,.4,.1,1]],float)
    X=rng.normal(size=(n,6))@M.T; w=np.exp(rng.normal(0,.15,n)); ids=np.array([f'CLASS.{i%6+1}.txt' for i in range(n)],object)
    A=g.endpoint_detail({k:X[:,i] for i,k in enumerate(g.VARS)},w,ids)
    Y=X+np.array([.5,-.2,.15,.3,-.1,.25]); B=g.endpoint_detail({k:Y[:,i] for i,k in enumerate(g.VARS)},w,ids)
    r=g.directed_metric('E','TEST','boundary',.3,'A','B',A,B,'FORWARD')
    assert abs(r['full6d_distance_squared']-r['tn2d_distance_squared']-r['conditional4d_distance_squared'])<1e-10
    assert -1e-10<=r['conditional_fraction_full_distance_squared']<=1+1e-10
    assert len(g.support_rows('A',.3,A))==6
    print('HTS59 SELFTEST PASS')
if __name__=='__main__':main()
