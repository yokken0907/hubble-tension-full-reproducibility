#!/usr/bin/env python3
import numpy as np
import hts62_metric as g
def main():
 rng=np.random.default_rng(62);n=16000
 M=np.array([[1,0,0,0,0,0],[.25,1,0,0,0,0],[.1,.1,1,0,0,0],[.1,.2,.15,1,0,0],[.2,-.1,.45,.1,1,0],[-.1,.2,.05,.55,.1,1]],float)
 X=rng.normal(size=(n,6))@M.T;w=np.exp(rng.normal(0,.1,n));ids=np.array([f'CLASS.{i%6+1}.txt' for i in range(n)],object)
 A=g.endpoint_detail({k:X[:,i] for i,k in enumerate(g.VARS)},w,ids);Y=X+np.array([.2,-.1,.25,.15,-.35,.2]);B=g.endpoint_detail({k:Y[:,i] for i,k in enumerate(g.VARS)},w,ids)
 q=g.directed_block_decomposition('E','TEST','boundary',.3,'A','B',A,B,'FORWARD')
 assert abs(q['baryon_tilt_shapley_distance_squared']+q['tau_amplitude_shapley_distance_squared']-q['conditional4d_distance_squared'])<1e-10
 assert abs(q['baryon_tilt_shapley_share']+q['tau_amplitude_shapley_share']-1)<1e-10
 assert 0<=q['max_block_canonical_correlation']<1
 assert len(g.support_rows('A',.3,A))==6
 print('HTS62 SELFTEST PASS')
if __name__=='__main__':main()
