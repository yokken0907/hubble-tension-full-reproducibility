#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, shutil, subprocess, sys, traceback
from pathlib import Path
import hts59_common as c
import hts59_metric as g

BURNS=(0.3,0.5); PRIMARY=0.3; SENS=0.5
ORDER=('SPT_BASE','SPT_ACT','SPT_PR4','FULL_ORIGINAL','FULL_FIXED')
DOCS=('CANONICAL_STATE_THROUGH_HTS58.md','HTS58_CANONICALIZATION_AUDIT.md','HTS59_EXECUTION_CONTRACT.md','HTS59_SELECTION_AUDIT.md','HTS59_SOURCE_ADEQUACY_AUDIT.md','HTS59_PREFLIGHT_RESULT.md','HTS59_PREFLIGHT_TEST_AUDIT.md','README_RUN.md')

def main():
    pkg=Path(__file__).resolve().parent
    downloads=Path(os.environ.get('HTS59_DOWNLOADS',str(pkg.parent))).resolve()
    store=Path(os.environ.get('HTS_CACHE_STORE',str(downloads/'HTS_CHAIN_CACHE_STORE'))).resolve()
    stage_cache=Path(os.environ.get('HTS59_CACHE',str(store/'HTS59'))).resolve()
    out=Path(os.environ.get('HTS59_OUTPUT',str(downloads/'HTS59_RESULTS_FOR_REVIEW'))).resolve()
    zp=Path(os.environ.get('HTS59_ZIP_OUTPUT',str(downloads/'HTS59_RESULTS_FOR_REVIEW.zip'))).resolve()
    test=os.environ.get('HTS59_TEST_MODE','0')=='1'
    store.mkdir(parents=True,exist_ok=True); stage_cache.mkdir(parents=True,exist_ok=True)
    shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True)
    try:
        obase,ometa,oprov,oroots=c.materialize_original_factorial(downloads,store,stage_cache,test)
        fbase,fmeta,fprov,froots=c.materialize_fixed_full(downloads,store,stage_cache,test)
        c.write_tsv(out/'HTS59_SOURCE_FREEZE.tsv',[{'source':'ORIGINAL',**ometa},{'source':'FIXED',**fmeta}])
        c.write_tsv(out/'HTS59_SELECTED_MEMBER_PROVENANCE.tsv',oprov+fprov)
        inv=stage_cache/'HTS59_ORIGINAL_ROOT_INVENTORY.tsv'
        if inv.exists(): shutil.copy2(inv,out/inv.name)
        roots={'SPT_BASE':obase/oroots['SPT_BASE'],'SPT_ACT':obase/oroots['SPT_ACT'],'SPT_PR4':obase/oroots['SPT_PR4'],
               'FULL_ORIGINAL':obase/oroots['FULL_ORIGINAL'],'FULL_FIXED':fbase/froots['FULL_FIXED']}
        lr,likes,fr,fams,ok,checks,rawchecks=c.factor_contract_rows(roots)
        c.write_tsv(out/'HTS59_LIKELIHOOD_MEMBERSHIP.tsv',lr)
        c.write_tsv(out/'HTS59_SEMANTIC_DATA_FAMILY_MEMBERSHIP.tsv',fr)
        c.write_tsv(out/'HTS59_RELEASE_ENDPOINT_CONTRACT_CHECKS.tsv',checks)
        c.write_tsv(out/'HTS59_RAW_IMPLEMENTATION_DIAGNOSTICS.tsv',rawchecks)
        if not ok: raise RuntimeError('release endpoint semantic contract failed')
        counts={**c.FACTOR_EXPECTED_CHAINS,**c.FACTOR_EXPECTED_CHAINS_FIXED}
        details={}; endpoints=[]; support=[]; root_json={}
        for burn in BURNS:
            for label in ORDER:
                d,w,ids,h,cols,files=c.load_factor_root(roots[label],counts[label],burn)
                D=g.endpoint_detail(d,w,ids); details[(label,burn)]=D
                endpoints.append(g.endpoint_row(label,burn,D)); support+=g.support_rows(label,burn,D)
                root_json[label]={'path':str(roots[label]),'count':counts[label]}
        c.write_tsv(out/'HTS59_ENDPOINT_6D_CONDITIONING.tsv',endpoints)
        c.write_tsv(out/'HTS59_CHAIN_SUPPORT.tsv',support)
        rows=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A=details[(frm,burn)]; B=details[(to,burn)]
                rows.append(g.directed_metric(edge,etype,boundary,burn,frm,to,A,B,'FORWARD'))
                rows.append(g.directed_metric(edge,etype,boundary,burn,to,frm,B,A,'REVERSE'))
        c.write_tsv(out/'HTS59_DIRECTED_6D_DECOMPOSITION.tsv',rows)
        idx={(r['edge'],r['direction'],r['burn_fraction_per_chain']):r for r in rows}
        loo=[]
        for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A=details[(frm,burn)]; B=details[(to,burn)]
                for direction,sl,tl,S,T in (('FORWARD',frm,to,A,B),('REVERSE',to,frm,B,A)):
                    base=idx[(edge,direction,burn)]
                    for side,D in (('SOURCE',S),('TARGET',T)):
                        for ch in sorted(set(D['ids'])):
                            sub=g.subset_detail(D,D['ids']!=ch)
                            SS=sub if side=='SOURCE' else S; TT=sub if side=='TARGET' else T
                            m=g.directed_metric(edge,etype,boundary,burn,sl,tl,SS,TT,direction)
                            loo.append({'edge':edge,'direction':direction,'burn_fraction_per_chain':burn,
                                'omission_side':side,'omitted_chain':ch,
                                'full6d_mahalanobis_drift':m['full6d_mahalanobis']-base['full6d_mahalanobis'],
                                'tn2d_mahalanobis_drift':m['tn2d_mahalanobis']-base['tn2d_mahalanobis'],
                                'conditional4d_mahalanobis_drift':m['conditional4d_mahalanobis']-base['conditional4d_mahalanobis'],
                                'conditional_fraction_drift':m['conditional_fraction_full_distance_squared']-base['conditional_fraction_full_distance_squared'],
                                'log_source_condition_number_drift':math.log(m['source_correlation_condition_number']/base['source_correlation_condition_number']),
                                'closure_error':m['decomposition_closure_error']})
        c.write_tsv(out/'HTS59_DIRECTED_LOO_STABILITY.tsv',loo)
        sens=[]
        for edge,_,_,_,_ in c.RELEASE_GRAPH_EDGES:
            for direction in ('FORWARD','REVERSE'):
                a=idx[(edge,direction,PRIMARY)]; b=idx[(edge,direction,SENS)]
                sens.append({'edge':edge,'direction':direction,
                    'full6d_mahalanobis_change':b['full6d_mahalanobis']-a['full6d_mahalanobis'],
                    'tn2d_mahalanobis_change':b['tn2d_mahalanobis']-a['tn2d_mahalanobis'],
                    'conditional4d_mahalanobis_change':b['conditional4d_mahalanobis']-a['conditional4d_mahalanobis'],
                    'conditional_fraction_change':b['conditional_fraction_full_distance_squared']-a['conditional_fraction_full_distance_squared'],
                    'log_condition_number_change':math.log(b['source_correlation_condition_number']/a['source_correlation_condition_number'])})
        c.write_tsv(out/'HTS59_BURNIN_SENSITIVITY.tsv',sens)
        runtime=stage_cache/'HTS59_RUNTIME_ROOTS.json'; runtime.write_text(json.dumps(root_json,indent=2)+'\n')
        for name in DOCS: shutil.copy2(pkg/name,out/name)
        proc=subprocess.run([sys.executable,str(pkg/'audit_hts59.py'),'--output-dir',str(out),'--root-json',str(runtime)],capture_output=True,text=True)
        (out/'HTS59_AUDIT_STDOUT.txt').write_text(proc.stdout); (out/'HTS59_AUDIT_STDERR.txt').write_text(proc.stderr)
        audit_pass=proc.returncode==0
        ps=[r for r in support if r['burn_fraction_per_chain']==PRIMARY]; pl=[r for r in loo if r['burn_fraction_per_chain']==PRIMARY]
        min_kish=min(r['kish_effective_rows'] for r in ps); max_share=max(r['weight_share'] for r in ps)
        min_eig=min(r['min_correlation_eigenvalue'] for r in endpoints); max_cond=max(r['correlation_condition_number'] for r in endpoints)
        max_closure=max(abs(r['decomposition_closure_error']) for r in rows)
        max_loo_full=max(abs(r['full6d_mahalanobis_drift']) for r in pl); max_loo_cond=max(abs(r['conditional4d_mahalanobis_drift']) for r in pl)
        max_loo_frac=max(abs(r['conditional_fraction_drift']) for r in pl); max_loo_logc=max(abs(r['log_source_condition_number_drift']) for r in pl)
        max_burn_full=max(abs(r['full6d_mahalanobis_change']) for r in sens); max_burn_cond=max(abs(r['conditional4d_mahalanobis_change']) for r in sens)
        max_burn_frac=max(abs(r['conditional_fraction_change']) for r in sens); max_burn_logc=max(abs(r['log_condition_number_change']) for r in sens)
        gates={'support_gate_pass':min_kish>=100 and max_share<=0.35,
               'numerical_condition_gate_pass':min_eig>=1e-8 and max_cond<=1e8 and max_closure<=1e-8,
               'loo_decomposition_gate_pass':max_loo_full<=0.35 and max_loo_cond<=0.35 and max_loo_frac<=0.20 and max_loo_logc<=0.35,
               'burnin_decomposition_gate_pass':max_burn_full<=0.35 and max_burn_cond<=0.35 and max_burn_frac<=0.20 and max_burn_logc<=0.35,
               'independent_audit_pass':audit_pass}
        classification='PASS_TN2D_SUFFICIENCY_AND_CONDITIONAL_4D_RESIDUAL_AUDIT' if all(gates.values()) else 'HOLD_6D_CONDITIONING_OR_STABILITY_FAILURE'
        c.write_tsv(out/'HTS59_CLASSIFICATION.tsv',[{'classification':classification,'min_chain_kish_effective_rows':min_kish,
            'max_chain_weight_share':max_share,'min_endpoint_correlation_eigenvalue':min_eig,'max_endpoint_correlation_condition_number':max_cond,
            'max_decomposition_closure_error':max_closure,'max_LOO_full6d_drift':max_loo_full,'max_LOO_conditional4d_drift':max_loo_cond,
            'max_LOO_conditional_fraction_drift':max_loo_frac,'max_LOO_log_condition_number_drift':max_loo_logc,
            'max_burn_full6d_change':max_burn_full,'max_burn_conditional4d_change':max_burn_cond,
            'max_burn_conditional_fraction_change':max_burn_frac,'max_burn_log_condition_number_change':max_burn_logc,
            **gates,'interpretation_boundary':'Gaussian covariance decomposition of correlated release posteriors; not independent tension significance or causal attribution.'}])
        (out/'HTS59_EXECUTION_REPORT.md').write_text('# HTS59 execution report\n\n`'+classification+'`\n\nHTS59 decomposes each directed release-edge displacement into the frozen tangent-normal marginal distance and the conditional residual in omega_b, tau, n_s and logA.\n')
        (out/'MANIFEST.json').write_text(json.dumps({'stage':'HTS59','classification':classification,'primary_burn':PRIMARY,'sensitivity_burn':SENS,'variables':g.VARS,'cache_store':str(store),'boundary':'Correlated release-posterior covariance decomposition only.'},indent=2)+'\n')
        c.make_zip(out,zp); print(classification); print(zp)
    except Exception as e:
        (out/'HTS59_RUNTIME_FAILURE.txt').write_text(traceback.format_exc())
        for name in DOCS:
            if (pkg/name).exists(): shutil.copy2(pkg/name,out/name)
        c.write_tsv(out/'HTS59_CLASSIFICATION.tsv',[{'classification':'HOLD_SOURCE_MATERIALIZATION_OR_6D_AUDIT_FAILURE','error':str(e)}])
        (out/'HTS59_EXECUTION_REPORT.md').write_text('# HTS59 execution report\n\n`HOLD_SOURCE_MATERIALIZATION_OR_6D_AUDIT_FAILURE`\n\n```text\n'+str(e)+'\n```\n')
        c.make_zip(out,zp); print('HOLD_SOURCE_MATERIALIZATION_OR_6D_AUDIT_FAILURE'); print(zp)

if __name__=='__main__': main()
