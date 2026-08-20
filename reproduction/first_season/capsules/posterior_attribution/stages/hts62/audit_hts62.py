#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
import hts62_common as c
import hts62_metric as g
def read(p):
 with Path(p).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f,delimiter='\t'))
def ff(x):return float(x)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output-dir',required=True);ap.add_argument('--root-json',required=True);a=ap.parse_args();out=Path(a.output_dir);roots=json.loads(Path(a.root_json).read_text())
 saved={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain'])):r for r in read(out/'HTS62_DIRECTED_FIXED_BLOCK_DECOMPOSITION.tsv')};savedloo={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain']),r['omission_side'],r['omitted_chain']):r for r in read(out/'HTS62_DIRECTED_LOO_STABILITY.tsv')};details={};maxerr=0.;maxclose=0.
 for burn in (.3,.5):
  for label,rec in roots.items():
   d,w,ids,h,cols,files=c.load_factor_root(Path(rec['path']),int(rec['count']),burn);details[(label,burn)]=g.endpoint_detail(d,w,ids)
 for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
  for burn in (.3,.5):
   A=details[(frm,burn)];B=details[(to,burn)]
   for direction,sl,tl,S,T in (('FORWARD',frm,to,A,B),('REVERSE',to,frm,B,A)):
    q=g.directed_block_decomposition(edge,etype,boundary,burn,sl,tl,S,T,direction);s=saved[(edge,direction,burn)]
    for k in ('conditional4d_distance_squared','baryon_tilt_marginal_distance_squared','tau_amplitude_given_baryon_tilt_distance_squared','tau_amplitude_marginal_distance_squared','baryon_tilt_given_tau_amplitude_distance_squared','baryon_tilt_shapley_distance_squared','tau_amplitude_shapley_distance_squared','baryon_tilt_shapley_share','tau_amplitude_shapley_share','cross_block_interaction_distance_squared','order_sensitivity_fraction','shapley_closure_error','max_block_canonical_correlation'):
     maxerr=max(maxerr,abs(float(q[k])-ff(s[k])))
    maxclose=max(maxclose,abs(q['shapley_closure_error']))
    for side,D in (('SOURCE',S),('TARGET',T)):
     for ch in sorted(set(D['ids'])):
      sub=g.subset_detail(D,D['ids']!=ch);SS=sub if side=='SOURCE' else S;TT=sub if side=='TARGET' else T;qq=g.directed_block_decomposition(edge,etype,boundary,burn,sl,tl,SS,TT,direction);z=savedloo[(edge,direction,burn,side,ch)]
      vals={'conditional4d_mahalanobis_drift':qq['conditional4d_mahalanobis']-q['conditional4d_mahalanobis'],'baryon_tilt_shapley_share_drift':qq['baryon_tilt_shapley_share']-q['baryon_tilt_shapley_share'],'tau_amplitude_shapley_share_drift':qq['tau_amplitude_shapley_share']-q['tau_amplitude_shapley_share'],'order_sensitivity_fraction_drift':qq['order_sensitivity_fraction']-q['order_sensitivity_fraction'],'max_block_canonical_correlation_drift':qq['max_block_canonical_correlation']-q['max_block_canonical_correlation']}
      for k,v in vals.items():maxerr=max(maxerr,abs(v-ff(z[k])))
 checks=[{'check':'raw_chain_block_and_LOO_reconstruction_max_error','observed':maxerr,'required':'<=1e-9','result':'PASS' if maxerr<=1e-9 else 'FAIL'},{'check':'shapley_closure_max_error','observed':maxclose,'required':'<=1e-8','result':'PASS' if maxclose<=1e-8 else 'FAIL'}]
 sup=read(out/'HTS62_CHAIN_SUPPORT.tsv')
 for burn in (.3,.5):
  for label in roots:
   s=sum(ff(r['weight_share']) for r in sup if r['contract']==label and ff(r['burn_fraction_per_chain'])==burn);checks.append({'check':f'{label}_{burn}_weight_share_sum','observed':s,'required':'1 within 1e-10','result':'PASS' if abs(s-1)<=1e-10 else 'FAIL'})
 with (out/'HTS62_INDEPENDENT_AUDIT_CHECKS.tsv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['check','observed','required','result'],delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(checks)
 ok=all(r['result']=='PASS' for r in checks);(out/'HTS62_INDEPENDENT_AUDIT_RESULT.md').write_text('# HTS62 independent audit result\n\n`'+('PASS' if ok else 'FAIL')+'`\n');return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
