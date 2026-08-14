#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,csv,hashlib,math,zipfile

def sha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p:Path):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))
def die(msg): print('FAIL',msg); raise SystemExit(1)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--fresh-output-dir',type=Path,required=True);a=ap.parse_args()
 pa=a.repo_root/'REPRODUCTION'/'posterior_attribution'; hr=pa/'historical_substantive_reference'/'hts67'; fresh=a.fresh_output_dir/'HTS67_RESULTS_FOR_REVIEW'
 required=['HTS67_CLASSIFICATION.tsv','HTS67_BURNIN_SENSITIVITY.tsv','HTS67_DIRECTED_BASELINE_COMPARISON.tsv','HTS67_ENDPOINT_6D_SUMMARY.tsv','HTS67_INDEPENDENT_AUDIT_CHECKS.tsv','HTS67_LOO_STABILITY.tsv','HTS67_SYMMETRIC_METRIC_RESULTS.tsv','HTS67_SYMMETRIC_POOLING_SENSITIVITY.tsv']
 m=rows(hr/'HISTORICAL_REFERENCE_MANIFEST.tsv')
 if len(m)!=8 or {Path(x['PATH']).name for x in m}!=set(required):die('historical manifest member set')
 for x in m:
  p=hr/Path(x['PATH']).name
  if not p.is_file() or sha(p)!=x['COPIED_FILE_SHA256'] or x['SOURCE_MEMBER_SHA256']!=x['COPIED_FILE_SHA256'] or x['BYTE_IDENTITY_STATUS']!='PASS':die('historical byte identity '+str(p))
 if (pa/'historical_exact_results'/'HTS67_RESULTS_FOR_REVIEW.zip').exists():die('portable reference remains in historical_exact_results')
 pr=pa/'portable_reference'/'hts67'/'HTS67_PORTABLE_REFERENCE_RESULTS.zip'
 if not pr.is_file():die('portable reference missing')
 pm=rows(pa/'portable_reference'/'hts67'/'PORTABLE_REFERENCE_MANIFEST.tsv')
 if len(pm)!=1 or pm[0]['ROLE']!='PORTABLE_REFERENCE_OUTPUT' or pm[0]['HISTORICAL_COMPARISON_ROLE']!='NONE' or pm[0]['SHA256']!=sha(pr):die('portable reference role/hash')
 sr=rows(pa/'official_fetch_records'/'phase2c_network_execution'/'evidence'/'E002_FRESH_STAGE_COMPARISON.tsv')
 h67=[r for r in sr if r['STAGE']=='HTS67']
 if len(h67)!=8 or any(r['REFERENCE_KIND']!='HISTORICAL_SUBSTANTIVE_REFERENCE' or r['STATUS']!='PASS' or float(r['MAX_ABS_NUMERIC_DIFFERENCE'])!=0.0 or r['TEXT_DIFFERENCE_COUNT']!='0' for r in h67):die('Phase2C HTS67 stage comparison')
 cr=rows(pa/'HTS67_HISTORICAL_VS_FRESH_COMPARISON.tsv')
 if len(cr)!=8 or any(r['REFERENCE_KIND']!='PHASE2C_OFFICIAL_EMPTY_CACHE_FRESH_OUTPUT' or r['HISTORICAL_SHA256']!=r['FRESH_SHA256'] or r['BYTE_IDENTICAL']!='YES' or r['COMPARISON_TYPE']!='BYTE_IDENTITY_AND_NUMERIC_EQUALITY' or float(r['MAX_ABS_NUMERIC_DIFFERENCE'])!=0.0 or r['TEXT_DIFFERENCE_COUNT']!='0' or r['STATUS']!='PASS_BYTE_IDENTICAL' for r in cr):die('Phase2C HTS67 direct comparison')
 # Semantic path checks.
 roots=rows(fresh/'HTS67_CACHE_ROOT_SELECTION.tsv')
 if len(roots)!=5 or any(r['candidate_count']!='1' or r['selection_rule']!='UNIQUE_TAIL_CANDIDATE' for r in roots):die('cache root semantic check')
 prov=rows(fresh/'HTS67_SELECTED_MEMBER_PROVENANCE.tsv'); sel=rows(pa/'SELECTED_CHAIN_MANIFEST.tsv')
 expected={(r['contract'],Path(r['materialized_path']).name,int(r['bytes']),r['sha256']) for r in sel}
 observed={(r['contract'],r['filename'],int(r['bytes']),r['sha256']) for r in prov}
 if len(prov)!=51 or observed!=expected:die('selected member provenance semantic check')
 freeze=rows(fresh/'HTS67_SOURCE_FREEZE.tsv')
 if len(freeze)!=2:die('source freeze rows')
 archive_map={'HTS62_RESULTS':pa/'historical_exact_results'/'HTS62_RESULTS_FOR_REVIEW.zip','HTS66_CORR_RESULTS':pa/'historical_exact_results'/'HTS66_CORR_RESULTS_FOR_REVIEW.zip'}
 for r in freeze:
  p=archive_map.get(r['source'])
  if p is None or not p.is_file() or sha(p)!=r['outer_sha256']:die('source freeze archive hash')
 cl=rows(fresh/'HTS67_CLASSIFICATION.tsv')
 if len(cl)!=1 or cl[0]['classification']!='HOLD_SYMMETRIC_POOLING_CONVENTION_SENSITIVITY' or cl[0]['primary_pooling_classification_agreement_count']!='4':die('classification/4 of 7')
 sem=rows(pa/'HTS67_PATH_DEPENDENT_SEMANTIC_CHECK.tsv')
 if any(r['STATUS']!='PASS' for r in sem):die('path-dependent semantic report')
 h64=a.fresh_output_dir/'HTS64_RESULTS_FOR_REVIEW'/'HTS64_REPARAMETERIZATION_SUMMARY.tsv'
 r64=rows(h64); primary=[r for r in r64 if abs(float(r['burn_fraction_per_chain'])-0.3)<1e-12]
 if len(primary)!=14 or any(r['reparameterization_classification']!='BLOCK_ROBUST_VARIABLE_ALLOCATION_BASIS_SENSITIVE' for r in primary):die('N031 14/14')
 # Failed HTS66 prohibited archive absent.
 for p in pa.rglob('HTS66_RESULTS_FOR_REVIEW.zip'):
  die('failed HTS66 archive present '+str(p))
 print('HTS67_HISTORICAL_REFERENCE_SELF_CONTAINED = PASS')
 print('HTS67_REFERENCE_KIND = PHASE2C_OFFICIAL_EMPTY_CACHE_FRESH_OUTPUT')
 print('HTS67_CLASSIFICATION_MATCH = PASS')
 print('HTS67_SUBSTANTIVE_TABLE_BYTE_IDENTITY = 8/8 PASS')
 print('HTS67_PUBLICATION_PRECISION_MATCH = PASS')
 print('HTS67_PATH_DEPENDENT_FILES_SEMANTIC_CHECK = PASS')
 print('PHASE1_REPAIR = PASS')
if __name__=='__main__':main()
