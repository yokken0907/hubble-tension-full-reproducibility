#!/usr/bin/env python3
import numpy as np
import hts64_metric as g

def main():
    rng=np.random.default_rng(64)
    n=14000
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
    s,grid,coords=g.directed_rotation_audit('E','TEST','boundary',.3,'A','B',A,B,'FORWARD')
    assert len(grid)==49
    assert len(coords)==196
    assert s['max_total_distance_invariance_error']<1e-10
    assert s['max_block_share_invariance_error']<1e-10
    assert s['rotation_grid_unique_top_coordinate_count']>=1
    assert np.isfinite(s['physical_amplitude_top_shapley_share'])
    print('HTS64 SELFTEST PASS')

if __name__=='__main__':
    main()
