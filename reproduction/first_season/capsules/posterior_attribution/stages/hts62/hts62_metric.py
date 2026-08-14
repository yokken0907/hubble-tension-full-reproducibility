#!/usr/bin/env python3
from __future__ import annotations
import math
import numpy as np
VARS=('tangent_DESI_sigma','normal_DESI_sigma','omega_b','tau','n_s','logA')
AUX=VARS[2:]
BLOCKS={'BARYON_TILT':(0,2),'TAU_AMPLITUDE':(1,3)}
def wmean_matrix(X,w): return np.sum(X*w[:,None],axis=0)/float(np.sum(w))
def wcov_matrix(X,w):
 sw=float(np.sum(w));m=wmean_matrix(X,w);Z=X-m;C=(Z*w[:,None]).T@Z/sw;return m,(C+C.T)/2
def kish(w): return float(np.sum(w)**2/np.sum(w*w))
def invsqrt_spd(M):
 vals,vecs=np.linalg.eigh((M+M.T)/2)
 if vals[0]<=0 or not np.all(np.isfinite(vals)): raise RuntimeError(f'non-positive block eigenvalue: {vals}')
 return (vecs*(1/np.sqrt(vals)))@vecs.T,vals
def endpoint_detail(d,w,ids):
 X=np.column_stack([np.asarray(d[k],float) for k in VARS]);w=np.asarray(w,float);ids=np.asarray(ids,object);m,C=wcov_matrix(X,w);sd=np.sqrt(np.diag(C))
 if np.any(~np.isfinite(sd)) or np.any(sd<=0): raise RuntimeError('non-positive endpoint scale')
 R=C/np.outer(sd,sd);R=(R+R.T)/2;vals=np.linalg.eigvalsh(R)
 if vals[0]<=0 or not np.all(np.isfinite(vals)): raise RuntimeError(f'non-positive 6D correlation eigenvalue: {vals}')
 return {'X':X,'w':w,'ids':ids,'mean':m,'cov':C,'sd':sd,'corr':R,'eig':vals,'condition_number':float(vals[-1]/vals[0])}
def subset_detail(D,mask):
 X=D['X'][mask];w=D['w'][mask];ids=D['ids'][mask];return endpoint_detail({k:X[:,i] for i,k in enumerate(VARS)},w,ids)
def conditional_system(C):
 sd=np.sqrt(np.diag(C));R=C/np.outer(sd,sd);R=(R+R.T)/2;Rtt=R[:2,:2];Rto=R[:2,2:];Rot=R[2:,:2];Roo=R[2:,2:]
 S=Roo-Rot@np.linalg.inv(Rtt)@Rto;S=(S+S.T)/2;csd=np.sqrt(np.diag(S))
 if np.any(csd<=0): raise RuntimeError('non-positive conditional scale')
 T=S/np.outer(csd,csd);T=(T+T.T)/2;vals=np.linalg.eigvalsh(T)
 if vals[0]<=0 or not np.all(np.isfinite(vals)): raise RuntimeError(f'non-positive conditional correlation eigenvalue: {vals}')
 b=np.array(BLOCKS['BARYON_TILT']);a=np.array(BLOCKS['TAU_AMPLITUDE']);Tbb=T[np.ix_(b,b)];Taa=T[np.ix_(a,a)];Tba=T[np.ix_(b,a)];iB,eB=invsqrt_spd(Tbb);iA,eA=invsqrt_spd(Taa);canon=np.linalg.svd(iB@Tba@iA,compute_uv=False)
 return {'R':R,'Rtt':Rtt,'Rot':Rot,'S':S,'csd':csd,'T':T,'eigvals':vals,'condition_number':float(vals[-1]/vals[0]),'block_b_eig':eB,'block_a_eig':eA,'canonical_correlations':canon}
def endpoint_block_coupling(label,burn,D):
 Q=conditional_system(D['cov']);cc=Q['canonical_correlations'];return {'contract':label,'burn_fraction_per_chain':burn,'max_block_canonical_correlation':float(cc[0]),'min_block_canonical_correlation':float(cc[-1]),'conditional_correlation_min_eigenvalue':float(Q['eigvals'][0]),'conditional_correlation_condition_number':Q['condition_number'],'baryon_tilt_block_condition_number':float(Q['block_b_eig'][-1]/Q['block_b_eig'][0]),'tau_amplitude_block_condition_number':float(Q['block_a_eig'][-1]/Q['block_a_eig'][0])}
def support_rows(label,burn,D):
 out=[];sw=float(np.sum(D['w']))
 for ch in sorted(set(D['ids'])):
  m=D['ids']==ch;ww=D['w'][m];out.append({'contract':label,'burn_fraction_per_chain':burn,'chain_file':ch,'row_count':int(np.sum(m)),'weight_sum':float(np.sum(ww)),'weight_share':float(np.sum(ww)/sw),'kish_effective_rows':kish(ww)})
 return out
def subset_value(T,z,idx):
 idx=np.asarray(idx,int);M=T[np.ix_(idx,idx)];q=z[idx];return float(q@np.linalg.inv(M)@q)
def classify(sh_b,sh_a,total,order_sens):
 if total<=0:return 'ZERO_DISTANCE'
 tol=1e-10*max(1,total)
 if sh_b<-tol or sh_a<-tol or sh_b>total+tol or sh_a>total+tol:return 'SUPPRESSION_OR_NEGATIVE_SHAPLEY'
 if order_sens>0.25:return 'ORDER_SENSITIVE'
 diff=(sh_b-sh_a)/total
 if abs(diff)<0.20:return 'MIXED_BLOCK'
 return 'BARYON_TILT_DOMINANT' if diff>0 else 'TAU_AMPLITUDE_DOMINANT'
def directed_block_decomposition(edge,etype,boundary,burn,source_label,target_label,A,B,direction):
 delta=B['mean']-A['mean'];dz=delta/A['sd'];Q=conditional_system(A['cov']);resid=dz[2:]-Q['Rot']@np.linalg.inv(Q['Rtt'])@dz[:2];z=resid/Q['csd'];T=Q['T'];b=BLOCKS['BARYON_TILT'];a=BLOCKS['TAU_AMPLITUDE'];total=float(z@np.linalg.inv(T)@z);bm=subset_value(T,z,b);am=subset_value(T,z,a);agivenb=total-bm;bgivena=total-am;shb=.5*(bm+bgivena);sha=.5*(am+agivenb);interaction=total-bm-am;closure=shb+sha-total
 if total>0:sb=shb/total;sa=sha/total;order=abs(interaction)/total
 else:sb=sa=order=0.0
 return {'edge':edge,'direction':direction,'edge_type':etype,'interpretation_boundary':boundary,'burn_fraction_per_chain':burn,'source_contract':source_label,'target_contract':target_label,'conditional4d_distance_squared':total,'conditional4d_mahalanobis':math.sqrt(max(total,0)),'baryon_tilt_marginal_distance_squared':bm,'tau_amplitude_given_baryon_tilt_distance_squared':agivenb,'tau_amplitude_marginal_distance_squared':am,'baryon_tilt_given_tau_amplitude_distance_squared':bgivena,'baryon_tilt_shapley_distance_squared':shb,'tau_amplitude_shapley_distance_squared':sha,'baryon_tilt_shapley_share':sb,'tau_amplitude_shapley_share':sa,'cross_block_interaction_distance_squared':interaction,'order_sensitivity_fraction':order,'shapley_closure_error':closure,'max_block_canonical_correlation':float(Q['canonical_correlations'][0]),'min_block_canonical_correlation':float(Q['canonical_correlations'][-1]),'block_pattern_classification':classify(shb,sha,total,order),'conditional_residual_omega_b':float(z[0]),'conditional_residual_tau':float(z[1]),'conditional_residual_n_s':float(z[2]),'conditional_residual_logA':float(z[3])}
