#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, csv, math, sys

ROOT=Path(__file__).resolve().parent

def rows(path:Path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f,delimiter='\t'))

def one_row(path:Path):
    rs=rows(path)
    if len(rs)!=1:
        raise RuntimeError(f'expected exactly one data row: {path}; observed={len(rs)}')
    return rs[0]

def finite_float(value:str,label:str)->float:
    try: x=float(value)
    except Exception as e: raise RuntimeError(f'cannot parse finite float for {label}: {value!r}') from e
    if not math.isfinite(x): raise RuntimeError(f'non-finite value for {label}: {value!r}')
    return x

def extract(output_dir:Path)->dict[str,dict[str,str]]:
    h66=output_dir/'HTS66_RESULTS_FOR_REVIEW'
    h64=output_dir/'HTS64_RESULTS_FOR_REVIEW'
    h67=output_dir/'HTS67_RESULTS_FOR_REVIEW'
    required=[h66/'HTS66_CLASSIFICATION.tsv',h64/'HTS64_REPARAMETERIZATION_SUMMARY.tsv',h67/'HTS67_CLASSIFICATION.tsv',h67/'HTS67_SYMMETRIC_POOLING_SENSITIVITY.tsv']
    missing=[str(p) for p in required if not p.is_file()]
    if missing: raise RuntimeError('missing fresh output files: '+', '.join(missing))
    c66=one_row(required[0]); c67=one_row(required[2])
    r64=rows(required[1]); r67=rows(required[3])
    if not r64 or not r67: raise RuntimeError('fresh output tables are empty')
    primary64=[r for r in r64 if abs(finite_float(r['burn_fraction_per_chain'],'HTS64 burn')-0.3)<1e-15]
    if len(primary64)!=14: raise RuntimeError(f'HTS64 primary directed comparison count is not 14: {len(primary64)}')
    sensitive=sum(r.get('reparameterization_classification')=='BLOCK_ROBUST_VARIABLE_ALLOCATION_BASIS_SENSITIVE' for r in primary64)
    n032=max(finite_float(r['rotation_grid_top_share_range'],'N032 candidate') for r in primary64)
    primary67=[r for r in r67 if abs(finite_float(r['burn_fraction_per_chain'],'HTS67 burn')-0.3)<1e-15]
    if len(primary67)!=7: raise RuntimeError(f'HTS67 primary comparison count is not 7: {len(primary67)}')
    stable=sum(str(r.get('classification_stable','')).strip().lower()=='true' for r in primary67)
    n033=max(abs(finite_float(r['baryon_tilt_share_difference'],'N033 candidate')) for r in r67)
    n034=max(abs(finite_float(r['order_sensitivity_difference'],'N034 candidate')) for r in r67)
    values={
      'N029':{'observed':repr(finite_float(c66['max_conditional4d_distance_squared_cross_stage_error'],'N029')),'display':format(finite_float(c66['max_conditional4d_distance_squared_cross_stage_error'],'N029'),'.2e')},
      'N030':{'observed':repr(finite_float(c66['max_fixed_block_cross_stage_error'],'N030')),'display':format(finite_float(c66['max_fixed_block_cross_stage_error'],'N030'),'.2e')},
      'N031':{'observed':f'{sensitive}/14','display':f'{sensitive}/14'},
      'N032':{'observed':repr(n032),'display':f'{n032:.4f}'},
      'N033':{'observed':repr(n033),'display':f'{n033:.4f}'},
      'N034':{'observed':repr(n034),'display':f'{n034:.4f}'},
      'N035':{'observed':f'{stable}/7','display':f'{stable}/7'},
      'HTS66_CLASSIFICATION':{'observed':c66['classification'],'display':c66['classification']},
      'HTS67_CLASSIFICATION':{'observed':c67['classification'],'display':c67['classification']},
    }
    return values

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--expected',type=Path,default=ROOT/'EXPECTED_OUTPUT.tsv')
    ap.add_argument('--report',type=Path,required=True)
    a=ap.parse_args(); out=a.output_dir.resolve(); exp=a.expected.resolve(); report=a.report.resolve()
    try:
        values=extract(out); expected=rows(exp)
        if not expected: raise RuntimeError('expected-output table is empty')
        seen=set(); report_rows=[]; failures=[]
        for r in expected:
            item=r['ITEM_ID'].strip()
            if item in seen: raise RuntimeError(f'duplicate expected ITEM_ID: {item}')
            seen.add(item)
            if item not in values: raise RuntimeError(f'unsupported expected ITEM_ID: {item}')
            obs=values[item]['observed']; display=values[item]['display']; rule=r['COMPARISON_RULE']; expected_raw=r['EXPECTED_RAW']; expected_display=r['EXPECTED_DISPLAY']
            status='PASS'; difference=''
            if rule=='EXACT':
                if obs!=expected_raw: status='FAIL'; difference='not exact'
            elif rule.startswith('ABS<='):
                tol=float(rule.split('<=',1)[1]); difference=repr(abs(float(obs)-float(expected_raw)))
                if abs(float(obs)-float(expected_raw))>tol: status='FAIL'
            else: raise RuntimeError(f'unknown comparison rule: {rule}')
            if display!=expected_display:
                status='FAIL'; difference=(difference+'; ' if difference else '')+f'display {display!r}!={expected_display!r}'
            if status!='PASS': failures.append(item)
            report_rows.append({'ITEM_ID':item,'EXPECTED_RAW':expected_raw,'OBSERVED_RAW':obs,'COMPARISON_RULE':rule,'ABS_DIFFERENCE_OR_NOTE':difference,'EXPECTED_DISPLAY':expected_display,'OBSERVED_DISPLAY':display,'STATUS':status,'SOURCE_PATH':r['SOURCE_PATH']})
        if set(values)!=seen:
            raise RuntimeError('expected table does not cover extracted items: '+','.join(sorted(set(values)-seen)))
        report.parent.mkdir(parents=True,exist_ok=True)
        fields=['ITEM_ID','EXPECTED_RAW','OBSERVED_RAW','COMPARISON_RULE','ABS_DIFFERENCE_OR_NOTE','EXPECTED_DISPLAY','OBSERVED_DISPLAY','STATUS','SOURCE_PATH']
        with report.open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(report_rows)
        print(f'E002_FRESH_OUTPUT_VERIFY={"PASS" if not failures else "FAIL"} items={len(report_rows)} report={report}')
        if failures: print('failed items: '+','.join(failures),file=sys.stderr)
        return 1 if failures else 0
    except Exception as e:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text('STATUS\tERROR\nFAIL\t'+str(e).replace('\t',' ')+'\n',encoding='utf-8')
        print(f'E002_FRESH_OUTPUT_VERIFY=FAIL error={e}',file=sys.stderr)
        return 2
if __name__=='__main__': raise SystemExit(main())
