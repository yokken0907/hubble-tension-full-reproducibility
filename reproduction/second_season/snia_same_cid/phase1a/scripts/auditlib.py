#!/usr/bin/env python3
"""Independent routines for the frozen H0DN SN Ia Phase 1A audit."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import platform
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
import scipy
import scipy.linalg
import scipy.stats
from scipy.constants import c as C_METRES_PER_SECOND


CONTRACT_ID = "H0DN-SNIA-RESIDUAL-PHASE1A-20260730-01"
CONTRACT_FREEZE_SHA256 = (
    "a66fb62ef0be291be754f6c8cbc73a98f20c6002304fba1938e0b75f6efec7df"
)
AMENDMENT_FIELDS = (
    "amendment_id",
    "timestamp_utc",
    "changed_file",
    "reason",
    "results_observed",
    "interpretation_affected",
)
LEGACY_DUPLICATE_NAME_ROW_NOTE = (
    "Historical name; value equals excess rows / contrast df, not all rows "
    "in multi-row groups"
)


class AuditFailure(RuntimeError):
    """Raised when a required audit invariant is not satisfied."""


@dataclass(frozen=True)
class HubbleFlowInputs:
    names: tuple[str, ...]
    mb: np.ndarray
    mb_err: np.ndarray
    zhel: np.ndarray
    zcmb: np.ndarray
    vp: np.ndarray
    vp_2mpp_sdss_6df: np.ndarray
    vp_2mrs: np.ndarray
    vp_2mpp: np.ndarray
    covariance_mag: np.ndarray
    table_sha256: str
    covariance_sha256: str


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AuditFailure(f"Non-finite value cannot be serialized: {value}")
        return value
    if isinstance(value, pathlib.Path):
        return str(value)
    return value


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            json_safe(value),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def write_tsv(
    path: pathlib.Path,
    rows: Sequence[dict[str, Any]],
    fieldnames: Sequence[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fieldnames),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (
                        json.dumps(
                            json_safe(row.get(key)),
                            ensure_ascii=False,
                            separators=(",", ":"),
                            allow_nan=False,
                        )
                        if isinstance(row.get(key), (dict, list, tuple, np.ndarray))
                        else json_safe(row.get(key))
                    )
                    for key in fieldnames
                }
            )


def load_config(project: pathlib.Path) -> dict[str, Any]:
    path = project / "provenance" / "DECISION_CONFIG.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("contract_id") != CONTRACT_ID:
        raise AuditFailure("Decision config contract identifier mismatch")
    return config


def load_contract_amendments(project: pathlib.Path) -> list[dict[str, str]]:
    path = project / "provenance" / "CONTRACT_AMENDMENTS.tsv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != AMENDMENT_FIELDS:
            raise AuditFailure("CONTRACT_AMENDMENTS.tsv has an unexpected schema")
        rows = list(reader)
    identifiers = [row["amendment_id"] for row in rows]
    if any(not value for row in rows for value in row.values()):
        raise AuditFailure("CONTRACT_AMENDMENTS.tsv contains a blank field")
    if len(identifiers) != len(set(identifiers)):
        raise AuditFailure("CONTRACT_AMENDMENTS.tsv contains duplicate identifiers")
    return rows


def verify_contract_freeze(project: pathlib.Path) -> dict[str, Any]:
    freeze_path = project / "provenance" / "CONTRACT_FREEZE.json"
    freeze_sha256 = sha256_file(freeze_path)
    if freeze_sha256 != CONTRACT_FREEZE_SHA256:
        raise AuditFailure("CONTRACT_FREEZE.json no longer matches its frozen hash")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("contract_id") != CONTRACT_ID:
        raise AuditFailure("Contract-freeze identifier mismatch")
    checks: list[dict[str, Any]] = []
    for relpath, record in freeze["files"].items():
        path = project / relpath
        expected = record["sha256"]
        if relpath == "provenance/CONTRACT_AMENDMENTS.tsv" and path.is_file():
            lines = path.read_bytes().splitlines(keepends=True)
            frozen_bytes = lines[0] if lines else b""
            actual = hashlib.sha256(frozen_bytes).hexdigest()
            verification_scope = "frozen_header_plus_append_only_ledger"
        else:
            actual = sha256_file(path) if path.is_file() else None
            verification_scope = "whole_file"
        checks.append(
            {
                "path": relpath,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "verification_scope": verification_scope,
                "status": "PASS" if actual == expected else "FAIL",
            }
        )
    status = "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"
    if status != "PASS":
        raise AuditFailure("Frozen contract files no longer match their hashes")
    amendments = load_contract_amendments(project)
    return {
        "contract_id": CONTRACT_ID,
        "contract_freeze_sha256": freeze_sha256,
        "freeze_timestamp_utc": freeze["freeze_timestamp_utc"],
        "partition_results_observed_before_freeze": freeze[
            "partition_results_observed_before_freeze"
        ],
        "contract_amendment_count": len(amendments),
        "contract_amendment_ids": [row["amendment_id"] for row in amendments],
        "checks": checks,
        "status": status,
    }


def load_hubble_flow_inputs(upstream: pathlib.Path) -> HubbleFlowInputs:
    table_path = upstream / "data" / "sn1a_hf_pp.dat"
    covariance_path = upstream / "data" / "sn1a_covar_pp.dat"
    if not table_path.is_file() or not covariance_path.is_file():
        raise AuditFailure("Required public Pantheon+ files are missing")

    names: list[str] = []
    columns: list[list[float]] = [[] for _ in range(8)]
    with table_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            fields = line.split()
            if len(fields) != 9:
                raise AuditFailure(
                    f"Unexpected table schema at line {line_number}: "
                    f"expected 9 fields, found {len(fields)}"
                )
            names.append(fields[0])
            try:
                for index, text_value in enumerate(fields[1:]):
                    columns[index].append(float(text_value))
            except ValueError as exc:
                raise AuditFailure(
                    f"Non-numeric table value at line {line_number}"
                ) from exc

    flat = np.asarray(np.loadtxt(covariance_path, dtype=float)).reshape(-1)
    if flat.size < 2 or not float(flat[0]).is_integer():
        raise AuditFailure("Covariance header is not an integer dimension")
    dimension = int(flat[0])
    if flat.size - 1 != dimension * dimension:
        raise AuditFailure(
            f"Covariance payload has {flat.size - 1} values; "
            f"expected {dimension * dimension}"
        )
    covariance = flat[1:].reshape(dimension, dimension)
    arrays = [np.asarray(column, dtype=float) for column in columns]
    return HubbleFlowInputs(
        names=tuple(names),
        mb=arrays[0],
        mb_err=arrays[1],
        zhel=arrays[2],
        zcmb=arrays[3],
        vp=arrays[4],
        vp_2mpp_sdss_6df=arrays[5],
        vp_2mrs=arrays[6],
        vp_2mpp=arrays[7],
        covariance_mag=covariance,
        table_sha256=sha256_file(table_path),
        covariance_sha256=sha256_file(covariance_path),
    )


def matrix_diagnostics(matrix: np.ndarray) -> dict[str, Any]:
    eigenvalues = scipy.linalg.eigvalsh(matrix, check_finite=True)
    singular_values = scipy.linalg.svdvals(matrix, check_finite=True)
    return {
        "shape": list(matrix.shape),
        "all_finite": bool(np.all(np.isfinite(matrix))),
        "symmetry_max_absolute_error": float(
            np.max(np.abs(matrix - matrix.T))
        ),
        "diagonal_minimum": float(np.min(np.diag(matrix))),
        "diagonal_maximum": float(np.max(np.diag(matrix))),
        "eigenvalue_minimum": float(eigenvalues[0]),
        "eigenvalue_maximum": float(eigenvalues[-1]),
        "condition_number": float(singular_values[0] / singular_values[-1]),
        "numerical_rank": int(np.linalg.matrix_rank(matrix)),
    }


def _velocity_to_redshift(
    velocity: np.ndarray, speed_of_light: float
) -> np.ndarray:
    return np.sqrt(
        (1.0 + velocity / speed_of_light)
        / (1.0 - velocity / speed_of_light)
    ) - 1.0


def _redshift_to_velocity(
    redshift: np.ndarray, speed_of_light: float
) -> np.ndarray:
    ratio = 1.0 + redshift
    return speed_of_light * (ratio**2 - 1.0) / (ratio**2 + 1.0)


def _cosmographic_k(
    redshift: np.ndarray, q0: float, j0: float
) -> np.ndarray:
    return (
        1.0
        + 0.5 * (1.0 - q0) * redshift
        - (1.0 / 6.0)
        * (1.0 - q0 - 3.0 * q0**2 + j0)
        * redshift**2
    )


def build_hubble_flow_system(
    inputs: HubbleFlowInputs, config: dict[str, Any]
) -> dict[str, np.ndarray]:
    model = config["fixed_model"]
    speed_of_light = C_METRES_PER_SECOND / 1000.0
    q0 = float(model["q0"])
    j0 = float(model["j0"])
    velocity_dispersion = float(model["velocity_dispersion_km_s"])
    vpec = np.asarray(inputs.vp_2mpp, dtype=float)
    zpec = _velocity_to_redshift(vpec, speed_of_light)
    zcorrected = (1.0 + inputs.zcmb) / (1.0 + zpec) - 1.0
    vcorrected = _redshift_to_velocity(zcorrected, speed_of_light)
    factor_1 = (1.0 + inputs.zhel) / (1.0 + zcorrected)
    factor_2 = speed_of_light * zcorrected
    factor_3 = _cosmographic_k(zcorrected, q0, j0)
    if np.any(factor_1 <= 0) or np.any(factor_2 <= 0) or np.any(factor_3 <= 0):
        raise AuditFailure("Non-positive cosmographic model factor")
    magnitude_model = 5.0 * np.log10(factor_1 * factor_2 * factor_3)
    data_alpha = 0.2 * (magnitude_model - inputs.mb)
    velocity_variance = (
        np.log10(vcorrected + velocity_dispersion)
        - np.log10(vcorrected)
    ) ** 2
    covariance_alpha = (
        inputs.covariance_mag / 25.0 + np.diag(velocity_variance)
    )
    return {
        "data_alpha": data_alpha,
        "covariance_alpha": covariance_alpha,
        "velocity_variance": velocity_variance,
        "zcorrected": zcorrected,
        "vcorrected": vcorrected,
    }


def build_group_design(names: Sequence[str]) -> dict[str, Any]:
    first_order: list[str] = []
    column_by_name: dict[str, int] = {}
    for name in names:
        if name not in column_by_name:
            column_by_name[name] = len(first_order)
            first_order.append(name)
    design = np.zeros((len(names), len(first_order)), dtype=float)
    for row, name in enumerate(names):
        design[row, column_by_name[name]] = 1.0
    multiplicities = Counter(names)
    histogram = Counter(multiplicities.values())
    unique_exact_name_count = len(first_order)
    multi_row_exact_name_group_count = sum(
        count for size, count in histogram.items() if size > 1
    )
    rows_in_multi_row_exact_name_groups = sum(
        size * count for size, count in histogram.items() if size > 1
    )
    duplicate_name_excess_row_count = len(names) - unique_exact_name_count
    return {
        "design": design,
        "ordered_names": tuple(first_order),
        "object_count": len(names),
        "unique_exact_name_count": unique_exact_name_count,
        "multi_row_exact_name_group_count": multi_row_exact_name_group_count,
        "rows_in_multi_row_exact_name_groups": (
            rows_in_multi_row_exact_name_groups
        ),
        "duplicate_name_excess_row_count": duplicate_name_excess_row_count,
        "duplicate_name_contrast_df": duplicate_name_excess_row_count,
        "legacy_duplicate_name_row_count": duplicate_name_excess_row_count,
        "legacy_field_note": LEGACY_DUPLICATE_NAME_ROW_NOTE,
        "multiplicity_histogram": {
            str(size): int(count) for size, count in sorted(histogram.items())
        },
        "row_sum_max_absolute_error": float(
            np.max(np.abs(np.sum(design, axis=1) - 1.0))
        ),
    }


def input_inventory(
    inputs: HubbleFlowInputs,
    system: dict[str, np.ndarray],
    groups: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    expected = config["expected_inputs"]
    mag_diag = matrix_diagnostics(inputs.covariance_mag)
    alpha_diag = matrix_diagnostics(system["covariance_alpha"])
    n = len(inputs.names)
    checks = {
        "object_count": n == int(expected["object_count"]),
        "unique_exact_name_count": groups["unique_exact_name_count"]
        == int(expected["unique_exact_name_count"]),
        "multi_row_exact_name_group_count": (
            groups["multi_row_exact_name_group_count"] == 30
        ),
        "rows_in_multi_row_exact_name_groups": (
            groups["rows_in_multi_row_exact_name_groups"] == 69
        ),
        "duplicate_name_excess_row_count": (
            groups["duplicate_name_excess_row_count"]
            == int(expected["duplicate_name_row_count"])
        ),
        "duplicate_name_contrast_df": (
            groups["duplicate_name_contrast_df"]
            == int(config["analytic_null"]["duplicate_degrees_of_freedom"])
        ),
        "legacy_duplicate_name_row_count": (
            groups["legacy_duplicate_name_row_count"]
            == int(expected["duplicate_name_row_count"])
        ),
        "table_sha256": inputs.table_sha256 == expected["table_sha256"],
        "covariance_sha256": inputs.covariance_sha256
        == expected["covariance_sha256"],
        "covariance_shape": inputs.covariance_mag.shape == (n, n),
        "all_numeric_values_finite": bool(
            all(
                np.all(np.isfinite(array))
                for array in (
                    inputs.mb,
                    inputs.mb_err,
                    inputs.zhel,
                    inputs.zcmb,
                    inputs.vp,
                    inputs.vp_2mpp_sdss_6df,
                    inputs.vp_2mrs,
                    inputs.vp_2mpp,
                    inputs.covariance_mag,
                    system["data_alpha"],
                    system["covariance_alpha"],
                )
            )
        ),
        "magnitude_covariance_symmetric": mag_diag[
            "symmetry_max_absolute_error"
        ]
        <= 1.0e-14,
        "alpha_covariance_symmetric": alpha_diag[
            "symmetry_max_absolute_error"
        ]
        <= 1.0e-14,
        "alpha_covariance_spd": alpha_diag["eigenvalue_minimum"]
        > float(config["tolerances"]["covariance_minimum_eigenvalue"]),
        "group_row_sums": groups["row_sum_max_absolute_error"] == 0.0,
    }
    try:
        scipy.linalg.cholesky(
            system["covariance_alpha"], lower=True, check_finite=True
        )
        checks["alpha_covariance_cholesky"] = True
    except scipy.linalg.LinAlgError:
        checks["alpha_covariance_cholesky"] = False
    return {
        "object_count": n,
        "unique_exact_name_count": groups["unique_exact_name_count"],
        "multi_row_exact_name_group_count": (
            groups["multi_row_exact_name_group_count"]
        ),
        "rows_in_multi_row_exact_name_groups": (
            groups["rows_in_multi_row_exact_name_groups"]
        ),
        "duplicate_name_excess_row_count": (
            groups["duplicate_name_excess_row_count"]
        ),
        "duplicate_name_contrast_df": groups["duplicate_name_contrast_df"],
        "legacy_duplicate_name_row_count": (
            groups["legacy_duplicate_name_row_count"]
        ),
        "legacy_field_note": groups["legacy_field_note"],
        "multiplicity_histogram": groups["multiplicity_histogram"],
        "table_sha256": inputs.table_sha256,
        "covariance_sha256": inputs.covariance_sha256,
        "magnitude_covariance": mag_diag,
        "alpha_covariance": alpha_diag,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def _rank_and_basis(matrix: np.ndarray) -> tuple[int, np.ndarray, dict[str, Any]]:
    singular_values = scipy.linalg.svdvals(matrix, check_finite=True)
    threshold = (
        max(matrix.shape)
        * np.finfo(float).eps
        * float(singular_values[0])
    )
    rank = int(np.count_nonzero(singular_values > threshold))
    q, r = scipy.linalg.qr(
        matrix, mode="economic", pivoting=False, check_finite=True
    )
    orthogonality_error = float(
        np.max(np.abs(q.T @ q - np.eye(q.shape[1])))
    )
    return rank, q, {
        "shape": list(matrix.shape),
        "rank": rank,
        "rank_threshold": threshold,
        "singular_value_maximum": float(singular_values[0]),
        "singular_value_minimum": float(singular_values[-1]),
        "condition_number": float(singular_values[0] / singular_values[-1]),
        "qr_diagonal_minimum_absolute": float(np.min(np.abs(np.diag(r)))),
        "orthogonality_max_absolute_error": orthogonality_error,
    }


def primary_partition(
    data: np.ndarray,
    covariance: np.ndarray,
    group_design: np.ndarray,
) -> dict[str, Any]:
    n = len(data)
    x0 = np.ones((n, 1), dtype=float)
    lower = scipy.linalg.cholesky(
        covariance, lower=True, check_finite=True
    )
    yw = scipy.linalg.solve_triangular(
        lower, data, lower=True, check_finite=True
    )
    x0w = scipy.linalg.solve_triangular(
        lower, x0, lower=True, check_finite=True
    )
    x1w = scipy.linalg.solve_triangular(
        lower, group_design, lower=True, check_finite=True
    )
    rank0, q0, diag0 = _rank_and_basis(x0w)
    rank1, q1, diag1 = _rank_and_basis(x1w)
    if rank0 != 1 or rank1 != group_design.shape[1]:
        raise AuditFailure(
            f"Unexpected whitened design ranks: {rank0}, {rank1}"
        )
    projection0 = q0 @ (q0.T @ yw)
    projection1 = q1 @ (q1.T @ yw)
    residual0 = yw - projection0
    residual1 = yw - projection1
    chi_total = float(residual0 @ residual0)
    chi_duplicate = float(residual1 @ residual1)
    chi_between = float(
        (projection1 @ projection1) - (projection0 @ projection0)
    )
    closure = chi_total - chi_duplicate - chi_between
    alpha_information = float(x0w[:, 0] @ x0w[:, 0])
    coefficient0 = float((x0w[:, 0] @ yw) / alpha_information)
    return {
        "policy": "cholesky_whitening_qr_projection",
        "alpha": coefficient0,
        "alpha_error": math.sqrt(1.0 / alpha_information),
        "chi2_total": chi_total,
        "chi2_duplicate_name_contrasts": chi_duplicate,
        "chi2_between_name_modes": chi_between,
        "partition_closure_residual": closure,
        "rank_global_design": rank0,
        "rank_group_design": rank1,
        "df_total": n - rank0,
        "df_duplicate_name_contrasts": n - rank1,
        "df_between_name_modes": rank1 - rank0,
        "global_design_diagnostics": diag0,
        "group_design_diagnostics": diag1,
        "_q0": q0,
        "_q1": q1,
    }


def _reference_gls_fit(
    data: np.ndarray, covariance: np.ndarray, design: np.ndarray
) -> dict[str, Any]:
    factor = scipy.linalg.cho_factor(
        covariance, lower=True, check_finite=True
    )
    precision_design = scipy.linalg.cho_solve(
        factor, design, check_finite=True
    )
    precision_data = scipy.linalg.cho_solve(
        factor, data, check_finite=True
    )
    normal = design.T @ precision_design
    rhs = design.T @ precision_data
    coefficients = scipy.linalg.solve(
        normal,
        rhs,
        assume_a="pos",
        check_finite=True,
    )
    residual = data - design @ coefficients
    precision_residual = scipy.linalg.cho_solve(
        factor, residual, check_finite=True
    )
    chi2 = float(residual @ precision_residual)
    return {
        "chi2": chi2,
        "coefficients": coefficients,
        "normal_condition_number": float(np.linalg.cond(normal)),
        "normal_rank": int(np.linalg.matrix_rank(normal)),
    }


def reference_partition(
    data: np.ndarray,
    covariance: np.ndarray,
    group_design: np.ndarray,
) -> dict[str, Any]:
    n = len(data)
    global_fit = _reference_gls_fit(
        data, covariance, np.ones((n, 1), dtype=float)
    )
    group_fit = _reference_gls_fit(
        data, covariance, group_design
    )
    ones = np.ones((n, 1), dtype=float)
    factor = scipy.linalg.cho_factor(
        covariance, lower=True, check_finite=True
    )
    information = float(
        (
            ones.T
            @ scipy.linalg.cho_solve(factor, ones, check_finite=True)
        ).item()
    )
    return {
        "policy": "direct_gls_normal_systems",
        "alpha": float(global_fit["coefficients"][0]),
        "alpha_error": math.sqrt(1.0 / information),
        "chi2_total": global_fit["chi2"],
        "chi2_duplicate_name_contrasts": group_fit["chi2"],
        "chi2_between_name_modes": global_fit["chi2"] - group_fit["chi2"],
        "global_normal_rank": global_fit["normal_rank"],
        "group_normal_rank": group_fit["normal_rank"],
        "global_normal_condition_number": global_fit[
            "normal_condition_number"
        ],
        "group_normal_condition_number": group_fit[
            "normal_condition_number"
        ],
    }


def public_partition(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: json_safe(value)
        for key, value in result.items()
        if not key.startswith("_")
    }


def baseline_checks(
    primary: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    expected = config["known_phase0_baseline"]
    tolerance = float(config["tolerances"]["baseline_absolute"])
    comparisons = [
        ("alpha", float(primary["alpha"]), float(expected["alpha"])),
        (
            "alpha_error",
            float(primary["alpha_error"]),
            float(expected["alpha_error"]),
        ),
        (
            "minimum_chi2",
            float(primary["chi2_total"]),
            float(expected["minimum_chi2"]),
        ),
        ("ndof", int(primary["df_total"]), int(expected["ndof"])),
    ]
    rows = []
    for quantity, actual, target in comparisons:
        difference = abs(actual - target)
        row_tolerance = 0.0 if quantity == "ndof" else tolerance
        rows.append(
            {
                "quantity": quantity,
                "actual": actual,
                "expected": target,
                "absolute_difference": difference,
                "tolerance": row_tolerance,
                "status": (
                    "PASS" if difference <= row_tolerance else "FAIL"
                ),
            }
        )
    return {
        "comparisons": rows,
        "status": (
            "PASS"
            if all(row["status"] == "PASS" for row in rows)
            else "FAIL"
        ),
    }


def numerical_crosschecks(
    primary: dict[str, Any],
    reference: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    reference_tolerance = float(
        config["tolerances"]["reference_solver_absolute"]
    )
    closure_tolerance = float(
        config["tolerances"]["partition_closure_absolute"]
    )
    rows: list[dict[str, Any]] = []
    for quantity in (
        "chi2_total",
        "chi2_duplicate_name_contrasts",
        "chi2_between_name_modes",
    ):
        difference = abs(float(primary[quantity]) - float(reference[quantity]))
        rows.append(
            {
                "check": f"primary_vs_reference:{quantity}",
                "absolute_difference": difference,
                "tolerance": reference_tolerance,
                "status": "PASS" if difference <= reference_tolerance else "FAIL",
            }
        )
    closure = abs(float(primary["partition_closure_residual"]))
    rows.append(
        {
            "check": "primary_partition_closure",
            "absolute_difference": closure,
            "tolerance": closure_tolerance,
            "status": "PASS" if closure <= closure_tolerance else "FAIL",
        }
    )
    expected_df = config["analytic_null"]
    df_ok = (
        int(primary["df_total"]) == int(expected_df["global_degrees_of_freedom"])
        and int(primary["df_duplicate_name_contrasts"])
        == int(expected_df["duplicate_degrees_of_freedom"])
        and int(primary["df_between_name_modes"])
        == int(expected_df["between_degrees_of_freedom"])
    )
    rows.append(
        {
            "check": "degrees_of_freedom",
            "absolute_difference": 0 if df_ok else 1,
            "tolerance": 0,
            "status": "PASS" if df_ok else "FAIL",
        }
    )
    return {
        "checks": rows,
        "status": (
            "PASS"
            if all(row["status"] == "PASS" for row in rows)
            else "FAIL"
        ),
    }


def statistical_interpretation(
    primary: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    analytic = config["analytic_null"]
    df_total = int(analytic["global_degrees_of_freedom"])
    df_duplicate = int(analytic["duplicate_degrees_of_freedom"])
    df_between = int(analytic["between_degrees_of_freedom"])
    total = float(primary["chi2_total"])
    duplicate = float(primary["chi2_duplicate_name_contrasts"])
    between = float(primary["chi2_between_name_modes"])
    ratio = duplicate / total
    beta_a = df_duplicate / 2.0
    beta_b = df_between / 2.0
    global_lower = float(scipy.stats.chi2.cdf(total, df_total))
    duplicate_lower = float(
        scipy.stats.chi2.cdf(duplicate, df_duplicate)
    )
    between_lower = float(scipy.stats.chi2.cdf(between, df_between))
    beta_lower = float(scipy.stats.beta.cdf(ratio, beta_a, beta_b))
    beta_upper = float(scipy.stats.beta.sf(ratio, beta_a, beta_b))
    beta_two_sided = min(1.0, 2.0 * min(beta_lower, beta_upper))
    lower_threshold = float(analytic["lower_beta_tail_threshold"])
    upper_threshold = float(analytic["upper_beta_tail_threshold"])
    labels = config["status_labels"]
    if global_lower > float(analytic["localization_alpha_two_sided"]):
        status = labels["no_strong_global"]
        localization = "NO_STRONG_GLOBAL_LOW_CHI2"
    elif beta_lower <= lower_threshold:
        status = labels["duplicate_localized"]
        localization = "DUPLICATE_NAME_CONTRAST_DEFICIT"
    elif beta_upper <= upper_threshold:
        status = labels["between_localized"]
        localization = "BETWEEN_NAME_MODE_DEFICIT"
    else:
        status = labels["proportional"]
        localization = "PROPORTIONAL_ACROSS_NAME_PARTITIONS"
    return {
        "fixed_known_gaussian_covariance_condition": True,
        "chi2_total": total,
        "chi2_duplicate_name_contrasts": duplicate,
        "chi2_between_name_modes": between,
        "df_total": df_total,
        "df_duplicate_name_contrasts": df_duplicate,
        "df_between_name_modes": df_between,
        "global_lower_tail_probability": global_lower,
        "duplicate_component_lower_tail_probability_secondary": duplicate_lower,
        "between_component_lower_tail_probability_secondary": between_lower,
        "duplicate_share_ratio": ratio,
        "beta_parameters": {"a": beta_a, "b": beta_b},
        "beta_lower_tail_probability": beta_lower,
        "beta_upper_tail_probability": beta_upper,
        "beta_two_sided_probability": beta_two_sided,
        "localization_alpha_two_sided": float(
            analytic["localization_alpha_two_sided"]
        ),
        "localization_class": localization,
        "status": status,
        "chronology_note": (
            "The global chi-square was known before contract freeze. "
            "The conditional partition and localization class were not."
        ),
    }


def monte_carlo_null_check(
    primary: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    q0 = primary["_q0"]
    q1 = primary["_q1"]
    n = q0.shape[0]
    mc = config["monte_carlo"]
    draws = int(mc["draw_count"])
    seed = int(mc["seed"])
    rng = np.random.default_rng(seed)
    totals = {
        "duplicate_sum": 0.0,
        "duplicate_sum_sq": 0.0,
        "between_sum": 0.0,
        "between_sum_sq": 0.0,
        "ratio_sum": 0.0,
        "ratio_sum_sq": 0.0,
    }
    completed = 0
    while completed < draws:
        batch = min(1000, draws - completed)
        z = rng.standard_normal((n, batch))
        norm_sq = np.sum(z * z, axis=0)
        projection0_sq = np.sum((q0.T @ z) ** 2, axis=0)
        projection1_sq = np.sum((q1.T @ z) ** 2, axis=0)
        duplicate = norm_sq - projection1_sq
        between = projection1_sq - projection0_sq
        ratio = duplicate / (duplicate + between)
        totals["duplicate_sum"] += float(np.sum(duplicate))
        totals["duplicate_sum_sq"] += float(np.sum(duplicate**2))
        totals["between_sum"] += float(np.sum(between))
        totals["between_sum_sq"] += float(np.sum(between**2))
        totals["ratio_sum"] += float(np.sum(ratio))
        totals["ratio_sum_sq"] += float(np.sum(ratio**2))
        completed += batch

    analytic = config["analytic_null"]
    df_duplicate = int(analytic["duplicate_degrees_of_freedom"])
    df_between = int(analytic["between_degrees_of_freedom"])
    beta_a = df_duplicate / 2.0
    beta_b = df_between / 2.0
    expected_ratio = beta_a / (beta_a + beta_b)
    beta_variance = (
        beta_a
        * beta_b
        / ((beta_a + beta_b) ** 2 * (beta_a + beta_b + 1.0))
    )
    limits = float(mc["mean_gate_standard_errors"])
    metrics = []
    for name, total_key, total_sq_key, expected, variance in (
        (
            "duplicate_component_mean",
            "duplicate_sum",
            "duplicate_sum_sq",
            float(df_duplicate),
            float(2 * df_duplicate),
        ),
        (
            "between_component_mean",
            "between_sum",
            "between_sum_sq",
            float(df_between),
            float(2 * df_between),
        ),
        (
            "duplicate_share_mean",
            "ratio_sum",
            "ratio_sum_sq",
            float(expected_ratio),
            float(beta_variance),
        ),
    ):
        mean = totals[total_key] / draws
        sample_variance = max(
            0.0,
            (totals[total_sq_key] - draws * mean**2) / (draws - 1),
        )
        analytic_standard_error = math.sqrt(variance / draws)
        absolute_difference = abs(mean - expected)
        tolerance = limits * analytic_standard_error
        metrics.append(
            {
                "metric": name,
                "empirical_mean": mean,
                "empirical_standard_deviation": math.sqrt(sample_variance),
                "expected_mean": expected,
                "analytic_mean_standard_error": analytic_standard_error,
                "gate_standard_errors": limits,
                "absolute_difference": absolute_difference,
                "tolerance": tolerance,
                "status": "PASS" if absolute_difference <= tolerance else "FAIL",
            }
        )
    return {
        "purpose": "implementation_check_only_not_covariance_validation",
        "seed": seed,
        "draw_count": draws,
        "metrics": metrics,
        "status": (
            "PASS"
            if all(metric["status"] == "PASS" for metric in metrics)
            else "FAIL"
        ),
    }


def permutation_checks(
    data: np.ndarray,
    covariance: np.ndarray,
    names: Sequence[str],
    baseline: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    permutation_config = config["permutations"]
    rng = np.random.default_rng(int(permutation_config["seed"]))
    count = int(permutation_config["count"])
    tolerance = float(config["tolerances"]["permutation_absolute"])
    quantities = (
        "chi2_total",
        "chi2_duplicate_name_contrasts",
        "chi2_between_name_modes",
    )
    rows: list[dict[str, Any]] = []
    maximums = {quantity: 0.0 for quantity in quantities}
    names_array = np.asarray(names, dtype=object)
    for index in range(count):
        permutation = rng.permutation(len(data))
        permuted_names = tuple(names_array[permutation].tolist())
        design = build_group_design(permuted_names)["design"]
        result = primary_partition(
            data[permutation],
            covariance[np.ix_(permutation, permutation)],
            design,
        )
        differences = {
            quantity: abs(float(result[quantity]) - float(baseline[quantity]))
            for quantity in quantities
        }
        for quantity, difference in differences.items():
            maximums[quantity] = max(maximums[quantity], difference)
        status = (
            "PASS"
            if max(differences.values()) <= tolerance
            else "FAIL"
        )
        rows.append(
            {
                "permutation_index": index + 1,
                "permutation_sha256": hashlib.sha256(
                    np.asarray(permutation, dtype="<i8").tobytes()
                ).hexdigest(),
                "total_chi2_absolute_difference": differences["chi2_total"],
                "duplicate_chi2_absolute_difference": differences[
                    "chi2_duplicate_name_contrasts"
                ],
                "between_chi2_absolute_difference": differences[
                    "chi2_between_name_modes"
                ],
                "tolerance": tolerance,
                "status": status,
            }
        )
    return {
        "seed": int(permutation_config["seed"]),
        "count": count,
        "rows": rows,
        "maximum_absolute_differences": maximums,
        "tolerance": tolerance,
        "status": (
            "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL"
        ),
    }


def environment_summary() -> dict[str, Any]:
    return {
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
