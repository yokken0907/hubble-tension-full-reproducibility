#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
import hts61_common as c
import hts61_metric as g

def read(p):
    with Path(p).open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f,delimiter='\t'))
def ff(x): return float(x)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-dir',required=True);ap.add_argument('--root-json',required=True);a=ap.parse_args()
    out=Path(a.output_dir);roots=json.loads(Path(a.root_json).read_text());details={};maxerr=0.0;checks=[]
    savedm={(r['contract'],ff(r['burn_fraction_per_chain']),int(r['mode_index'])):r for r in read(out/'HTS61_ENDPOINT_MODE_IDENTIFIABILITY.tsv')}
    savedb={(r['contract'],ff(r['burn_fraction_per_chain']),r['block']):r for r in read(out/'HTS61_ENDPOINT_BLOCK_SUBSPACE.tsv')}
    savededge={(r['edge'],r['direction'],ff(r['burn_fraction_per_chain'])):r for r in read(out/'HTS61_EDGE_CONTRIBUTION_IDENTIFIABILITY.tsv')}
    saved_lm={(r['contract'],ff(r['burn_fraction_per_chain']),r['perturbation'],int(r['baseline_mode_index'])):r for r in read(out/'HTS61_ENDPOINT_LOO_MODE_STABILITY.tsv')}
    saved_lc={(r['contract'],ff(r['burn_fraction_per_chain']),r['perturbation'],int(r['baseline_cluster_id'])):r for r in read(out/'HTS61_ENDPOINT_LOO_CLUSTER_STABILITY.tsv')}
    saved_lb={(r['contract'],ff(r['burn_fraction_per_chain']),r['perturbation'],r['block']):r for r in read(out/'HTS61_ENDPOINT_LOO_BLOCK_STABILITY.tsv')}
    saved_bm={(r['contract'],r['perturbation'],int(r['baseline_mode_index'])):r for r in read(out/'HTS61_BURNIN_MODE_STABILITY.tsv')}
    saved_bc={(r['contract'],r['perturbation'],int(r['baseline_cluster_id'])):r for r in read(out/'HTS61_BURNIN_CLUSTER_STABILITY.tsv')}
    saved_bb={(r['contract'],r['perturbation'],r['block']):r for r in read(out/'HTS61_BURNIN_BLOCK_STABILITY.tsv')}
    saved_cross={(r['endpoint_a'],r['endpoint_b'],ff(r['burn_fraction_per_chain']),r['block']):r for r in read(out/'HTS61_CROSS_ENDPOINT_BLOCK_ALIGNMENT.tsv')}

    for burn in (0.3,0.5):
        for label,rec in roots.items():
            d,w,ids,h,cols,files=c.load_factor_root(Path(rec['path']),int(rec['count']),burn)
            D=g.endpoint_detail(d,w,ids);details[(label,burn)]=D
            for r in g.mode_rows(label,burn,D):
                q=savedm[(label,burn,int(r['mode_index']))]
                for k in ('conditional_correlation_eigenvalue','nearest_relative_gap','baryon_tilt_purity','tau_amplitude_purity','loading_omega_b','loading_tau','loading_n_s','loading_logA'):
                    maxerr=max(maxerr,abs(float(r[k])-ff(q[k])))
            for r in g.block_rows(label,burn,D):
                q=savedb[(label,burn,r['block'])]
                for k in ('coordinate_block_overlap_fraction','principal_angle_min_deg','principal_angle_max_deg'):
                    maxerr=max(maxerr,abs(float(r[k])-ff(q[k])))
            for ch in sorted(set(D['ids'])):
                perturb='LOO:'+ch
                mrows,crows,brows=g.perturbation_rows(label,burn,perturb,D,g.subset_detail(D,D['ids']!=ch))
                for r in mrows:
                    q=saved_lm[(label,burn,perturb,int(r['baseline_mode_index']))]
                    for k in ('matched_abs_dot','matched_angle_deg','baseline_eigenvalue','perturbed_eigenvalue','relative_eigenvalue_drift'):
                        maxerr=max(maxerr,abs(float(r[k])-ff(q[k])))
                    if int(r['matched_perturbed_mode_index'])!=int(q['matched_perturbed_mode_index']):
                        maxerr=max(maxerr,1.0)
                for r in crows:
                    q=saved_lc[(label,burn,perturb,int(r['baseline_cluster_id']))]
                    for k in ('principal_angle_min_deg','principal_angle_max_deg'):
                        maxerr=max(maxerr,abs(float(r[k])-ff(q[k])))
                for r in brows:
                    q=saved_lb[(label,burn,perturb,r['block'])]
                    for k in ('principal_angle_min_deg','principal_angle_max_deg','block_overlap_fraction_drift'):
                        maxerr=max(maxerr,abs(float(r[k])-ff(q[k])))

    for label in roots:
        mrows,crows,brows=g.perturbation_rows(label,0.3,'BURN_30_TO_50',details[(label,0.3)],details[(label,0.5)])
        for r in mrows:
            q=saved_bm[(label,'BURN_30_TO_50',int(r['baseline_mode_index']))]
            for k in ('matched_abs_dot','matched_angle_deg','relative_eigenvalue_drift'):
                maxerr=max(maxerr,abs(float(r[k])-ff(q[k])))
        for r in crows:
            q=saved_bc[(label,'BURN_30_TO_50',int(r['baseline_cluster_id']))]
            for k in ('principal_angle_min_deg','principal_angle_max_deg'):
                maxerr=max(maxerr,abs(float(r[k])-ff(q[k])))
        for r in brows:
            q=saved_bb[(label,'BURN_30_TO_50',r['block'])]
            for k in ('principal_angle_min_deg','principal_angle_max_deg','block_overlap_fraction_drift'):
                maxerr=max(maxerr,abs(float(r[k])-ff(q[k])))

    labels=list(roots)
    for burn in (0.3,0.5):
        for i,a0 in enumerate(labels):
            for b0 in labels[i+1:]:
                for block,idx in g.BLOCKS.items():
                    qa=g.block_subspace(details[(a0,burn)]['basis']['eigvecs'],idx)
                    qb=g.block_subspace(details[(b0,burn)]['basis']['eigvecs'],idx)
                    ang=g.subspace_angles_deg(qa['U'],qb['U'])
                    q=saved_cross[(a0,b0,burn,block)]
                    maxerr=max(maxerr,abs(float(min(ang))-ff(q['principal_angle_min_deg'])),abs(float(max(ang))-ff(q['principal_angle_max_deg'])))

    for edge,frm,to,etype,boundary in c.RELEASE_GRAPH_EDGES:
        for burn in (0.3,0.5):
            for direction,sl,tl,A,B in (('FORWARD',frm,to,details[(frm,burn)],details[(to,burn)]),('REVERSE',to,frm,details[(to,burn)],details[(frm,burn)])):
                r=g.directed_contribution(edge,etype,boundary,burn,sl,tl,A,B,direction);q=savededge[(edge,direction,burn)]
                for k in ('conditional4d_mahalanobis','top_mode_fraction','top_mode_nearest_relative_gap','top_mode_cluster_fraction','top_mode_baryon_tilt_purity','top_mode_tau_amplitude_purity'):
                    maxerr=max(maxerr,abs(float(r[k])-ff(q[k])))

    checks.append({'check':'raw_chain_endpoint_LOO_burn_cross_edge_reconstruction_max_error','observed':maxerr,'required':'<=1e-9','result':'PASS' if maxerr<=1e-9 else 'FAIL'})
    sup=read(out/'HTS61_CHAIN_SUPPORT.tsv')
    for burn in (0.3,0.5):
        for label in roots:
            s=sum(ff(r['weight_share']) for r in sup if r['contract']==label and ff(r['burn_fraction_per_chain'])==burn)
            checks.append({'check':f'{label}_{burn}_weight_share_sum','observed':s,'required':'1 within 1e-10','result':'PASS' if abs(s-1)<=1e-10 else 'FAIL'})
    with (out/'HTS61_INDEPENDENT_AUDIT_CHECKS.tsv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['check','observed','required','result'],delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(checks)
    ok=all(r['result']=='PASS' for r in checks)
    (out/'HTS61_INDEPENDENT_AUDIT_RESULT.md').write_text('# HTS61 independent audit result\n\n`'+('PASS' if ok else 'FAIL')+'`\n')
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
