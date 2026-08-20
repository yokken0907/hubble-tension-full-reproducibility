#!/usr/bin/env python3
import numpy as np
import hts61_metric as g
def make(seed=61):
 rng=np.random.default_rng(seed);n=16000;T=np.array([[1,.02,.18,.03],[.02,1,.01,.78],[.18,.01,1,.02],[.03,.78,.02,1]],float);L=np.linalg.cholesky(T);aux=rng.normal(size=(n,4))@L.T;tn=rng.normal(size=(n,2));X=np.column_stack([tn,aux]);w=np.exp(rng.normal(0,.1,n));ids=np.array([f'CLASS.{i%6+1}.txt' for i in range(n)],object);return g.endpoint_detail({k:X[:,i] for i,k in enumerate(g.VARS)},w,ids)
def main():
 A=make();B=make(62);assert len(g.mode_rows('A',.3,A))==4 and len(g.block_rows('A',.3,A))==2;a,c,b=g.perturbation_rows('A',.3,'TEST',A,B);assert len(a)==4 and len(b)==2;e=g.directed_contribution('E','TEST','boundary',.3,'A','B',A,B,'FORWARD');assert 0<=e['top_mode_cluster_fraction']<=1;V=A['basis']['eigvecs'].copy();th=np.radians(35);R=np.array([[np.cos(th),-np.sin(th)],[np.sin(th),np.cos(th)]]);V2=V.copy();V2[:,1:3]=V[:,1:3]@R;assert max(g.subspace_angles_deg(V[:,1:3],V2[:,1:3]))<1e-6;perm,dots,angles=g.best_permutation(V,V2);assert len(perm)==4;print('HTS61 SELFTEST PASS')
if __name__=='__main__':main()
