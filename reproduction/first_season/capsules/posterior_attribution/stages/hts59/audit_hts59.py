#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
import hts59_common as c
import hts59_metric as g

def read(p):
    with Path(p).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f,delimiter='\t'))
def ff(x):return float(x)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-dir',required=True);ap.add_argument('--root-json',required=True);a=ap.parse_args()
    out=Path(a.output_dir); roots=json.loads(Path(a.root_json).read_text())
    saved={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain'])):r for r in read(out/'HTS59_DIRECTED_6D_DECOMPOSITION.tsv')}
    savedloo={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain']),r['omission_side'],r['omitted_chain']):r for r in read(out/'HTS59_DIRECTED_LOO_STABILITY.tsv')}
    checks=[]; maxerr=0.0; maxclose=0.0; details={}
    for burn in (0.3,0.5):
        for label,rec in roots.items():
            d,w,ids,h,cols,files=c.load_factor_root(Path(rec['path']),int(rec['count']),burn)
            details[(label,burn)]=g.endpoint_detail(d,w,ids)
    for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
        for burn in (0.3,0.5):
            A=details[(frm,burn)];B=details[(to,burn)]
            for direction,sl,tl,S,T in (('FORWARD',frm,to,A,B),('REVERSE',to,frm,B,A)):
                m=g.directed_metric(edge,etype,boundary,burn,sl,tl,S,T,direction); q=saved[(edge,direction,burn)]
                for k in ('full6d_mahalanobis','tn2d_mahalanobis','conditional4d_mahalanobis','conditional_fraction_full_distance_squared','decomposition_closure_error','source_correlation_condition_number'):
                    maxerr=max(maxerr,abs(float(m[k])-ff(q[k])))
                maxclose=max(maxclose,abs(float(m['decomposition_closure_error'])))
                for side,D in (('SOURCE',S),('TARGET',T)):
                    for ch in sorted(set(D['ids'])):
                        sub=g.subset_detail(D,D['ids']!=ch);SS=sub if side=='SOURCE' else S;TT=sub if side=='TARGET' else T
                        mm=g.directed_metric(edge,etype,boundary,burn,sl,tl,SS,TT,direction)
                        qq=savedloo[(edge,direction,burn,side,ch)]
                        vals={'full6d_mahalanobis_drift':mm['full6d_mahalanobis']-m['full6d_mahalanobis'],
                              'tn2d_mahalanobis_drift':mm['tn2d_mahalanobis']-m['tn2d_mahalanobis'],
                              'conditional4d_mahalanobis_drift':mm['conditional4d_mahalanobis']-m['conditional4d_mahalanobis'],
                              'conditional_fraction_drift':mm['conditional_fraction_full_distance_squared']-m['conditional_fraction_full_distance_squared']}
                        for k,v in vals.items():maxerr=max(maxerr,abs(v-ff(qq[k])))
    checks.append({'check':'raw_chain_6d_and_LOO_reconstruction_max_error','observed':maxerr,'required':'<=1e-9','result':'PASS' if maxerr<=1e-9 else 'FAIL'})
    checks.append({'check':'schur_decomposition_closure_max_error','observed':maxclose,'required':'<=1e-8','result':'PASS' if maxclose<=1e-8 else 'FAIL'})
    sup=read(out/'HTS59_CHAIN_SUPPORT.tsv')
    for burn in (0.3,0.5):
        for label in roots:
            s=sum(ff(r['weight_share']) for r in sup if r['contract']==label and ff(r['burn_fraction_per_chain'])==burn)
            checks.append({'check':f'{label}_{burn}_weight_share_sum','observed':s,'required':'1 within 1e-10','result':'PASS' if abs(s-1)<=1e-10 else 'FAIL'})
    with (out/'HTS59_INDEPENDENT_AUDIT_CHECKS.tsv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['check','observed','required','result'],delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(checks)
    ok=all(r['result']=='PASS' for r in checks)
    (out/'HTS59_INDEPENDENT_AUDIT_RESULT.md').write_text('# HTS59 independent audit result\n\n`'+('PASS' if ok else 'FAIL')+'`\n')
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
