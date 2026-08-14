#!/usr/bin/env python3
from pathlib import Path
import argparse,csv,math
from scipy.stats import norm

def rows(p):
 with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))
def main():
 a=argparse.ArgumentParser();a.add_argument('--output-dir',type=Path,required=True);x=a.parse_args()
 exp=rows(Path(__file__).with_name('EXPECTED_OUTPUT.tsv'));obs={r['test']:r for r in rows(x.output_dir/'04_NESTED_MODEL_TESTS.tsv')}
 fail=[]
 for e in exp:
  r=obs[e['TEST']];p=float(r['bootstrap_p']);sig=float(r['bootstrap_equivalent_sigma']);cnt=round(p*1001-1)
  if int(r['bootstrap_draws'])!=int(e['DRAWS']) or cnt!=int(e['EXCEEDANCE_COUNT']) or abs(p-float(e['BOOTSTRAP_P']))>1e-15 or abs(sig-float(e['EQUIVALENT_SIGMA']))>1e-10 or f'{sig:.3f}'!=e['MANUSCRIPT_DISPLAY']:fail.append(e['ITEM_ID'])
 print('E001_VERIFY=' + ('PASS' if not fail else 'FAIL:'+','.join(fail)))
 raise SystemExit(1 if fail else 0)
if __name__=='__main__':main()
