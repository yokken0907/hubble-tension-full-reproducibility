#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,math,sys
from pathlib import Path

def read(p):
    with Path(p).open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f,delimiter='\t'))
def ff(x):
    v=float(x)
    if not math.isfinite(v): raise ValueError(f'non-finite numeric value: {x!r}')
    return v

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output-dir',required=True)
    ap.add_argument('--root-json',required=True)  # retained for preserved public CLI compatibility
    a=ap.parse_args();out=Path(a.output_dir)
    summary=read(out/'HTS64_REPARAMETERIZATION_SUMMARY.tsv')
    loo=read(out/'HTS64_DIRECTED_LOO_STABILITY.tsv')
    support=read(out/'HTS64_CHAIN_SUPPORT.tsv')
    checks=[]
    checks.append({'check':'fresh_summary_row_count','observed':len(summary),'required':28,'result':'PASS' if len(summary)==28 else 'FAIL'})
    checks.append({'check':'fresh_LOO_row_count','observed':len(loo),'required':400,'result':'PASS' if len(loo)==400 else 'FAIL'})
    maxinv=max([ff(r['max_total_distance_invariance_error']) for r in summary]+[ff(r['max_block_share_invariance_error']) for r in summary]+[ff(r['max_total_distance_invariance_error']) for r in loo]+[ff(r['max_block_share_invariance_error']) for r in loo])
    checks.append({'check':'fresh_total_and_block_invariance_max_error','observed':maxinv,'required':'<=1e-8','result':'PASS' if maxinv<=1e-8 else 'FAIL'})
    # Fresh tables must cover 14 directed edge comparisons at each of two burns.
    keys={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain'])) for r in summary}
    checks.append({'check':'fresh_directed_burn_key_count','observed':len(keys),'required':28,'result':'PASS' if len(keys)==28 else 'FAIL'})
    # Chain-weight normalization is checked directly from the newly generated support table.
    groups={}
    for r in support:groups.setdefault((r['contract'],ff(r['burn_fraction_per_chain'])),0.0);groups[(r['contract'],ff(r['burn_fraction_per_chain']))]+=ff(r['weight_share'])
    for (label,burn),s in sorted(groups.items()):
        checks.append({'check':f'{label}_{burn}_fresh_weight_share_sum','observed':s,'required':'1 within 1e-10','result':'PASS' if abs(s-1)<=1e-10 else 'FAIL'})
    with (out/'HTS64_INDEPENDENT_AUDIT_CHECKS.tsv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['check','observed','required','result'],delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(checks)
    ok=all(r['result']=='PASS' for r in checks)
    (out/'HTS64_INDEPENDENT_AUDIT_RESULT.md').write_text('# HTS64 independent fresh-output consistency audit result\n\n`'+('PASS' if ok else 'FAIL')+'`\n\nThe preserved scientific runner generated the substantive tables. This portable audit validates their fresh row structure, invariance residuals, key coverage, and chain-weight normalization; cross-version substantive equality is checked separately by the E002 stage comparator.\n')
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
