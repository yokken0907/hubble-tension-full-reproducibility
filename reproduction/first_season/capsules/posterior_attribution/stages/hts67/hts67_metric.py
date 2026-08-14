#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any

import numpy as np

VARS = ('tangent_DESI_sigma', 'normal_DESI_sigma', 'omega_b', 'tau', 'n_s', 'logA')
AUX = VARS[2:]
BARYON_IDX = np.array([0, 2], dtype=int)  # omega_b, n_s within AUX
TAU_IDX = np.array([1, 3], dtype=int)     # tau, logA within AUX
METRICS = ('ARITHMETIC_COVARIANCE_POOL', 'PRECISION_MEAN_POOL')


def wmean_matrix(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    return np.sum(X * w[:, None], axis=0) / float(np.sum(w))


def wcov_matrix(X: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sw = float(np.sum(w))
    mean = wmean_matrix(X, w)
    centered = X - mean
    cov = (centered * w[:, None]).T @ centered / sw
    return mean, (cov + cov.T) / 2.0


def kish(w: np.ndarray) -> float:
    return float(np.sum(w) ** 2 / np.sum(w * w))


def endpoint_detail(data: dict[str, np.ndarray], weights: np.ndarray, ids: np.ndarray) -> dict[str, Any]:
    X = np.column_stack([np.asarray(data[key], dtype=float) for key in VARS])
    w = np.asarray(weights, dtype=float)
    ids = np.asarray(ids, dtype=object)
    mean, cov = wcov_matrix(X, w)
    sd = np.sqrt(np.diag(cov))
    if np.any(~np.isfinite(sd)) or np.any(sd <= 0):
        raise RuntimeError('non-positive endpoint scale')
    corr = cov / np.outer(sd, sd)
    corr = (corr + corr.T) / 2.0
    eig = np.linalg.eigvalsh(corr)
    if np.any(~np.isfinite(eig)) or eig[0] <= 0:
        raise RuntimeError(f'non-positive endpoint correlation eigenvalue: {eig}')
    return {
        'X': X, 'w': w, 'ids': ids, 'mean': mean, 'cov': cov, 'sd': sd,
        'corr': corr, 'eig': eig, 'condition_number': float(eig[-1] / eig[0]),
    }


def subset_detail(detail: dict[str, Any], mask: np.ndarray) -> dict[str, Any]:
    X = detail['X'][mask]
    return endpoint_detail({key: X[:, i] for i, key in enumerate(VARS)}, detail['w'][mask], detail['ids'][mask])


def endpoint_row(label: str, burn: float, detail: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        'contract': label,
        'burn_fraction_per_chain': burn,
        'row_count': len(detail['w']),
        'weight_sum': float(np.sum(detail['w'])),
        'kish_effective_rows': kish(detail['w']),
        'min_correlation_eigenvalue': float(detail['eig'][0]),
        'max_correlation_eigenvalue': float(detail['eig'][-1]),
        'correlation_condition_number': detail['condition_number'],
    }
    for i, key in enumerate(VARS):
        row[f'mean_{key}'] = float(detail['mean'][i])
        row[f'sd_{key}'] = float(detail['sd'][i])
    return row


def support_rows(label: str, burn: float, detail: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    total = float(np.sum(detail['w']))
    for chain in sorted(set(detail['ids'])):
        mask = detail['ids'] == chain
        ww = detail['w'][mask]
        out.append({
            'contract': label,
            'burn_fraction_per_chain': burn,
            'chain_file': chain,
            'row_count': int(np.sum(mask)),
            'weight_sum': float(np.sum(ww)),
            'weight_share': float(np.sum(ww) / total),
            'kish_effective_rows': kish(ww),
        })
    return out


def _spd_inverse(matrix: np.ndarray, label: str) -> np.ndarray:
    matrix = (matrix + matrix.T) / 2.0
    eig = np.linalg.eigvalsh(matrix)
    if eig[0] <= 0 or not np.all(np.isfinite(eig)):
        raise RuntimeError(f'non-positive matrix in {label}: {eig}')
    return np.linalg.inv(matrix)


def symmetric_covariance(A: dict[str, Any], B: dict[str, Any], metric: str) -> np.ndarray:
    CA = A['cov']
    CB = B['cov']
    if metric == 'ARITHMETIC_COVARIANCE_POOL':
        C = 0.5 * (CA + CB)
    elif metric == 'PRECISION_MEAN_POOL':
        precision = 0.5 * (_spd_inverse(CA, 'endpoint A covariance') + _spd_inverse(CB, 'endpoint B covariance'))
        C = _spd_inverse(precision, 'mean precision')
    else:
        raise ValueError(f'unknown symmetric metric: {metric}')
    return (C + C.T) / 2.0


def _invsqrt_spd(matrix: np.ndarray) -> np.ndarray:
    matrix = (matrix + matrix.T) / 2.0
    eig, vec = np.linalg.eigh(matrix)
    if eig[0] <= 0:
        raise RuntimeError(f'non-positive matrix for inverse square root: {eig}')
    return (vec * (1.0 / np.sqrt(eig))) @ vec.T


def _block_geometry(residual: np.ndarray, conditional_cov: np.ndarray) -> dict[str, Any]:
    S = (conditional_cov + conditional_cov.T) / 2.0
    invS = _spd_inverse(S, 'conditional covariance')
    d2_total = float(residual @ invS @ residual)

    def marginal(idx: np.ndarray) -> float:
        sub = S[np.ix_(idx, idx)]
        r = residual[idx]
        return float(r @ _spd_inverse(sub, 'block marginal covariance') @ r)

    d2_b_marg = marginal(BARYON_IDX)
    d2_t_marg = marginal(TAU_IDX)
    d2_b_given_t = d2_total - d2_t_marg
    d2_t_given_b = d2_total - d2_b_marg
    phi_b = 0.5 * (d2_b_marg + d2_b_given_t)
    phi_t = 0.5 * (d2_t_marg + d2_t_given_b)
    closure = phi_b + phi_t - d2_total
    if d2_total > 0:
        share_b = phi_b / d2_total
        share_t = phi_t / d2_total
        order_fraction = abs(d2_b_marg - d2_b_given_t) / d2_total
    else:
        share_b = share_t = 0.5
        order_fraction = 0.0

    Sbb = S[np.ix_(BARYON_IDX, BARYON_IDX)]
    Stt = S[np.ix_(TAU_IDX, TAU_IDX)]
    Sbt = S[np.ix_(BARYON_IDX, TAU_IDX)]
    whitened = _invsqrt_spd(Sbb) @ Sbt @ _invsqrt_spd(Stt)
    canonical = np.linalg.svd(whitened, compute_uv=False)
    canonical = np.sort(np.clip(canonical, 0.0, 1.0))[::-1]

    if order_fraction > 0.20:
        pattern = 'ORDER_SENSITIVE'
    elif share_b >= 0.60:
        pattern = 'BARYON_TILT_DOMINANT'
    elif share_b <= 0.40:
        pattern = 'TAU_AMPLITUDE_DOMINANT'
    else:
        pattern = 'MIXED_BLOCK'

    return {
        'conditional4d_distance_squared': d2_total,
        'conditional4d_mahalanobis': math.sqrt(max(d2_total, 0.0)),
        'baryon_tilt_marginal_distance_squared': d2_b_marg,
        'tau_amplitude_given_baryon_tilt_distance_squared': d2_t_given_b,
        'tau_amplitude_marginal_distance_squared': d2_t_marg,
        'baryon_tilt_given_tau_amplitude_distance_squared': d2_b_given_t,
        'baryon_tilt_shapley_distance_squared': phi_b,
        'tau_amplitude_shapley_distance_squared': phi_t,
        'baryon_tilt_shapley_share': share_b,
        'tau_amplitude_shapley_share': share_t,
        'cross_block_interaction_distance_squared': d2_total - d2_b_marg - d2_t_marg,
        'order_sensitivity_fraction': order_fraction,
        'shapley_closure_error': closure,
        'max_block_canonical_correlation': float(canonical[0]),
        'min_block_canonical_correlation': float(canonical[-1]),
        'block_pattern_classification': pattern,
    }


def _decompose(delta_raw: np.ndarray, covariance: np.ndarray) -> dict[str, Any]:
    C = (covariance + covariance.T) / 2.0
    sd = np.sqrt(np.diag(C))
    if np.any(sd <= 0):
        raise RuntimeError('non-positive symmetric metric scale')
    R = C / np.outer(sd, sd)
    R = (R + R.T) / 2.0
    eig = np.linalg.eigvalsh(R)
    if eig[0] <= 0:
        raise RuntimeError(f'non-positive symmetric correlation eigenvalue: {eig}')
    dz = delta_raw / sd
    Rtt = R[:2, :2]
    Rto = R[:2, 2:]
    Rot = R[2:, :2]
    Roo = R[2:, 2:]
    invR = _spd_inverse(R, 'symmetric full correlation')
    invT = _spd_inverse(Rtt, 'symmetric tangent-normal correlation')
    S = Roo - Rot @ invT @ Rto
    S = (S + S.T) / 2.0
    seig = np.linalg.eigvalsh(S)
    if seig[0] <= 0:
        raise RuntimeError(f'non-positive symmetric conditional eigenvalue: {seig}')
    residual = dz[2:] - Rot @ invT @ dz[:2]
    d2_full = float(dz @ invR @ dz)
    d2_tn = float(dz[:2] @ invT @ dz[:2])
    blocks = _block_geometry(residual, S)
    d2_cond = blocks['conditional4d_distance_squared']
    out: dict[str, Any] = {
        'full6d_distance_squared': d2_full,
        'tn2d_distance_squared': d2_tn,
        'full6d_mahalanobis': math.sqrt(max(d2_full, 0.0)),
        'tn2d_mahalanobis': math.sqrt(max(d2_tn, 0.0)),
        'conditional_fraction_full_distance_squared': float(d2_cond / d2_full) if d2_full > 0 else 0.0,
        'decomposition_closure_error': d2_full - d2_tn - d2_cond,
        'metric_correlation_condition_number': float(eig[-1] / eig[0]),
        'conditional_correlation_condition_number': float(seig[-1] / seig[0]),
        'metric_min_correlation_eigenvalue': float(eig[0]),
        'conditional_min_eigenvalue': float(seig[0]),
        'conditional_residual': residual,
    }
    out.update(blocks)
    return out


def symmetric_metric_row(edge: str, edge_type: str, boundary: str, burn: float,
                         label_a: str, label_b: str, A: dict[str, Any], B: dict[str, Any], metric: str) -> dict[str, Any]:
    delta = B['mean'] - A['mean']
    covariance = symmetric_covariance(A, B, metric)
    q = _decompose(delta, covariance)
    swap = _decompose(-delta, symmetric_covariance(B, A, metric))
    swap_keys = (
        'full6d_distance_squared', 'tn2d_distance_squared', 'conditional4d_distance_squared',
        'baryon_tilt_shapley_share', 'tau_amplitude_shapley_share',
        'order_sensitivity_fraction', 'max_block_canonical_correlation',
    )
    swap_error = max(abs(float(q[k]) - float(swap[k])) for k in swap_keys)
    row: dict[str, Any] = {
        'edge': edge,
        'metric': metric,
        'edge_type': edge_type,
        'interpretation_boundary': boundary,
        'burn_fraction_per_chain': burn,
        'endpoint_a': label_a,
        'endpoint_b': label_b,
        'swap_invariance_max_error': swap_error,
    }
    row.update({k: v for k, v in q.items() if k != 'conditional_residual'})
    for i, key in enumerate(AUX):
        row[f'conditional_residual_{key}'] = float(q['conditional_residual'][i])
    for i, key in enumerate(VARS):
        row[f'delta_{key}'] = float(delta[i])
    return row
