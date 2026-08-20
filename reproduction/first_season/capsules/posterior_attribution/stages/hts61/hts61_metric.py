#!/usr/bin/env python3
from __future__ import annotations
import itertools, math
import numpy as np

VARS=('tangent_DESI_sigma','normal_DESI_sigma','omega_b','tau','n_s','logA')
AUX=VARS[2:]
BLOCKS={'BARYON_TILT':(0,2),'TAU_AMPLITUDE':(1,3)}
GAP_THRESHOLD=0.12

def wmean_matrix(X,w): return np.sum(X*w[:,None],axis=0)/float(np.sum(w))
def wcov_matrix(X,w):
 sw=float(np.sum(w));m=wmean_matrix(X,w);Z=X-m;C=(Z*w[:,None]).T@Z/sw
 return m,(C+C.T)/2
def kish(w): return float(np.sum(w)**2/np.sum(w*w))

def endpoint_detail(d,w,ids):
 X=np.column_stack([np.asarray(d[k],float) for k in VARS]);w=np.asarray(w,float);ids=np.asarray(ids,object)
 m,C=wcov_matrix(X,w);sd=np.sqrt(np.diag(C))
 if np.any(~np.isfinite(sd)) or np.any(sd<=0): raise RuntimeError('non-positive endpoint scale')
 R=C/np.outer(sd,sd);R=(R+R.T)/2;vals=np.linalg.eigvalsh(R)
 if vals[0]<=0 or not np.all(np.isfinite(vals)): raise RuntimeError(f'non-positive 6D correlation eigenvalue: {vals}')
 B=conditional_basis(C)
 return {'X':X,'w':w,'ids':ids,'mean':m,'cov':C,'sd':sd,'corr':R,'eig':vals,
         'condition_number':float(vals[-1]/vals[0]),'basis':B}

def subset_detail(D,mask):
 X=D['X'][mask];w=D['w'][mask];ids=D['ids'][mask]
 return endpoint_detail({k:X[:,i] for i,k in enumerate(VARS)},w,ids)

def conditional_basis(C):
 sd=np.sqrt(np.diag(C));R=C/np.outer(sd,sd);R=(R+R.T)/2
 Rtt=R[:2,:2];Rto=R[:2,2:];Rot=R[2:,:2];Roo=R[2:,2:]
 S=Roo-Rot@np.linalg.inv(Rtt)@Rto;S=(S+S.T)/2;csd=np.sqrt(np.diag(S))
 if np.any(csd<=0): raise RuntimeError('non-positive conditional scale')
 T=S/np.outer(csd,csd);T=(T+T.T)/2;vals,vecs=np.linalg.eigh(T)
 if vals[0]<=0 or not np.all(np.isfinite(vals)): raise RuntimeError(f'non-positive conditional-correlation eigenvalue: {vals}')
 for j in range(4):
  k=int(np.argmax(np.abs(vecs[:,j])))
  if vecs[k,j]<0: vecs[:,j]*=-1
 return {'R':R,'Rtt':Rtt,'Rot':Rot,'Rto':Rto,'S':S,'csd':csd,'T':T,
         'eigvals':vals,'eigvecs':vecs,'condition_number':float(vals[-1]/vals[0])}

def relative_gaps(vals):
 vals=np.asarray(vals,float)
 return np.array([(vals[i+1]-vals[i])/max(abs(vals[i]),abs(vals[i+1]),1e-15) for i in range(len(vals)-1)])

def clusters(vals,threshold=GAP_THRESHOLD):
 gaps=relative_gaps(vals);out=[];cur=[0]
 for i,gap in enumerate(gaps):
  if gap<threshold: cur.append(i+1)
  else: out.append(tuple(cur));cur=[i+1]
 out.append(tuple(cur));return out,gaps

def mode_nearest_gap(gaps,j):
 xs=[]
 if j>0: xs.append(gaps[j-1])
 if j<len(gaps): xs.append(gaps[j])
 return float(min(xs)) if xs else float('inf')

def subspace_angles_deg(U,V):
 s=np.linalg.svd(np.asarray(U,float).T@np.asarray(V,float),compute_uv=False);s=np.clip(s,0,1)
 return np.degrees(np.arccos(s))

def best_permutation(V0,V1):
 A=np.abs(np.asarray(V0,float).T@np.asarray(V1,float));best=None
 for perm in itertools.permutations(range(A.shape[1])):
  score=sum(A[i,perm[i]] for i in range(A.shape[0]))
  if best is None or score>best[0]: best=(score,perm)
 perm=best[1];dots=np.array([A[i,perm[i]] for i in range(A.shape[0])])
 return perm,dots,np.degrees(np.arccos(np.clip(dots,0,1)))

def block_subspace(V,block_indices):
 V=np.asarray(V,float);P=np.zeros((4,4));P[list(block_indices),list(block_indices)]=1;best=None
 for subset in itertools.combinations(range(4),2):
  U=V[:,subset];score=float(np.trace(U.T@P@U)/2)
  if best is None or score>best[0]: best=(score,subset,U)
 E=np.eye(4)[:,list(block_indices)];ang=subspace_angles_deg(best[2],E)
 return {'score':best[0],'subset':best[1],'U':best[2],'angle_min_deg':float(np.min(ang)),'angle_max_deg':float(np.max(ang))}

def mode_rows(label,burn,D):
 B=D['basis'];vals=B['eigvals'];V=B['eigvecs'];cls,gaps=clusters(vals)
 cid={j:i+1 for i,c in enumerate(cls) for j in c};csize={j:len(c) for c in cls for j in c};rows=[]
 for j in range(4):
  v=V[:,j];bp=float(v[0]**2+v[2]**2);ap=float(v[1]**2+v[3]**2);dom=int(np.argmax(np.abs(v)))
  rows.append({'contract':label,'burn_fraction_per_chain':burn,'mode_index':j+1,
   'conditional_correlation_eigenvalue':float(vals[j]),'left_relative_gap':float(gaps[j-1]) if j>0 else math.nan,
   'right_relative_gap':float(gaps[j]) if j<3 else math.nan,'nearest_relative_gap':mode_nearest_gap(gaps,j),
   'identifiability_cluster_id':cid[j],'identifiability_cluster_size':csize[j],
   'individually_identifiable_by_gap':csize[j]==1,'baryon_tilt_purity':bp,'tau_amplitude_purity':ap,
   'dominant_loading_parameter':AUX[dom],'dominant_abs_loading':float(abs(v[dom])),
   **{f'loading_{AUX[i]}':float(v[i]) for i in range(4)}})
 return rows

def block_rows(label,burn,D):
 V=D['basis']['eigvecs'];out=[]
 for name,idx in BLOCKS.items():
  q=block_subspace(V,idx)
  out.append({'contract':label,'burn_fraction_per_chain':burn,'block':name,
   'selected_modes':','.join(str(i+1) for i in q['subset']),'coordinate_block_overlap_fraction':q['score'],
   'principal_angle_min_deg':q['angle_min_deg'],'principal_angle_max_deg':q['angle_max_deg']})
 return out

def support_rows(label,burn,D):
 out=[];sw=float(np.sum(D['w']))
 for ch in sorted(set(D['ids'])):
  mask=D['ids']==ch;ww=D['w'][mask]
  out.append({'contract':label,'burn_fraction_per_chain':burn,'chain_file':ch,'row_count':int(np.sum(mask)),
   'weight_sum':float(np.sum(ww)),'weight_share':float(np.sum(ww)/sw),'kish_effective_rows':kish(ww)})
 return out

def perturbation_rows(label,burn,perturbation,base,pert):
 B0=base['basis'];B1=pert['basis'];V0=B0['eigvecs'];V1=B1['eigvecs'];perm,dots,angles=best_permutation(V0,V1);cls,_=clusters(B0['eigvals'])
 mode=[];cluster=[];block=[];cinfo={j:(ci+1,c) for ci,c in enumerate(cls) for j in c}
 for j in range(4):
  ci,c=cinfo[j]
  mode.append({'contract':label,'burn_fraction_per_chain':burn,'perturbation':perturbation,
   'baseline_mode_index':j+1,'matched_perturbed_mode_index':perm[j]+1,'baseline_cluster_id':ci,'baseline_cluster_size':len(c),
   'matched_abs_dot':float(dots[j]),'matched_angle_deg':float(angles[j]),'baseline_eigenvalue':float(B0['eigvals'][j]),
   'perturbed_eigenvalue':float(B1['eigvals'][perm[j]]),'relative_eigenvalue_drift':float(B1['eigvals'][perm[j]]/B0['eigvals'][j]-1)})
 for ci,c in enumerate(cls,1):
  cols=[perm[j] for j in c];ang=subspace_angles_deg(V0[:,c],V1[:,cols])
  cluster.append({'contract':label,'burn_fraction_per_chain':burn,'perturbation':perturbation,'baseline_cluster_id':ci,
   'baseline_cluster_members':','.join(str(j+1) for j in c),'cluster_size':len(c),
   'principal_angle_min_deg':float(np.min(ang)),'principal_angle_max_deg':float(np.max(ang))})
 for name,idx in BLOCKS.items():
  q0=block_subspace(V0,idx);q1=block_subspace(V1,idx);ang=subspace_angles_deg(q0['U'],q1['U'])
  block.append({'contract':label,'burn_fraction_per_chain':burn,'perturbation':perturbation,'block':name,
   'baseline_selected_modes':','.join(str(i+1) for i in q0['subset']),'perturbed_selected_modes':','.join(str(i+1) for i in q1['subset']),
   'principal_angle_min_deg':float(np.min(ang)),'principal_angle_max_deg':float(np.max(ang)),
   'block_overlap_fraction_drift':float(q1['score']-q0['score'])})
 return mode,cluster,block

def directed_contribution(edge,etype,boundary,burn,source_label,target_label,A,B,direction):
 delta=B['mean']-A['mean'];sd=A['sd'];dz=delta/sd;Q=A['basis']
 resid=dz[2:]-Q['Rot']@np.linalg.inv(Q['Rtt'])@dz[:2];zc=resid/Q['csd'];vals=Q['eigvals'];V=Q['eigvecs']
 amp=V.T@zc/np.sqrt(vals);contrib=amp*amp;d2=float(np.sum(contrib));frac=contrib/d2 if d2>0 else np.zeros(4)
 top=int(np.argmax(contrib));cls,gaps=clusters(vals);cluster=next(c for c in cls if top in c)
 return {'edge':edge,'direction':direction,'edge_type':etype,'interpretation_boundary':boundary,
  'burn_fraction_per_chain':burn,'source_contract':source_label,'target_contract':target_label,
  'conditional4d_mahalanobis':math.sqrt(max(d2,0)),'top_mode_index':top+1,'top_mode_fraction':float(frac[top]),
  'top_mode_nearest_relative_gap':mode_nearest_gap(gaps,top),'top_mode_individually_identifiable':len(cluster)==1,
  'top_mode_cluster_members':','.join(str(j+1) for j in cluster),'top_mode_cluster_fraction':float(np.sum(frac[list(cluster)])) if d2>0 else 0,
  'top_mode_dominant_parameter':AUX[int(np.argmax(np.abs(V[:,top])))],
  'top_mode_baryon_tilt_purity':float(V[0,top]**2+V[2,top]**2),'top_mode_tau_amplitude_purity':float(V[1,top]**2+V[3,top]**2)}
