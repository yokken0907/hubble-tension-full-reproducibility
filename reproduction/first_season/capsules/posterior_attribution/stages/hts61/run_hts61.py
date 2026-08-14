#!/usr/bin/env python3
from __future__ import annotations
import json,math,os,shutil,subprocess,sys,traceback
from pathlib import Path
import hts61_common as c
import hts61_metric as g
BURNS=(0.3,0.5);PRIMARY=0.3;SENS=0.5
ORDER=('SPT_BASE','SPT_ACT','SPT_PR4','FULL_ORIGINAL','FULL_FIXED')
DOCS=('CANONICAL_STATE_THROUGH_HTS60.md','HTS60_CANONICALIZATION_AUDIT.md','HTS61_EXECUTION_CONTRACT.md','HTS61_SELECTION_AUDIT.md','HTS61_SOURCE_ADEQUACY_AUDIT.md','HTS61_PREFLIGHT_RESULT.md','HTS61_PREFLIGHT_TEST_AUDIT.md','README_RUN.md')
def main():
 pkg=Path(__file__).resolve().parent;downloads=Path(os.environ.get('HTS61_DOWNLOADS',str(pkg.parent))).resolve();store=Path(os.environ.get('HTS_CACHE_STORE',str(downloads/'HTS_CHAIN_CACHE_STORE'))).resolve();stage_cache=Path(os.environ.get('HTS61_CACHE',str(store/'HTS61'))).resolve();out=Path(os.environ.get('HTS61_OUTPUT',str(downloads/'HTS61_RESULTS_FOR_REVIEW'))).resolve();zp=Path(os.environ.get('HTS61_ZIP_OUTPUT',str(downloads/'HTS61_RESULTS_FOR_REVIEW.zip'))).resolve();test=os.environ.get('HTS61_TEST_MODE','0')=='1'
 store.mkdir(parents=True,exist_ok=True);stage_cache.mkdir(parents=True,exist_ok=True);shutil.rmtree(out,ignore_errors=True);out.mkdir(parents=True)
 try:
  obase,ometa,oprov,oroots=c.materialize_original_factorial(downloads,store,stage_cache,test);fbase,fmeta,fprov,froots=c.materialize_fixed_full(downloads,store,stage_cache,test)
  c.write_tsv(out/'HTS61_SOURCE_FREEZE.tsv',[{'source':'ORIGINAL',**ometa},{'source':'FIXED',**fmeta}]);c.write_tsv(out/'HTS61_SELECTED_MEMBER_PROVENANCE.tsv',oprov+fprov)
  inv=stage_cache/'HTS61_ORIGINAL_ROOT_INVENTORY.tsv'
  if inv.exists():shutil.copy2(inv,out/inv.name)
  roots={'SPT_BASE':obase/oroots['SPT_BASE'],'SPT_ACT':obase/oroots['SPT_ACT'],'SPT_PR4':obase/oroots['SPT_PR4'],'FULL_ORIGINAL':obase/oroots['FULL_ORIGINAL'],'FULL_FIXED':fbase/froots['FULL_FIXED']}
  lr,likes,fr,fams,ok,checks,raw=c.factor_contract_rows(roots);c.write_tsv(out/'HTS61_LIKELIHOOD_MEMBERSHIP.tsv',lr);c.write_tsv(out/'HTS61_SEMANTIC_DATA_FAMILY_MEMBERSHIP.tsv',fr);c.write_tsv(out/'HTS61_RELEASE_ENDPOINT_CONTRACT_CHECKS.tsv',checks);c.write_tsv(out/'HTS61_RAW_IMPLEMENTATION_DIAGNOSTICS.tsv',raw)
  if not ok:raise RuntimeError('release endpoint semantic contract failed')
  counts={**c.FACTOR_EXPECTED_CHAINS,**c.FACTOR_EXPECTED_CHAINS_FIXED};D={};support=[];modes=[];blocks=[];root_json={}
  for burn in BURNS:
   for label in ORDER:
    d,w,ids,h,cols,files=c.load_factor_root(roots[label],counts[label],burn);q=g.endpoint_detail(d,w,ids);D[(label,burn)]=q;support+=g.support_rows(label,burn,q);modes+=g.mode_rows(label,burn,q);blocks+=g.block_rows(label,burn,q);root_json[label]={'path':str(roots[label]),'count':counts[label]}
  c.write_tsv(out/'HTS61_CHAIN_SUPPORT.tsv',support);c.write_tsv(out/'HTS61_ENDPOINT_MODE_IDENTIFIABILITY.tsv',modes);c.write_tsv(out/'HTS61_ENDPOINT_BLOCK_SUBSPACE.tsv',blocks)
  loo_mode=[];loo_cluster=[];loo_block=[]
  for burn in BURNS:
   for label in ORDER:
    base=D[(label,burn)]
    for ch in sorted(set(base['ids'])):
     a,b,cc=g.perturbation_rows(label,burn,'LOO:'+ch,base,g.subset_detail(base,base['ids']!=ch));loo_mode+=a;loo_cluster+=b;loo_block+=cc
  c.write_tsv(out/'HTS61_ENDPOINT_LOO_MODE_STABILITY.tsv',loo_mode);c.write_tsv(out/'HTS61_ENDPOINT_LOO_CLUSTER_STABILITY.tsv',loo_cluster);c.write_tsv(out/'HTS61_ENDPOINT_LOO_BLOCK_STABILITY.tsv',loo_block)
  burn_mode=[];burn_cluster=[];burn_block=[]
  for label in ORDER:
   a,b,cc=g.perturbation_rows(label,PRIMARY,'BURN_30_TO_50',D[(label,PRIMARY)],D[(label,SENS)]);burn_mode+=a;burn_cluster+=b;burn_block+=cc
  c.write_tsv(out/'HTS61_BURNIN_MODE_STABILITY.tsv',burn_mode);c.write_tsv(out/'HTS61_BURNIN_CLUSTER_STABILITY.tsv',burn_cluster);c.write_tsv(out/'HTS61_BURNIN_BLOCK_STABILITY.tsv',burn_block)
  cross=[]
  for burn in BURNS:
   for i,a in enumerate(ORDER):
    for b in ORDER[i+1:]:
     for block,idx in g.BLOCKS.items():
      qa=g.block_subspace(D[(a,burn)]['basis']['eigvecs'],idx);qb=g.block_subspace(D[(b,burn)]['basis']['eigvecs'],idx);ang=g.subspace_angles_deg(qa['U'],qb['U']);cross.append({'endpoint_a':a,'endpoint_b':b,'burn_fraction_per_chain':burn,'block':block,'a_selected_modes':','.join(str(x+1) for x in qa['subset']),'b_selected_modes':','.join(str(x+1) for x in qb['subset']),'principal_angle_min_deg':float(min(ang)),'principal_angle_max_deg':float(max(ang))})
  c.write_tsv(out/'HTS61_CROSS_ENDPOINT_BLOCK_ALIGNMENT.tsv',cross)
  edge_rows=[]
  for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
   for burn in BURNS:
    for direction,sl,tl,A,B in (('FORWARD',frm,to,D[(frm,burn)],D[(to,burn)]),('REVERSE',to,frm,D[(to,burn)],D[(frm,burn)])):edge_rows.append(g.directed_contribution(edge,etype,boundary,burn,sl,tl,A,B,direction))
  c.write_tsv(out/'HTS61_EDGE_CONTRIBUTION_IDENTIFIABILITY.tsv',edge_rows)
  runtime=stage_cache/'HTS61_RUNTIME_ROOTS.json';runtime.write_text(json.dumps(root_json,indent=2)+'\n')
  for name in DOCS:shutil.copy2(pkg/name,out/name)
  proc=subprocess.run([sys.executable,str(pkg/'audit_hts61.py'),'--output-dir',str(out),'--root-json',str(runtime)],capture_output=True,text=True);(out/'HTS61_AUDIT_STDOUT.txt').write_text(proc.stdout);(out/'HTS61_AUDIT_STDERR.txt').write_text(proc.stderr);audit_pass=proc.returncode==0
  ps=[r for r in support if r['burn_fraction_per_chain']==PRIMARY];pm=[r for r in loo_mode if r['burn_fraction_per_chain']==PRIMARY and r['baseline_cluster_size']==1];pc=[r for r in loo_cluster if r['burn_fraction_per_chain']==PRIMARY and r['cluster_size']>1];pb=[r for r in loo_block if r['burn_fraction_per_chain']==PRIMARY];bm=[r for r in burn_mode if r['baseline_cluster_size']==1];bc=[r for r in burn_cluster if r['cluster_size']>1]
  min_kish=min(r['kish_effective_rows'] for r in ps);max_share=max(r['weight_share'] for r in ps);min_eig=min(r['conditional_correlation_eigenvalue'] for r in modes);max_cond=max(D[(l,b)]['basis']['condition_number'] for l in ORDER for b in BURNS);max_loo_single=max([abs(r['matched_angle_deg']) for r in pm] or [0]);max_loo_cluster=max([abs(r['principal_angle_max_deg']) for r in pc] or [0]);max_loo_block=max(abs(r['principal_angle_max_deg']) for r in pb);max_burn_single=max([abs(r['matched_angle_deg']) for r in bm] or [0]);max_burn_cluster=max([abs(r['principal_angle_max_deg']) for r in bc] or [0]);max_burn_block=max(abs(r['principal_angle_max_deg']) for r in burn_block)
  block_partition=True
  for label in ORDER:
   for burn in BURNS:
    rr=[r for r in blocks if r['contract']==label and r['burn_fraction_per_chain']==burn];sets=[set(int(x) for x in r['selected_modes'].split(',')) for r in rr];block_partition &= len(sets)==2 and not (sets[0]&sets[1]) and (sets[0]|sets[1])=={1,2,3,4}
  gates={'support_gate_pass':min_kish>=100 and max_share<=0.35,'numerical_eigensystem_gate_pass':min_eig>1e-6 and max_cond<=500,'block_partition_gate_pass':block_partition,'loo_identifiability_gate_pass':max_loo_single<=10 and max_loo_cluster<=8 and max_loo_block<=8,'burnin_identifiability_gate_pass':max_burn_single<=10 and max_burn_cluster<=8 and max_burn_block<=8,'independent_audit_pass':audit_pass};passed=all(gates.values());classification='PASS_CONDITIONAL_EIGENMODE_IDENTIFIABILITY_AND_SUBSPACE_STABILITY_AUDIT' if passed else 'HOLD_EIGENMODE_IDENTIFIABILITY_OR_SUBSPACE_STABILITY_FAILURE'
  c.write_tsv(out/'HTS61_CLASSIFICATION.tsv',[{'classification':classification,'gap_cluster_threshold':g.GAP_THRESHOLD,'min_chain_kish_effective_rows':min_kish,'max_chain_weight_share':max_share,'min_conditional_eigenvalue':min_eig,'max_conditional_condition_number':max_cond,'max_LOO_singleton_mode_angle_deg':max_loo_single,'max_LOO_degenerate_cluster_angle_deg':max_loo_cluster,'max_LOO_block_subspace_angle_deg':max_loo_block,'max_burn_singleton_mode_angle_deg':max_burn_single,'max_burn_degenerate_cluster_angle_deg':max_burn_cluster,'max_burn_block_subspace_angle_deg':max_burn_block,**gates,'interpretation_boundary':'Mode labels require eigengap support; near-degenerate modes are interpreted only as subspaces, not unique physical directions.'}]);(out/'HTS61_EXECUTION_REPORT.md').write_text('# HTS61 execution report\n\n`'+classification+'`\n\nHTS61 audits whether HTS60 conditional eigenmodes are individually identifiable or only stable as near-degenerate subspaces.\n');(out/'MANIFEST.json').write_text(json.dumps({'stage':'HTS61','classification':classification,'gap_threshold':g.GAP_THRESHOLD,'cache_store':str(store),'boundary':'Conditional posterior eigensystem identifiability only.'},indent=2)+'\n');c.make_zip(out,zp);print(classification);print(zp)
 except Exception as e:
  (out/'HTS61_RUNTIME_FAILURE.txt').write_text(traceback.format_exc())
  for name in DOCS:
   if (pkg/name).exists():shutil.copy2(pkg/name,out/name)
  c.write_tsv(out/'HTS61_CLASSIFICATION.tsv',[{'classification':'HOLD_SOURCE_MATERIALIZATION_OR_IDENTIFIABILITY_AUDIT_FAILURE','error':str(e)}]);(out/'HTS61_EXECUTION_REPORT.md').write_text('# HTS61 execution report\n\n`HOLD_SOURCE_MATERIALIZATION_OR_IDENTIFIABILITY_AUDIT_FAILURE`\n\n```text\n'+str(e)+'\n```\n');c.make_zip(out,zp);print('HOLD_SOURCE_MATERIALIZATION_OR_IDENTIFIABILITY_AUDIT_FAILURE');print(zp)
if __name__=='__main__':main()
