#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, shutil, subprocess, sys, traceback
from pathlib import Path
import hts63_common as c
import hts63_metric as g

BURNS=(0.3,0.5); PRIMARY=0.3; SENS=0.5
ORDER=('SPT_BASE','SPT_ACT','SPT_PR4','FULL_ORIGINAL','FULL_FIXED')
DOCS=('CANONICAL_STATE_THROUGH_HTS62.md','HTS62_CANONICALIZATION_AUDIT.md',
      'HTS63_EXECUTION_CONTRACT.md','HTS63_SELECTION_AUDIT.md',
      'HTS63_SOURCE_ADEQUACY_AUDIT.md','HTS63_PREFLIGHT_RESULT.md',
      'HTS63_PREFLIGHT_TEST_AUDIT.md','README_RUN.md')

def main():
    pkg=Path(__file__).resolve().parent
    downloads=Path(os.environ.get('HTS63_DOWNLOADS',str(pkg.parent))).resolve()
    store=Path(os.environ.get('HTS_CACHE_STORE',str(downloads/'HTS_CHAIN_CACHE_STORE'))).resolve()
    stage_cache=Path(os.environ.get('HTS63_CACHE',str(store/'HTS63'))).resolve()
    out=Path(os.environ.get('HTS63_OUTPUT',str(downloads/'HTS63_RESULTS_FOR_REVIEW'))).resolve()
    zp=Path(os.environ.get('HTS63_ZIP_OUTPUT',str(downloads/'HTS63_RESULTS_FOR_REVIEW.zip'))).resolve()
    test=os.environ.get('HTS63_TEST_MODE','0')=='1'
    store.mkdir(parents=True,exist_ok=True); stage_cache.mkdir(parents=True,exist_ok=True)
    shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True)
    try:
        obase,ometa,oprov,oroots=c.materialize_original_factorial(downloads,store,stage_cache,test)
        fbase,fmeta,fprov,froots=c.materialize_fixed_full(downloads,store,stage_cache,test)
        c.write_tsv(out/'HTS63_SOURCE_FREEZE.tsv',[{'source':'ORIGINAL',**ometa},{'source':'FIXED',**fmeta}])
        c.write_tsv(out/'HTS63_SELECTED_MEMBER_PROVENANCE.tsv',oprov+fprov)
        inv=stage_cache/'HTS63_ORIGINAL_ROOT_INVENTORY.tsv'
        if inv.exists(): shutil.copy2(inv,out/inv.name)
        roots={'SPT_BASE':obase/oroots['SPT_BASE'],'SPT_ACT':obase/oroots['SPT_ACT'],
               'SPT_PR4':obase/oroots['SPT_PR4'],'FULL_ORIGINAL':obase/oroots['FULL_ORIGINAL'],
               'FULL_FIXED':fbase/froots['FULL_FIXED']}
        lr,likes,fr,fams,ok,checks,rawchecks=c.factor_contract_rows(roots)
        c.write_tsv(out/'HTS63_LIKELIHOOD_MEMBERSHIP.tsv',lr)
        c.write_tsv(out/'HTS63_SEMANTIC_DATA_FAMILY_MEMBERSHIP.tsv',fr)
        c.write_tsv(out/'HTS63_RELEASE_ENDPOINT_CONTRACT_CHECKS.tsv',checks)
        c.write_tsv(out/'HTS63_RAW_IMPLEMENTATION_DIAGNOSTICS.tsv',rawchecks)
        if not ok: raise RuntimeError('release endpoint semantic contract failed')

        counts={**c.FACTOR_EXPECTED_CHAINS,**c.FACTOR_EXPECTED_CHAINS_FIXED}
        details={}; support=[]; root_json={}
        for burn in BURNS:
            for label in ORDER:
                d,w,ids,h,cols,files=c.load_factor_root(roots[label],counts[label],burn)
                D=g.endpoint_detail(d,w,ids); details[(label,burn)]=D
                support+=g.support_rows(label,burn,D)
                root_json[label]={'path':str(roots[label]),'count':counts[label]}
        c.write_tsv(out/'HTS63_CHAIN_SUPPORT.tsv',support)

        summaries=[]; allocations=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A=details[(frm,burn)]; B=details[(to,burn)]
                for direction,sl,tl,S,T in (('FORWARD',frm,to,A,B),('REVERSE',to,frm,B,A)):
                    s,v=g.directed_variable_allocation(edge,etype,boundary,burn,sl,tl,S,T,direction)
                    summaries.append(s); allocations+=v
        c.write_tsv(out/'HTS63_DIRECTED_VARIABLE_ALLOCATION_SUMMARY.tsv',summaries)
        c.write_tsv(out/'HTS63_DIRECTED_VARIABLE_ALLOCATIONS.tsv',allocations)
        sidx={(r['edge'],r['direction'],r['burn_fraction_per_chain']):r for r in summaries}
        aidx={}
        for r in allocations:
            aidx.setdefault((r['edge'],r['direction'],r['burn_fraction_per_chain']),[]).append(r)

        loo=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A=details[(frm,burn)]; B=details[(to,burn)]
                for direction,sl,tl,S,T in (('FORWARD',frm,to,A,B),('REVERSE',to,frm,B,A)):
                    base=sidx[(edge,direction,burn)]
                    base_rows=aidx[(edge,direction,burn)]
                    bs=g.vector_from_rows(base_rows,'unrestricted_shapley_share')
                    bo=g.vector_from_rows(base_rows,'owen_share')
                    for side,D in (('SOURCE',S),('TARGET',T)):
                        for ch in sorted(set(D['ids'])):
                            sub=g.subset_detail(D,D['ids']!=ch)
                            SS=sub if side=='SOURCE' else S
                            TT=sub if side=='TARGET' else T
                            q,qrows=g.directed_variable_allocation(edge,etype,boundary,burn,sl,tl,SS,TT,direction)
                            qs=g.vector_from_rows(qrows,'unrestricted_shapley_share')
                            qo=g.vector_from_rows(qrows,'owen_share')
                            loo.append({
                                'edge':edge,'direction':direction,'burn_fraction_per_chain':burn,
                                'omission_side':side,'omitted_chain':ch,
                                'conditional4d_mahalanobis_drift':q['conditional4d_mahalanobis']-base['conditional4d_mahalanobis'],
                                'max_unrestricted_shapley_share_drift':float(max(abs(qs-bs))),
                                'max_owen_share_drift':float(max(abs(qo-bo))),
                                'effective_variable_count_shapley_drift':q['effective_variable_count_shapley']-base['effective_variable_count_shapley'],
                                'effective_variable_count_owen_drift':q['effective_variable_count_owen']-base['effective_variable_count_owen'],
                                'max_abs_coalition_shift_drift':q['max_abs_owen_minus_shapley_share']-base['max_abs_owen_minus_shapley_share'],
                                'top_shapley_variable_changed':q['top_shapley_variable']!=base['top_shapley_variable'],
                                'top_owen_variable_changed':q['top_owen_variable']!=base['top_owen_variable'],
                                'max_block_reconciliation_error':max(abs(q['baryon_tilt_block_reconciliation_error']),
                                                                     abs(q['tau_amplitude_block_reconciliation_error'])),
                            })
        c.write_tsv(out/'HTS63_DIRECTED_LOO_STABILITY.tsv',loo)

        sens=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for direction in ('FORWARD','REVERSE'):
                a=sidx[(edge,direction,PRIMARY)]; b=sidx[(edge,direction,SENS)]
                ar=aidx[(edge,direction,PRIMARY)]; br=aidx[(edge,direction,SENS)]
                ass=g.vector_from_rows(ar,'unrestricted_shapley_share')
                bss=g.vector_from_rows(br,'unrestricted_shapley_share')
                ao=g.vector_from_rows(ar,'owen_share'); bo=g.vector_from_rows(br,'owen_share')
                sens.append({
                    'edge':edge,'direction':direction,
                    'conditional4d_mahalanobis_change':b['conditional4d_mahalanobis']-a['conditional4d_mahalanobis'],
                    'max_unrestricted_shapley_share_change':float(max(abs(bss-ass))),
                    'max_owen_share_change':float(max(abs(bo-ao))),
                    'effective_variable_count_shapley_change':b['effective_variable_count_shapley']-a['effective_variable_count_shapley'],
                    'effective_variable_count_owen_change':b['effective_variable_count_owen']-a['effective_variable_count_owen'],
                    'max_abs_coalition_shift_change':b['max_abs_owen_minus_shapley_share']-a['max_abs_owen_minus_shapley_share'],
                    'top_shapley_variable_30':a['top_shapley_variable'],
                    'top_shapley_variable_50':b['top_shapley_variable'],
                    'top_owen_variable_30':a['top_owen_variable'],
                    'top_owen_variable_50':b['top_owen_variable'],
                    'classification_30':a['variable_pattern_classification'],
                    'classification_50':b['variable_pattern_classification'],
                })
        c.write_tsv(out/'HTS63_BURNIN_SENSITIVITY.tsv',sens)

        runtime=stage_cache/'HTS63_RUNTIME_ROOTS.json'
        runtime.write_text(json.dumps(root_json,indent=2)+'\n')
        for name in DOCS: shutil.copy2(pkg/name,out/name)
        proc=subprocess.run([sys.executable,str(pkg/'audit_hts63.py'),
                             '--output-dir',str(out),'--root-json',str(runtime)],
                            capture_output=True,text=True)
        (out/'HTS63_AUDIT_STDOUT.txt').write_text(proc.stdout)
        (out/'HTS63_AUDIT_STDERR.txt').write_text(proc.stderr)
        audit_pass=proc.returncode==0

        ps=[r for r in support if r['burn_fraction_per_chain']==PRIMARY]
        pl=[r for r in loo if r['burn_fraction_per_chain']==PRIMARY]
        min_kish=min(r['kish_effective_rows'] for r in ps)
        max_share=max(r['weight_share'] for r in ps)
        min_eig=min(g.conditional_system(details[(label,burn)]['cov'])['eigvals'][0]
                    for label in ORDER for burn in BURNS)
        max_cond=max(g.conditional_system(details[(label,burn)]['cov'])['condition_number']
                     for label in ORDER for burn in BURNS)
        max_close=max(max(abs(r['shapley_closure_error']),abs(r['owen_closure_error']),
                          abs(r['baryon_tilt_block_reconciliation_error']),
                          abs(r['tau_amplitude_block_reconciliation_error'])) for r in summaries)
        min_marg=min(r['minimum_permutation_marginal_contribution'] for r in summaries)
        max_loo_d=max(abs(r['conditional4d_mahalanobis_drift']) for r in pl)
        max_loo_s=max(r['max_unrestricted_shapley_share_drift'] for r in pl)
        max_loo_o=max(r['max_owen_share_drift'] for r in pl)
        max_loo_eff=max(max(abs(r['effective_variable_count_shapley_drift']),
                            abs(r['effective_variable_count_owen_drift'])) for r in pl)
        max_loo_coal=max(abs(r['max_abs_coalition_shift_drift']) for r in pl)
        max_burn_d=max(abs(r['conditional4d_mahalanobis_change']) for r in sens)
        max_burn_s=max(r['max_unrestricted_shapley_share_change'] for r in sens)
        max_burn_o=max(r['max_owen_share_change'] for r in sens)
        max_burn_eff=max(max(abs(r['effective_variable_count_shapley_change']),
                             abs(r['effective_variable_count_owen_change'])) for r in sens)
        max_burn_coal=max(abs(r['max_abs_coalition_shift_change']) for r in sens)
        gates={
            'support_gate_pass':min_kish>=100 and max_share<=0.35,
            'numerical_allocation_gate_pass':min_eig>1e-6 and max_cond<=500 and max_close<=1e-8 and min_marg>=-1e-8,
            'loo_variable_allocation_gate_pass':max_loo_d<=0.25 and max_loo_s<=0.15 and max_loo_o<=0.15 and max_loo_eff<=0.5 and max_loo_coal<=0.15,
            'burnin_variable_allocation_gate_pass':max_burn_d<=0.25 and max_burn_s<=0.15 and max_burn_o<=0.15 and max_burn_eff<=0.5 and max_burn_coal<=0.15,
            'independent_audit_pass':audit_pass,
        }
        passed=all(gates.values())
        classification='PASS_EXACT_VARIABLE_SHAPLEY_AND_OWEN_COALITION_AUDIT' if passed else 'HOLD_VARIABLE_ALLOCATION_SUPPORT_OR_STABILITY_FAILURE'
        c.write_tsv(out/'HTS63_CLASSIFICATION.tsv',[{
            'classification':classification,
            'min_chain_kish_effective_rows':min_kish,
            'max_chain_weight_share':max_share,
            'min_conditional_correlation_eigenvalue':min_eig,
            'max_conditional_correlation_condition_number':max_cond,
            'max_allocation_closure_or_reconciliation_error':max_close,
            'minimum_permutation_marginal_contribution':min_marg,
            'max_LOO_conditional4d_drift':max_loo_d,
            'max_LOO_unrestricted_shapley_share_drift':max_loo_s,
            'max_LOO_owen_share_drift':max_loo_o,
            'max_LOO_effective_variable_count_drift':max_loo_eff,
            'max_LOO_coalition_shift_drift':max_loo_coal,
            'max_burn_conditional4d_change':max_burn_d,
            'max_burn_unrestricted_shapley_share_change':max_burn_s,
            'max_burn_owen_share_change':max_burn_o,
            'max_burn_effective_variable_count_change':max_burn_eff,
            'max_burn_coalition_shift_change':max_burn_coal,
            **gates,
            'interpretation_boundary':'Coordinate Shapley and Owen values are symmetric posterior-distance bookkeeping, not causal or physical attribution.',
        }])
        (out/'HTS63_EXECUTION_REPORT.md').write_text(
            '# HTS63 execution report\n\n`'+classification+'`\n\n'
            'HTS63 compares exact unrestricted four-variable Shapley allocations with '
            'coalition-respecting Owen allocations for the two fixed HTS62 coordinate blocks.\n')
        (out/'MANIFEST.json').write_text(json.dumps({
            'stage':'HTS63','classification':classification,'primary_burn':PRIMARY,
            'sensitivity_burn':SENS,'variables':list(g.AUX),'blocks':g.BLOCKS,
            'cache_store':str(store),
            'boundary':'Exact coordinate-allocation diagnostics only.'
        },indent=2)+'\n')
        c.make_zip(out,zp)
        print(classification); print(zp)
    except Exception as e:
        (out/'HTS63_RUNTIME_FAILURE.txt').write_text(traceback.format_exc())
        for name in DOCS:
            if (pkg/name).exists(): shutil.copy2(pkg/name,out/name)
        c.write_tsv(out/'HTS63_CLASSIFICATION.tsv',[{
            'classification':'HOLD_SOURCE_MATERIALIZATION_OR_VARIABLE_ALLOCATION_FAILURE',
            'error':str(e)}])
        (out/'HTS63_EXECUTION_REPORT.md').write_text(
            '# HTS63 execution report\n\n'
            '`HOLD_SOURCE_MATERIALIZATION_OR_VARIABLE_ALLOCATION_FAILURE`\n\n'
            f'```text\n{e}\n```\n')
        c.make_zip(out,zp)
        print('HOLD_SOURCE_MATERIALIZATION_OR_VARIABLE_ALLOCATION_FAILURE'); print(zp)

if __name__=='__main__':
    main()
