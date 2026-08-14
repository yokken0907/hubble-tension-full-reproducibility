#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, shutil, subprocess, sys, traceback
from pathlib import Path
import hts64_common as c
import hts64_metric as g

BURNS=(0.3,0.5)
PRIMARY=0.3
SENS=0.5
ORDER=('SPT_BASE','SPT_ACT','SPT_PR4','FULL_ORIGINAL','FULL_FIXED')
DOCS=('CANONICAL_STATE_THROUGH_HTS63.md','HTS63_CANONICALIZATION_AUDIT.md',
      'HTS64_EXECUTION_CONTRACT.md','HTS64_SELECTION_AUDIT.md',
      'HTS64_SOURCE_ADEQUACY_AUDIT.md','HTS64_PREFLIGHT_RESULT.md',
      'HTS64_PREFLIGHT_TEST_AUDIT.md','README_RUN.md')

def main():
    pkg=Path(__file__).resolve().parent
    downloads=Path(os.environ.get('HTS64_DOWNLOADS',str(pkg.parent))).resolve()
    store=Path(os.environ.get('HTS_CACHE_STORE',str(downloads/'HTS_CHAIN_CACHE_STORE'))).resolve()
    stage_cache=Path(os.environ.get('HTS64_CACHE',str(store/'HTS64'))).resolve()
    out=Path(os.environ.get('HTS64_OUTPUT',str(downloads/'HTS64_RESULTS_FOR_REVIEW'))).resolve()
    zp=Path(os.environ.get('HTS64_ZIP_OUTPUT',str(downloads/'HTS64_RESULTS_FOR_REVIEW.zip'))).resolve()
    test=os.environ.get('HTS64_TEST_MODE','0')=='1'
    store.mkdir(parents=True,exist_ok=True)
    stage_cache.mkdir(parents=True,exist_ok=True)
    shutil.rmtree(out,ignore_errors=True)
    out.mkdir(parents=True)
    try:
        obase,ometa,oprov,oroots=c.materialize_original_factorial(downloads,store,stage_cache,test)
        fbase,fmeta,fprov,froots=c.materialize_fixed_full(downloads,store,stage_cache,test)
        c.write_tsv(out/'HTS64_SOURCE_FREEZE.tsv',[{'source':'ORIGINAL',**ometa},{'source':'FIXED',**fmeta}])
        c.write_tsv(out/'HTS64_SELECTED_MEMBER_PROVENANCE.tsv',oprov+fprov)
        inv=stage_cache/'HTS64_ORIGINAL_ROOT_INVENTORY.tsv'
        if inv.exists():
            shutil.copy2(inv,out/inv.name)
        roots={
            'SPT_BASE':obase/oroots['SPT_BASE'],
            'SPT_ACT':obase/oroots['SPT_ACT'],
            'SPT_PR4':obase/oroots['SPT_PR4'],
            'FULL_ORIGINAL':obase/oroots['FULL_ORIGINAL'],
            'FULL_FIXED':fbase/froots['FULL_FIXED'],
        }
        lr,likes,fr,fams,ok,checks,rawchecks=c.factor_contract_rows(roots)
        c.write_tsv(out/'HTS64_LIKELIHOOD_MEMBERSHIP.tsv',lr)
        c.write_tsv(out/'HTS64_SEMANTIC_DATA_FAMILY_MEMBERSHIP.tsv',fr)
        c.write_tsv(out/'HTS64_RELEASE_ENDPOINT_CONTRACT_CHECKS.tsv',checks)
        c.write_tsv(out/'HTS64_RAW_IMPLEMENTATION_DIAGNOSTICS.tsv',rawchecks)
        if not ok:
            raise RuntimeError('release endpoint semantic contract failed')

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
        c.write_tsv(out/'HTS64_CHAIN_SUPPORT.tsv',support)

        summaries=[]
        grid=[]
        coords=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A=details[(frm,burn)]
                B=details[(to,burn)]
                for direction,sl,tl,S,T in (
                    ('FORWARD',frm,to,A,B),
                    ('REVERSE',to,frm,B,A),
                ):
                    s,r,q=g.directed_rotation_audit(edge,etype,boundary,burn,sl,tl,S,T,direction)
                    summaries.append(s)
                    grid+=r
                    coords+=q
        c.write_tsv(out/'HTS64_REPARAMETERIZATION_SUMMARY.tsv',summaries)
        c.write_tsv(out/'HTS64_ROTATION_GRID.tsv',grid)
        c.write_tsv(out/'HTS64_ROTATED_COORDINATE_ALLOCATIONS.tsv',coords)
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
                            q,_,_=g.directed_rotation_audit(edge,etype,boundary,burn,sl,tl,SS,TT,direction)
                            loo.append({
                                'edge':edge,'direction':direction,'burn_fraction_per_chain':burn,
                                'omission_side':side,'omitted_chain':ch,
                                'conditional4d_mahalanobis_drift':q['conditional4d_mahalanobis']-base['conditional4d_mahalanobis'],
                                'rotation_top_share_range_drift':q['rotation_grid_top_share_range']-base['rotation_grid_top_share_range'],
                                'rotation_effective_count_range_drift':q['rotation_grid_effective_count_range']-base['rotation_grid_effective_count_range'],
                                'physical_amplitude_top_share_drift':q['physical_amplitude_top_shapley_share']-base['physical_amplitude_top_shapley_share'],
                                'max_total_distance_invariance_error':q['max_total_distance_invariance_error'],
                                'max_block_share_invariance_error':q['max_block_share_invariance_error'],
                            })
        c.write_tsv(out/'HTS64_DIRECTED_LOO_STABILITY.tsv',loo)

        sens=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for direction in ('FORWARD','REVERSE'):
                a=sidx[(edge,direction,PRIMARY)]
                b=sidx[(edge,direction,SENS)]
                sens.append({
                    'edge':edge,'direction':direction,
                    'conditional4d_mahalanobis_change':b['conditional4d_mahalanobis']-a['conditional4d_mahalanobis'],
                    'rotation_top_share_range_change':b['rotation_grid_top_share_range']-a['rotation_grid_top_share_range'],
                    'rotation_effective_count_range_change':b['rotation_grid_effective_count_range']-a['rotation_grid_effective_count_range'],
                    'physical_amplitude_top_share_change':b['physical_amplitude_top_shapley_share']-a['physical_amplitude_top_shapley_share'],
                    'classification_30':a['reparameterization_classification'],
                    'classification_50':b['reparameterization_classification'],
                })
        c.write_tsv(out/'HTS64_BURNIN_SENSITIVITY.tsv',sens)

        runtime=stage_cache/'HTS64_RUNTIME_ROOTS.json'
        runtime.write_text(json.dumps(root_json,indent=2)+'\n')
        for name in DOCS:
            shutil.copy2(pkg/name,out/name)
        proc=subprocess.run(
            [sys.executable,str(pkg/'audit_hts64.py'),'--output-dir',str(out),'--root-json',str(runtime)],
            capture_output=True,text=True
        )
        (out/'HTS64_AUDIT_STDOUT.txt').write_text(proc.stdout)
        (out/'HTS64_AUDIT_STDERR.txt').write_text(proc.stderr)
        audit_pass=proc.returncode==0

        ps=[r for r in support if r['burn_fraction_per_chain']==PRIMARY]
        pl=[r for r in loo if r['burn_fraction_per_chain']==PRIMARY]
        min_kish=min(r['kish_effective_rows'] for r in ps)
        max_share=max(r['weight_share'] for r in ps)
        max_total=max(r['max_total_distance_invariance_error'] for r in summaries)
        max_block=max(r['max_block_share_invariance_error'] for r in summaries)
        min_eig=min(r['minimum_transformed_correlation_eigenvalue'] for r in summaries)
        max_cond=max(r['maximum_transformed_condition_number'] for r in summaries)
        min_marg=min(r['minimum_permutation_marginal_contribution'] for r in summaries)
        max_close=max(r['max_allocation_closure_error'] for r in summaries)
        max_loo_d=max(abs(r['conditional4d_mahalanobis_drift']) for r in pl)
        max_loo_range=max(abs(r['rotation_top_share_range_drift']) for r in pl)
        max_loo_eff=max(abs(r['rotation_effective_count_range_drift']) for r in pl)
        max_loo_phys=max(abs(r['physical_amplitude_top_share_drift']) for r in pl)
        max_burn_d=max(abs(r['conditional4d_mahalanobis_change']) for r in sens)
        max_burn_range=max(abs(r['rotation_top_share_range_change']) for r in sens)
        max_burn_eff=max(abs(r['rotation_effective_count_range_change']) for r in sens)
        max_burn_phys=max(abs(r['physical_amplitude_top_share_change']) for r in sens)
        gates={
            'support_gate_pass':min_kish>=100 and max_share<=0.35,
            'numerical_invariance_gate_pass':max_total<=1e-8 and max_block<=1e-8 and min_eig>1e-6 and max_cond<=500 and min_marg>=-1e-8 and max_close<=1e-8,
            'loo_reparameterization_gate_pass':max_loo_d<=0.25 and max_loo_range<=0.15 and max_loo_eff<=0.5 and max_loo_phys<=0.15,
            'burnin_reparameterization_gate_pass':max_burn_d<=0.25 and max_burn_range<=0.15 and max_burn_eff<=0.5 and max_burn_phys<=0.15,
            'independent_audit_pass':audit_pass,
        }
        passed=all(gates.values())
        classification='PASS_WITHIN_BLOCK_REPARAMETERIZATION_INVARIANCE_AUDIT' if passed else 'HOLD_REPARAMETERIZATION_NUMERICAL_OR_STABILITY_FAILURE'
        c.write_tsv(out/'HTS64_CLASSIFICATION.tsv',[{
            'classification':classification,
            'min_chain_kish_effective_rows':min_kish,
            'max_chain_weight_share':max_share,
            'max_total_distance_invariance_error':max_total,
            'max_block_share_invariance_error':max_block,
            'min_transformed_correlation_eigenvalue':min_eig,
            'max_transformed_condition_number':max_cond,
            'minimum_permutation_marginal_contribution':min_marg,
            'max_allocation_closure_error':max_close,
            'max_LOO_conditional4d_drift':max_loo_d,
            'max_LOO_rotation_top_share_range_drift':max_loo_range,
            'max_LOO_rotation_effective_count_range_drift':max_loo_eff,
            'max_LOO_physical_amplitude_top_share_drift':max_loo_phys,
            'max_burn_conditional4d_change':max_burn_d,
            'max_burn_rotation_top_share_range_change':max_burn_range,
            'max_burn_rotation_effective_count_range_change':max_burn_eff,
            'max_burn_physical_amplitude_top_share_change':max_burn_phys,
            **gates,
            'interpretation_boundary':'Block totals are invariant bookkeeping quantities; coordinate allocations within a block may change under invertible reparameterization and are not physical attributions.',
        }])
        (out/'HTS64_EXECUTION_REPORT.md').write_text(
            '# HTS64 execution report\n\n`'+classification+'`\n\n'
            'HTS64 stress-tests HTS63 coordinate allocations under 49 predeclared within-block '
            'rotations and a logA-2tau amplitude reparameterization while requiring exact total '
            'distance and fixed-block invariance.\n'
        )
        (out/'MANIFEST.json').write_text(json.dumps({
            'stage':'HTS64','classification':classification,
            'primary_burn':PRIMARY,'sensitivity_burn':SENS,
            'rotation_angles_deg':list(g.ANGLES),
            'physical_amplitude_transform':'logA_minus_2tau',
            'cache_store':str(store),
            'boundary':'Within-block coordinate reparameterization audit only.'
        },indent=2)+'\n')
        c.make_zip(out,zp)
        print(classification)
        print(zp)
    except Exception as e:
        (out/'HTS64_RUNTIME_FAILURE.txt').write_text(traceback.format_exc())
        for name in DOCS:
            if (pkg/name).exists():
                shutil.copy2(pkg/name,out/name)
        c.write_tsv(out/'HTS64_CLASSIFICATION.tsv',[{
            'classification':'HOLD_SOURCE_MATERIALIZATION_OR_REPARAMETERIZATION_FAILURE',
            'error':str(e),
        }])
        (out/'HTS64_EXECUTION_REPORT.md').write_text(
            '# HTS64 execution report\n\n'
            '`HOLD_SOURCE_MATERIALIZATION_OR_REPARAMETERIZATION_FAILURE`\n\n'
            f'```text\n{e}\n```\n'
        )
        c.make_zip(out,zp)
        print('HOLD_SOURCE_MATERIALIZATION_OR_REPARAMETERIZATION_FAILURE')
        print(zp)

if __name__=='__main__':
    main()
