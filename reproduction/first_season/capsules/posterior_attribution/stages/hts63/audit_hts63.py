#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
import hts63_common as c
import hts63_metric as g

def read(p):
    with Path(p).open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f,delimiter='\t'))
def ff(x): return float(x)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output-dir',required=True)
    ap.add_argument('--root-json',required=True)
    a=ap.parse_args()
    out=Path(a.output_dir); roots=json.loads(Path(a.root_json).read_text())
    saved={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain'])):r
           for r in read(out/'HTS63_DIRECTED_VARIABLE_ALLOCATION_SUMMARY.tsv')}
    savedv={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain']),r['variable']):r
            for r in read(out/'HTS63_DIRECTED_VARIABLE_ALLOCATIONS.tsv')}
    savedloo={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain']),
              r['omission_side'],r['omitted_chain']):r
              for r in read(out/'HTS63_DIRECTED_LOO_STABILITY.tsv')}
    details={}; checks=[]; maxerr=0.0; maxclose=0.0; minmarg=1e300
    for burn in (0.3,0.5):
        for label,rec in roots.items():
            d,w,ids,h,cols,files=c.load_factor_root(Path(rec['path']),int(rec['count']),burn)
            details[(label,burn)]=g.endpoint_detail(d,w,ids)
    for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
        for burn in (0.3,0.5):
            A=details[(frm,burn)]; B=details[(to,burn)]
            for direction,sl,tl,S,T in (('FORWARD',frm,to,A,B),('REVERSE',to,frm,B,A)):
                s,v=g.directed_variable_allocation(edge,etype,boundary,burn,sl,tl,S,T,direction)
                q=saved[(edge,direction,burn)]
                for k in ('conditional4d_mahalanobis','top_shapley_share','top_owen_share',
                          'effective_variable_count_shapley','effective_variable_count_owen',
                          'max_abs_owen_minus_shapley_share','max_order_range_fraction',
                          'shapley_closure_error','owen_closure_error',
                          'baryon_tilt_block_reconciliation_error','tau_amplitude_block_reconciliation_error'):
                    maxerr=max(maxerr,abs(float(s[k])-ff(q[k])))
                maxclose=max(maxclose,abs(s['shapley_closure_error']),abs(s['owen_closure_error']),
                             abs(s['baryon_tilt_block_reconciliation_error']),
                             abs(s['tau_amplitude_block_reconciliation_error']))
                minmarg=min(minmarg,s['minimum_permutation_marginal_contribution'])
                for r in v:
                    qq=savedv[(edge,direction,burn,r['variable'])]
                    for k in ('unrestricted_shapley_distance_squared','unrestricted_shapley_share',
                              'owen_distance_squared','owen_share','owen_minus_shapley_share',
                              'all_order_marginal_mean','all_order_marginal_std',
                              'all_order_marginal_min','all_order_marginal_max',
                              'all_order_range_fraction'):
                        maxerr=max(maxerr,abs(float(r[k])-ff(qq[k])))
                base_s=g.vector_from_rows(v,'unrestricted_shapley_share')
                base_o=g.vector_from_rows(v,'owen_share')
                for side,D in (('SOURCE',S),('TARGET',T)):
                    for ch in sorted(set(D['ids'])):
                        sub=g.subset_detail(D,D['ids']!=ch)
                        SS=sub if side=='SOURCE' else S
                        TT=sub if side=='TARGET' else T
                        ss,vv=g.directed_variable_allocation(edge,etype,boundary,burn,sl,tl,SS,TT,direction)
                        qs=g.vector_from_rows(vv,'unrestricted_shapley_share')
                        qo=g.vector_from_rows(vv,'owen_share')
                        qq=savedloo[(edge,direction,burn,side,ch)]
                        vals={
                            'conditional4d_mahalanobis_drift':ss['conditional4d_mahalanobis']-s['conditional4d_mahalanobis'],
                            'max_unrestricted_shapley_share_drift':float(max(abs(qs-base_s))),
                            'max_owen_share_drift':float(max(abs(qo-base_o))),
                            'effective_variable_count_shapley_drift':ss['effective_variable_count_shapley']-s['effective_variable_count_shapley'],
                            'effective_variable_count_owen_drift':ss['effective_variable_count_owen']-s['effective_variable_count_owen'],
                            'max_abs_coalition_shift_drift':ss['max_abs_owen_minus_shapley_share']-s['max_abs_owen_minus_shapley_share'],
                        }
                        for k,val in vals.items():
                            maxerr=max(maxerr,abs(val-ff(qq[k])))
    checks.append({'check':'raw_chain_variable_allocation_and_LOO_reconstruction_max_error',
                   'observed':maxerr,'required':'<=1e-9',
                   'result':'PASS' if maxerr<=1e-9 else 'FAIL'})
    checks.append({'check':'allocation_closure_and_block_reconciliation_max_error',
                   'observed':maxclose,'required':'<=1e-8',
                   'result':'PASS' if maxclose<=1e-8 else 'FAIL'})
    checks.append({'check':'minimum_permutation_marginal_contribution',
                   'observed':minmarg,'required':'>=-1e-8',
                   'result':'PASS' if minmarg>=-1e-8 else 'FAIL'})
    sup=read(out/'HTS63_CHAIN_SUPPORT.tsv')
    for burn in (0.3,0.5):
        for label in roots:
            s=sum(ff(r['weight_share']) for r in sup
                  if r['contract']==label and ff(r['burn_fraction_per_chain'])==burn)
            checks.append({'check':f'{label}_{burn}_weight_share_sum',
                           'observed':s,'required':'1 within 1e-10',
                           'result':'PASS' if abs(s-1)<=1e-10 else 'FAIL'})
    with (out/'HTS63_INDEPENDENT_AUDIT_CHECKS.tsv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['check','observed','required','result'],
                         delimiter='\t',lineterminator='\n')
        w.writeheader(); w.writerows(checks)
    ok=all(r['result']=='PASS' for r in checks)
    (out/'HTS63_INDEPENDENT_AUDIT_RESULT.md').write_text(
        '# HTS63 independent audit result\n\n`'+('PASS' if ok else 'FAIL')+'`\n')
    return 0 if ok else 1

if __name__=='__main__':
    sys.exit(main())
