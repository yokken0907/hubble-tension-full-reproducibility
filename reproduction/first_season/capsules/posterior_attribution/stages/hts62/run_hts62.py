#!/usr/bin/env python3
from __future__ import annotations
import json,math,os,shutil,subprocess,sys,traceback
from pathlib import Path
import hts62_common as c
import hts62_metric as g
BURNS=(0.3,0.5);PRIMARY=0.3;SENS=0.5
ORDER=('SPT_BASE','SPT_ACT','SPT_PR4','FULL_ORIGINAL','FULL_FIXED')
DOCS=('CANONICAL_STATE_THROUGH_HTS61.md','HTS61_CANONICALIZATION_AUDIT.md','HTS62_EXECUTION_CONTRACT.md','HTS62_SELECTION_AUDIT.md','HTS62_SOURCE_ADEQUACY_AUDIT.md','HTS62_PREFLIGHT_RESULT.md','HTS62_PREFLIGHT_TEST_AUDIT.md','README_RUN.md')
def main():
 pkg=Path(__file__).resolve().parent;downloads=Path(os.environ.get('HTS62_DOWNLOADS',str(pkg.parent))).resolve();store=Path(os.environ.get('HTS_CACHE_STORE',str(downloads/'HTS_CHAIN_CACHE_STORE'))).resolve();stage_cache=Path(os.environ.get('HTS62_CACHE',str(store/'HTS62'))).resolve();out=Path(os.environ.get('HTS62_OUTPUT',str(downloads/'HTS62_RESULTS_FOR_REVIEW'))).resolve();zp=Path(os.environ.get('HTS62_ZIP_OUTPUT',str(downloads/'HTS62_RESULTS_FOR_REVIEW.zip'))).resolve();test=os.environ.get('HTS62_TEST_MODE','0')=='1'
 store.mkdir(parents=True,exist_ok=True);stage_cache.mkdir(parents=True,exist_ok=True);shutil.rmtree(out,ignore_errors=True);out.mkdir(parents=True)
 try:
  obase,ometa,oprov,oroots=c.materialize_original_factorial(downloads,store,stage_cache,test);fbase,fmeta,fprov,froots=c.materialize_fixed_full(downloads,store,stage_cache,test)
  c.write_tsv(out/'HTS62_SOURCE_FREEZE.tsv',[{'source':'ORIGINAL',**ometa},{'source':'FIXED',**fmeta}]);c.write_tsv(out/'HTS62_SELECTED_MEMBER_PROVENANCE.tsv',oprov+fprov)
  inv=stage_cache/'HTS62_ORIGINAL_ROOT_INVENTORY.tsv'
  if inv.exists():shutil.copy2(inv,out/inv.name)
  roots={'SPT_BASE':obase/oroots['SPT_BASE'],'SPT_ACT':obase/oroots['SPT_ACT'],'SPT_PR4':obase/oroots['SPT_PR4'],'FULL_ORIGINAL':obase/oroots['FULL_ORIGINAL'],'FULL_FIXED':fbase/froots['FULL_FIXED']}
  lr,likes,fr,fams,ok,checks,raw=c.factor_contract_rows(roots);c.write_tsv(out/'HTS62_LIKELIHOOD_MEMBERSHIP.tsv',lr);c.write_tsv(out/'HTS62_SEMANTIC_DATA_FAMILY_MEMBERSHIP.tsv',fr);c.write_tsv(out/'HTS62_RELEASE_ENDPOINT_CONTRACT_CHECKS.tsv',checks);c.write_tsv(out/'HTS62_RAW_IMPLEMENTATION_DIAGNOSTICS.tsv',raw)
  if not ok:raise RuntimeError('release endpoint semantic contract failed')
  counts={**c.FACTOR_EXPECTED_CHAINS,**c.FACTOR_EXPECTED_CHAINS_FIXED};D={};support=[];coupling=[];root_json={}
  for burn in BURNS:
   for label in ORDER:
    d,w,ids,h,cols,files=c.load_factor_root(roots[label],counts[label],burn);q=g.endpoint_detail(d,w,ids);D[(label,burn)]=q;support+=g.support_rows(label,burn,q);coupling.append(g.endpoint_block_coupling(label,burn,q));root_json[label]={'path':str(roots[label]),'count':counts[label]}
  c.write_tsv(out/'HTS62_CHAIN_SUPPORT.tsv',support);c.write_tsv(out/'HTS62_ENDPOINT_BLOCK_COUPLING.tsv',coupling)
  rows=[]
  for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
   for burn in BURNS:
    for direction,sl,tl,A,B in (('FORWARD',frm,to,D[(frm,burn)],D[(to,burn)]),('REVERSE',to,frm,D[(to,burn)],D[(frm,burn)])):
     rows.append(g.directed_block_decomposition(edge,etype,boundary,burn,sl,tl,A,B,direction))
  c.write_tsv(out/'HTS62_DIRECTED_FIXED_BLOCK_DECOMPOSITION.tsv',rows)
  idx={(r['edge'],r['direction'],r['burn_fraction_per_chain']):r for r in rows}
  loo=[]
  for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
   for burn in BURNS:
    for direction,sl,tl,A,B in (('FORWARD',frm,to,D[(frm,burn)],D[(to,burn)]),('REVERSE',to,frm,D[(to,burn)],D[(frm,burn)])):
     base=idx[(edge,direction,burn)]
     for side,Q in (('SOURCE',A),('TARGET',B)):
      for ch in sorted(set(Q['ids'])):
       sub=g.subset_detail(Q,Q['ids']!=ch);AA=sub if side=='SOURCE' else A;BB=sub if side=='TARGET' else B
       q=g.directed_block_decomposition(edge,etype,boundary,burn,sl,tl,AA,BB,direction)
       loo.append({'edge':edge,'direction':direction,'burn_fraction_per_chain':burn,'omission_side':side,'omitted_chain':ch,'conditional4d_mahalanobis_drift':q['conditional4d_mahalanobis']-base['conditional4d_mahalanobis'],'baryon_tilt_shapley_share_drift':q['baryon_tilt_shapley_share']-base['baryon_tilt_shapley_share'],'tau_amplitude_shapley_share_drift':q['tau_amplitude_shapley_share']-base['tau_amplitude_shapley_share'],'order_sensitivity_fraction_drift':q['order_sensitivity_fraction']-base['order_sensitivity_fraction'],'max_block_canonical_correlation_drift':q['max_block_canonical_correlation']-base['max_block_canonical_correlation'],'shapley_closure_error':q['shapley_closure_error']})
  c.write_tsv(out/'HTS62_DIRECTED_LOO_STABILITY.tsv',loo)
  sens=[]
  for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
   for direction in ('FORWARD','REVERSE'):
    a=idx[(edge,direction,PRIMARY)];b=idx[(edge,direction,SENS)]
    sens.append({'edge':edge,'direction':direction,'conditional4d_mahalanobis_change':b['conditional4d_mahalanobis']-a['conditional4d_mahalanobis'],'baryon_tilt_shapley_share_change':b['baryon_tilt_shapley_share']-a['baryon_tilt_shapley_share'],'tau_amplitude_shapley_share_change':b['tau_amplitude_shapley_share']-a['tau_amplitude_shapley_share'],'order_sensitivity_fraction_change':b['order_sensitivity_fraction']-a['order_sensitivity_fraction'],'max_block_canonical_correlation_change':b['max_block_canonical_correlation']-a['max_block_canonical_correlation'],'classification_30':a['block_pattern_classification'],'classification_50':b['block_pattern_classification']})
  c.write_tsv(out/'HTS62_BURNIN_SENSITIVITY.tsv',sens)
  runtime=stage_cache/'HTS62_RUNTIME_ROOTS.json';runtime.write_text(json.dumps(root_json,indent=2)+'\n')
  for name in DOCS:shutil.copy2(pkg/name,out/name)
  proc=subprocess.run([sys.executable,str(pkg/'audit_hts62.py'),'--output-dir',str(out),'--root-json',str(runtime)],capture_output=True,text=True);(out/'HTS62_AUDIT_STDOUT.txt').write_text(proc.stdout);(out/'HTS62_AUDIT_STDERR.txt').write_text(proc.stderr);audit_pass=proc.returncode==0
  ps=[r for r in support if r['burn_fraction_per_chain']==PRIMARY];pl=[r for r in loo if r['burn_fraction_per_chain']==PRIMARY]
  min_kish=min(r['kish_effective_rows'] for r in ps);max_share=max(r['weight_share'] for r in ps);min_eig=min(r['conditional_correlation_min_eigenvalue'] for r in coupling);max_cond=max(r['conditional_correlation_condition_number'] for r in coupling);max_close=max(abs(r['shapley_closure_error']) for r in rows)
  max_loo_d=max(abs(r['conditional4d_mahalanobis_drift']) for r in pl);max_loo_share=max(max(abs(r['baryon_tilt_shapley_share_drift']),abs(r['tau_amplitude_shapley_share_drift'])) for r in pl);max_loo_order=max(abs(r['order_sensitivity_fraction_drift']) for r in pl);max_loo_cc=max(abs(r['max_block_canonical_correlation_drift']) for r in pl)
  max_burn_d=max(abs(r['conditional4d_mahalanobis_change']) for r in sens);max_burn_share=max(max(abs(r['baryon_tilt_shapley_share_change']),abs(r['tau_amplitude_shapley_share_change'])) for r in sens);max_burn_order=max(abs(r['order_sensitivity_fraction_change']) for r in sens);max_burn_cc=max(abs(r['max_block_canonical_correlation_change']) for r in sens)
  gates={'support_gate_pass':min_kish>=100 and max_share<=0.35,'numerical_block_gate_pass':min_eig>1e-6 and max_cond<=500 and max_close<=1e-8,'loo_block_decomposition_gate_pass':max_loo_d<=0.25 and max_loo_share<=0.15 and max_loo_order<=0.15 and max_loo_cc<=0.10,'burnin_block_decomposition_gate_pass':max_burn_d<=0.25 and max_burn_share<=0.15 and max_burn_order<=0.15 and max_burn_cc<=0.10,'independent_audit_pass':audit_pass}
  passed=all(gates.values());classification='PASS_FIXED_BLOCK_SHAPLEY_AND_ORDER_SENSITIVITY_AUDIT' if passed else 'HOLD_FIXED_BLOCK_DECOMPOSITION_SUPPORT_OR_STABILITY_FAILURE'
  c.write_tsv(out/'HTS62_CLASSIFICATION.tsv',[{'classification':classification,'min_chain_kish_effective_rows':min_kish,'max_chain_weight_share':max_share,'min_conditional_correlation_eigenvalue':min_eig,'max_conditional_correlation_condition_number':max_cond,'max_shapley_closure_error':max_close,'max_LOO_conditional4d_drift':max_loo_d,'max_LOO_shapley_share_drift':max_loo_share,'max_LOO_order_sensitivity_drift':max_loo_order,'max_LOO_block_canonical_correlation_drift':max_loo_cc,'max_burn_conditional4d_change':max_burn_d,'max_burn_shapley_share_change':max_burn_share,'max_burn_order_sensitivity_change':max_burn_order,'max_burn_block_canonical_correlation_change':max_burn_cc,**gates,'interpretation_boundary':'Fixed coordinate-block Shapley values are symmetric posterior-distance bookkeeping, not causal or physical attribution.'}])
  (out/'HTS62_EXECUTION_REPORT.md').write_text('# HTS62 execution report\n\n`'+classification+'`\n\nHTS62 decomposes the HTS59 conditional four-dimensional posterior distance between fixed coordinate blocks using both sequential orders and their symmetric Shapley average.\n')
  (out/'MANIFEST.json').write_text(json.dumps({'stage':'HTS62','classification':classification,'primary_burn':PRIMARY,'sensitivity_burn':SENS,'blocks':g.BLOCKS,'cache_store':str(store),'boundary':'Fixed-block posterior-distance decomposition only.'},indent=2)+'\n');c.make_zip(out,zp);print(classification);print(zp)
 except Exception as e:
  (out/'HTS62_RUNTIME_FAILURE.txt').write_text(traceback.format_exc())
  for name in DOCS:
   if (pkg/name).exists():shutil.copy2(pkg/name,out/name)
  c.write_tsv(out/'HTS62_CLASSIFICATION.tsv',[{'classification':'HOLD_SOURCE_MATERIALIZATION_OR_BLOCK_DECOMPOSITION_FAILURE','error':str(e)}]);(out/'HTS62_EXECUTION_REPORT.md').write_text('# HTS62 execution report\n\n`HOLD_SOURCE_MATERIALIZATION_OR_BLOCK_DECOMPOSITION_FAILURE`\n\n```text\n'+str(e)+'\n```\n');c.make_zip(out,zp);print('HOLD_SOURCE_MATERIALIZATION_OR_BLOCK_DECOMPOSITION_FAILURE');print(zp)
if __name__=='__main__':main()
