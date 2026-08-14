#!/usr/bin/env python3
"""Independent numerical routines for the frozen Phase 0 sufficiency audit."""

from __future__ import annotations

import contextlib
import csv
import hashlib
import importlib
import io
import json
import math
import os
import pathlib
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator, Sequence

import numpy as np
import pandas as pd
import scipy
import scipy.linalg
from scipy.constants import c as C_METRES_PER_SECOND

from source_tools import UPSTREAM_COMMIT, verify_source


CONTRACT_ID = "H0DN-SNIA-COMP-PHASE0-CONTRACT-20260730-01"
FINAL_PASS_STATUS = "PASS_EXACT_SUFFICIENCY_FOR_FROZEN_LINEAR_MODEL"
OFFICIAL_ATOL = 1.0e-10
OFFICIAL_RTOL = 0.0
EXPECTED_OBJECT_COUNT = 277
PROFILE_OFFSETS_SIGMA = (-8.0, -4.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 4.0, 8.0)
PERMUTATION_SEED = 20260730
PERMUTATION_COUNT = 16

EXPECTED_BASELINE = {
    "neq": 255,
    "npars": 64,
    "covar_rank": 183,
    "ndof": 119,
    "h0_value": 73.4988,
    "h0_error": 0.8088,
    "chi2": 117.5597,
    "mzero_value": -19.252,
    "mzero_error": 0.022,
}

TOLERANCES = {
    "covariance_min_eigenvalue": 1.0e-12,
    "alpha_reconstruction": 5.0e-14,
    "solver_crosscheck": 5.0e-13,
    "profile_identity": 2.0e-10,
    "network": 2.0e-10,
    "normal_closure": 2.0e-9,
    "chi2_closure": 2.0e-9,
    "permutation": 2.0e-9,
}


class AuditFailure(RuntimeError):
    """Raised when required inputs cannot support a valid Phase 0 execution."""


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


@contextlib.contextmanager
def pushd(path: pathlib.Path) -> Iterator[None]:
    previous = pathlib.Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
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
    serialized = json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
    path.write_text(serialized + "\n", encoding="utf-8")


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
            safe: dict[str, Any] = {}
            for field in fieldnames:
                value = row.get(field)
                if isinstance(value, (list, tuple, dict, np.ndarray)):
                    safe[field] = json.dumps(
                        _json_safe(value),
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                elif value is None:
                    safe[field] = ""
                else:
                    safe[field] = _json_safe(value)
            writer.writerow(safe)


def capture_upstream_baseline(upstream: pathlib.Path) -> dict[str, Any]:
    """Execute the untouched upstream workflow while capturing its matrices."""

    module_root = (upstream / "h0_constrainer").resolve()
    config_dir = module_root / "configs"
    if not config_dir.is_dir():
        raise AuditFailure(f"Missing upstream Python package: {module_root}")

    for name in list(sys.modules):
        if name == "h0_constrainer" or name.startswith("h0_constrainer."):
            del sys.modules[name]
    sys.path.insert(0, str(module_root))

    main_module = importlib.import_module("h0_constrainer.main")
    equations_module = importlib.import_module("h0_constrainer.equations")
    solver_module = importlib.import_module("h0_constrainer.solver")
    loaded_from = pathlib.Path(main_module.__file__).resolve()
    if module_root not in loaded_from.parents:
        raise AuditFailure(
            f"Loaded h0_constrainer from {loaded_from}, not {module_root}"
        )

    captured: dict[str, Any] = {}
    original_build = equations_module.build_equations
    original_solve = solver_module.solve_system

    def capture_build(*args: Any, **kwargs: Any) -> dict[str, Any]:
        captured["build_args"] = args
        captured["build_kwargs"] = kwargs
        result = original_build(*args, **kwargs)
        captured["equation_data"] = result
        return result

    def capture_solve(equation_data: dict[str, Any]) -> dict[str, Any]:
        result = original_solve(equation_data)
        captured["upstream_solution"] = result
        return result

    equations_module.build_equations = capture_build
    solver_module.solve_system = capture_solve
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with pushd(config_dir), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            main_module.main("config.ini")
    finally:
        equations_module.build_equations = original_build
        solver_module.solve_system = original_solve
        if sys.path and sys.path[0] == str(module_root):
            sys.path.pop(0)

    required = {"build_args", "build_kwargs", "equation_data", "upstream_solution"}
    missing = required - set(captured)
    if missing:
        raise AuditFailure(
            "Upstream capture incomplete: " + ", ".join(sorted(missing))
        )
    captured["stdout"] = stdout.getvalue()
    captured["stderr"] = stderr.getvalue()
    captured["loaded_module"] = str(loaded_from)
    return captured


def public_network_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _json_safe(value)
        for key, value in result.items()
        if not key.startswith("_")
    }


def upstream_baseline_summary(captured: dict[str, Any]) -> dict[str, Any]:
    eq = captured["equation_data"]
    solution = captured["upstream_solution"]
    return {
        "loaded_module": captured["loaded_module"],
        "neq": int(eq["neq"]),
        "npars": int(eq["npars"]),
        "nhosts": int(eq["nhosts"]),
        "covar_rank": int(solution["covar_rank"]),
        "covar_nullity": int(solution["covar_dim"] - solution["covar_rank"]),
        "h0_value": float(solution["h0_value"]),
        "h0_error": float(solution["h0_error"]),
        "logh0_value": float(solution["logh0_value"]),
        "logh0_variance": float(solution["logh0_var"]),
        "chi2": float(solution["chi2"]),
        "ndof": int(solution["ndof"]),
        "ndof_full": int(solution["ndof_full"]),
        "mzero_value": float(solution["mzero_value"]),
        "mzero_error": float(solution["mzero_error"]),
        "sn1a_link_row": int(eq["ieq_h0_m1a"]),
        "upstream_alpha": float(eq["a_sn1a"]),
        "upstream_alpha_error": float(eq["a_sn1a_err"]),
        "upstream_hf_chi2": float(eq["chisq_sn1a_hf"]),
        "upstream_hf_ndof": int(eq["ndof_sn1a_hf"]),
        "stdout": captured["stdout"],
        "stderr": captured["stderr"],
    }


def baseline_fidelity(summary: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for key in ("neq", "npars", "covar_rank", "ndof"):
        actual = int(summary[key])
        expected = int(EXPECTED_BASELINE[key])
        checks.append(
            {
                "quantity": key,
                "actual": actual,
                "expected": expected,
                "tolerance": 0,
                "absolute_difference": abs(actual - expected),
                "status": "PASS" if actual == expected else "FAIL",
            }
        )
    rounded_tolerances = {
        "h0_value": 5.0e-5,
        "h0_error": 5.0e-5,
        "chi2": 5.0e-5,
        "mzero_value": 5.0e-4,
        "mzero_error": 5.0e-4,
    }
    for key, tolerance in rounded_tolerances.items():
        actual = float(summary[key])
        expected = float(EXPECTED_BASELINE[key])
        difference = abs(actual - expected)
        checks.append(
            {
                "quantity": key,
                "actual": actual,
                "expected": expected,
                "tolerance": tolerance,
                "absolute_difference": difference,
                "status": "PASS" if difference < tolerance else "FAIL",
            }
        )
    return {
        "checks": checks,
        "status": (
            "PASS"
            if all(check["status"] == "PASS" for check in checks)
            else "FAIL"
        ),
    }


def load_hubble_flow_inputs(upstream: pathlib.Path) -> HubbleFlowInputs:
    """Parse the two public Pantheon+ input files without the upstream loader."""

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
                    f"Non-numeric Pantheon+ value at line {line_number}"
                ) from exc

    raw_covariance = np.loadtxt(covariance_path, dtype=float)
    flat = np.asarray(raw_covariance, dtype=float).reshape(-1)
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
    symmetry_error = float(np.max(np.abs(matrix - matrix.T)))
    eigenvalues = scipy.linalg.eigvalsh(matrix, check_finite=True)
    singular_values = scipy.linalg.svdvals(matrix, check_finite=True)
    return {
        "shape": list(matrix.shape),
        "finite": bool(np.all(np.isfinite(matrix))),
        "symmetry_max_absolute_error": symmetry_error,
        "diagonal_min": float(np.min(np.diag(matrix))),
        "diagonal_max": float(np.max(np.diag(matrix))),
        "eigenvalue_min": float(eigenvalues[0]),
        "eigenvalue_max": float(eigenvalues[-1]),
        "condition_number": float(singular_values[0] / singular_values[-1]),
        "rank_at_official_absolute_cutoff": int(
            np.count_nonzero(singular_values > OFFICIAL_ATOL)
        ),
    }


def input_inventory(inputs: HubbleFlowInputs) -> dict[str, Any]:
    n = len(inputs.names)
    covariance = inputs.covariance_mag
    diagnostics = matrix_diagnostics(covariance)
    checks = {
        "object_count_277": n == EXPECTED_OBJECT_COUNT,
        "column_lengths_match": all(
            len(array) == n
            for array in (
                inputs.mb,
                inputs.mb_err,
                inputs.zhel,
                inputs.zcmb,
                inputs.vp,
                inputs.vp_2mpp_sdss_6df,
                inputs.vp_2mrs,
                inputs.vp_2mpp,
            )
        ),
        "covariance_shape_277x277": covariance.shape
        == (EXPECTED_OBJECT_COUNT, EXPECTED_OBJECT_COUNT),
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
                    covariance,
                )
            )
        ),
        "covariance_symmetric": diagnostics["symmetry_max_absolute_error"] <= 1.0e-14,
        "covariance_positive_diagonal": diagnostics["diagonal_min"] > 0.0,
    }
    return {
        "object_count": n,
        "unique_name_count": len(set(inputs.names)),
        "duplicate_name_row_count": n - len(set(inputs.names)),
        "velocity_column": "vp_2mpp",
        "q0": -0.55,
        "j0": 1.0,
        "velocity_dispersion_km_s": 240.0,
        "redshift_cut_applied": False,
        "table_sha256": inputs.table_sha256,
        "covariance_sha256": inputs.covariance_sha256,
        "magnitude_covariance": diagnostics,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def _vel_to_z(velocity: np.ndarray, speed_of_light: float) -> np.ndarray:
    return np.sqrt(
        (1.0 + velocity / speed_of_light)
        / (1.0 - velocity / speed_of_light)
    ) - 1.0


def _z_to_vel(redshift: np.ndarray, speed_of_light: float) -> np.ndarray:
    ratio = 1.0 + redshift
    return speed_of_light * (ratio**2 - 1.0) / (ratio**2 + 1.0)


def _kz(redshift: np.ndarray, q0: float, j0: float) -> np.ndarray:
    return (
        1.0
        + 0.5 * (1.0 - q0) * redshift
        - (1.0 / 6.0)
        * (1.0 - q0 - 3.0 * q0**2 + j0)
        * redshift**2
    )


def build_hubble_flow_system(inputs: HubbleFlowInputs) -> dict[str, Any]:
    """Construct alpha-unit data and covariance from frozen public inputs."""

    speed_of_light = C_METRES_PER_SECOND / 1000.0
    q0 = -0.55
    j0 = 1.0
    velocity_dispersion = 240.0
    vpec = np.asarray(inputs.vp_2mpp, dtype=float)
    zpec = _vel_to_z(vpec, speed_of_light)
    zcorrected = (1.0 + inputs.zcmb) / (1.0 + zpec) - 1.0
    vcorrected = _z_to_vel(zcorrected, speed_of_light)
    t1 = (1.0 + inputs.zhel) / (1.0 + zcorrected)
    t2 = speed_of_light * zcorrected
    t3 = _kz(zcorrected, q0, j0)
    if np.any(t1 <= 0.0) or np.any(t2 <= 0.0) or np.any(t3 <= 0.0):
        raise AuditFailure("Non-positive cosmographic model factor")
    magnitude_model = 5.0 * np.log10(t1 * t2 * t3)
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
        "magnitude_model": magnitude_model,
    }


def solve_intercept_cholesky(
    data: np.ndarray, covariance: np.ndarray
) -> dict[str, Any]:
    factor = scipy.linalg.cho_factor(
        covariance, lower=True, overwrite_a=False, check_finite=True
    )
    ones = np.ones(len(data), dtype=float)
    precision_ones = scipy.linalg.cho_solve(factor, ones, check_finite=True)
    precision_data = scipy.linalg.cho_solve(factor, data, check_finite=True)
    information = float(ones @ precision_ones)
    variance = 1.0 / information
    alpha = float(variance * (ones @ precision_data))
    residual = data - alpha
    precision_residual = scipy.linalg.cho_solve(
        factor, residual, check_finite=True
    )
    return {
        "policy": "independent_cholesky_solve",
        "alpha": alpha,
        "alpha_variance": variance,
        "alpha_error": math.sqrt(variance),
        "information": information,
        "chi2": float(residual @ precision_residual),
        "ndof": len(data) - 1,
        "object_count": len(data),
        "_factor": factor,
    }


def solve_intercept_inverse(
    data: np.ndarray, covariance: np.ndarray
) -> dict[str, Any]:
    inverse = np.linalg.inv(covariance)
    ones = np.ones(len(data), dtype=float)
    information = float(ones @ inverse @ ones)
    variance = 1.0 / information
    alpha = float(variance * (ones @ inverse @ data))
    residual = data - alpha
    return {
        "policy": "explicit_inverse_crosscheck",
        "alpha": alpha,
        "alpha_variance": variance,
        "alpha_error": math.sqrt(variance),
        "information": information,
        "chi2": float(residual @ inverse @ residual),
        "ndof": len(data) - 1,
        "object_count": len(data),
    }


def public_intercept_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _json_safe(value)
        for key, value in result.items()
        if not key.startswith("_")
    }


def compression_identity_grid(
    data: np.ndarray,
    covariance: np.ndarray,
    fit: dict[str, Any],
) -> list[dict[str, Any]]:
    factor = fit["_factor"]
    alpha_hat = float(fit["alpha"])
    sigma = float(fit["alpha_error"])
    minimum_chi2 = float(fit["chi2"])
    rows: list[dict[str, Any]] = []
    for offset in PROFILE_OFFSETS_SIGMA:
        trial = alpha_hat + offset * sigma
        residual = data - trial
        full_chi2 = float(
            residual
            @ scipy.linalg.cho_solve(factor, residual, check_finite=True)
        )
        full_delta = full_chi2 - minimum_chi2
        scalar_delta = (trial - alpha_hat) ** 2 / float(fit["alpha_variance"])
        identity_residual = full_delta - scalar_delta
        rows.append(
            {
                "offset_sigma": offset,
                "trial_alpha": trial,
                "full_chi2": full_chi2,
                "full_delta_chi2": full_delta,
                "scalar_delta_chi2": scalar_delta,
                "identity_residual": identity_residual,
                "absolute_identity_residual": abs(identity_residual),
                "tolerance": TOLERANCES["profile_identity"],
                "status": (
                    "PASS"
                    if abs(identity_residual) <= TOLERANCES["profile_identity"]
                    else "FAIL"
                ),
            }
        )
    return rows


def solve_network(
    coefficients: np.ndarray,
    observations: np.ndarray,
    covariance: np.ndarray,
    *,
    ihub: int,
    iabs: int,
    policy: str,
) -> dict[str, Any]:
    precision, rank = scipy.linalg.pinv(
        covariance,
        atol=OFFICIAL_ATOL,
        rtol=OFFICIAL_RTOL,
        return_rank=True,
        check_finite=True,
    )
    normal = coefficients.T @ precision @ coefficients
    rhs = coefficients.T @ precision @ observations
    parameter_covariance = np.linalg.inv(normal)
    parameters = parameter_covariance @ rhs
    residual = observations - coefficients @ parameters
    logh0 = float(parameters[ihub])
    logh0_variance = float(parameter_covariance[ihub, ihub])
    h0 = 10.0**logh0
    h0_error = 10.0 ** (logh0 + math.sqrt(logh0_variance)) - h0
    return {
        "policy": policy,
        "status": "OK",
        "nrows": int(len(observations)),
        "npars": int(coefficients.shape[1]),
        "covar_rank": int(rank),
        "covar_nullity": int(len(observations) - rank),
        "ndof": int(rank - coefficients.shape[1]),
        "h0_value": h0,
        "h0_error": h0_error,
        "logh0_value": logh0,
        "logh0_variance": logh0_variance,
        "mzero_value": float(parameters[iabs]),
        "mzero_error": math.sqrt(float(parameter_covariance[iabs, iabs])),
        "chi2": float(residual @ precision @ residual),
        "_precision": precision,
        "_normal": normal,
        "_rhs": rhs,
        "_parameters": parameters,
        "_parameter_covariance": parameter_covariance,
        "_residual": residual,
    }


def compare_network_results(
    reference: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    return {
        "max_abs_parameter_difference": float(
            np.max(
                np.abs(
                    reference["_parameters"] - candidate["_parameters"]
                )
            )
        ),
        "max_abs_parameter_covariance_difference": float(
            np.max(
                np.abs(
                    reference["_parameter_covariance"]
                    - candidate["_parameter_covariance"]
                )
            )
        ),
        "absolute_h0_difference": abs(
            float(reference["h0_value"]) - float(candidate["h0_value"])
        ),
        "absolute_h0_error_difference": abs(
            float(reference["h0_error"]) - float(candidate["h0_error"])
        ),
        "absolute_logh0_difference": abs(
            float(reference["logh0_value"])
            - float(candidate["logh0_value"])
        ),
        "absolute_mzero_difference": abs(
            float(reference["mzero_value"])
            - float(candidate["mzero_value"])
        ),
    }


def captured_upstream_as_internal(captured: dict[str, Any]) -> dict[str, Any]:
    solution = captured["upstream_solution"]
    return {
        "policy": "untouched_upstream",
        "status": "OK",
        "nrows": int(captured["equation_data"]["neq"]),
        "npars": int(captured["equation_data"]["npars"]),
        "covar_rank": int(solution["covar_rank"]),
        "covar_nullity": int(solution["covar_dim"] - solution["covar_rank"]),
        "ndof": int(solution["ndof"]),
        "h0_value": float(solution["h0_value"]),
        "h0_error": float(solution["h0_error"]),
        "logh0_value": float(solution["logh0_value"]),
        "logh0_variance": float(solution["logh0_var"]),
        "mzero_value": float(solution["mzero_value"]),
        "mzero_error": float(solution["mzero_error"]),
        "chi2": float(solution["chi2"]),
        "_normal": np.asarray(solution["solmat"], dtype=float),
        "_rhs": np.asarray(solution["solval"], dtype=float),
        "_parameters": np.asarray(solution["params"], dtype=float),
        "_parameter_covariance": np.asarray(solution["invsolmat"], dtype=float),
        "_residual": np.asarray(solution["residuals"], dtype=float),
    }


def build_recompressed_network(
    captured: dict[str, Any], fit: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int, int]:
    eq = captured["equation_data"]
    coefficients = np.array(eq["coeffs"], dtype=float, copy=True)
    observations = np.array(eq["yval"], dtype=float, copy=True)
    covariance = np.array(eq["covar"], dtype=float, copy=True)
    link_row = int(eq["ieq_h0_m1a"])
    observations[link_row] = float(fit["alpha"]) + 5.0
    covariance[link_row, link_row] = float(fit["alpha_variance"])
    return (
        coefficients,
        observations,
        covariance,
        int(eq["ihub"]),
        int(eq["iabs"]),
        link_row,
    )


def build_expanded_network(
    captured: dict[str, Any],
    data_alpha: np.ndarray,
    covariance_alpha: np.ndarray,
) -> dict[str, Any]:
    eq = captured["equation_data"]
    coefficients = np.asarray(eq["coeffs"], dtype=float)
    observations = np.asarray(eq["yval"], dtype=float)
    covariance = np.asarray(eq["covar"], dtype=float)
    link_row = int(eq["ieq_h0_m1a"])
    offdiagonal = np.delete(covariance[link_row, :], link_row)
    if np.max(np.abs(offdiagonal)) > 1.0e-15:
        raise AuditFailure(
            "The frozen SN Ia scalar link has nonzero cross-covariance; "
            "the pre-specified block embedding is invalid"
        )
    keep = np.arange(len(observations)) != link_row
    coefficients_rest = coefficients[keep, :]
    observations_rest = observations[keep]
    covariance_rest = covariance[np.ix_(keep, keep)]
    link_coefficients = coefficients[link_row, :]
    coefficients_hf = np.tile(link_coefficients, (len(data_alpha), 1))
    observations_hf = np.asarray(data_alpha, dtype=float) + 5.0
    coefficients_expanded = np.vstack((coefficients_rest, coefficients_hf))
    observations_expanded = np.concatenate(
        (observations_rest, observations_hf)
    )
    covariance_expanded = scipy.linalg.block_diag(
        covariance_rest, covariance_alpha
    )
    return {
        "coefficients": coefficients_expanded,
        "observations": observations_expanded,
        "covariance": covariance_expanded,
        "coefficients_rest": coefficients_rest,
        "observations_rest": observations_rest,
        "covariance_rest": covariance_rest,
        "coefficients_hf": coefficients_hf,
        "observations_hf": observations_hf,
        "covariance_hf": covariance_alpha,
        "link_row": link_row,
        "link_coefficients": link_coefficients,
        "ihub": int(eq["ihub"]),
        "iabs": int(eq["iabs"]),
    }


def solve_expanded_blockwise(
    expanded: dict[str, Any],
) -> dict[str, Any]:
    precision_rest, rank_rest = scipy.linalg.pinv(
        expanded["covariance_rest"],
        atol=OFFICIAL_ATOL,
        rtol=OFFICIAL_RTOL,
        return_rank=True,
        check_finite=True,
    )
    factor_hf = scipy.linalg.cho_factor(
        expanded["covariance_hf"], lower=True, check_finite=True
    )
    identity_hf = np.eye(expanded["covariance_hf"].shape[0])
    precision_hf = scipy.linalg.cho_solve(
        factor_hf, identity_hf, check_finite=True
    )
    a_rest = expanded["coefficients_rest"]
    y_rest = expanded["observations_rest"]
    a_hf = expanded["coefficients_hf"]
    y_hf = expanded["observations_hf"]
    normal = (
        a_rest.T @ precision_rest @ a_rest
        + a_hf.T @ precision_hf @ a_hf
    )
    rhs = (
        a_rest.T @ precision_rest @ y_rest
        + a_hf.T @ precision_hf @ y_hf
    )
    parameter_covariance = np.linalg.inv(normal)
    parameters = parameter_covariance @ rhs
    residual_rest = y_rest - a_rest @ parameters
    residual_hf = y_hf - a_hf @ parameters
    ihub = int(expanded["ihub"])
    iabs = int(expanded["iabs"])
    logh0 = float(parameters[ihub])
    logh0_variance = float(parameter_covariance[ihub, ihub])
    h0 = 10.0**logh0
    h0_error = 10.0 ** (logh0 + math.sqrt(logh0_variance)) - h0
    rank = int(rank_rest + len(y_hf))
    return {
        "policy": "independent_blockwise_pinv_plus_cholesky",
        "status": "OK",
        "nrows": int(len(y_rest) + len(y_hf)),
        "npars": int(a_rest.shape[1]),
        "covar_rank": rank,
        "covar_nullity": int(len(y_rest) + len(y_hf) - rank),
        "ndof": int(rank - a_rest.shape[1]),
        "h0_value": h0,
        "h0_error": h0_error,
        "logh0_value": logh0,
        "logh0_variance": logh0_variance,
        "mzero_value": float(parameters[iabs]),
        "mzero_error": math.sqrt(float(parameter_covariance[iabs, iabs])),
        "chi2": float(
            residual_rest @ precision_rest @ residual_rest
            + residual_hf @ precision_hf @ residual_hf
        ),
        "rest_covariance_rank": int(rank_rest),
        "hubble_flow_covariance_rank": int(len(y_hf)),
        "_normal": normal,
        "_rhs": rhs,
        "_parameters": parameters,
        "_parameter_covariance": parameter_covariance,
        "_residual": np.concatenate((residual_rest, residual_hf)),
    }


def run_network_embedding_audit(
    captured: dict[str, Any],
    data_alpha: np.ndarray,
    covariance_alpha: np.ndarray,
    fit: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    upstream = captured_upstream_as_internal(captured)
    (
        scalar_a,
        scalar_y,
        scalar_c,
        ihub,
        iabs,
        link_row,
    ) = build_recompressed_network(captured, fit)
    recompressed = solve_network(
        scalar_a,
        scalar_y,
        scalar_c,
        ihub=ihub,
        iabs=iabs,
        policy="independently_recompressed_scalar_link",
    )
    expanded_system = build_expanded_network(
        captured, data_alpha, covariance_alpha
    )
    expanded = solve_network(
        expanded_system["coefficients"],
        expanded_system["observations"],
        expanded_system["covariance"],
        ihub=ihub,
        iabs=iabs,
        policy="full_277_row_hubble_flow_embedding",
    )
    blockwise = solve_expanded_blockwise(expanded_system)

    scalar_vs_upstream = compare_network_results(upstream, recompressed)
    expanded_vs_scalar = compare_network_results(recompressed, expanded)
    blockwise_vs_expanded = compare_network_results(expanded, blockwise)
    normal_closure = {
        "max_abs_normal_matrix_difference": float(
            np.max(np.abs(recompressed["_normal"] - expanded["_normal"]))
        ),
        "max_abs_normal_rhs_difference": float(
            np.max(np.abs(recompressed["_rhs"] - expanded["_rhs"]))
        ),
    }
    chi2_delta = float(expanded["chi2"] - recompressed["chi2"])
    chi2_closure_residual = chi2_delta - float(fit["chi2"])
    rank_increase = int(expanded["covar_rank"] - recompressed["covar_rank"])
    ndof_increase = int(expanded["ndof"] - recompressed["ndof"])

    rng = np.random.default_rng(PERMUTATION_SEED)
    permutation_rows: list[dict[str, Any]] = []
    for iteration in range(PERMUTATION_COUNT):
        permutation = rng.permutation(len(data_alpha))
        permuted_data = data_alpha[permutation]
        permuted_covariance = covariance_alpha[np.ix_(permutation, permutation)]
        permuted_system = build_expanded_network(
            captured, permuted_data, permuted_covariance
        )
        permuted = solve_network(
            permuted_system["coefficients"],
            permuted_system["observations"],
            permuted_system["covariance"],
            ihub=ihub,
            iabs=iabs,
            policy=f"seeded_hf_permutation_{iteration:02d}",
        )
        comparison = compare_network_results(expanded, permuted)
        maximum = max(
            comparison["max_abs_parameter_difference"],
            comparison["max_abs_parameter_covariance_difference"],
            comparison["absolute_h0_difference"],
            comparison["absolute_h0_error_difference"],
        )
        permutation_sha256 = hashlib.sha256(
            np.asarray(permutation, dtype="<i8").tobytes()
        ).hexdigest()
        permutation_rows.append(
            {
                "iteration": iteration,
                "seed": PERMUTATION_SEED,
                "permutation_sha256": permutation_sha256,
                **comparison,
                "maximum_tested_difference": maximum,
                "tolerance": TOLERANCES["permutation"],
                "status": (
                    "PASS"
                    if maximum <= TOLERANCES["permutation"]
                    else "FAIL"
                ),
            }
        )

    return (
        {
            "scalar_link_row": link_row,
            "original_row_count": int(recompressed["nrows"]),
            "expanded_row_count": int(expanded["nrows"]),
            "hubble_flow_row_count": int(len(data_alpha)),
            "upstream": public_network_result(upstream),
            "independently_recompressed_scalar": public_network_result(
                recompressed
            ),
            "expanded_full_block": public_network_result(expanded),
            "expanded_blockwise": public_network_result(blockwise),
            "scalar_vs_upstream": scalar_vs_upstream,
            "expanded_vs_scalar": expanded_vs_scalar,
            "blockwise_vs_expanded": blockwise_vs_expanded,
            "normal_equation_closure": normal_closure,
            "expanded_minus_scalar_chi2": chi2_delta,
            "hubble_flow_minimum_chi2": float(fit["chi2"]),
            "chi2_closure_residual": chi2_closure_residual,
            "covariance_rank_increase": rank_increase,
            "ndof_increase": ndof_increase,
            "expected_rank_and_ndof_increase": len(data_alpha) - 1,
        },
        permutation_rows,
    )


def environment_record() -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pandas": pd.__version__,
        "upstream_commit": UPSTREAM_COMMIT,
        "contract_id": CONTRACT_ID,
        "official_pinv_atol": OFFICIAL_ATOL,
        "official_pinv_rtol": OFFICIAL_RTOL,
        "permutation_seed": PERMUTATION_SEED,
        "permutation_count": PERMUTATION_COUNT,
    }


def max_network_comparison(comparison: dict[str, Any]) -> float:
    return max(
        float(comparison["max_abs_parameter_difference"]),
        float(comparison["max_abs_parameter_covariance_difference"]),
        float(comparison["absolute_h0_difference"]),
        float(comparison["absolute_h0_error_difference"]),
    )


def scientific_gates(
    source: dict[str, Any],
    inventory: dict[str, Any],
    alpha_record: dict[str, Any],
    profile_rows: Sequence[dict[str, Any]],
    network: dict[str, Any],
    permutation_rows: Sequence[dict[str, Any]],
    fidelity: dict[str, Any],
) -> list[dict[str, Any]]:
    alpha_match = max(
        float(alpha_record["upstream_match"]["alpha_absolute_difference"]),
        float(
            alpha_record["upstream_match"][
                "alpha_error_absolute_difference"
            ]
        ),
    )
    solver_crosscheck = max(
        float(alpha_record["solver_crosscheck"]["alpha_absolute_difference"]),
        float(
            alpha_record["solver_crosscheck"][
                "alpha_error_absolute_difference"
            ]
        ),
        float(alpha_record["solver_crosscheck"]["chi2_absolute_difference"]),
    )
    scalar_difference = max_network_comparison(
        network["scalar_vs_upstream"]
    )
    expanded_difference = max_network_comparison(
        network["expanded_vs_scalar"]
    )
    blockwise_difference = max_network_comparison(
        network["blockwise_vs_expanded"]
    )
    normal_difference = max(
        float(
            network["normal_equation_closure"][
                "max_abs_normal_matrix_difference"
            ]
        ),
        float(
            network["normal_equation_closure"][
                "max_abs_normal_rhs_difference"
            ]
        ),
    )
    profile_max = max(
        float(row["absolute_identity_residual"]) for row in profile_rows
    )
    permutation_max = max(
        float(row["maximum_tested_difference"]) for row in permutation_rows
    )
    gates = [
        {
            "gate_id": "source_lock",
            "observed": int(source["locked_file_count"]),
            "requirement": 69,
            "status": (
                "PASS"
                if source["status"] == "PASS"
                and int(source["locked_file_count"]) == 69
                else "FAIL"
            ),
        },
        {
            "gate_id": "input_schema",
            "observed": inventory["status"],
            "requirement": "PASS",
            "status": inventory["status"],
        },
        {
            "gate_id": "covariance_spd",
            "observed": alpha_record["alpha_covariance"][
                "eigenvalue_min"
            ],
            "requirement": f">{TOLERANCES['covariance_min_eigenvalue']}",
            "status": (
                "PASS"
                if alpha_record["cholesky_succeeded"]
                and float(
                    alpha_record["alpha_covariance"]["eigenvalue_min"]
                )
                > TOLERANCES["covariance_min_eigenvalue"]
                else "FAIL"
            ),
        },
        {
            "gate_id": "upstream_baseline",
            "observed": fidelity["status"],
            "requirement": "PASS",
            "status": fidelity["status"],
        },
        {
            "gate_id": "alpha_reconstruction",
            "observed": alpha_match,
            "requirement": TOLERANCES["alpha_reconstruction"],
            "status": (
                "PASS"
                if alpha_match <= TOLERANCES["alpha_reconstruction"]
                else "FAIL"
            ),
        },
        {
            "gate_id": "solver_crosscheck",
            "observed": solver_crosscheck,
            "requirement": TOLERANCES["solver_crosscheck"],
            "status": (
                "PASS"
                if solver_crosscheck <= TOLERANCES["solver_crosscheck"]
                else "FAIL"
            ),
        },
        {
            "gate_id": "profile_identity",
            "observed": profile_max,
            "requirement": TOLERANCES["profile_identity"],
            "status": (
                "PASS"
                if profile_max <= TOLERANCES["profile_identity"]
                else "FAIL"
            ),
        },
        {
            "gate_id": "scalar_network_replacement",
            "observed": scalar_difference,
            "requirement": TOLERANCES["network"],
            "status": (
                "PASS"
                if scalar_difference <= TOLERANCES["network"]
                else "FAIL"
            ),
        },
        {
            "gate_id": "expanded_network_equivalence",
            "observed": expanded_difference,
            "requirement": TOLERANCES["network"],
            "status": (
                "PASS"
                if expanded_difference <= TOLERANCES["network"]
                else "FAIL"
            ),
        },
        {
            "gate_id": "normal_equation_closure",
            "observed": normal_difference,
            "requirement": TOLERANCES["normal_closure"],
            "status": (
                "PASS"
                if normal_difference <= TOLERANCES["normal_closure"]
                else "FAIL"
            ),
        },
        {
            "gate_id": "chi2_closure",
            "observed": abs(float(network["chi2_closure_residual"])),
            "requirement": TOLERANCES["chi2_closure"],
            "status": (
                "PASS"
                if abs(float(network["chi2_closure_residual"]))
                <= TOLERANCES["chi2_closure"]
                else "FAIL"
            ),
        },
        {
            "gate_id": "rank_dof_closure",
            "observed": [
                int(network["covariance_rank_increase"]),
                int(network["ndof_increase"]),
            ],
            "requirement": [EXPECTED_OBJECT_COUNT - 1, EXPECTED_OBJECT_COUNT - 1],
            "status": (
                "PASS"
                if int(network["covariance_rank_increase"])
                == EXPECTED_OBJECT_COUNT - 1
                and int(network["ndof_increase"])
                == EXPECTED_OBJECT_COUNT - 1
                else "FAIL"
            ),
        },
        {
            "gate_id": "blockwise_solver",
            "observed": blockwise_difference,
            "requirement": TOLERANCES["network"],
            "status": (
                "PASS"
                if blockwise_difference <= TOLERANCES["network"]
                else "FAIL"
            ),
        },
        {
            "gate_id": "seeded_permutations",
            "observed": permutation_max,
            "requirement": TOLERANCES["permutation"],
            "status": (
                "PASS"
                if len(permutation_rows) == PERMUTATION_COUNT
                and permutation_max <= TOLERANCES["permutation"]
                and all(row["status"] == "PASS" for row in permutation_rows)
                else "FAIL"
            ),
        },
    ]
    return gates


def resolve_execution_status(gates: Sequence[dict[str, Any]]) -> str:
    failed = {
        gate["gate_id"] for gate in gates if gate["status"] != "PASS"
    }
    if not failed:
        return FINAL_PASS_STATUS
    if "source_lock" in failed:
        return "HOLD_SOURCE_MISMATCH"
    if failed & {"input_schema", "covariance_spd"}:
        return "HOLD_PUBLIC_INPUT_INCOMPLETE"
    if failed & {
        "upstream_baseline",
        "alpha_reconstruction",
        "solver_crosscheck",
    }:
        return "HOLD_BASELINE_RECONSTRUCTION_MISMATCH"
    if "profile_identity" in failed:
        return "HOLD_COMPRESSION_IDENTITY_FAILURE"
    if failed & {
        "scalar_network_replacement",
        "expanded_network_equivalence",
        "normal_equation_closure",
        "chi2_closure",
        "rank_dof_closure",
        "blockwise_solver",
        "seeded_permutations",
    }:
        return "HOLD_NETWORK_EMBEDDING_MISMATCH"
    return "HOLD_VERIFICATION_FAILURE"

