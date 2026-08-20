#!/usr/bin/env python3
from __future__ import annotations

import numpy as np

import hts67_metric as g


def main() -> None:
    rng = np.random.default_rng(67)
    n = 16000
    transform = np.array([
        [1, 0, 0, 0, 0, 0],
        [.35, 1, 0, 0, 0, 0],
        [.25, .10, 1, 0, 0, 0],
        [.10, .25, .30, 1, 0, 0],
        [.20, -.10, .15, .20, 1, 0],
        [-.10, .20, .20, .35, .10, 1],
    ], dtype=float)
    X = rng.normal(size=(n, 6)) @ transform.T
    Y = rng.normal(size=(n, 6)) @ (transform * np.array([1.05, .95, 1.10, .90, 1.08, .92])[:, None]).T
    Y += np.array([.5, -.2, .15, .3, -.1, .25])
    weights_a = np.exp(rng.normal(0, .15, n))
    weights_b = np.exp(rng.normal(0, .18, n))
    ids = np.array([f'CLASS.{i % 8 + 1}.txt' for i in range(n)], dtype=object)
    A = g.endpoint_detail({key: X[:, i] for i, key in enumerate(g.VARS)}, weights_a, ids)
    B = g.endpoint_detail({key: Y[:, i] for i, key in enumerate(g.VARS)}, weights_b, ids)
    for metric in g.METRICS:
        row = g.symmetric_metric_row('E', 'TEST', 'boundary', .3, 'A', 'B', A, B, metric)
        assert abs(row['full6d_distance_squared'] - row['tn2d_distance_squared'] - row['conditional4d_distance_squared']) < 1e-9
        assert abs(row['baryon_tilt_shapley_share'] + row['tau_amplitude_shapley_share'] - 1.0) < 1e-10
        assert row['swap_invariance_max_error'] < 1e-12
        assert 0 <= row['max_block_canonical_correlation'] <= 1
    same_a = g.endpoint_detail({key: X[:, i] for i, key in enumerate(g.VARS)}, weights_a, ids)
    shifted = X + np.array([.2, .1, -.05, .08, .03, -.07])
    same_b = g.endpoint_detail({key: shifted[:, i] for i, key in enumerate(g.VARS)}, weights_a, ids)
    arithmetic = g.symmetric_metric_row('S', 'TEST', 'boundary', .3, 'A', 'B', same_a, same_b, g.METRICS[0])
    precision = g.symmetric_metric_row('S', 'TEST', 'boundary', .3, 'A', 'B', same_a, same_b, g.METRICS[1])
    assert abs(arithmetic['full6d_distance_squared'] - precision['full6d_distance_squared']) < 1e-9
    assert abs(arithmetic['baryon_tilt_shapley_share'] - precision['baryon_tilt_shapley_share']) < 1e-9
    print('HTS67 SELFTEST PASS')


if __name__ == '__main__':
    main()
