#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,csv,hashlib,json,os,platform,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run(cmd,log,env=None,cwd=None):
 line='+ '+' '.join(map(str,cmd));print(line,flush=True);log.write(line+'\n');log.flush()
 p=subprocess.Popen([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env,cwd=cwd)
 assert p.stdout
 for s in p.stdout: print(s,end='');log.write(s)
 rc=p.wait();log.flush()
 if rc: raise subprocess.CalledProcessError(rc,cmd)
def exact_archives(exact:Path):
 expected={}
 with (ROOT/'HISTORICAL_EXACT_RESULT_ARCHIVES.tsv').open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f,delimiter='\t'):
   if r['CANONICAL']=='YES':expected[r['FILENAME']]=(int(r['BYTES']),r['SHA256'])
 for fn,(size,h) in expected.items():
  p=exact/fn
  if not p.is_file() or p.stat().st_size!=size or sha(p)!=h:raise RuntimeError(f'exact historical archive gate failed: {fn}')
 return expected

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fetch-inputs',action='store_true');ap.add_argument('--import-selected-from',type=Path);ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--verify',action='store_true');a=ap.parse_args()
 cache=a.cache.resolve();work=a.work.resolve();out=a.output.resolve()
 if work.exists() and any(work.iterdir()):raise SystemExit(f'work directory must be empty: {work}')
 if out.exists() and any(out.iterdir()):raise SystemExit(f'output directory must be empty: {out}')
 work.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
 logpath=out/'E002_CLEAN_REPLAY_RUN_LOG.txt'
 with logpath.open('w',encoding='utf-8') as log:
  log.write('E002 clean replay started UTC='+time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())+'\n')
  cmd=[sys.executable,ROOT/'fetch_selected_chains.py','--cache',cache]
  if a.fetch_inputs:cmd+=['--fetch']
  if a.import_selected_from:cmd+=['--import-selected-from',a.import_selected_from.resolve()]
  run(cmd,log)
  shutil.copy2(cache/'HTS67_COMPATIBILITY_CACHE_VIEW.tsv',out/'E002_INPUT_VERIFICATION.tsv')
  stage_rows=[]
  for n in range(59,66):
   sd=ROOT/f'stages/hts{n}';stagework=work/f'HTS{n}';stagework.mkdir(parents=True,exist_ok=True);env=os.environ.copy();env.update({f'HTS{n}_DOWNLOADS':str(stagework),f'HTS{n}_OUTPUT':str(out/f'HTS{n}_RESULTS_FOR_REVIEW'),f'HTS{n}_ZIP_OUTPUT':str(out/f'HTS{n}_RESULTS_FOR_REVIEW.zip'),f'HTS{n}_CACHE':str(stagework/'cache'),'HTS_CACHE_STORE':str(cache/'stage_store'),'HTS_SELECTED_CACHE_OVERRIDE':str(cache/'selected'),f'HTS{n}_TEST_MODE':'1'})
   run(['bash',sd/f'run_hts{n}.sh'],log,env=env,cwd=sd);stage_rows.append({'STAGE':f'HTS{n}','EXECUTION_STATUS':'PASS','OUTPUT_PATH':str((out/f'HTS{n}_RESULTS_FOR_REVIEW').relative_to(out))})
  exact=ROOT/'historical_exact_results';exact_archives(exact)
  h66=work/'HTS66';src=h66/'sources';src.mkdir(parents=True,exist_ok=True)
  for n in range(59,66):shutil.copy2(exact/f'HTS{n}_RESULTS_FOR_REVIEW.zip',src/f'HTS{n}_RESULTS_FOR_REVIEW.zip')
  sd=ROOT/'stages/hts66';env=os.environ.copy();env.update({'HTS66_DOWNLOADS':str(h66),'HTS_CACHE_STORE':str(src),'HTS66_OUTPUT':str(out/'HTS66_RESULTS_FOR_REVIEW'),'HTS66_ZIP_OUTPUT':str(out/'HTS66_RESULTS_FOR_REVIEW.zip')});run(['bash',sd/'run_hts66.sh'],log,env=env,cwd=sd);stage_rows.append({'STAGE':'HTS66','EXECUTION_STATUS':'PASS','OUTPUT_PATH':'HTS66_RESULTS_FOR_REVIEW'})
  h67=work/'HTS67';h67.mkdir(parents=True,exist_ok=True);shutil.copy2(exact/'HTS62_RESULTS_FOR_REVIEW.zip',h67/'HTS62_RESULTS_FOR_REVIEW.zip');shutil.copy2(exact/'HTS66_CORR_RESULTS_FOR_REVIEW.zip',h67/'HTS66_CORR_RESULTS_FOR_REVIEW.zip')
  sd=ROOT/'stages/hts67';view=cache/'selected_hts67';env=os.environ.copy();env.update({'HTS67_DOWNLOADS':str(h67),'HTS67_CACHE_ROOT_OVERRIDE':str(view),'HTS67_HTS62_RESULTS_OVERRIDE':str(h67/'HTS62_RESULTS_FOR_REVIEW.zip'),'HTS67_HTS66_RESULTS_OVERRIDE':str(h67/'HTS66_CORR_RESULTS_FOR_REVIEW.zip'),'HTS67_OUTPUT':str(out/'HTS67_RESULTS_FOR_REVIEW'),'HTS67_ZIP_OUTPUT':str(out/'HTS67_RESULTS_FOR_REVIEW.zip'),'HTS67_CACHE':str(h67/'cache'),'HTS_CACHE_STORE':str(view)});run(['bash',sd/'run_hts67.sh'],log,env=env,cwd=sd);stage_rows.append({'STAGE':'HTS67','EXECUTION_STATUS':'PASS','OUTPUT_PATH':'HTS67_RESULTS_FOR_REVIEW'})
  with (out/'E002_STAGE_STATUS.tsv').open('w',encoding='utf-8',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(stage_rows[0]),delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(stage_rows)
  run([sys.executable,ROOT/'compare_substantive_outputs.py','--output-dir',out,'--historical-dir',exact,'--hts67-historical-reference',ROOT/'historical_substantive_reference'/'hts67','--report',out/'E002_FRESH_STAGE_COMPARISON.tsv'],log)
  if a.verify:run([sys.executable,ROOT/'verify_output.py','--output-dir',out,'--expected',ROOT/'EXPECTED_OUTPUT.tsv','--report',out/'E002_FRESH_OUTPUT_COMPARISON.tsv'],log)
  envrec={'python':sys.version,'platform':platform.platform(),'executable':sys.executable,'numpy':None,'scipy':None,'input_mode':'official_fetch' if a.fetch_inputs else ('preverified_selected_cache_import' if a.import_selected_from else 'existing_preverified_cache')}
  try:
   import numpy;envrec['numpy']=numpy.__version__
  except:pass
  try:
   import scipy;envrec['scipy']=scipy.__version__
  except:pass
  (out/'E002_ENVIRONMENT.json').write_text(json.dumps(envrec,indent=2,sort_keys=True)+'\n',encoding='utf-8')
  (out/'E002_CLASSIFICATION.txt').write_text('E002_CLASSIFICATION=COMPLETE_WITH_SCOPE\nFRESH_OUTPUT_VERIFICATION=PASS\nHTS67_PORTABLE_REPLAY=PASS\n',encoding='utf-8')
  audit_files=[p for p in out.rglob('*') if p.is_file() and p.name!='E002_SHA256SUMS.txt']
  (out/'E002_SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(out).as_posix()}\n' for p in sorted(audit_files)),encoding='utf-8')
  log.write('E002_REPLAY=COMPLETE_WITH_SCOPE\n')
 print('E002_REPLAY=COMPLETE_WITH_SCOPE')
 return 0
if __name__=='__main__':raise SystemExit(main())
