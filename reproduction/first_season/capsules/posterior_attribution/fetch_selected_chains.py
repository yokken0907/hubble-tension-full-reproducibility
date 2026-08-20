#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,csv,hashlib,importlib.util,os,shutil,sys,zipfile
ROOT=Path(__file__).resolve().parent

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))
def load_common():
 p=ROOT/'stages/hts59/hts59_common.py';spec=importlib.util.spec_from_file_location('public_hts59_common',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def verify(base):
 bad=[]
 for r in rows(ROOT/'SELECTED_CHAIN_MANIFEST.tsv'):
  p=base/r['source']/r['materialized_path']
  if not p.is_file() or p.stat().st_size!=int(r['bytes']) or sha(p)!=r['sha256']:bad.append(str(p))
 if bad:raise RuntimeError('selected-member verification failed: '+', '.join(bad[:10]))
 return 51
def copy_or_link(src:Path,dst:Path):
 dst.parent.mkdir(parents=True,exist_ok=True)
 try: os.link(src,dst)
 except OSError: shutil.copy2(src,dst)
def build_hts67_view(selected:Path,cache:Path):
 view=cache/'selected_hts67';shutil.rmtree(view,ignore_errors=True)
 mappings=[]
 roots={'ORIGINAL':'ORIGINAL_FACTORIAL_SELECTED','FIXED':'FIXED_FULL_SELECTED'}
 for r in rows(ROOT/'SELECTED_CHAIN_MANIFEST.tsv'):
  src=selected/r['source']/r['materialized_path']; dst=view/roots[r['source']]/r['materialized_path']
  copy_or_link(src,dst)
  status='PASS' if dst.stat().st_size==src.stat().st_size and sha(dst)==sha(src)==r['sha256'] else 'FAIL'
  mappings.append({'SOURCE':r['source'],'SOURCE_PATH':str(src.relative_to(cache)),'HTS67_VIEW_PATH':str(dst.relative_to(cache)),'BYTES':str(dst.stat().st_size),'SHA256':sha(dst),'STATUS':status})
 if len(mappings)!=51 or any(r['STATUS']!='PASS' for r in mappings):raise RuntimeError('HTS67 compatibility cache view verification failed')
 with (cache/'HTS67_COMPATIBILITY_CACHE_VIEW.tsv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(mappings[0]),delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(mappings)
 return view

def selected_fingerprint(selected):
 items=[]
 for r in rows(ROOT/'SELECTED_CHAIN_MANIFEST.tsv'):
  p=selected/r['source']/r['materialized_path'];items.append(r['source']+'\t'+r['materialized_path']+'\t'+str(p.stat().st_size)+'\t'+sha(p))
 return hashlib.sha256(('\n'.join(items)+'\n').encode()).hexdigest()
def build_wrappers(selected,cache):
 wrappers=cache/'wrappers';wrappers.mkdir(parents=True,exist_ok=True);inner=wrappers/'LCDM.zip';outer=wrappers/'chains_ttteee_winter1920.zip';fixed=wrappers/'CMB_SPA_DESI_Fixed.zip';marker=wrappers/'SELECTED_FINGERPRINT.txt';fp=selected_fingerprint(selected)
 if marker.is_file() and marker.read_text().strip()==fp and all(p.is_file() and zipfile.is_zipfile(p) for p in (outer,fixed)):
  return outer,fixed
 with zipfile.ZipFile(inner,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
  for p in sorted((selected/'ORIGINAL').rglob('*')):
   if p.is_file():z.write(p,p.relative_to(selected/'ORIGINAL').as_posix())
 with zipfile.ZipFile(outer,'w',zipfile.ZIP_STORED,allowZip64=True) as z:z.write(inner,'Compressed_Chains/LCDM.zip')
 with zipfile.ZipFile(fixed,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
  for p in sorted((selected/'FIXED').rglob('*')):
   if p.is_file():z.write(p,p.relative_to(selected/'FIXED').as_posix())
 marker.write_text(fp+'\n',encoding='utf-8')
 return outer,fixed

def main():
 a=argparse.ArgumentParser();a.add_argument('--cache',type=Path,required=True);a.add_argument('--fetch',action='store_true');a.add_argument('--import-selected-from',type=Path,help='offline audit only: import a preverified selected cache, then enforce the published 51-member manifest');a.add_argument('--build-legacy-wrappers',action='store_true',help='optional historical compatibility only; public stages use the verified selected cache directly')
 x=a.parse_args();x.cache=x.cache.resolve();selected=x.cache/'selected'
 if x.fetch and x.import_selected_from:raise SystemExit('--fetch and --import-selected-from are mutually exclusive')
 if x.import_selected_from:
  src=x.import_selected_from.resolve();shutil.rmtree(selected,ignore_errors=True);shutil.copytree(src,selected)
 if x.fetch:
  c=load_common();stage=x.cache/'materialization';downloads=x.cache/'downloads';store=x.cache/'store';stage.mkdir(parents=True,exist_ok=True);downloads.mkdir(parents=True,exist_ok=True);store.mkdir(parents=True,exist_ok=True)
  od,_,_,_=c.materialize_original_factorial(downloads,store,stage,False);fd,_,_,_=c.materialize_fixed_full(downloads,store,stage,False)
  shutil.rmtree(selected,ignore_errors=True);shutil.copytree(od,selected/'ORIGINAL');shutil.copytree(fd,selected/'FIXED')
 n=verify(selected);view=build_hts67_view(selected,x.cache)
 if x.build_legacy_wrappers:
  o,f=build_wrappers(selected,x.cache);wrapper_status=f'ORIGINAL_WRAPPER={o}\nFIXED_WRAPPER={f}'
 else: wrapper_status='LEGACY_WRAPPERS=NOT_BUILT_NOT_REQUIRED_BY_PORTABLE_STAGES'
 print(f'SELECTED_MEMBER_VERIFY=PASS count={n}\nHTS67_COMPATIBILITY_VIEW_VERIFY=PASS count={n}\nHTS67_COMPATIBILITY_VIEW={view}\n{wrapper_status}')
if __name__=='__main__':main()
