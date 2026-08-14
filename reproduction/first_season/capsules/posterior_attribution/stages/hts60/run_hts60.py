#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, shutil, subprocess, sys, traceback
from pathlib import Path
import hts60_common as c
import hts60_metric as g

BURNS=(0.3,0.5); PRIMARY=0.3; SENS=0.5
ORDER=('SPT_BASE','SPT_ACT','SPT_PR4','FULL_ORIGINAL','FULL_FIXED')
DOCS=('CANONICAL_STATE_THROUGH_HTS59.md','HTS59_CANONICALIZATION_AUDIT.md',
      'HTS60_EXECUTION_CONTRACT.md','HTS60_SELECTION_AUDIT.md',
      'HTS60_SOURCE_ADEQUACY_AUDIT.md','HTS60_PREFLIGHT_RESULT.md',
      'HTS60_PREFLIGHT_TEST_AUDIT.md','README_RUN.md')

def main():
    pkg=Path(__file__).resolve().parent
    downloads=Path(os.environ.get('HTS60_DOWNLOADS',str(pkg.parent))).resolve()
    store=Path(os.environ.get('HTS_CACHE_STORE',str(downloads/'HTS_CHAIN_CACHE_STORE'))).resolve()
    stage_cache=Path(os.environ.get('HTS60_CACHE',str(store/'HTS60'))).resolve()
    out=Path(os.environ.get('HTS60_OUTPUT',str(downloads/'HTS60_RESULTS_FOR_REVIEW'))).resolve()
    zp=Path(os.environ.get('HTS60_ZIP_OUTPUT',str(downloads/'HTS60_RESULTS_FOR_REVIEW.zip'))).resolve()
    test=os.environ.get('HTS60_TEST_MODE','0')=='1'
    store.mkdir(parents=True,exist_ok=True); stage_cache.mkdir(parents=True,exist_ok=True)
    shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True)
    try:
        obase,ometa,oprov,oroots=c.materialize_original_factorial(downloads,store,stage_cache,test)
        fbase,fmeta,fprov,froots=c.materialize_fixed_full(downloads,store,stage_cache,test)
        c.write_tsv(out/'HTS60_SOURCE_FREEZE.tsv',[{'source':'ORIGINAL',**ometa},{'source':'FIXED',**fmeta}])
        c.write_tsv(out/'HTS60_SELECTED_MEMBER_PROVENANCE.tsv',oprov+fprov)
        inv=stage_cache/'HTS60_ORIGINAL_ROOT_INVENTORY.tsv'
        if inv.exists(): shutil.copy2(inv,out/inv.name)
        roots={'SPT_BASE':obase/oroots['SPT_BASE'],'SPT_ACT':obase/oroots['SPT_ACT'],
               'SPT_PR4':obase/oroots['SPT_PR4'],'FULL_ORIGINAL':obase/oroots['FULL_ORIGINAL'],
               'FULL_FIXED':fbase/froots['FULL_FIXED']}
        lr,likes,fr,fams,ok,checks,rawchecks=c.factor_contract_rows(roots)
        c.write_tsv(out/'HTS60_LIKELIHOOD_MEMBERSHIP.tsv',lr)
        c.write_tsv(out/'HTS60_SEMANTIC_DATA_FAMILY_MEMBERSHIP.tsv',fr)
        c.write_tsv(out/'HTS60_RELEASE_ENDPOINT_CONTRACT_CHECKS.tsv',checks)
        c.write_tsv(out/'HTS60_RAW_IMPLEMENTATION_DIAGNOSTICS.tsv',rawchecks)
        if not ok: raise RuntimeError('release endpoint semantic contract failed')

        counts={**c.FACTOR_EXPECTED_CHAINS,**c.FACTOR_EXPECTED_CHAINS_FIXED}
        details={}; support=[]; basis=[]; root_json={}
        for burn in BURNS:
            for label in ORDER:
                d,w,ids,h,cols,files=c.load_factor_root(roots[label],counts[label],burn)
                D=g.endpoint_detail(d,w,ids); details[(label,burn)]=D
                support+=g.support_rows(label,burn,D)
                basis+=g.endpoint_mode_rows(label,burn,D)
                root_json[label]={'path':str(roots[label]),'count':counts[label]}
        c.write_tsv(out/'HTS60_CHAIN_SUPPORT.tsv',support)
        c.write_tsv(out/'HTS60_ENDPOINT_CONDITIONAL_MODE_BASIS.tsv',basis)

        summaries=[]; modes=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A=details[(frm,burn)]; B=details[(to,burn)]
                for direction,sl,tl,S,T in (('FORWARD',frm,to,A,B),('REVERSE',to,frm,B,A)):
                    s,m=g.directed_modes(edge,etype,boundary,burn,sl,tl,S,T,direction)
                    summaries.append(s); modes+=m
        c.write_tsv(out/'HTS60_DIRECTED_MODE_SUMMARY.tsv',summaries)
        c.write_tsv(out/'HTS60_DIRECTED_MODE_CONTRIBUTIONS.tsv',modes)
        idx={(r['edge'],r['direction'],r['burn_fraction_per_chain']):r for r in summaries}

        loo=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A=details[(frm,burn)]; B=details[(to,burn)]
                for direction,sl,tl,S,T in (('FORWARD',frm,to,A,B),('REVERSE',to,frm,B,A)):
                    base=idx[(edge,direction,burn)]
                    for side,D in (('SOURCE',S),('TARGET',T)):
                        for ch in sorted(set(D['ids'])):
                            sub=g.subset_detail(D,D['ids']!=ch)
                            SS=sub if side=='SOURCE' else S
                            TT=sub if side=='TARGET' else T
                            q,_=g.directed_modes(edge,etype,boundary,burn,sl,tl,SS,TT,direction)
                            loo.append({
                                'edge':edge,'direction':direction,'burn_fraction_per_chain':burn,
                                'omission_side':side,'omitted_chain':ch,
                                'conditional4d_mahalanobis_drift':q['conditional4d_mahalanobis']-base['conditional4d_mahalanobis'],
                                'top1_mode_fraction_drift':q['top1_mode_fraction']-base['top1_mode_fraction'],
                                'top2_mode_fraction_drift':q['top2_mode_fraction']-base['top2_mode_fraction'],
                                'effective_mode_count_drift':q['effective_contributing_mode_count']-base['effective_contributing_mode_count'],
                                'log_condition_number_drift':math.log(q['conditional_mode_condition_number']/base['conditional_mode_condition_number']),
                                'mode_closure_error':q['mode_decomposition_closure_error'],
                            })
        c.write_tsv(out/'HTS60_DIRECTED_LOO_STABILITY.tsv',loo)

        sens=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for direction in ('FORWARD','REVERSE'):
                a=idx[(edge,direction,PRIMARY)]; b=idx[(edge,direction,SENS)]
                sens.append({
                    'edge':edge,'direction':direction,
                    'conditional4d_mahalanobis_change':b['conditional4d_mahalanobis']-a['conditional4d_mahalanobis'],
                    'top1_mode_fraction_change':b['top1_mode_fraction']-a['top1_mode_fraction'],
                    'top2_mode_fraction_change':b['top2_mode_fraction']-a['top2_mode_fraction'],
                    'effective_mode_count_change':b['effective_contributing_mode_count']-a['effective_contributing_mode_count'],
                    'log_condition_number_change':math.log(b['conditional_mode_condition_number']/a['conditional_mode_condition_number']),
                })
        c.write_tsv(out/'HTS60_BURNIN_SENSITIVITY.tsv',sens)

        runtime=stage_cache/'HTS60_RUNTIME_ROOTS.json'
        runtime.write_text(json.dumps(root_json,indent=2)+'\n')
        for name in DOCS: shutil.copy2(pkg/name,out/name)
        proc=subprocess.run([sys.executable,str(pkg/'audit_hts60.py'),'--output-dir',str(out),'--root-json',str(runtime)],
                            capture_output=True,text=True)
        (out/'HTS60_AUDIT_STDOUT.txt').write_text(proc.stdout)
        (out/'HTS60_AUDIT_STDERR.txt').write_text(proc.stderr)
        audit_pass=proc.returncode==0

        ps=[r for r in support if r['burn_fraction_per_chain']==PRIMARY]
        pl=[r for r in loo if r['burn_fraction_per_chain']==PRIMARY]
        min_kish=min(r['kish_effective_rows'] for r in ps)
        max_share=max(r['weight_share'] for r in ps)
        min_eig=min(r['conditional_correlation_eigenvalue'] for r in basis)
        max_cond=max(r['conditional_mode_condition_number'] for r in summaries)
        max_close=max(abs(r['mode_decomposition_closure_error']) for r in summaries)
        max_loo_d=max(abs(r['conditional4d_mahalanobis_drift']) for r in pl)
        max_loo_f1=max(abs(r['top1_mode_fraction_drift']) for r in pl)
        max_loo_eff=max(abs(r['effective_mode_count_drift']) for r in pl)
        max_burn_d=max(abs(r['conditional4d_mahalanobis_change']) for r in sens)
        max_burn_f1=max(abs(r['top1_mode_fraction_change']) for r in sens)
        max_burn_eff=max(abs(r['effective_mode_count_change']) for r in sens)
        gates={
            'support_gate_pass':min_kish>=100 and max_share<=0.35,
            'numerical_mode_gate_pass':min_eig>1e-6 and max_cond<=500 and max_close<=1e-8,
            'loo_mode_summary_gate_pass':max_loo_d<=0.25 and max_loo_f1<=0.15 and max_loo_eff<=0.5,
            'burnin_mode_summary_gate_pass':max_burn_d<=0.25 and max_burn_f1<=0.15 and max_burn_eff<=0.5,
            'independent_audit_pass':audit_pass,
        }
        ok=all(gates.values())
        classification='PASS_CONDITIONAL_4D_EIGENMODE_LOCALIZATION_AUDIT' if ok else 'HOLD_CONDITIONAL_MODE_SUPPORT_OR_STABILITY_FAILURE'
        c.write_tsv(out/'HTS60_CLASSIFICATION.tsv',[{
            'classification':classification,
            'min_chain_kish_effective_rows':min_kish,'max_chain_weight_share':max_share,
            'min_conditional_correlation_eigenvalue':min_eig,
            'max_conditional_mode_condition_number':max_cond,
            'max_mode_decomposition_closure_error':max_close,
            'max_LOO_conditional4d_drift':max_loo_d,
            'max_LOO_top1_fraction_drift':max_loo_f1,
            'max_LOO_effective_mode_count_drift':max_loo_eff,
            'max_burn_conditional4d_change':max_burn_d,
            'max_burn_top1_fraction_change':max_burn_f1,
            'max_burn_effective_mode_count_change':max_burn_eff,
            **gates,
            'interpretation_boundary':'Conditional correlation eigenmodes are source-posterior linear diagnostics, not physical parameters or causal data contributions.',
        }])
        (out/'HTS60_EXECUTION_REPORT.md').write_text(
            '# HTS60 execution report\n\n`'+classification+'`\n\n'
            'HTS60 decomposes the HTS59 conditional four-dimensional residual into exact '
            'source-posterior conditional-correlation eigenmodes. Mode loadings are linear '
            'diagnostics in conditionally standardized direct variables, not new physical parameters.\n')
        (out/'MANIFEST.json').write_text(json.dumps({
            'stage':'HTS60','classification':classification,'primary_burn':PRIMARY,
            'sensitivity_burn':SENS,'variables':list(g.AUX),'cache_store':str(store),
            'boundary':'Conditional posterior eigenmode localization only.'
        },indent=2)+'\n')
        c.make_zip(out,zp)
        print(classification); print(zp)
    except Exception as e:
        (out/'HTS60_RUNTIME_FAILURE.txt').write_text(traceback.format_exc())
        for name in DOCS:
            if (pkg/name).exists(): shutil.copy2(pkg/name,out/name)
        c.write_tsv(out/'HTS60_CLASSIFICATION.tsv',[{
            'classification':'HOLD_SOURCE_MATERIALIZATION_OR_MODE_AUDIT_FAILURE','error':str(e)}])
        (out/'HTS60_EXECUTION_REPORT.md').write_text(
            '# HTS60 execution report\n\n`HOLD_SOURCE_MATERIALIZATION_OR_MODE_AUDIT_FAILURE`\n\n'
            f'```text\n{e}\n```\n')
        c.make_zip(out,zp)
        print('HOLD_SOURCE_MATERIALIZATION_OR_MODE_AUDIT_FAILURE'); print(zp)

if __name__=='__main__': main()
