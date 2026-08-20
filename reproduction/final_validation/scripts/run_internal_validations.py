#!/usr/bin/env python3
"""Self-contained project-internal mathematical validation runner."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import platform
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, Callable

import numpy as np
import scipy
import scipy.linalg


ATOL = 1.0e-10
EXPECTED_H0 = 73.49875364360662
EXPECTED_DELTA_H0 = -0.052445422611000936


class ValidationError(RuntimeError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def public_solution(
    coeffs: np.ndarray,
    observations: np.ndarray,
    precision: np.ndarray,
    ihub: int,
) -> dict[str, Any]:
    normal = coeffs.T @ precision @ coeffs
    normal = 0.5 * (normal + normal.T)
    rhs = coeffs.T @ precision @ observations
    parameters = scipy.linalg.solve(normal, rhs, assume_a="sym")
    covariance = scipy.linalg.inv(normal)
    logh0 = float(parameters[ihub])
    h0 = float(10.0**logh0)
    return {
        "parameters": parameters,
        "normal": normal,
        "rhs": rhs,
        "logh0": logh0,
        "h0": h0,
        "logh0_variance": float(covariance[ihub, ihub]),
    }


def precision_scipy(covariance: np.ndarray) -> tuple[np.ndarray, int]:
    precision, rank = scipy.linalg.pinv(
        covariance, atol=ATOL, rtol=0.0, return_rank=True
    )
    return precision, int(rank)


def precision_svd(covariance: np.ndarray) -> tuple[np.ndarray, int]:
    u, singular, vh = scipy.linalg.svd(
        covariance,
        full_matrices=False,
        check_finite=True,
        lapack_driver="gesvd",
    )
    retained = singular > ATOL
    precision = (vh.T[:, retained] / singular[retained]) @ u.T[retained, :]
    precision = 0.5 * (precision + precision.T)
    return precision, int(np.count_nonzero(retained))


def spectral_components(covariance: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    eigenvalues, eigenvectors = scipy.linalg.eigh(
        0.5 * (covariance + covariance.T),
        check_finite=True,
        driver="evd",
    )
    retained = eigenvalues > ATOL
    return eigenvalues, eigenvectors, retained


def precision_eigh(covariance: np.ndarray) -> tuple[np.ndarray, int]:
    eigenvalues, eigenvectors, retained = spectral_components(covariance)
    selected = eigenvectors[:, retained]
    precision = (selected / eigenvalues[retained]) @ selected.T
    precision = 0.5 * (precision + precision.T)
    return precision, int(np.count_nonzero(retained))


def support_solution(
    coeffs: np.ndarray,
    observations: np.ndarray,
    covariance: np.ndarray,
    ihub: int,
) -> tuple[dict[str, Any], int]:
    eigenvalues, eigenvectors, retained = spectral_components(covariance)
    selected = eigenvectors[:, retained]
    roots = np.sqrt(eigenvalues[retained])
    design = (selected.T @ coeffs) / roots[:, None]
    data = (selected.T @ observations) / roots
    parameters, _, rank, _ = scipy.linalg.lstsq(
        design, data, cond=None, lapack_driver="gelsy"
    )
    normal = design.T @ design
    rhs = design.T @ data
    covariance_parameters = scipy.linalg.inv(normal)
    logh0 = float(parameters[ihub])
    return (
        {
            "parameters": parameters,
            "normal": normal,
            "rhs": rhs,
            "logh0": logh0,
            "h0": float(10.0**logh0),
            "logh0_variance": float(covariance_parameters[ihub, ihub]),
            "design_rank": int(rank),
        },
        int(np.count_nonzero(retained)),
    )


def decimal_linear_solve(matrix: np.ndarray, vector: np.ndarray) -> list[Decimal]:
    with localcontext() as context:
        context.prec = 80
        n = int(matrix.shape[0])
        augmented = [
            [Decimal(repr(float(matrix[i, j]))) for j in range(n)]
            + [Decimal(repr(float(vector[i])))]
            for i in range(n)
        ]
        for column in range(n):
            pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
            if augmented[pivot][column] == 0:
                raise ValidationError("singular decimal normal system")
            if pivot != column:
                augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
            pivot_value = augmented[column][column]
            for row in range(column + 1, n):
                factor = augmented[row][column] / pivot_value
                augmented[row][column] = Decimal(0)
                for j in range(column + 1, n + 1):
                    augmented[row][j] -= factor * augmented[column][j]
        answer = [Decimal(0)] * n
        for row in range(n - 1, -1, -1):
            residual = augmented[row][n] - sum(
                augmented[row][j] * answer[j] for j in range(row + 1, n)
            )
            answer[row] = residual / augmented[row][row]
        return answer


def decimal_h0(normal: np.ndarray, rhs: np.ndarray, ihub: int) -> Decimal:
    with localcontext() as context:
        context.prec = 80
        solution = decimal_linear_solve(normal, rhs)
        return (solution[ihub] * Decimal(10).ln()).exp()


def rational_rank_one_estimate(v: list[Fraction], a: list[Fraction], y: list[Fraction]) -> Fraction:
    numerator = sum(vi * yi for vi, yi in zip(v, y))
    denominator = sum(vi * ai for vi, ai in zip(v, a))
    return numerator / denominator


def exact_synthetic_h0dn() -> dict[str, Any]:
    one = Fraction(1, 1)
    zero = Fraction(0, 1)
    v = [one, one]
    a = [one, one]
    y = [one, zero]
    baseline = rational_rank_one_estimate(v, a, y)
    scaled_v = [one, Fraction(2, 1)]
    scaled_a = [one, Fraction(2, 1)]
    scaled_y = [one, zero]
    scaled = rational_rank_one_estimate(scaled_v, scaled_a, scaled_y)
    rotated_v = [-one, one]
    rotated_a = [-one, one]
    rotated_y = [zero, one]
    rotated = rational_rank_one_estimate(rotated_v, rotated_a, rotated_y)
    null_a = a[0] - a[1]
    null_y = y[0] - y[1]
    scaled_null_a = Fraction(2, 1) * scaled_a[0] - scaled_a[1]
    scaled_null_y = Fraction(2, 1) * scaled_y[0] - scaled_y[1]
    passed = (
        baseline == Fraction(1, 2)
        and scaled == Fraction(1, 5)
        and rotated == Fraction(1, 2)
        and null_a == 0
        and null_y != 0
        and scaled_null_a == 0
        and scaled_null_y != 0
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "baseline_estimate": str(baseline),
        "nonorthogonal_scaled_estimate": str(scaled),
        "orthogonally_rotated_estimate": str(rotated),
        "scaled_minus_baseline": str(scaled - baseline),
        "rank_original": 1,
        "rank_scaled": 1,
        "null_vector_dot_A_original": str(null_a),
        "null_vector_dot_y_original": str(null_y),
        "null_vector_dot_A_scaled": str(scaled_null_a),
        "null_vector_dot_y_scaled": str(scaled_null_y),
        "support_feasible_original": False,
        "support_feasible_scaled": False,
    }


def exact_synthetic_sn() -> dict[str, Any]:
    first = [Fraction(-1), Fraction(0), Fraction(1)]
    second = [Fraction(-2), Fraction(0), Fraction(2)]
    mean_first = sum(first) / len(first)
    mean_second = sum(second) / len(second)
    variance = Fraction(1, len(first))
    chi2_first = sum((value - mean_first) ** 2 for value in first)
    chi2_second = sum((value - mean_second) ** 2 for value in second)
    passed = (
        mean_first == mean_second == 0
        and variance == Fraction(1, 3)
        and chi2_first == 2
        and chi2_second == 8
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "compressed_mean_first": str(mean_first),
        "compressed_mean_second": str(mean_second),
        "compressed_variance_both": str(variance),
        "residual_chi2_first": str(chi2_first),
        "residual_chi2_second": str(chi2_second),
    }


def make_check(
    identifier: str,
    description: str,
    observed: Any,
    requirement: str,
    passed: bool,
) -> dict[str, Any]:
    return {
        "check_id": identifier,
        "description": description,
        "observed": observed,
        "requirement": requirement,
        "status": "PASS" if passed else "FAIL",
    }


def validate_h0dn(vector_path: pathlib.Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with np.load(vector_path, allow_pickle=False) as archive:
        coeffs = np.asarray(archive["coeffs"], dtype=np.float64)
        observations = np.asarray(archive["observations"], dtype=np.float64)
        covariance = np.asarray(archive["covariance"], dtype=np.float64)
        ihub = int(archive["ihub"][0])
    scaling = 1.0 / np.sqrt(np.diag(covariance))
    coeffs_scaled = scaling[:, None] * coeffs
    observations_scaled = scaling * observations
    covariance_scaled = scaling[:, None] * covariance * scaling[None, :]

    methods: dict[str, dict[str, Any]] = {}
    precisions: dict[str, tuple[Callable[[np.ndarray], tuple[np.ndarray, int]], str]] = {
        "scipy_pinv": (precision_scipy, "SciPy pinv"),
        "svd_gesvd": (precision_svd, "explicit SVD gesvd"),
        "eigh_evd": (precision_eigh, "symmetric eigh evd"),
    }
    raw_solutions: dict[str, tuple[dict[str, Any], dict[str, Any], np.ndarray, np.ndarray]] = {}
    for key, (builder, label) in precisions.items():
        precision, rank = builder(covariance)
        precision_scaled, rank_scaled = builder(covariance_scaled)
        original = public_solution(coeffs, observations, precision, ihub)
        standardized = public_solution(
            coeffs_scaled, observations_scaled, precision_scaled, ihub
        )
        methods[key] = {
            "label": label,
            "rank_original": rank,
            "rank_standardized": rank_scaled,
            "h0_original": original["h0"],
            "h0_standardized": standardized["h0"],
            "delta_h0": standardized["h0"] - original["h0"],
        }
        raw_solutions[key] = (original, standardized, precision, precision_scaled)

    support_original, support_rank = support_solution(
        coeffs, observations, covariance, ihub
    )
    support_scaled, support_rank_scaled = support_solution(
        coeffs_scaled, observations_scaled, covariance_scaled, ihub
    )
    methods["support_gelsy"] = {
        "label": "retained-support whitening plus gelsy",
        "rank_original": support_rank,
        "rank_standardized": support_rank_scaled,
        "h0_original": support_original["h0"],
        "h0_standardized": support_scaled["h0"],
        "delta_h0": support_scaled["h0"] - support_original["h0"],
    }

    eigen_original = raw_solutions["eigh_evd"][0]
    eigen_scaled = raw_solutions["eigh_evd"][1]
    decimal_original = decimal_h0(eigen_original["normal"], eigen_original["rhs"], ihub)
    decimal_scaled = decimal_h0(eigen_scaled["normal"], eigen_scaled["rhs"], ihub)
    decimal_record = {
        "precision_digits": 80,
        "h0_original": str(decimal_original),
        "h0_standardized": str(decimal_scaled),
        "delta_h0": str(decimal_scaled - decimal_original),
        "absolute_difference_from_double_original": float(
            abs(decimal_original - Decimal(repr(eigen_original["h0"])))
        ),
        "absolute_difference_from_double_standardized": float(
            abs(decimal_scaled - Decimal(repr(eigen_scaled["h0"])))
        ),
    }

    reference_precision = raw_solutions["scipy_pinv"][2]
    standardized_precision = raw_solutions["scipy_pinv"][3]
    mapped_precision = scaling[:, None] * standardized_precision * scaling[None, :]
    congruence_defect = float(
        np.linalg.norm(mapped_precision - reference_precision, ord="fro")
        / np.linalg.norm(reference_precision, ord="fro")
    )

    eigenvalues, eigenvectors, retained = spectral_components(covariance)
    null_basis = eigenvectors[:, ~retained]
    null_design_norm = float(np.linalg.norm(null_basis.T @ coeffs, ord="fro"))
    null_data_norm = float(np.linalg.norm(null_basis.T @ observations))

    rng = np.random.default_rng(20260809)
    orthogonal_rows: list[dict[str, Any]] = []
    reference_h0 = methods["eigh_evd"]["h0_original"]
    for trial in range(4):
        raw = rng.normal(size=(covariance.shape[0], covariance.shape[0]))
        q, r = np.linalg.qr(raw)
        signs = np.where(np.diag(r) < 0.0, -1.0, 1.0)
        q = q * signs
        rotated_covariance = q @ covariance @ q.T
        rotated_precision, rotated_rank = precision_eigh(rotated_covariance)
        rotated = public_solution(q @ coeffs, q @ observations, rotated_precision, ihub)
        orthogonal_rows.append(
            {
                "trial": trial,
                "rank": rotated_rank,
                "h0": rotated["h0"],
                "delta_h0": rotated["h0"] - reference_h0,
            }
        )
    maximum_orthogonal_delta = max(abs(row["delta_h0"]) for row in orthogonal_rows)

    deltas = [float(item["delta_h0"]) for item in methods.values()]
    checks: list[dict[str, Any]] = []
    checks.append(make_check("H0-001", "test-vector shapes", [list(coeffs.shape), list(covariance.shape)], "[255x64,255x255]", coeffs.shape == (255, 64) and covariance.shape == (255, 255)))
    checks.append(make_check("H0-002", "rank preserved in all decompositions", [[item["rank_original"], item["rank_standardized"]] for item in methods.values()], "all 183/183", all(item["rank_original"] == 183 and item["rank_standardized"] == 183 for item in methods.values())))
    checks.append(make_check("H0-003", "baseline H0", methods["eigh_evd"]["h0_original"], f"abs difference <=5e-9 from {EXPECTED_H0}", abs(methods["eigh_evd"]["h0_original"] - EXPECTED_H0) <= 5e-9))
    for index, (key, item) in enumerate(methods.items(), start=4):
        checks.append(make_check(f"H0-{index:03d}", f"{key} standardized-minus-original H0", item["delta_h0"], f"abs difference <=5e-8 from {EXPECTED_DELTA_H0}", abs(item["delta_h0"] - EXPECTED_DELTA_H0) <= 5e-8))
    checks.append(make_check("H0-008", "cross-implementation delta spread", max(deltas) - min(deltas), "<=5e-8", max(deltas) - min(deltas) <= 5e-8))
    checks.append(make_check("H0-009", "80-digit original normal solve", decimal_record["absolute_difference_from_double_original"], "<=5e-9", decimal_record["absolute_difference_from_double_original"] <= 5e-9))
    checks.append(make_check("H0-010", "80-digit standardized normal solve", decimal_record["absolute_difference_from_double_standardized"], "<=5e-9", decimal_record["absolute_difference_from_double_standardized"] <= 5e-9))
    checks.append(make_check("H0-011", "dense orthogonal invariance", maximum_orthogonal_delta, "<=5e-8", maximum_orthogonal_delta <= 5e-8 and all(row["rank"] == 183 for row in orthogonal_rows)))
    checks.append(make_check("H0-012", "non-orthogonal Moore-Penrose congruence defect", congruence_defect, ">1e-6", congruence_defect > 1e-6))
    checks.append(make_check("H0-013", "nullspace projected design norm", null_design_norm, "<=1e-10", null_design_norm <= 1e-10))
    checks.append(make_check("H0-014", "nullspace projected data norm", null_data_norm, ">1e-4", null_data_norm > 1e-4))

    synthetic = exact_synthetic_h0dn()
    checks.append(make_check("H0-015", "exact rational mechanism fixture", synthetic["status"], "PASS", synthetic["status"] == "PASS"))
    result = {
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "test_vector_sha256": sha256_file(vector_path),
        "methods": methods,
        "decimal_normal_solve": decimal_record,
        "orthogonal_trials": orthogonal_rows,
        "maximum_absolute_orthogonal_delta_h0": maximum_orthogonal_delta,
        "moore_penrose_congruence_relative_frobenius_defect": congruence_defect,
        "support": {
            "covariance_nullity": int(np.count_nonzero(~retained)),
            "projected_design_frobenius_norm": null_design_norm,
            "projected_data_l2_norm": null_data_norm,
        },
        "exact_synthetic_mechanism": synthetic,
    }
    return result, checks


def validate_sn(vector_path: pathlib.Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with np.load(vector_path, allow_pickle=False) as archive:
        data = np.asarray(archive["data_alpha"], dtype=np.float64)
        covariance = np.asarray(archive["covariance_alpha"], dtype=np.float64)
    ones = np.ones_like(data)
    factor = scipy.linalg.cho_factor(covariance, lower=True, check_finite=True)
    precision_ones = scipy.linalg.cho_solve(factor, ones, check_finite=True)
    precision_data = scipy.linalg.cho_solve(factor, data, check_finite=True)
    information = float(ones @ precision_ones)
    variance = 1.0 / information
    alpha = float(variance * (ones @ precision_data))
    residual = data - alpha
    precision_residual = scipy.linalg.cho_solve(factor, residual, check_finite=True)
    chi2 = float(residual @ precision_residual)

    eigenvalues, eigenvectors = scipy.linalg.eigh(covariance, driver="evd")
    eigen_precision = (eigenvectors / eigenvalues) @ eigenvectors.T
    eigen_information = float(ones @ eigen_precision @ ones)
    eigen_variance = 1.0 / eigen_information
    eigen_alpha = float(eigen_variance * (ones @ eigen_precision @ data))
    eigen_residual = data - eigen_alpha
    eigen_chi2 = float(eigen_residual @ eigen_precision @ eigen_residual)

    offsets = [-8.0, -4.0, -1.0, 0.0, 1.0, 4.0, 8.0]
    profile: list[dict[str, Any]] = []
    sigma = math.sqrt(variance)
    for offset in offsets:
        trial = alpha + offset * sigma
        delta = data - trial
        full = float(delta @ scipy.linalg.cho_solve(factor, delta, check_finite=True))
        expected = chi2 + (trial - alpha) ** 2 / variance
        profile.append(
            {
                "offset_sigma": offset,
                "full_chi2": full,
                "complete_square_chi2": expected,
                "residual": full - expected,
            }
        )
    maximum_identity_residual = max(abs(row["residual"]) for row in profile)
    synthetic = exact_synthetic_sn()
    checks = [
        make_check("SN-001", "test-vector dimensions", [list(data.shape), list(covariance.shape)], "[277,277x277]", data.shape == (277,) and covariance.shape == (277, 277)),
        make_check("SN-002", "one-intercept estimate", alpha, "abs difference <=5e-13 from 0.7163834210954622", abs(alpha - 0.7163834210954622) <= 5e-13),
        make_check("SN-003", "one-intercept standard error", sigma, "abs difference <=5e-13 from 0.0018926416391806472", abs(sigma - 0.0018926416391806472) <= 5e-13),
        make_check("SN-004", "parameter-independent residual chi-square", chi2, "abs difference <=5e-10 from 206.76063643732414", abs(chi2 - 206.76063643732414) <= 5e-10),
        make_check("SN-005", "Cholesky/eigendecomposition alpha", abs(alpha - eigen_alpha), "<=5e-10", abs(alpha - eigen_alpha) <= 5e-10),
        make_check("SN-006", "Cholesky/eigendecomposition variance", abs(variance - eigen_variance), "<=5e-10", abs(variance - eigen_variance) <= 5e-10),
        make_check("SN-007", "Cholesky/eigendecomposition chi-square", abs(chi2 - eigen_chi2), "<=5e-10", abs(chi2 - eigen_chi2) <= 5e-10),
        make_check("SN-008", "complete-square identity", maximum_identity_residual, "<=5e-9", maximum_identity_residual <= 5e-9),
        make_check("SN-009", "same compression with different residual chi-square fixture", synthetic["status"], "PASS", synthetic["status"] == "PASS"),
    ]
    result = {
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "test_vector_sha256": sha256_file(vector_path),
        "row_count": int(data.size),
        "alpha": alpha,
        "alpha_variance": variance,
        "alpha_error": sigma,
        "residual_chi2": chi2,
        "eigendecomposition": {
            "alpha": eigen_alpha,
            "alpha_variance": eigen_variance,
            "residual_chi2": eigen_chi2,
            "minimum_eigenvalue": float(eigenvalues[0]),
        },
        "complete_square_profile": profile,
        "maximum_complete_square_residual": maximum_identity_residual,
        "exact_synthetic_diagnostic_loss": synthetic,
    }
    return result, checks


def compute(root: pathlib.Path) -> dict[str, Any]:
    vector_root = root / "test_vectors"
    h0dn, h0_checks = validate_h0dn(vector_root / "h0dn_network_gls.npz")
    sn, sn_checks = validate_sn(vector_root / "sn_intercept_block.npz")
    checks = h0_checks + sn_checks
    return {
        "contract_id": "HT-FINAL-INTERNAL-CLOSURE-20260809-01",
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "h0dn": h0dn,
        "sn_compression": sn,
        "checks": checks,
        "check_count": len(checks),
        "pass_count": sum(row["status"] == "PASS" for row in checks),
        "independence_boundary": (
            "Project-internal independent linear-algebra reimplementation; "
            "not external independent replication."
        ),
    }


def write_outputs(root: pathlib.Path, result: dict[str, Any]) -> None:
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "internal_validation_results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    with (results / "validation_checks.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["check_id", "description", "observed", "requirement", "status"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in result["checks"]:
            writer.writerow(
                {
                    **row,
                    "observed": json.dumps(row["observed"], ensure_ascii=False, separators=(",", ":"))
                    if isinstance(row["observed"], (list, dict))
                    else row["observed"],
                }
            )


def verify_recorded(root: pathlib.Path, current: dict[str, Any]) -> None:
    recorded_path = root / "results" / "internal_validation_results.json"
    recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
    if current["status"] != "PASS" or recorded["status"] != "PASS":
        raise ValidationError("current or recorded validation status is not PASS")
    current_states = {row["check_id"]: row["status"] for row in current["checks"]}
    recorded_states = {row["check_id"]: row["status"] for row in recorded["checks"]}
    if current_states != recorded_states or any(value != "PASS" for value in current_states.values()):
        raise ValidationError("recorded check status drift")
    comparisons = [
        (current["h0dn"]["methods"]["eigh_evd"]["h0_original"], recorded["h0dn"]["methods"]["eigh_evd"]["h0_original"], 5e-10, "H0 baseline"),
        (current["h0dn"]["methods"]["eigh_evd"]["delta_h0"], recorded["h0dn"]["methods"]["eigh_evd"]["delta_h0"], 5e-10, "H0 delta"),
        (current["sn_compression"]["alpha"], recorded["sn_compression"]["alpha"], 5e-12, "SN alpha"),
        (current["sn_compression"]["residual_chi2"], recorded["sn_compression"]["residual_chi2"], 5e-9, "SN chi2"),
    ]
    for actual, expected, tolerance, label in comparisons:
        if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=tolerance):
            raise ValidationError(f"{label} drift")
    print(
        f"checks={current['check_count']} pass={current['pass_count']} fail=0 "
        "recorded_comparison=PASS"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--write-results", action="store_true")
    parser.add_argument("--verify-recorded", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    result = compute(root)
    if args.write_results:
        write_outputs(root, result)
    if args.verify_recorded:
        verify_recorded(root, result)
    if not args.write_results and not args.verify_recorded:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
