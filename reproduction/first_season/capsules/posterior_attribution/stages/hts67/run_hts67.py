#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path
from typing import Any

import hts67_common as c
import hts67_metric as g

BURNS = (0.3, 0.5)
PRIMARY = 0.3
SENSITIVITY = 0.5
PRIMARY_METRIC = 'ARITHMETIC_COVARIANCE_POOL'
SECONDARY_METRIC = 'PRECISION_MEAN_POOL'
DOCS = (
    'CANONICAL_STATE_THROUGH_HTS66.md',
    'HTS66_CANONICALIZATION_AUDIT.md',
    'HTS67_EXECUTION_CONTRACT.md',
    'HTS67_SELECTION_AUDIT.md',
    'HTS67_SOURCE_ADEQUACY_AUDIT.md',
    'HTS67_PREFLIGHT_RESULT.md',
    'HTS67_PREFLIGHT_TEST_AUDIT.md',
    'README_RUN.md',
)


def f(value: Any) -> float:
    return float(value)


def read_baseline(path: Path) -> tuple[list[dict[str, str]], dict[str, str]]:
    with zipfile.ZipFile(path) as zf:
        directed = c.read_tsv_bytes(zf.read('HTS62_DIRECTED_FIXED_BLOCK_DECOMPOSITION.tsv'))
        classification_rows = c.read_tsv_bytes(zf.read('HTS62_CLASSIFICATION.tsv'))
    if len(classification_rows) != 1:
        raise RuntimeError('HTS62 classification row count mismatch')
    classification = classification_rows[0]
    if classification.get('classification') != 'PASS_FIXED_BLOCK_SHAPLEY_AND_ORDER_SENSITIVITY_AUDIT':
        raise RuntimeError(f'unexpected HTS62 classification: {classification}')
    return directed, classification


def verify_hts66_closeout(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as zf:
        rows = c.read_tsv_bytes(zf.read('HTS66_CLASSIFICATION.tsv'))
    if len(rows) != 1:
        raise RuntimeError('HTS66 classification row count mismatch')
    row = rows[0]
    if row.get('classification') != 'PASS_ATTRIBUTION_INVARIANT_CORE_SYNTHESIS_AND_BRANCH_CLOSEOUT':
        raise RuntimeError(f'unexpected HTS66 classification: {row}')
    if row.get('branch_decision') != 'CLOSE_ATTRIBUTION_DIAGNOSTIC_BRANCH':
        raise RuntimeError(f'unexpected HTS66 branch decision: {row}')
    return row


def baseline_comparison(rows: list[dict[str, Any]], directed: list[dict[str, str]]) -> list[dict[str, Any]]:
    idx = {(r['edge'], r['direction'], f(r['burn_fraction_per_chain'])): r for r in directed}
    out = []
    for row in rows:
        edge = row['edge']
        burn = f(row['burn_fraction_per_chain'])
        fw = idx[(edge, 'FORWARD', burn)]
        rv = idx[(edge, 'REVERSE', burn)]
        b_fw = f(fw['baryon_tilt_shapley_share'])
        b_rv = f(rv['baryon_tilt_shapley_share'])
        b_sym = f(row['baryon_tilt_shapley_share'])
        c_fw = fw['block_pattern_classification']
        c_rv = rv['block_pattern_classification']
        c_sym = row['block_pattern_classification']
        directed_agree = c_fw == c_rv
        if directed_agree and c_sym == c_fw:
            relation = 'DIRECTED_CONSENSUS_PRESERVED'
        elif directed_agree:
            relation = 'DIRECTED_CONSENSUS_CHANGED_BY_SYMMETRIZATION'
        elif c_sym == c_fw and c_sym != c_rv:
            relation = 'DIRECTED_DISAGREEMENT_SYMMETRIC_MATCHES_FORWARD'
        elif c_sym == c_rv and c_sym != c_fw:
            relation = 'DIRECTED_DISAGREEMENT_SYMMETRIC_MATCHES_REVERSE'
        else:
            relation = 'DIRECTED_DISAGREEMENT_SYMMETRIC_THIRD_CLASS'
        lo, hi = sorted((b_fw, b_rv))
        out.append({
            'edge': edge,
            'metric': row['metric'],
            'burn_fraction_per_chain': burn,
            'directed_forward_baryon_share': b_fw,
            'directed_reverse_baryon_share': b_rv,
            'directed_baryon_share_spread': abs(b_fw - b_rv),
            'directed_baryon_share_mean': 0.5 * (b_fw + b_rv),
            'symmetric_baryon_share': b_sym,
            'symmetric_minus_directed_mean': b_sym - 0.5 * (b_fw + b_rv),
            'symmetric_within_directed_share_range': (lo - 1e-12) <= b_sym <= (hi + 1e-12),
            'directed_forward_classification': c_fw,
            'directed_reverse_classification': c_rv,
            'symmetric_classification': c_sym,
            'directed_pair_agrees': directed_agree,
            'comparison_classification': relation,
        })
    return out


def main() -> None:
    pkg = Path(__file__).resolve().parent
    downloads = Path(os.environ.get('HTS67_DOWNLOADS', str(pkg.parent))).resolve()
    store = Path(os.environ.get('HTS_CACHE_STORE', str(downloads / 'HTS_CHAIN_CACHE_STORE'))).resolve()
    stage_cache = Path(os.environ.get('HTS67_CACHE', str(store / 'HTS67'))).resolve()
    out = Path(os.environ.get('HTS67_OUTPUT', str(downloads / 'HTS67_RESULTS_FOR_REVIEW'))).resolve()
    zip_out = Path(os.environ.get('HTS67_ZIP_OUTPUT', str(downloads / 'HTS67_RESULTS_FOR_REVIEW.zip'))).resolve()
    stage_cache.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    try:
        hts62_path = c.find_exact_file(downloads, c.HTS62_FILENAME, c.HTS62_SHA256, 'HTS67_HTS62_RESULTS_OVERRIDE')
        hts66_path = c.find_exact_file(downloads, c.HTS66_FILENAME, c.HTS66_SHA256, 'HTS67_HTS66_RESULTS_OVERRIDE')
        hts62_verify = c.verify_zip_manifest(hts62_path, c.HTS62_SHA256)
        hts66_verify = c.verify_zip_manifest(hts66_path, c.HTS66_SHA256)
        directed_baseline, hts62_class = read_baseline(hts62_path)
        hts66_class = verify_hts66_closeout(hts66_path)
        roots, root_selection = c.discover_cache_roots(store)
        contract_checks = []
        for label in c.ORDER:
            contract_checks.extend(c.validate_root(label, roots[label]))
        if not all(r['result'] == 'PASS' for r in contract_checks):
            raise RuntimeError('release endpoint cache contract failed')

        c.write_tsv(out / 'HTS67_SOURCE_FREEZE.tsv', [
            {'source': 'HTS62_RESULTS', 'path': str(hts62_path), **hts62_verify, 'canonical_classification': hts62_class['classification']},
            {'source': 'HTS66_CORR_RESULTS', 'path': str(hts66_path), **hts66_verify, 'canonical_classification': hts66_class['classification']},
        ])
        c.write_tsv(out / 'HTS67_CACHE_ROOT_SELECTION.tsv', root_selection)
        c.write_tsv(out / 'HTS67_RELEASE_ENDPOINT_CONTRACT_CHECKS.tsv', contract_checks)
        c.write_tsv(out / 'HTS67_SELECTED_MEMBER_PROVENANCE.tsv', c.provenance_rows(roots))

        details: dict[tuple[str, float], dict[str, Any]] = {}
        endpoint_rows = []
        support_rows = []
        runtime_roots: dict[str, dict[str, Any]] = {}
        for burn in BURNS:
            for label in c.ORDER:
                data, weights, ids, _, _, _ = c.load_factor_root(roots[label], c.EXPECTED_CHAINS[label], burn)
                detail = g.endpoint_detail(data, weights, ids)
                details[(label, burn)] = detail
                endpoint_rows.append(g.endpoint_row(label, burn, detail))
                support_rows.extend(g.support_rows(label, burn, detail))
                runtime_roots[label] = {'path': str(roots[label]), 'count': c.EXPECTED_CHAINS[label]}
        c.write_tsv(out / 'HTS67_ENDPOINT_6D_SUMMARY.tsv', endpoint_rows)
        c.write_tsv(out / 'HTS67_CHAIN_SUPPORT.tsv', support_rows)

        rows: list[dict[str, Any]] = []
        for edge, a_label, b_label, edge_type, boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A = details[(a_label, burn)]
                B = details[(b_label, burn)]
                for metric in g.METRICS:
                    rows.append(g.symmetric_metric_row(edge, edge_type, boundary, burn, a_label, b_label, A, B, metric))
        c.write_tsv(out / 'HTS67_SYMMETRIC_METRIC_RESULTS.tsv', rows)

        comparisons = baseline_comparison(rows, directed_baseline)
        c.write_tsv(out / 'HTS67_DIRECTED_BASELINE_COMPARISON.tsv', comparisons)

        index = {(r['edge'], r['metric'], f(r['burn_fraction_per_chain'])): r for r in rows}
        loo_rows = []
        for edge, a_label, b_label, edge_type, boundary in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                A = details[(a_label, burn)]
                B = details[(b_label, burn)]
                for metric in g.METRICS:
                    base = index[(edge, metric, burn)]
                    for endpoint_label, endpoint_side, detail in ((a_label, 'ENDPOINT_A', A), (b_label, 'ENDPOINT_B', B)):
                        for chain in sorted(set(detail['ids'])):
                            sub = g.subset_detail(detail, detail['ids'] != chain)
                            AA = sub if endpoint_side == 'ENDPOINT_A' else A
                            BB = sub if endpoint_side == 'ENDPOINT_B' else B
                            result = g.symmetric_metric_row(edge, edge_type, boundary, burn, a_label, b_label, AA, BB, metric)
                            loo_rows.append({
                                'edge': edge,
                                'metric': metric,
                                'burn_fraction_per_chain': burn,
                                'omitted_endpoint': endpoint_label,
                                'omitted_side': endpoint_side,
                                'omitted_chain': chain,
                                'full6d_mahalanobis_drift': result['full6d_mahalanobis'] - base['full6d_mahalanobis'],
                                'conditional4d_mahalanobis_drift': result['conditional4d_mahalanobis'] - base['conditional4d_mahalanobis'],
                                'conditional_fraction_drift': result['conditional_fraction_full_distance_squared'] - base['conditional_fraction_full_distance_squared'],
                                'baryon_tilt_share_drift': result['baryon_tilt_shapley_share'] - base['baryon_tilt_shapley_share'],
                                'order_sensitivity_drift': result['order_sensitivity_fraction'] - base['order_sensitivity_fraction'],
                                'max_canonical_correlation_drift': result['max_block_canonical_correlation'] - base['max_block_canonical_correlation'],
                                'decomposition_closure_error': result['decomposition_closure_error'],
                                'shapley_closure_error': result['shapley_closure_error'],
                                'swap_invariance_max_error': result['swap_invariance_max_error'],
                            })
        c.write_tsv(out / 'HTS67_LOO_STABILITY.tsv', loo_rows)

        burn_rows = []
        for edge, *_ in c.RELEASE_GRAPH_EDGES:
            for metric in g.METRICS:
                p = index[(edge, metric, PRIMARY)]
                s = index[(edge, metric, SENSITIVITY)]
                burn_rows.append({
                    'edge': edge,
                    'metric': metric,
                    'full6d_mahalanobis_change': s['full6d_mahalanobis'] - p['full6d_mahalanobis'],
                    'conditional4d_mahalanobis_change': s['conditional4d_mahalanobis'] - p['conditional4d_mahalanobis'],
                    'conditional_fraction_change': s['conditional_fraction_full_distance_squared'] - p['conditional_fraction_full_distance_squared'],
                    'baryon_tilt_share_change': s['baryon_tilt_shapley_share'] - p['baryon_tilt_shapley_share'],
                    'order_sensitivity_change': s['order_sensitivity_fraction'] - p['order_sensitivity_fraction'],
                    'max_canonical_correlation_change': s['max_block_canonical_correlation'] - p['max_block_canonical_correlation'],
                    'classification_primary': p['block_pattern_classification'],
                    'classification_sensitivity': s['block_pattern_classification'],
                    'classification_stable': p['block_pattern_classification'] == s['block_pattern_classification'],
                })
        c.write_tsv(out / 'HTS67_BURNIN_SENSITIVITY.tsv', burn_rows)

        pooling_rows = []
        for edge, *_ in c.RELEASE_GRAPH_EDGES:
            for burn in BURNS:
                a = index[(edge, PRIMARY_METRIC, burn)]
                b = index[(edge, SECONDARY_METRIC, burn)]
                pooling_rows.append({
                    'edge': edge,
                    'burn_fraction_per_chain': burn,
                    'conditional4d_mahalanobis_difference': b['conditional4d_mahalanobis'] - a['conditional4d_mahalanobis'],
                    'conditional_fraction_difference': b['conditional_fraction_full_distance_squared'] - a['conditional_fraction_full_distance_squared'],
                    'baryon_tilt_share_difference': b['baryon_tilt_shapley_share'] - a['baryon_tilt_shapley_share'],
                    'order_sensitivity_difference': b['order_sensitivity_fraction'] - a['order_sensitivity_fraction'],
                    'max_canonical_correlation_difference': b['max_block_canonical_correlation'] - a['max_block_canonical_correlation'],
                    'arithmetic_classification': a['block_pattern_classification'],
                    'precision_mean_classification': b['block_pattern_classification'],
                    'classification_stable': a['block_pattern_classification'] == b['block_pattern_classification'],
                })
        c.write_tsv(out / 'HTS67_SYMMETRIC_POOLING_SENSITIVITY.tsv', pooling_rows)

        runtime_path = stage_cache / 'HTS67_RUNTIME_ROOTS.json'
        runtime_path.write_text(json.dumps({
            'roots': runtime_roots,
            'hts62_results': str(hts62_path),
            'hts66_results': str(hts66_path),
        }, indent=2) + '\n', encoding='utf-8')

        for name in DOCS:
            shutil.copy2(pkg / name, out / name)
        proc = subprocess.run([
            sys.executable, str(pkg / 'audit_hts67.py'),
            '--output-dir', str(out), '--runtime-json', str(runtime_path),
        ], capture_output=True, text=True)
        (out / 'HTS67_AUDIT_STDOUT.txt').write_text(proc.stdout, encoding='utf-8')
        (out / 'HTS67_AUDIT_STDERR.txt').write_text(proc.stderr, encoding='utf-8')
        audit_pass = proc.returncode == 0

        primary_support = [r for r in support_rows if f(r['burn_fraction_per_chain']) == PRIMARY]
        primary_loo = [r for r in loo_rows if f(r['burn_fraction_per_chain']) == PRIMARY]
        primary_rows = [r for r in rows if f(r['burn_fraction_per_chain']) == PRIMARY]
        primary_pooling = [r for r in pooling_rows if f(r['burn_fraction_per_chain']) == PRIMARY]
        primary_comparison = [r for r in comparisons if f(r['burn_fraction_per_chain']) == PRIMARY and r['metric'] == PRIMARY_METRIC]

        min_kish = min(f(r['kish_effective_rows']) for r in primary_support)
        max_weight_share = max(f(r['weight_share']) for r in primary_support)
        min_eig = min(f(r['metric_min_correlation_eigenvalue']) for r in rows)
        min_cond_eig = min(f(r['conditional_min_eigenvalue']) for r in rows)
        max_cond = max(f(r['metric_correlation_condition_number']) for r in rows)
        max_conditional_cond = max(f(r['conditional_correlation_condition_number']) for r in rows)
        max_decomp_closure = max(abs(f(r['decomposition_closure_error'])) for r in rows)
        max_shapley_closure = max(abs(f(r['shapley_closure_error'])) for r in rows)
        max_swap_error = max(abs(f(r['swap_invariance_max_error'])) for r in rows)
        max_loo_cond = max(abs(f(r['conditional4d_mahalanobis_drift'])) for r in primary_loo)
        max_loo_share = max(abs(f(r['baryon_tilt_share_drift'])) for r in primary_loo)
        max_loo_order = max(abs(f(r['order_sensitivity_drift'])) for r in primary_loo)
        max_loo_corr = max(abs(f(r['max_canonical_correlation_drift'])) for r in primary_loo)
        max_burn_cond = max(abs(f(r['conditional4d_mahalanobis_change'])) for r in burn_rows)
        max_burn_share = max(abs(f(r['baryon_tilt_share_change'])) for r in burn_rows)
        max_burn_order = max(abs(f(r['order_sensitivity_change'])) for r in burn_rows)
        max_burn_corr = max(abs(f(r['max_canonical_correlation_change'])) for r in burn_rows)
        max_pool_share = max(abs(f(r['baryon_tilt_share_difference'])) for r in pooling_rows)
        max_pool_order = max(abs(f(r['order_sensitivity_difference'])) for r in pooling_rows)
        pool_primary_class_agreement = sum(str(r['classification_stable']).lower() == 'true' for r in primary_pooling)
        directed_consensus_edges = [r for r in primary_comparison if bool(r['directed_pair_agrees'])]
        directed_consensus_preserved = sum(r['comparison_classification'] == 'DIRECTED_CONSENSUS_PRESERVED' for r in directed_consensus_edges)
        directionally_disagreeing_edges = sum(not bool(r['directed_pair_agrees']) for r in primary_comparison)

        gates = {
            'support_gate_pass': min_kish >= 100 and max_weight_share <= 0.35,
            'numerical_condition_gate_pass': min_eig >= 1e-8 and min_cond_eig >= 1e-6 and max_cond <= 1e8 and max_conditional_cond <= 500,
            'closure_and_symmetry_gate_pass': max_decomp_closure <= 1e-8 and max_shapley_closure <= 1e-8 and max_swap_error <= 1e-10,
            'loo_stability_gate_pass': max_loo_cond <= 0.25 and max_loo_share <= 0.15 and max_loo_order <= 0.15 and max_loo_corr <= 0.10,
            'burnin_stability_gate_pass': max_burn_cond <= 0.25 and max_burn_share <= 0.15 and max_burn_order <= 0.15 and max_burn_corr <= 0.10,
            'symmetric_pooling_robustness_gate_pass': max_pool_share <= 0.15 and max_pool_order <= 0.15 and pool_primary_class_agreement >= 6,
            'independent_audit_pass': audit_pass,
        }

        technical = all(v for k, v in gates.items() if k != 'symmetric_pooling_robustness_gate_pass')
        if not technical:
            classification = 'HOLD_SYMMETRIC_METRIC_NUMERICAL_OR_STABILITY_FAILURE'
            branch_decision = 'DO_NOT_CLOSE_METRIC_DIRECTIONALITY_QUESTION'
        elif not gates['symmetric_pooling_robustness_gate_pass']:
            classification = 'HOLD_SYMMETRIC_POOLING_CONVENTION_SENSITIVITY'
            branch_decision = 'DO_NOT_CLOSE_METRIC_DIRECTIONALITY_QUESTION'
        elif directed_consensus_preserved == len(directed_consensus_edges):
            classification = 'PASS_SYMMETRIC_METRIC_ROBUSTNESS_AND_DIRECTIONALITY_CLOSEOUT'
            branch_decision = 'CLOSE_POSTERIOR_METRIC_DIRECTIONALITY_QUESTION_WITH_SCOPE'
        else:
            classification = 'PASS_SYMMETRIC_METRIC_AUDIT_WITH_DIRECTIONALITY_LIMITATION_AND_CLOSEOUT'
            branch_decision = 'CLOSE_POSTERIOR_METRIC_DIRECTIONALITY_QUESTION_WITH_LIMITED_BLOCK_PATTERN_CLAIMS'

        c.write_tsv(out / 'HTS67_CLASSIFICATION.tsv', [{
            'classification': classification,
            'primary_symmetric_metric': PRIMARY_METRIC,
            'sensitivity_symmetric_metric': SECONDARY_METRIC,
            'primary_burn_fraction_per_chain': PRIMARY,
            'sensitivity_burn_fraction_per_chain': SENSITIVITY,
            'min_chain_kish_effective_rows': min_kish,
            'max_chain_weight_share': max_weight_share,
            'min_metric_correlation_eigenvalue': min_eig,
            'min_conditional_eigenvalue': min_cond_eig,
            'max_metric_correlation_condition_number': max_cond,
            'max_conditional_correlation_condition_number': max_conditional_cond,
            'max_decomposition_closure_error': max_decomp_closure,
            'max_shapley_closure_error': max_shapley_closure,
            'max_swap_invariance_error': max_swap_error,
            'max_LOO_conditional4d_mahalanobis_drift': max_loo_cond,
            'max_LOO_baryon_tilt_share_drift': max_loo_share,
            'max_LOO_order_sensitivity_drift': max_loo_order,
            'max_LOO_canonical_correlation_drift': max_loo_corr,
            'max_burn_conditional4d_mahalanobis_change': max_burn_cond,
            'max_burn_baryon_tilt_share_change': max_burn_share,
            'max_burn_order_sensitivity_change': max_burn_order,
            'max_burn_canonical_correlation_change': max_burn_corr,
            'max_pooling_baryon_tilt_share_difference': max_pool_share,
            'max_pooling_order_sensitivity_difference': max_pool_order,
            'primary_pooling_classification_agreement_count': pool_primary_class_agreement,
            'primary_directed_consensus_edge_count': len(directed_consensus_edges),
            'primary_directed_consensus_preserved_count': directed_consensus_preserved,
            'primary_directionally_disagreeing_edge_count': directionally_disagreeing_edges,
            **gates,
            'branch_decision': branch_decision,
            'interpretation_boundary': 'Symmetric pooled posterior covariance geometry only; not independent tension significance, causal likelihood contribution, or uniquely physical block attribution.',
        }])

        report = f'''# HTS67 execution report

`{classification}`

HTS67 replaced the frozen directed source-covariance metric with two predeclared symmetric endpoint-pair metrics. It audited the same six-dimensional split and the same fixed BARYON_TILT / TAU_AMPLITUDE bookkeeping without reopening coordinate, eigenmode or coalition attribution searches.

## Branch decision

`{branch_decision}`

## Boundary

A stable symmetric result closes only the metric-directionality robustness question for this released endpoint set. It does not establish a causal component, physical sector, independent tension significance or new cosmological model.
'''
        (out / 'HTS67_EXECUTION_REPORT.md').write_text(report, encoding='utf-8')
        (out / 'MANIFEST.json').write_text(json.dumps({
            'stage': 'HTS67',
            'classification': classification,
            'branch_decision': branch_decision,
            'primary_metric': PRIMARY_METRIC,
            'sensitivity_metric': SECONDARY_METRIC,
            'primary_burn': PRIMARY,
            'sensitivity_burn': SENSITIVITY,
            'variables': g.VARS,
            'fixed_blocks': {'BARYON_TILT': ['omega_b', 'n_s'], 'TAU_AMPLITUDE': ['tau', 'logA']},
            'boundary': 'Symmetric pooled covariance posterior geometry only.',
        }, indent=2) + '\n', encoding='utf-8')
        c.make_zip(out, zip_out)
        print(classification)
        print(zip_out)
    except Exception as exc:
        (out / 'HTS67_RUNTIME_FAILURE.txt').write_text(traceback.format_exc(), encoding='utf-8')
        for name in DOCS:
            if (pkg / name).exists():
                shutil.copy2(pkg / name, out / name)
        c.write_tsv(out / 'HTS67_CLASSIFICATION.tsv', [{
            'classification': 'HOLD_SOURCE_MATERIALIZATION_OR_SYMMETRIC_METRIC_AUDIT_FAILURE',
            'error': str(exc),
            'branch_decision': 'DO_NOT_CLOSE_METRIC_DIRECTIONALITY_QUESTION',
        }])
        (out / 'HTS67_EXECUTION_REPORT.md').write_text(
            '# HTS67 execution report\n\n`HOLD_SOURCE_MATERIALIZATION_OR_SYMMETRIC_METRIC_AUDIT_FAILURE`\n\n```text\n' + str(exc) + '\n```\n',
            encoding='utf-8',
        )
        c.make_zip(out, zip_out)
        print('HOLD_SOURCE_MATERIALIZATION_OR_SYMMETRIC_METRIC_AUDIT_FAILURE')
        print(zip_out)


if __name__ == '__main__':
    main()
