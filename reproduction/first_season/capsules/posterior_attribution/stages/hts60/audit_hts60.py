#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
import hts60_common as c
import hts60_metric as g

def read(p):
    with Path(p).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f,delimiter='\t'))
def ff(x):return float(x)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-dir',required=True);ap.add_argument('--root-json',required=True);a=ap.parse_args()
    out=Path(a.output_dir); roots=json.loads(Path(a.root_json).read_text())
    saved={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain'])):r for r in read(out/'HTS60_DIRECTED_MODE_SUMMARY.tsv')}
    savedm={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain']),int(r['contribution_rank'])):r for r in read(out/'HTS60_DIRECTED_MODE_CONTRIBUTIONS.tsv')}
    savedloo={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain']),r['omission_side'],r['omitted_chain']):r for r in read(out/'HTS60_DIRECTED_LOO_STABILITY.tsv')}
    checks=[]; maxerr=0.0; maxclose=0.0; details={}
    for burn in (0.3,0.5):
        for label,rec in roots.items():
            d,w,ids,h,cols,files=c.load_factor_root(Path(rec['path']),int(rec['count']),burn)
            details[(label,burn)]=g.endpoint_detail(d,w,ids)
    for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
        for burn in (0.3,0.5):
            A=details[(frm,burn)];B=details[(to,burn)]
            for direction,sl,tl,S,T in (('FORWARD',frm,to,A,B),('REVERSE',to,frm,B,A)):
                s,m=g.directed_modes(edge,etype,boundary,burn,sl,tl,S,T,direction)
                q=saved[(edge,direction,burn)]
                for k in ('conditional4d_mahalanobis','top1_mode_fraction','top2_mode_fraction',
                          'effective_contributing_mode_count','conditional_mode_condition_number',
                          'mode_decomposition_closure_error'):
                    maxerr=max(maxerr,abs(float(s[k])-ff(q[k])))
                maxclose=max(maxclose,abs(float(s['mode_decomposition_closure_error'])))
                for r in m:
                    qq=savedm[(edge,direction,burn,int(r['contribution_rank']))]
                    for k in ('conditional_correlation_eigenvalue','signed_mahalanobis_mode_amplitude',
                              'mode_distance_squared_contribution','mode_fraction_conditional_distance_squared',
                              'loading_omega_b','loading_tau','loading_n_s','loading_logA'):
                        maxerr=max(maxerr,abs(float(r[k])-ff(qq[k])))
                for side,D in (('SOURCE',S),('TARGET',T)):
                    for ch in sorted(set(D['ids'])):
                        sub=g.subset_detail(D,D['ids']!=ch)
                        SS=sub if side=='SOURCE' else S; TT=sub if side=='TARGET' else T
                        ss,_=g.directed_modes(edge,etype,boundary,burn,sl,tl,SS,TT,direction)
                        qq=savedloo[(edge,direction,burn,side,ch)]
                        vals={
                            'conditional4d_mahalanobis_drift':ss['conditional4d_mahalanobis']-s['conditional4d_mahalanobis'],
                            'top1_mode_fraction_drift':ss['top1_mode_fraction']-s['top1_mode_fraction'],
                            'top2_mode_fraction_drift':ss['top2_mode_fraction']-s['top2_mode_fraction'],
                            'effective_mode_count_drift':ss['effective_contributing_mode_count']-s['effective_contributing_mode_count'],
                        }
                        for k,v in vals.items():maxerr=max(maxerr,abs(v-ff(qq[k])))
    checks.append({'check':'raw_chain_mode_and_LOO_reconstruction_max_error','observed':maxerr,'required':'<=1e-9','result':'PASS' if maxerr<=1e-9 else 'FAIL'})
    checks.append({'check':'mode_decomposition_closure_max_error','observed':maxclose,'required':'<=1e-8','result':'PASS' if maxclose<=1e-8 else 'FAIL'})
    sup=read(out/'HTS60_CHAIN_SUPPORT.tsv')
    for burn in (0.3,0.5):
        for label in roots:
            s=sum(ff(r['weight_share']) for r in sup if r['contract']==label and ff(r['burn_fraction_per_chain'])==burn)
            checks.append({'check':f'{label}_{burn}_weight_share_sum','observed':s,'required':'1 within 1e-10','result':'PASS' if abs(s-1)<=1e-10 else 'FAIL'})
    with (out/'HTS60_INDEPENDENT_AUDIT_CHECKS.tsv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['check','observed','required','result'],delimiter='\t',lineterminator='\n')
        w.writeheader();w.writerows(checks)
    ok=all(r['result']=='PASS' for r in checks)
    (out/'HTS60_INDEPENDENT_AUDIT_RESULT.md').write_text('# HTS60 independent audit result\n\n`'+('PASS' if ok else 'FAIL')+'`\n')
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
