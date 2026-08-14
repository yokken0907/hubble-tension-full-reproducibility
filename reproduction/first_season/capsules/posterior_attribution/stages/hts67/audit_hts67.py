#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import hts67_common as c
import hts67_metric as g


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def ff(value: Any) -> float:
    return float(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--runtime-json', required=True)
    args = parser.parse_args()
    out = Path(args.output_dir)
    runtime = json.loads(Path(args.runtime_json).read_text())
    roots = {label: Path(rec['path']) for label, rec in runtime['roots'].items()}
    counts = {label: int(rec['count']) for label, rec in runtime['roots'].items()}

    saved = {(r['edge'], r['metric'], ff(r['burn_fraction_per_chain'])): r for r in read(out / 'HTS67_SYMMETRIC_METRIC_RESULTS.tsv')}
    saved_loo = {(r['edge'], r['metric'], ff(r['burn_fraction_per_chain']), r['omitted_endpoint'], r['omitted_chain']): r for r in read(out / 'HTS67_LOO_STABILITY.tsv')}
    details: dict[tuple[str, float], dict[str, Any]] = {}
    for burn in (0.3, 0.5):
        for label in c.ORDER:
            data, weights, ids, _, _, _ = c.load_factor_root(roots[label], counts[label], burn)
            details[(label, burn)] = g.endpoint_detail(data, weights, ids)

    max_error = 0.0
    max_closure = 0.0
    max_swap = 0.0
    for edge, a_label, b_label, edge_type, boundary in c.RELEASE_GRAPH_EDGES:
        for burn in (0.3, 0.5):
            A = details[(a_label, burn)]
            B = details[(b_label, burn)]
            for metric in g.METRICS:
                result = g.symmetric_metric_row(edge, edge_type, boundary, burn, a_label, b_label, A, B, metric)
                expected = saved[(edge, metric, burn)]
                keys = (
                    'full6d_mahalanobis', 'tn2d_mahalanobis', 'conditional4d_mahalanobis',
                    'conditional_fraction_full_distance_squared', 'baryon_tilt_shapley_share',
                    'tau_amplitude_shapley_share', 'order_sensitivity_fraction',
                    'max_block_canonical_correlation', 'decomposition_closure_error',
                    'shapley_closure_error', 'swap_invariance_max_error',
                )
                for key in keys:
                    max_error = max(max_error, abs(ff(result[key]) - ff(expected[key])))
                max_closure = max(max_closure, abs(ff(result['decomposition_closure_error'])), abs(ff(result['shapley_closure_error'])))
                max_swap = max(max_swap, abs(ff(result['swap_invariance_max_error'])))
                for endpoint_label, endpoint_side, detail in ((a_label, 'ENDPOINT_A', A), (b_label, 'ENDPOINT_B', B)):
                    for chain in sorted(set(detail['ids'])):
                        sub = g.subset_detail(detail, detail['ids'] != chain)
                        AA = sub if endpoint_side == 'ENDPOINT_A' else A
                        BB = sub if endpoint_side == 'ENDPOINT_B' else B
                        loo = g.symmetric_metric_row(edge, edge_type, boundary, burn, a_label, b_label, AA, BB, metric)
                        expected_loo = saved_loo[(edge, metric, burn, endpoint_label, chain)]
                        values = {
                            'conditional4d_mahalanobis_drift': loo['conditional4d_mahalanobis'] - result['conditional4d_mahalanobis'],
                            'baryon_tilt_share_drift': loo['baryon_tilt_shapley_share'] - result['baryon_tilt_shapley_share'],
                            'order_sensitivity_drift': loo['order_sensitivity_fraction'] - result['order_sensitivity_fraction'],
                            'max_canonical_correlation_drift': loo['max_block_canonical_correlation'] - result['max_block_canonical_correlation'],
                        }
                        for key, value in values.items():
                            max_error = max(max_error, abs(value - ff(expected_loo[key])))

    checks = [
        {'check': 'raw_chain_symmetric_metric_and_LOO_reconstruction_max_error', 'observed': max_error, 'required': '<=1e-9', 'result': 'PASS' if max_error <= 1e-9 else 'FAIL'},
        {'check': 'decomposition_and_shapley_closure_max_error', 'observed': max_closure, 'required': '<=1e-8', 'result': 'PASS' if max_closure <= 1e-8 else 'FAIL'},
        {'check': 'endpoint_swap_invariance_max_error', 'observed': max_swap, 'required': '<=1e-10', 'result': 'PASS' if max_swap <= 1e-10 else 'FAIL'},
    ]
    support = read(out / 'HTS67_CHAIN_SUPPORT.tsv')
    for burn in (0.3, 0.5):
        for label in c.ORDER:
            total = sum(ff(r['weight_share']) for r in support if r['contract'] == label and ff(r['burn_fraction_per_chain']) == burn)
            checks.append({'check': f'{label}_{burn}_weight_share_sum', 'observed': total, 'required': '1 within 1e-10', 'result': 'PASS' if abs(total - 1.0) <= 1e-10 else 'FAIL'})
    c.write_tsv(out / 'HTS67_INDEPENDENT_AUDIT_CHECKS.tsv', checks)
    ok = all(r['result'] == 'PASS' for r in checks)
    (out / 'HTS67_INDEPENDENT_AUDIT_RESULT.md').write_text('# HTS67 independent audit result\n\n`' + ('PASS' if ok else 'FAIL') + '`\n', encoding='utf-8')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
