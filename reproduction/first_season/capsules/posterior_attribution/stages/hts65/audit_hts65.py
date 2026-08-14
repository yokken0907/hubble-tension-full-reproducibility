#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
import hts65_common as c
import hts65_metric as g

def read(p):
    with Path(p).open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f,delimiter='\t'))
def ff(x): return float(x)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output-dir',required=True)
    ap.add_argument('--root-json',required=True)
    a=ap.parse_args()
    out=Path(a.output_dir)
    roots=json.loads(Path(a.root_json).read_text())
    saved={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain'])):r
           for r in read(out/'HTS65_DIRECTED_PARTITION_SUMMARY.tsv')}
    savedloo={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain']),
              r['omission_side'],r['omitted_chain']):r
              for r in read(out/'HTS65_DIRECTED_LOO_STABILITY.tsv')}
    details={}
    checks=[]
    maxerr=0.0
    maxclose=0.0
    minmarg=1e300
    for burn in (0.3,0.5):
        for label,rec in roots.items():
            d,w,ids,h,cols,files=c.load_factor_root(Path(rec['path']),int(rec['count']),burn)
            details[(label,burn)]=g.endpoint_detail(d,w,ids)
    for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
        for burn in (0.3,0.5):
            A=details[(frm,burn)]
            B=details[(to,burn)]
            for direction,sl,tl,S,T in (
                ('FORWARD',frm,to,A,B),
                ('REVERSE',to,frm,B,A),
            ):
                s,parts,vars_,blocks=g.directed_partition_audit(edge,etype,boundary,burn,sl,tl,S,T,direction)
                q=saved[(edge,direction,burn)]
                for k in (
                    'conditional4d_mahalanobis','canonical_partition_top_share',
                    'canonical_partition_max_abs_shift_from_shapley',
                    'partition_top_share_min','partition_top_share_max',
                    'partition_top_share_range','partition_effective_count_min',
                    'partition_effective_count_max','partition_effective_count_range',
                    'max_variable_owen_share_range_across_partitions',
                    'max_abs_partition_owen_minus_shapley_share',
                    'max_owen_closure_error','max_partition_block_reconciliation_error',
                ):
                    maxerr=max(maxerr,abs(float(s[k])-ff(q[k])))
                maxclose=max(maxclose,s['max_owen_closure_error'],
                             s['max_partition_block_reconciliation_error'])
                minmarg=min(minmarg,s['minimum_respecting_order_marginal_contribution'])
                for side,D in (('SOURCE',S),('TARGET',T)):
                    for ch in sorted(set(D['ids'])):
                        sub=g.subset_detail(D,D['ids']!=ch)
                        SS=sub if side=='SOURCE' else S
                        TT=sub if side=='TARGET' else T
                        ss,_,_,_=g.directed_partition_audit(edge,etype,boundary,burn,sl,tl,SS,TT,direction)
                        qq=savedloo[(edge,direction,burn,side,ch)]
                        vals={
                            'conditional4d_mahalanobis_drift':ss['conditional4d_mahalanobis']-s['conditional4d_mahalanobis'],
                            'max_variable_share_range_drift':ss['max_variable_owen_share_range_across_partitions']-s['max_variable_owen_share_range_across_partitions'],
                            'partition_effective_count_range_drift':ss['partition_effective_count_range']-s['partition_effective_count_range'],
                            'max_partition_shift_drift':ss['max_abs_partition_owen_minus_shapley_share']-s['max_abs_partition_owen_minus_shapley_share'],
                            'canonical_partition_top_share_drift':ss['canonical_partition_top_share']-s['canonical_partition_top_share'],
                        }
                        for k,v in vals.items():
                            maxerr=max(maxerr,abs(v-ff(qq[k])))
    checks.append({
        'check':'raw_chain_partition_and_LOO_reconstruction_max_error',
        'observed':maxerr,'required':'<=1e-9',
        'result':'PASS' if maxerr<=1e-9 else 'FAIL',
    })
    checks.append({
        'check':'owen_closure_and_block_reconciliation_max_error',
        'observed':maxclose,'required':'<=1e-8',
        'result':'PASS' if maxclose<=1e-8 else 'FAIL',
    })
    checks.append({
        'check':'minimum_respecting_order_marginal_contribution',
        'observed':minmarg,'required':'>=-1e-8',
        'result':'PASS' if minmarg>=-1e-8 else 'FAIL',
    })
    checks.append({
        'check':'set_partition_count',
        'observed':len(g.PARTITIONS),'required':'15',
        'result':'PASS' if len(g.PARTITIONS)==15 else 'FAIL',
    })
    sup=read(out/'HTS65_CHAIN_SUPPORT.tsv')
    for burn in (0.3,0.5):
        for label in roots:
            s=sum(ff(r['weight_share']) for r in sup
                  if r['contract']==label and ff(r['burn_fraction_per_chain'])==burn)
            checks.append({
                'check':f'{label}_{burn}_weight_share_sum',
                'observed':s,'required':'1 within 1e-10',
                'result':'PASS' if abs(s-1)<=1e-10 else 'FAIL',
            })
    with (out/'HTS65_INDEPENDENT_AUDIT_CHECKS.tsv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['check','observed','required','result'],
                         delimiter='\t',lineterminator='\n')
        w.writeheader(); w.writerows(checks)
    ok=all(r['result']=='PASS' for r in checks)
    (out/'HTS65_INDEPENDENT_AUDIT_RESULT.md').write_text(
        '# HTS65 independent audit result\n\n`'+('PASS' if ok else 'FAIL')+'`\n'
    )
    return 0 if ok else 1

if __name__=='__main__':
    sys.exit(main())
