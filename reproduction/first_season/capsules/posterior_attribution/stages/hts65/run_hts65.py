#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, shutil, subprocess, sys, traceback
from pathlib import Path
import hts65_common as c
import hts65_metric as g

BURNS=(0.3,0.5)
PRIMARY=0.3
SENS=0.5
ORDER=('SPT_BASE','SPT_ACT','SPT_PR4','FULL_ORIGINAL','FULL_FIXED')
DOCS=('CANONICAL_STATE_THROUGH_HTS64.md','HTS64_CANONICALIZATION_AUDIT.md',
      'HTS65_EXECUTION_CONTRACT.md','HTS65_SELECTION_AUDIT.md',
      'HTS65_SOURCE_ADEQUACY_AUDIT.md','HTS65_PREFLIGHT_RESULT.md',
      'HTS65_PREFLIGHT_TEST_AUDIT.md','README_RUN.md')

def main():
    pkg=Path(__file__).resolve().parent
    downloads=Path(os.environ.get('HTS65_DOWNLOADS',str(pkg.parent))).resolve()
    store=Path(os.environ.get('HTS_CACHE_STORE',str(downloads/'HTS_CHAIN_CACHE_STORE'))).resolve()
    stage_cache=Path(os.environ.get('HTS65_CACHE',str(store/'HTS65'))).resolve()
    out=Path(os.environ.get('HTS65_OUTPUT',str(downloads/'HTS65_RESULTS_FOR_REVIEW'))).resolve()
    zp=Path(os.environ.get('HTS65_ZIP_OUTPUT',str(downloads/'HTS65_RESULTS_FOR_REVIEW.zip'))).resolve()
    test=os.environ.get('HTS65_TEST_MODE','0')=='1'
    store.mkdir(parents=True,exist_ok=True)
    stage_cache.mkdir(parents=True,exist_ok=True)
    shutil.rmtree(out,ignore_errors=True)
    out.mkdir(parents=True)
    try:
        obase,ometa,oprov,oroots=c.materialize_original_factorial(downloads,store,stage_cache,test)
        fbase,fmeta,fprov,froots=c.materialize_fixed_full(downloads,store,stage_cache,test)
        c.write_tsv(out/'HTS65_SOURCE_FREEZE.tsv',[{'source':'ORIGINAL',**ometa},{'source':'FIXED',**fmeta}])
        c.write_tsv(out/'HTS65_SELECTED_MEMBER_PROVENANCE.tsv',oprov+fprov)
        inv=stage_cache/'HTS65_ORIGINAL_ROOT_INVENTORY.tsv'
        if inv.exists(): shutil.copy2(inv,out/inv.name)
        roots={
            'SPT_BASE':obase/oroots['SPT_BASE'],
            'SPT_ACT':obase/oroots['SPT_ACT'],
            'SPT_PR4':obase/oroots['SPT_PR4'],
            'FULL_ORIGINAL':obase/oroots['FULL_ORIGINAL'],
            'FULL_FIXED':fbase/froots['FULL_FIXED'],
        }
        lr,likes,fr,fams,ok,checks,rawchecks=c.factor_contract_rows(roots)
        c.write_tsv(out/'HTS65_LIKELIHOOD_MEMBERSHIP.tsv',lr)
        c.write_tsv(out/'HTS65_SEMANTIC_DATA_FAMILY_MEMBERSHIP.tsv',fr)
        c.write_tsv(out/'HTS65_RELEASE_ENDPOINT_CONTRACT_CHECKS.tsv',checks)
        c.write_tsv(out/'HTS65_RAW_IMPLEMENTATION_DIAGNOSTICS.tsv',rawchecks)
        if not ok: raise RuntimeError('release endpoint semantic contract failed')
        c.write_tsv(out/'HTS65_PARTITION_CATALOG.tsv',g.partition_catalog_rows())

        counts={**c.FACTOR_EXPECTED_CHAINS,**c.FACTOR_EXPECTED_CHAINS_FIXED}
        details={}
        support=[]
        root_json={}
        for burn in BURNS:
            for label in ORDER:
                d,w,ids,h,cols,files=c.load_factor_root(roots[label],counts[label],burn)
                D=g.endpoint_detail(d,w,ids)
                details[(label,burn)]=D
                support+=g.support_rows(label,burn,D)
                root_json[label]={'path':str(roots[label]),'count':counts[label]}
        c.write_tsv(out/'HTS65_CHAIN_SUPPORT.tsv',support)

        summaries=[]
        partitions=[]
        variables=[]
        blocks=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A=details[(frm,burn)]
                B=details[(to,burn)]
                for direction,sl,tl,S,T in (
                    ('FORWARD',frm,to,A,B),
                    ('REVERSE',to,frm,B,A),
                ):
                    s,p,v,b=g.directed_partition_audit(edge,etype,boundary,burn,sl,tl,S,T,direction)
                    summaries.append(s); partitions+=p; variables+=v; blocks+=b
        c.write_tsv(out/'HTS65_DIRECTED_PARTITION_SUMMARY.tsv',summaries)
        c.write_tsv(out/'HTS65_DIRECTED_PARTITION_RESULTS.tsv',partitions)
        c.write_tsv(out/'HTS65_DIRECTED_PARTITION_VARIABLE_ALLOCATIONS.tsv',variables)
        c.write_tsv(out/'HTS65_DIRECTED_PARTITION_BLOCK_ALLOCATIONS.tsv',blocks)
        sidx={(r['edge'],r['direction'],r['burn_fraction_per_chain']):r for r in summaries}

        loo=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A=details[(frm,burn)]
                B=details[(to,burn)]
                for direction,sl,tl,S,T in (
                    ('FORWARD',frm,to,A,B),
                    ('REVERSE',to,frm,B,A),
                ):
                    base=sidx[(edge,direction,burn)]
                    for side,D in (('SOURCE',S),('TARGET',T)):
                        for ch in sorted(set(D['ids'])):
                            sub=g.subset_detail(D,D['ids']!=ch)
                            SS=sub if side=='SOURCE' else S
                            TT=sub if side=='TARGET' else T
                            q,_,_,_=g.directed_partition_audit(edge,etype,boundary,burn,sl,tl,SS,TT,direction)
                            loo.append({
                                'edge':edge,'direction':direction,'burn_fraction_per_chain':burn,
                                'omission_side':side,'omitted_chain':ch,
                                'conditional4d_mahalanobis_drift':q['conditional4d_mahalanobis']-base['conditional4d_mahalanobis'],
                                'max_variable_share_range_drift':q['max_variable_owen_share_range_across_partitions']-base['max_variable_owen_share_range_across_partitions'],
                                'partition_effective_count_range_drift':q['partition_effective_count_range']-base['partition_effective_count_range'],
                                'max_partition_shift_drift':q['max_abs_partition_owen_minus_shapley_share']-base['max_abs_partition_owen_minus_shapley_share'],
                                'canonical_partition_top_share_drift':q['canonical_partition_top_share']-base['canonical_partition_top_share'],
                                'canonical_partition_top_variable_changed':q['canonical_partition_top_variable']!=base['canonical_partition_top_variable'],
                            })
        c.write_tsv(out/'HTS65_DIRECTED_LOO_STABILITY.tsv',loo)

        sens=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for direction in ('FORWARD','REVERSE'):
                a=sidx[(edge,direction,PRIMARY)]
                b=sidx[(edge,direction,SENS)]
                sens.append({
                    'edge':edge,'direction':direction,
                    'conditional4d_mahalanobis_change':b['conditional4d_mahalanobis']-a['conditional4d_mahalanobis'],
                    'max_variable_share_range_change':b['max_variable_owen_share_range_across_partitions']-a['max_variable_owen_share_range_across_partitions'],
                    'partition_effective_count_range_change':b['partition_effective_count_range']-a['partition_effective_count_range'],
                    'max_partition_shift_change':b['max_abs_partition_owen_minus_shapley_share']-a['max_abs_partition_owen_minus_shapley_share'],
                    'canonical_partition_top_share_change':b['canonical_partition_top_share']-a['canonical_partition_top_share'],
                    'classification_30':a['partition_sensitivity_classification'],
                    'classification_50':b['partition_sensitivity_classification'],
                })
        c.write_tsv(out/'HTS65_BURNIN_SENSITIVITY.tsv',sens)

        runtime=stage_cache/'HTS65_RUNTIME_ROOTS.json'
        runtime.write_text(json.dumps(root_json,indent=2)+'\n')
        for name in DOCS: shutil.copy2(pkg/name,out/name)
        proc=subprocess.run(
            [sys.executable,str(pkg/'audit_hts65.py'),'--output-dir',str(out),'--root-json',str(runtime)],
            capture_output=True,text=True
        )
        (out/'HTS65_AUDIT_STDOUT.txt').write_text(proc.stdout)
        (out/'HTS65_AUDIT_STDERR.txt').write_text(proc.stderr)
        audit_pass=proc.returncode==0

        ps=[r for r in support if r['burn_fraction_per_chain']==PRIMARY]
        pl=[r for r in loo if r['burn_fraction_per_chain']==PRIMARY]
        min_kish=min(r['kish_effective_rows'] for r in ps)
        max_share=max(r['weight_share'] for r in ps)
        min_eig=min(r['min_conditional_correlation_eigenvalue'] for r in summaries)
        max_cond=max(r['conditional_correlation_condition_number'] for r in summaries)
        min_marg=min(r['minimum_respecting_order_marginal_contribution'] for r in summaries)
        max_close=max(max(r['max_owen_closure_error'],r['max_partition_block_reconciliation_error']) for r in summaries)
        max_loo_d=max(abs(r['conditional4d_mahalanobis_drift']) for r in pl)
        max_loo_range=max(abs(r['max_variable_share_range_drift']) for r in pl)
        max_loo_eff=max(abs(r['partition_effective_count_range_drift']) for r in pl)
        max_loo_shift=max(abs(r['max_partition_shift_drift']) for r in pl)
        max_loo_canon=max(abs(r['canonical_partition_top_share_drift']) for r in pl)
        max_burn_d=max(abs(r['conditional4d_mahalanobis_change']) for r in sens)
        max_burn_range=max(abs(r['max_variable_share_range_change']) for r in sens)
        max_burn_eff=max(abs(r['partition_effective_count_range_change']) for r in sens)
        max_burn_shift=max(abs(r['max_partition_shift_change']) for r in sens)
        max_burn_canon=max(abs(r['canonical_partition_top_share_change']) for r in sens)
        gates={
            'support_gate_pass':min_kish>=100 and max_share<=0.35,
            'numerical_partition_gate_pass':min_eig>1e-6 and max_cond<=500 and min_marg>=-1e-8 and max_close<=1e-8 and len(g.PARTITIONS)==15,
            'loo_partition_gate_pass':max_loo_d<=0.25 and max_loo_range<=0.15 and max_loo_eff<=0.5 and max_loo_shift<=0.15 and max_loo_canon<=0.15,
            'burnin_partition_gate_pass':max_burn_d<=0.25 and max_burn_range<=0.15 and max_burn_eff<=0.5 and max_burn_shift<=0.15 and max_burn_canon<=0.15,
            'independent_audit_pass':audit_pass,
        }
        passed=all(gates.values())
        classification='PASS_EXHAUSTIVE_COALITION_PARTITION_SENSITIVITY_AUDIT' if passed else 'HOLD_PARTITION_NUMERICAL_OR_STABILITY_FAILURE'
        c.write_tsv(out/'HTS65_CLASSIFICATION.tsv',[{
            'classification':classification,
            'partition_count':len(g.PARTITIONS),
            'min_chain_kish_effective_rows':min_kish,
            'max_chain_weight_share':max_share,
            'min_conditional_correlation_eigenvalue':min_eig,
            'max_conditional_correlation_condition_number':max_cond,
            'minimum_respecting_order_marginal_contribution':min_marg,
            'max_owen_closure_or_block_reconciliation_error':max_close,
            'max_LOO_conditional4d_drift':max_loo_d,
            'max_LOO_variable_share_range_drift':max_loo_range,
            'max_LOO_effective_count_range_drift':max_loo_eff,
            'max_LOO_partition_shift_drift':max_loo_shift,
            'max_LOO_canonical_top_share_drift':max_loo_canon,
            'max_burn_conditional4d_change':max_burn_d,
            'max_burn_variable_share_range_change':max_burn_range,
            'max_burn_effective_count_range_change':max_burn_eff,
            'max_burn_partition_shift_change':max_burn_shift,
            'max_burn_canonical_top_share_change':max_burn_canon,
            **gates,
            'interpretation_boundary':'Exhaustive coalition-partition dependence is posterior-distance bookkeeping; alternative partitions are robustness probes, not equally physical models.',
        }])
        (out/'HTS65_EXECUTION_REPORT.md').write_text(
            '# HTS65 execution report\n\n`'+classification+'`\n\n'
            'HTS65 exhaustively enumerates all 15 set partitions of the four fixed conditional '
            'coordinates and recomputes coalition-respecting Owen allocations. The audit tests '
            'coalition-structure dependence without treating arbitrary partitions as physical sectors.\n'
        )
        (out/'MANIFEST.json').write_text(json.dumps({
            'stage':'HTS65','classification':classification,
            'primary_burn':PRIMARY,'sensitivity_burn':SENS,
            'partition_count':len(g.PARTITIONS),
            'canonical_partition':g.partition_string(g.CANONICAL_PARTITION),
            'cache_store':str(store),
            'boundary':'Coalition partition sensitivity of coordinate allocations only.'
        },indent=2)+'\n')
        c.make_zip(out,zp)
        print(classification)
        print(zp)
    except Exception as e:
        (out/'HTS65_RUNTIME_FAILURE.txt').write_text(traceback.format_exc())
        for name in DOCS:
            if (pkg/name).exists(): shutil.copy2(pkg/name,out/name)
        c.write_tsv(out/'HTS65_CLASSIFICATION.tsv',[{
            'classification':'HOLD_SOURCE_MATERIALIZATION_OR_PARTITION_AUDIT_FAILURE',
            'error':str(e),
        }])
        (out/'HTS65_EXECUTION_REPORT.md').write_text(
            '# HTS65 execution report\n\n'
            '`HOLD_SOURCE_MATERIALIZATION_OR_PARTITION_AUDIT_FAILURE`\n\n'
            f'```text\n{e}\n```\n'
        )
        c.make_zip(out,zp)
        print('HOLD_SOURCE_MATERIALIZATION_OR_PARTITION_AUDIT_FAILURE')
        print(zp)

if __name__=='__main__':
    main()
