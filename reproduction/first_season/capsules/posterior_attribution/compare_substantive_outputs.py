#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,csv,io,math,hashlib,zipfile

SUBSTANTIVE={
59:['HTS59_CLASSIFICATION.tsv','HTS59_DIRECTED_6D_DECOMPOSITION.tsv','HTS59_ENDPOINT_6D_CONDITIONING.tsv','HTS59_DIRECTED_LOO_STABILITY.tsv','HTS59_BURNIN_SENSITIVITY.tsv','HTS59_CHAIN_SUPPORT.tsv'],
60:['HTS60_CLASSIFICATION.tsv','HTS60_DIRECTED_MODE_CONTRIBUTIONS.tsv','HTS60_DIRECTED_MODE_SUMMARY.tsv','HTS60_ENDPOINT_CONDITIONAL_MODE_BASIS.tsv','HTS60_DIRECTED_LOO_STABILITY.tsv','HTS60_BURNIN_SENSITIVITY.tsv','HTS60_CHAIN_SUPPORT.tsv'],
61:['HTS61_CLASSIFICATION.tsv','HTS61_CROSS_ENDPOINT_BLOCK_ALIGNMENT.tsv','HTS61_EDGE_CONTRIBUTION_IDENTIFIABILITY.tsv','HTS61_ENDPOINT_BLOCK_SUBSPACE.tsv','HTS61_ENDPOINT_MODE_IDENTIFIABILITY.tsv','HTS61_ENDPOINT_LOO_BLOCK_STABILITY.tsv','HTS61_ENDPOINT_LOO_CLUSTER_STABILITY.tsv','HTS61_ENDPOINT_LOO_MODE_STABILITY.tsv','HTS61_BURNIN_BLOCK_STABILITY.tsv','HTS61_BURNIN_CLUSTER_STABILITY.tsv','HTS61_BURNIN_MODE_STABILITY.tsv','HTS61_CHAIN_SUPPORT.tsv'],
62:['HTS62_CLASSIFICATION.tsv','HTS62_DIRECTED_FIXED_BLOCK_DECOMPOSITION.tsv','HTS62_ENDPOINT_BLOCK_COUPLING.tsv','HTS62_DIRECTED_LOO_STABILITY.tsv','HTS62_BURNIN_SENSITIVITY.tsv','HTS62_CHAIN_SUPPORT.tsv'],
63:['HTS63_CLASSIFICATION.tsv','HTS63_DIRECTED_VARIABLE_ALLOCATIONS.tsv','HTS63_DIRECTED_VARIABLE_ALLOCATION_SUMMARY.tsv','HTS63_DIRECTED_LOO_STABILITY.tsv','HTS63_BURNIN_SENSITIVITY.tsv','HTS63_CHAIN_SUPPORT.tsv'],
64:['HTS64_CLASSIFICATION.tsv','HTS64_REPARAMETERIZATION_SUMMARY.tsv','HTS64_ROTATED_COORDINATE_ALLOCATIONS.tsv','HTS64_ROTATION_GRID.tsv','HTS64_DIRECTED_LOO_STABILITY.tsv','HTS64_BURNIN_SENSITIVITY.tsv','HTS64_CHAIN_SUPPORT.tsv'],
65:['HTS65_CLASSIFICATION.tsv','HTS65_PARTITION_CATALOG.tsv','HTS65_DIRECTED_PARTITION_RESULTS.tsv','HTS65_DIRECTED_PARTITION_SUMMARY.tsv','HTS65_DIRECTED_PARTITION_BLOCK_ALLOCATIONS.tsv','HTS65_DIRECTED_PARTITION_VARIABLE_ALLOCATIONS.tsv','HTS65_DIRECTED_LOO_STABILITY.tsv','HTS65_BURNIN_SENSITIVITY.tsv','HTS65_CHAIN_SUPPORT.tsv'],
66:['HTS66_CLASSIFICATION.tsv','HTS66_CONDITIONAL_DISTANCE_CONSISTENCY.tsv','HTS66_CROSS_STAGE_KEY_AUDIT.tsv','HTS66_FIXED_BLOCK_CONSISTENCY.tsv','HTS66_INVARIANT_HIERARCHY.tsv','HTS66_PRIMARY_SYNTHESIS.tsv'],
67:['HTS67_CLASSIFICATION.tsv','HTS67_BURNIN_SENSITIVITY.tsv','HTS67_DIRECTED_BASELINE_COMPARISON.tsv','HTS67_ENDPOINT_6D_SUMMARY.tsv','HTS67_INDEPENDENT_AUDIT_CHECKS.tsv','HTS67_LOO_STABILITY.tsv','HTS67_SYMMETRIC_METRIC_RESULTS.tsv','HTS67_SYMMETRIC_POOLING_SENSITIVITY.tsv'],
}

def sha256(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(text:str): return list(csv.reader(io.StringIO(text),delimiter='\t'))
def compare_tsv(a:str,b:str,tol=1e-8,strict_nonfinite=False):
 ra,rb=parse(a),parse(b)
 if len(ra)!=len(rb):return False,float('inf'),1
 maxdiff=0.0;textdiff=0
 for xa,xb in zip(ra,rb):
  if len(xa)!=len(xb):return False,float('inf'),1
  for va,vb in zip(xa,xb):
   try:
    fa,fb=float(va),float(vb)
    if math.isfinite(fa) and math.isfinite(fb):
     maxdiff=max(maxdiff,abs(fa-fb));continue
    if strict_nonfinite: return False,float('inf'),1
   except ValueError: pass
   if va!=vb:textdiff+=1
 return textdiff==0 and maxdiff<=tol,maxdiff,textdiff

def load_hist_manifest(d:Path):
 p=d/'HISTORICAL_REFERENCE_MANIFEST.tsv'
 with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f,delimiter='\t'))
 out={Path(r['PATH']).name:r for r in rows}
 for fn,r in out.items():
  hp=d/fn
  if not hp.is_file() or sha256(hp)!=r['COPIED_FILE_SHA256'] or r['SOURCE_MEMBER_SHA256']!=r['COPIED_FILE_SHA256'] or r['BYTE_IDENTITY_STATUS']!='PASS':
   raise SystemExit(f'historical reference integrity failure: {fn}')
 return out

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--output-dir',type=Path,required=True)
 ap.add_argument('--historical-dir',type=Path,required=True,help='HTS59-66 historical archive directory')
 ap.add_argument('--hts67-historical-reference',type=Path,required=True)
 ap.add_argument('--report',type=Path,required=True)
 a=ap.parse_args()
 h67manifest=load_hist_manifest(a.hts67_historical_reference)
 rows=[];fail=[]
 for n,files in SUBSTANTIVE.items():
  fresh=a.output_dir/f'HTS{n}_RESULTS_FOR_REVIEW'
  if n==67:
   reference_kind='HISTORICAL_SUBSTANTIVE_REFERENCE'
   for fn in files:
    p=fresh/fn; hp=a.hts67_historical_reference/fn
    if not p.is_file() or fn not in h67manifest or not hp.is_file():
     status='FAIL';md='';td='missing';fail.append(f'HTS{n}:{fn}')
    else:
     ok,md,td=compare_tsv(p.read_text(encoding='utf-8-sig'),hp.read_text(encoding='utf-8-sig'),strict_nonfinite=True)
     status='PASS' if ok else 'FAIL'
     if not ok: fail.append(f'HTS{n}:{fn}')
    rows.append({'STAGE':f'HTS{n}','FILE':fn,'REFERENCE_KIND':reference_kind,'STATUS':status,'MAX_ABS_NUMERIC_DIFFERENCE':md,'TEXT_DIFFERENCE_COUNT':td})
  else:
   reference_kind='VERIFIED_PORTABLE_REPLICA_OF_HISTORICAL_INTERMEDIATE'
   zname=f'HTS{n}_RESULTS_FOR_REVIEW.zip' if n!=66 else 'HTS66_CORR_RESULTS_FOR_REVIEW.zip';zp=a.historical_dir/zname
   if not zp.is_file(): raise SystemExit(f'missing historical archive: {zp}')
   with zipfile.ZipFile(zp) as z:
    names={Path(x).name:x for x in z.namelist() if not x.endswith('/')}
    for fn in files:
     p=fresh/fn
     if not p.is_file() or fn not in names:
      status='FAIL';md='';td='missing';fail.append(f'HTS{n}:{fn}')
     else:
      ok,md,td=compare_tsv(p.read_text(encoding='utf-8-sig'),z.read(names[fn]).decode('utf-8-sig'))
      status='PASS' if ok else 'FAIL'
      if not ok: fail.append(f'HTS{n}:{fn}')
     rows.append({'STAGE':f'HTS{n}','FILE':fn,'REFERENCE_KIND':reference_kind,'STATUS':status,'MAX_ABS_NUMERIC_DIFFERENCE':md,'TEXT_DIFFERENCE_COUNT':td})
 a.report.parent.mkdir(parents=True,exist_ok=True)
 with a.report.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rows)
 print(f'E002_STAGE_SUBSTANTIVE_COMPARE={"PASS" if not fail else "FAIL"} rows={len(rows)} report={a.report}')
 return 1 if fail else 0
if __name__=='__main__':raise SystemExit(main())
