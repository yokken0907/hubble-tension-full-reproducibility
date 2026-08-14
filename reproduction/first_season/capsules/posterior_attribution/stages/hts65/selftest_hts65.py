#!/usr/bin/env python3
import numpy as np
import hts65_metric as g

def main():
    assert len(g.PARTITIONS)==15
    assert g.CANONICAL_PARTITION in g.PARTITIONS
    rng=np.random.default_rng(65)
    n=15000
    M=np.array([
        [1,0,0,0,0,0],
        [.25,1,0,0,0,0],
        [.15,.1,1,0,0,0],
        [.1,.2,.35,1,0,0],
        [.2,-.1,.25,.2,1,0],
        [-.1,.15,.25,.4,.15,1],
    ],float)
    X=rng.normal(size=(n,6))@M.T
    w=np.exp(rng.normal(0,.12,n))
    ids=np.array([f'CLASS.{i%6+1}.txt' for i in range(n)],object)
    A=g.endpoint_detail({k:X[:,i] for i,k in enumerate(g.VARS)},w,ids)
    Y=X+np.array([.35,-.15,.25,.2,-.4,.15])
    B=g.endpoint_detail({k:Y[:,i] for i,k in enumerate(g.VARS)},w,ids)
    s,p,v,b=g.directed_partition_audit('E','TEST','boundary',.3,'A','B',A,B,'FORWARD')
    assert len(p)==15
    assert len(v)==60
    assert abs(max(r['owen_closure_error'] for r in p))<1e-10
    for pid in {r['partition_id'] for r in b}:
        total=sum(r['block_owen_distance_squared'] for r in b if r['partition_id']==pid)
        assert abs(total-s['conditional4d_distance_squared'])<1e-10
    assert s['partition_unique_top_variable_count']>=1
    print('HTS65 SELFTEST PASS')

if __name__=='__main__':
    main()
