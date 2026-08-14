#!/usr/bin/env python3
"""Core routines for the frozen H0DN numerical audit."""

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
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator

import numpy as np
import pandas as pd
import scipy
import scipy.linalg
from scipy.constants import c as C_METRES_PER_SECOND

from source_tools import UPSTREAM_COMMIT, verify_source


OFFICIAL_ATOL = 1.0e-10
OFFICIAL_RTOL = 0.0
PERMUTATION_SEED = 20260729
PERMUTATION_COUNT = 32
ZERO_DIAGONAL_ATOL = OFFICIAL_ATOL
ZERO_PRECISION_ROW_ATOL = OFFICIAL_ATOL
LEAVE_ONE_OUT_MATCH_ATOL = 1.0e-9

EXPECTED_BASELINE = {
    "neq": 255,
    "npars": 64,
    "covar_rank": 183,
    "h0_value": 73.4988,
    "h0_error": 0.8088,
    "chi2": 117.5597,
    "ndof": 119,
    "mzero_value": -19.252,
    "mzero_error": 0.022,
}


class AuditFailure(RuntimeError):
    """Raised when a frozen audit gate fails."""


@dataclass
class MatrixComponent:
    identifier: str
    family: str
    label: str
    rows: np.ndarray
    matrix: np.ndarray
    note: str
    aggregate: bool = False


@dataclass
class EquationBlock:
    identifier: str
    family: str
    label: str
    rows: np.ndarray
    note: str


@contextlib.contextmanager
def pushd(path: pathlib.Path) -> Iterator[None]:
    old = pathlib.Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo: pathlib.Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def slug(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"[^A-Za-z0-9._+-]+", "_", text)
    return text.strip("_") or "unnamed"


def finite_or_none(value: Any) -> Any:
    if isinstance(value, (np.floating, float)):
        converted = float(value)
        return converted if math.isfinite(converted) else None
    if isinstance(value, (np.integer, int)):
        return int(value)
    return value


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        converted = float(value)
        return converted if math.isfinite(converted) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if value is None or isinstance(value, str):
        return value
    return str(value)


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            json_safe(value),
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        handle.write("\n")


def write_tsv(path: pathlib.Path, rows: Iterable[dict[str, Any]]) -> None:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not materialized:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in materialized:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in materialized:
            converted: dict[str, Any] = {}
            for key in fields:
                value = row.get(key, "")
                if isinstance(value, (list, tuple, dict, np.ndarray)):
                    converted[key] = json.dumps(
                        json_safe(value),
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                else:
                    safe = finite_or_none(value)
                    converted[key] = "" if safe is None else safe
            writer.writerow(converted)


def capture_upstream_baseline(upstream: pathlib.Path) -> dict[str, Any]:
    """Run the untouched public main workflow and capture its matrices/metadata."""

    module_root = (upstream / "h0_constrainer").resolve()
    config_dir = module_root / "configs"
    if not config_dir.is_dir():
        raise AuditFailure(f"Missing upstream Python package: {module_root}")

    for name in list(sys.modules):
        if name == "h0_constrainer" or name.startswith("h0_constrainer."):
            del sys.modules[name]
    sys.path.insert(0, str(module_root))

    main_module = importlib.import_module("h0_constrainer.main")
    equation_module = importlib.import_module("h0_constrainer.equations")
    solver_module = importlib.import_module("h0_constrainer.solver")

    loaded_from = pathlib.Path(main_module.__file__).resolve()
    if module_root not in loaded_from.parents:
        raise AuditFailure(
            f"Loaded h0_constrainer from {loaded_from}, not {module_root}."
        )

    captured: dict[str, Any] = {}
    original_build = equation_module.build_equations
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

    equation_module.build_equations = capture_build
    solver_module.solve_system = capture_solve
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with pushd(config_dir), contextlib.redirect_stdout(
            stdout
        ), contextlib.redirect_stderr(stderr):
            main_module.main("config.ini")
    finally:
        equation_module.build_equations = original_build
        solver_module.solve_system = original_solve
        if sys.path and sys.path[0] == str(module_root):
            sys.path.pop(0)

    required = {
        "build_args",
        "build_kwargs",
        "equation_data",
        "upstream_solution",
    }
    if not required.issubset(captured):
        raise AuditFailure(
            "Upstream capture incomplete: "
            + ", ".join(sorted(required - set(captured)))
        )
    captured["stdout"] = stdout.getvalue()
    captured["stderr"] = stderr.getvalue()
    captured["loaded_module"] = str(loaded_from)
    return captured


def upstream_solution_summary(captured: dict[str, Any]) -> dict[str, Any]:
    equation_data = captured["equation_data"]
    solution = captured["upstream_solution"]
    return {
        "neq": int(equation_data["neq"]),
        "npars": int(equation_data["npars"]),
        "nhosts": int(equation_data["nhosts"]),
        "covar_rank": int(solution["covar_rank"]),
        "covar_nullity": int(solution["covar_dim"] - solution["covar_rank"]),
        "covar_condition_number": finite_or_none(solution["covar_cond"]),
        "h0_value": float(solution["h0_value"]),
        "h0_error": float(solution["h0_error"]),
        "logh0_value": float(solution["logh0_value"]),
        "logh0_variance": float(solution["logh0_var"]),
        "chi2": float(solution["chi2"]),
        "ndof": int(solution["ndof"]),
        "ndof_full": int(solution["ndof_full"]),
        "mzero_value": float(solution["mzero_value"]),
        "mzero_error": float(solution["mzero_error"]),
        "stdout": captured["stdout"],
        "stderr": captured["stderr"],
    }


def baseline_fidelity(summary: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    exact_keys = ["neq", "npars", "covar_rank", "ndof"]
    tolerances = {
        "h0_value": 5.0e-5,
        "h0_error": 5.0e-5,
        "chi2": 5.0e-5,
        "mzero_value": 5.0e-4,
        "mzero_error": 5.0e-4,
    }
    for key in exact_keys:
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
    for key, tolerance in tolerances.items():
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
        "status": "PASS"
        if all(check["status"] == "PASS" for check in checks)
        else "FAIL",
        "checks": checks,
    }


def _pinv_with_rank(
    matrix: np.ndarray,
    *,
    atol: float | None,
    rtol: float | None,
    use_default: bool,
) -> tuple[np.ndarray, int]:
    if use_default:
        inverse, rank = scipy.linalg.pinv(matrix, return_rank=True)
    else:
        inverse, rank = scipy.linalg.pinv(
            matrix,
            atol=float(atol),
            rtol=float(rtol),
            return_rank=True,
        )
    return inverse, int(rank)


def solve_gls(
    coeffs: np.ndarray,
    yval: np.ndarray,
    covar: np.ndarray,
    *,
    ihub: int,
    iabs: int | None,
    policy: str,
    atol: float | None = OFFICIAL_ATOL,
    rtol: float | None = OFFICIAL_RTOL,
    use_default: bool = False,
) -> dict[str, Any]:
    """Solve a GLS system and retain explicit rank/identifiability state."""

    nrows, npars = coeffs.shape
    covar_sym = 0.5 * (covar + covar.T)
    cov_eigenvalues = scipy.linalg.eigvalsh(covar_sym, check_finite=True)
    cov_scale = max(float(np.max(np.abs(cov_eigenvalues))), 1.0)
    materially_indefinite = bool(
        float(cov_eigenvalues[0]) < -1.0e-12 * cov_scale
    )

    try:
        inv_covar, covar_rank = _pinv_with_rank(
            covar_sym, atol=atol, rtol=rtol, use_default=use_default
        )
        normal = coeffs.T @ inv_covar @ coeffs
        normal = 0.5 * (normal + normal.T)
        _normal_pinv, normal_rank = _pinv_with_rank(
            normal, atol=atol, rtol=rtol, use_default=use_default
        )
    except (ValueError, np.linalg.LinAlgError) as exc:
        return {
            "policy": policy,
            "status": "HOLD_NUMERICAL_FAILURE",
            "message": str(exc),
            "nrows": nrows,
            "npars": npars,
        }

    common: dict[str, Any] = {
        "policy": policy,
        "nrows": int(nrows),
        "npars": int(npars),
        "atol": None if use_default else float(atol),
        "rtol": None if use_default else float(rtol),
        "covar_rank": covar_rank,
        "covar_nullity": int(nrows - covar_rank),
        "normal_rank": normal_rank,
        "normal_nullity": int(npars - normal_rank),
        "covar_min_eigenvalue": float(cov_eigenvalues[0]),
        "covar_max_eigenvalue": float(cov_eigenvalues[-1]),
        "covar_materially_indefinite": materially_indefinite,
        "_inv_covar": inv_covar,
        "_normal": normal,
    }
    if normal_rank < npars:
        return {
            **common,
            "status": "HOLD_UNIDENTIFIED",
            "message": "normal matrix is not full rank under the stated policy",
        }

    try:
        inv_normal = np.linalg.inv(normal)
        right_hand_side = coeffs.T @ inv_covar @ yval
        params = inv_normal @ right_hand_side
        residuals = yval - coeffs @ params
    except np.linalg.LinAlgError as exc:
        return {
            **common,
            "status": "HOLD_NUMERICAL_FAILURE",
            "message": str(exc),
        }

    logh0_variance = float(inv_normal[ihub, ihub])
    if not math.isfinite(logh0_variance) or logh0_variance <= 0:
        return {
            **common,
            "status": "HOLD_NONPOSITIVE_VARIANCE",
            "message": f"logH0 variance is {logh0_variance}",
        }

    logh0_value = float(params[ihub])
    h0_value = float(10.0**logh0_value)
    h0_error = float(
        10.0 ** (logh0_value + math.sqrt(logh0_variance)) - h0_value
    )
    chi2 = float(residuals.T @ inv_covar @ residuals)
    status = "OK_INDEFINITE_COVARIANCE" if materially_indefinite else "OK"
    result: dict[str, Any] = {
        **common,
        "status": status,
        "message": "",
        "logh0_value": logh0_value,
        "logh0_variance": logh0_variance,
        "h0_value": h0_value,
        "h0_error": h0_error,
        "chi2": chi2,
        "ndof": int(covar_rank - npars),
        "reduced_chi2": chi2 / (covar_rank - npars)
        if covar_rank > npars
        else None,
        "normal_condition_number": finite_or_none(np.linalg.cond(normal)),
        "_inv_normal": inv_normal,
        "_params": params,
        "_residuals": residuals,
    }
    if iabs is not None:
        mzero_variance = float(inv_normal[iabs, iabs])
        result["mzero_value"] = float(params[iabs])
        result["mzero_error"] = (
            math.sqrt(mzero_variance) if mzero_variance >= 0 else None
        )
    return result


def public_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: json_safe(value)
        for key, value in result.items()
        if not key.startswith("_")
    }


def matrix_diagnostics(
    matrix: np.ndarray,
    *,
    name: str,
    absolute_cutoff: float = OFFICIAL_ATOL,
) -> dict[str, Any]:
    sym = 0.5 * (matrix + matrix.T)
    finite = bool(np.all(np.isfinite(matrix)))
    eigenvalues = scipy.linalg.eigvalsh(sym, check_finite=True)
    singular_values = scipy.linalg.svdvals(sym, check_finite=True)
    max_abs = max(float(np.max(np.abs(sym))), np.finfo(float).tiny)
    symmetry_error = float(np.max(np.abs(matrix - matrix.T)))
    symmetry_relative = symmetry_error / max_abs
    retained = singular_values[singular_values > absolute_cutoff]
    scale = max(float(np.max(np.abs(eigenvalues))), np.finfo(float).tiny)
    material_negative = eigenvalues < (-1.0e-12 * scale)
    return {
        "name": name,
        "shape": list(matrix.shape),
        "dtype": str(matrix.dtype),
        "finite": finite,
        "symmetry_max_absolute_error": symmetry_error,
        "symmetry_relative_max_error": symmetry_relative,
        "diagonal_min": float(np.min(np.diag(sym))),
        "diagonal_max": float(np.max(np.diag(sym))),
        "eigenvalue_min": float(eigenvalues[0]),
        "eigenvalue_max": float(eigenvalues[-1]),
        "material_negative_eigenvalue_count": int(np.sum(material_negative)),
        "singular_value_min": float(singular_values[-1]),
        "singular_value_max": float(singular_values[0]),
        "rank_at_absolute_cutoff": int(np.sum(singular_values > absolute_cutoff)),
        "nullity_at_absolute_cutoff": int(
            matrix.shape[0] - np.sum(singular_values > absolute_cutoff)
        ),
        "full_condition_number": finite_or_none(np.linalg.cond(sym)),
        "retained_subspace_condition_number": (
            float(retained[0] / retained[-1]) if retained.size else None
        ),
        "smallest_eigenvalues": [float(value) for value in eigenvalues[:10]],
        "largest_eigenvalues": [float(value) for value in eigenvalues[-10:]],
        "smallest_singular_values": [
            float(value) for value in singular_values[-10:]
        ],
        "largest_singular_values": [
            float(value) for value in singular_values[:10]
        ],
    }


def _blank_matrix(size: int) -> np.ndarray:
    return np.zeros((size, size), dtype=float)


def reconstruct_covariance_components(
    captured: dict[str, Any],
) -> tuple[list[MatrixComponent], list[MatrixComponent], dict[str, Any]]:
    """Independently reconstruct every additive network covariance component."""

    equation_data = captured["equation_data"]
    args = captured["build_args"]
    kwargs = captured["build_kwargs"]
    covar = np.asarray(equation_data["covar"], dtype=float)
    size = covar.shape[0]
    host_df: pd.DataFrame = args[0]
    mm_df: pd.DataFrame | None = args[1]
    groups_df: pd.DataFrame | None = args[4]
    components: list[MatrixComponent] = []

    def add(
        identifier: str,
        family: str,
        label: str,
        rows: Iterable[int],
        matrix: np.ndarray,
        note: str,
    ) -> None:
        components.append(
            MatrixComponent(
                identifier=identifier,
                family=family,
                label=label,
                rows=np.asarray(sorted(set(int(row) for row in rows)), dtype=int),
                matrix=matrix,
                note=note,
            )
        )

    host_rows = np.arange(len(host_df), dtype=int)
    matrix = _blank_matrix(size)
    matrix[host_rows, host_rows] = (
        host_df["mu_error"].to_numpy(dtype=float) ** 2
    )
    add(
        "host_measurement_diagonal",
        "host_measurement",
        "All host-measurement diagonal variances",
        host_rows,
        matrix,
        "Reported host mu_error squared.",
    )

    anchors = np.asarray(kwargs["anchors"], dtype=object)
    anchor_index = np.asarray(kwargs["anchor_index"], dtype=int)
    anchor_errors = np.asarray(kwargs["mu_anchor_error"], dtype=float)
    for index, name in enumerate(anchors):
        rows = np.flatnonzero(anchor_index == index)
        matrix = _blank_matrix(size)
        matrix[np.ix_(rows, rows)] = anchor_errors[index] ** 2
        add(
            f"anchor:{index:02d}:{slug(name)}",
            "anchor",
            f"Geometric anchor {name}",
            rows,
            matrix,
            "Rank-one covariance from the encoded geometric-anchor uncertainty.",
        )

    mas = np.asarray(kwargs["mas"], dtype=object)
    mas_index = np.asarray(kwargs["mas_index"], dtype=int)
    mas_errors = np.asarray(kwargs["mas_error"], dtype=float)
    for index, name in enumerate(mas):
        rows = np.flatnonzero(mas_index == index)
        matrix = _blank_matrix(size)
        matrix[np.ix_(rows, rows)] = mas_errors[index] ** 2
        add(
            f"mas:{index:02d}:{slug(name)}",
            "mas",
            f"MAS {name}",
            rows,
            matrix,
            "Rank-one covariance from the encoded method-anchor-source reference.",
        )

    hms = np.asarray(kwargs["hms"], dtype=object)
    hms_index = np.asarray(kwargs["hms_index"], dtype=int)
    hms_errors = np.asarray(kwargs["mu_hms_error"], dtype=float)
    for index, name in enumerate(hms):
        rows = np.flatnonzero(hms_index == index)
        if len(rows) <= 1:
            continue
        matrix = _blank_matrix(size)
        matrix[np.ix_(rows, rows)] = hms_errors[index] ** 2
        matrix[rows, rows] = 0.0
        add(
            f"hms:{index:03d}:{slug(name)}",
            "hms",
            f"HMS {name}",
            rows,
            matrix,
            "Off-diagonal-only covariance exactly matching equations.py.",
        )

    group_start = len(host_df)
    if groups_df is not None and len(groups_df):
        rows = np.arange(group_start, group_start + len(groups_df), dtype=int)
        matrix = _blank_matrix(size)
        matrix[rows, rows] = groups_df["sigma"].to_numpy(dtype=float) ** 2
        add(
            "group_equation_diagonal",
            "group_equation",
            "All group-equation diagonal variances",
            rows,
            matrix,
            "Encoded intrinsic group dispersions.",
        )

    sn1a_df: pd.DataFrame | None = kwargs.get("sn1a_calib_df")
    sn1a_start = equation_data.get("ieq_sn1a_start")
    if sn1a_df is not None and sn1a_start is not None:
        rows = np.arange(sn1a_start, sn1a_start + len(sn1a_df), dtype=int)
        matrix = _blank_matrix(size)
        matrix[rows, rows] = sn1a_df["sigma"].to_numpy(dtype=float) ** 2
        add(
            "sn1a_calibrator_diagonal",
            "sn1a_calibrator",
            "All SN-Ia calibrator diagonal variances",
            rows,
            matrix,
            "Calibrator-magnitude variances including configured intrinsic dispersion.",
        )

    sbf_df: pd.DataFrame | None = kwargs.get("sbf_calib_df")
    sbf_start = equation_data.get("ieq_sbf_start")
    if sbf_df is not None and sbf_start is not None:
        rows = np.arange(sbf_start, sbf_start + len(sbf_df), dtype=int)
        matrix = _blank_matrix(size)
        matrix[rows, rows] = (
            sbf_df["m110_error"].to_numpy(dtype=float) ** 2
            + sbf_df["M110_error"].to_numpy(dtype=float) ** 2
        )
        add(
            "sbf_calibrator_diagonal",
            "sbf_calibrator",
            "All SBF calibrator diagonal variances",
            rows,
            matrix,
            "Sum of the encoded apparent- and absolute-magnitude variances.",
        )

    for identifier, family, label, key in [
        (
            "sn1a_hubble_flow_link_variance",
            "sn1a_hubble_flow_link",
            "SN-Ia Hubble-flow link variance",
            "ieq_h0_m1a",
        ),
        (
            "sbf_hubble_flow_link_variance",
            "sbf_hubble_flow_link",
            "SBF Hubble-flow link variance",
            "ieq_h0_msbf",
        ),
    ]:
        row = equation_data.get(key)
        if row is not None:
            matrix = _blank_matrix(size)
            matrix[row, row] = covar[row, row]
            add(
                identifier,
                family,
                label,
                [row],
                matrix,
                "The Hubble-flow fit is compressed to this one network variance.",
            )

    mm_start = equation_data.get("ieq_mm_start")
    if mm_df is not None and mm_start is not None:
        for index in range(len(mm_df)):
            row = int(mm_start + index)
            name = str(mm_df.iloc[index]["name"])
            matrix = _blank_matrix(size)
            matrix[row, row] = float(mm_df.iloc[index]["logh_error"]) ** 2
            add(
                f"megamaser:{index:02d}:{slug(name)}",
                "megamaser",
                f"Megamaser {name}",
                [row],
                matrix,
                "Individual megamaser log10(H0) variance.",
            )

    reconstructed = sum(
        (component.matrix for component in components),
        start=_blank_matrix(size),
    )
    residual = covar - reconstructed
    denominator = max(float(np.linalg.norm(covar, ord="fro")), np.finfo(float).tiny)
    closure = {
        "absolute_frobenius_error": float(np.linalg.norm(residual, ord="fro")),
        "relative_frobenius_error": float(
            np.linalg.norm(residual, ord="fro") / denominator
        ),
        "max_absolute_error": float(np.max(np.abs(residual))),
        "accepted_tolerance": 1.0e-12,
    }
    closure["status"] = (
        "PASS"
        if closure["relative_frobenius_error"]
        <= closure["accepted_tolerance"]
        else "FAIL"
    )

    aggregates: list[MatrixComponent] = []
    for family in ["anchor", "mas", "hms", "megamaser"]:
        members = [item for item in components if item.family == family]
        if len(members) <= 1:
            continue
        matrix = sum(
            (member.matrix for member in members), start=_blank_matrix(size)
        )
        rows = np.unique(np.concatenate([member.rows for member in members]))
        aggregates.append(
            MatrixComponent(
                identifier=f"aggregate:{family}:all",
                family=family,
                label=f"All {family} covariance components",
                rows=rows,
                matrix=matrix,
                note=f"Pre-specified aggregate of all {family} components.",
                aggregate=True,
            )
        )
    return components, aggregates, closure


def covariance_component_inventory(
    components: Iterable[MatrixComponent],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component in components:
        eigenvalues = scipy.linalg.eigvalsh(
            0.5 * (component.matrix + component.matrix.T),
            check_finite=True,
        )
        scale = max(float(np.max(np.abs(eigenvalues))), np.finfo(float).tiny)
        minimum = float(eigenvalues[0])
        rows.append(
            {
                "component_id": component.identifier,
                "family": component.family,
                "label": component.label,
                "is_aggregate": component.aggregate,
                "row_count": len(component.rows),
                "row_indices": component.rows.tolist(),
                "nonzero_element_count": int(np.count_nonzero(component.matrix)),
                "trace": float(np.trace(component.matrix)),
                "frobenius_norm": float(
                    np.linalg.norm(component.matrix, ord="fro")
                ),
                "minimum_eigenvalue": minimum,
                "maximum_eigenvalue": float(eigenvalues[-1]),
                "positive_semidefinite_at_fixed_tolerance": bool(
                    minimum >= -1.0e-12 * scale
                ),
                "note": component.note,
            }
        )
    return rows


def equation_inventory(captured: dict[str, Any]) -> list[dict[str, Any]]:
    equation_data = captured["equation_data"]
    args = captured["build_args"]
    kwargs = captured["build_kwargs"]
    host_df: pd.DataFrame = args[0]
    mm_df: pd.DataFrame | None = args[1]
    groups_df: pd.DataFrame | None = args[4]
    sn1a_df: pd.DataFrame | None = kwargs.get("sn1a_calib_df")
    sbf_df: pd.DataFrame | None = kwargs.get("sbf_calib_df")
    covar = equation_data["covar"]
    output: list[dict[str, Any]] = []

    group_start = len(host_df)
    group_stop = group_start + (0 if groups_df is None else len(groups_df))
    sn_start = equation_data.get("ieq_sn1a_start")
    sn_stop = None if sn_start is None else sn_start + len(sn1a_df)
    sbf_start = equation_data.get("ieq_sbf_start")
    sbf_stop = None if sbf_start is None else sbf_start + len(sbf_df)
    mm_start = equation_data.get("ieq_mm_start")
    mm_stop = None if mm_start is None else mm_start + len(mm_df)

    for index in range(equation_data["neq"]):
        metadata = {
            "equation_index": index,
            "equation_family": "unclassified",
            "object": "",
            "method": "",
            "anchor": "",
            "source": "",
            "mas": "",
            "hms": "",
        }
        if index < len(host_df):
            row = host_df.iloc[index]
            metadata.update(
                {
                    "equation_family": "host",
                    "object": row["host"],
                    "method": row["method"],
                    "anchor": row["anchor"],
                    "source": row["source"],
                    "mas": row["mas_name"],
                    "hms": row["hms_name"],
                }
            )
        elif group_start <= index < group_stop:
            row = groups_df.iloc[index - group_start]
            metadata.update(
                {
                    "equation_family": "group",
                    "object": f"{row['group']}:{row['host']}",
                }
            )
        elif sn_start is not None and sn_start <= index < sn_stop:
            row = sn1a_df.iloc[index - sn_start]
            metadata.update(
                {
                    "equation_family": "sn1a_calibrator",
                    "object": f"{row['host']}:{row['SN']}",
                }
            )
        elif sbf_start is not None and sbf_start <= index < sbf_stop:
            row = sbf_df.iloc[index - sbf_start]
            metadata.update(
                {
                    "equation_family": "sbf_calibrator",
                    "object": row["host"],
                }
            )
        elif index == equation_data.get("ieq_h0_m1a"):
            metadata.update(
                {
                    "equation_family": "sn1a_hubble_flow_link",
                    "object": "Pantheon+ intercept",
                }
            )
        elif index == equation_data.get("ieq_h0_msbf"):
            metadata.update(
                {
                    "equation_family": "sbf_hubble_flow_link",
                    "object": "SBF intercept",
                }
            )
        elif mm_start is not None and mm_start <= index < mm_stop:
            row = mm_df.iloc[index - mm_start]
            metadata.update(
                {
                    "equation_family": "megamaser",
                    "object": row["name"],
                }
            )
        metadata.update(
            {
                "equation_description": equation_data["eq_descr"][index],
                "equation_shape": equation_data["eq_shape"][index],
                "covariance_description": equation_data["eq_covar"][index],
                "y_value": float(equation_data["yval"][index]),
                "diagonal_variance": float(covar[index, index]),
                "diagonal_standard_deviation": float(
                    math.sqrt(covar[index, index])
                ),
            }
        )
        output.append(metadata)
    unclassified = [
        row["equation_index"]
        for row in output
        if row["equation_family"] == "unclassified"
    ]
    if unclassified:
        raise AuditFailure(f"Unclassified equation rows: {unclassified}")
    return output


def parameter_inventory(captured: dict[str, Any]) -> list[dict[str, Any]]:
    equation_data = captured["equation_data"]
    return [
        {
            "parameter_index": index,
            "name": item.get("name", ""),
            "object": item.get("objname", ""),
            "type": item.get("type", ""),
            "is_h0": index == equation_data["ihub"],
            "is_sn1a_absolute_magnitude": index == equation_data["iabs"],
        }
        for index, item in enumerate(equation_data["parinfo"])
    ]


def build_equation_blocks(captured: dict[str, Any]) -> list[EquationBlock]:
    equation_data = captured["equation_data"]
    args = captured["build_args"]
    kwargs = captured["build_kwargs"]
    host_df: pd.DataFrame = args[0]
    mm_df: pd.DataFrame | None = args[1]
    groups_df: pd.DataFrame | None = args[4]
    sn1a_df: pd.DataFrame | None = kwargs.get("sn1a_calib_df")
    sbf_df: pd.DataFrame | None = kwargs.get("sbf_calib_df")
    blocks: list[EquationBlock] = []

    def add(
        identifier: str,
        family: str,
        label: str,
        rows: Iterable[int],
        note: str,
    ) -> None:
        block_rows = np.asarray(sorted(set(int(row) for row in rows)), dtype=int)
        if block_rows.size == 0:
            return
        blocks.append(
            EquationBlock(identifier, family, label, block_rows, note)
        )

    for column, family in [
        ("method", "host_by_method"),
        ("anchor", "host_by_anchor"),
        ("source", "host_by_source"),
        ("mas_name", "host_by_mas"),
    ]:
        for value in pd.unique(host_df[column]):
            rows = np.flatnonzero(
                host_df[column].astype(str).to_numpy() == str(value)
            )
            add(
                f"{family}:{slug(value)}",
                family,
                f"Host rows with {column}={value}",
                rows,
                "Pre-specified grouping from the public host-data schema.",
            )

    group_start = len(host_df)
    if groups_df is not None and len(groups_df):
        add(
            "all_group_equations",
            "equation_family",
            "All group equations",
            range(group_start, group_start + len(groups_df)),
            "All encoded host-to-group ties.",
        )

    sn_start = equation_data.get("ieq_sn1a_start")
    if sn_start is not None and sn1a_df is not None:
        add(
            "all_sn1a_calibrator_equations",
            "equation_family",
            "All SN-Ia calibrator equations",
            range(sn_start, sn_start + len(sn1a_df)),
            "All nearby SN-Ia calibration equations.",
        )

    sbf_start = equation_data.get("ieq_sbf_start")
    if sbf_start is not None and sbf_df is not None:
        add(
            "all_sbf_calibrator_equations",
            "equation_family",
            "All SBF calibrator equations",
            range(sbf_start, sbf_start + len(sbf_df)),
            "All SBF calibration equations.",
        )

    for identifier, label, key in [
        (
            "sn1a_hubble_flow_link",
            "SN-Ia Hubble-flow link",
            "ieq_h0_m1a",
        ),
        ("sbf_hubble_flow_link", "SBF Hubble-flow link", "ieq_h0_msbf"),
    ]:
        row = equation_data.get(key)
        if row is not None:
            add(
                identifier,
                "hubble_flow_link",
                label,
                [row],
                "The single equation carrying the fitted Hubble-flow intercept.",
            )

    mm_start = equation_data.get("ieq_mm_start")
    if mm_start is not None and mm_df is not None:
        mm_rows = []
        for index in range(len(mm_df)):
            row = mm_start + index
            mm_rows.append(row)
            name = mm_df.iloc[index]["name"]
            add(
                f"megamaser:{index:02d}:{slug(name)}",
                "megamaser_individual",
                f"Megamaser equation {name}",
                [row],
                "One direct megamaser H0 constraint.",
            )
        add(
            "all_megamaser_equations",
            "equation_family",
            "All megamaser equations",
            mm_rows,
            "All direct megamaser H0 constraints.",
        )
    return blocks


def equation_block_inventory(
    blocks: Iterable[EquationBlock],
) -> list[dict[str, Any]]:
    return [
        {
            "block_id": block.identifier,
            "family": block.family,
            "label": block.label,
            "row_count": len(block.rows),
            "row_indices": block.rows.tolist(),
            "note": block.note,
        }
        for block in blocks
    ]


def with_baseline_deltas(
    row: dict[str, Any], result: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    output = {**row, **public_result(result)}
    if str(result.get("status", "")).startswith("OK"):
        delta_h0 = float(result["h0_value"] - baseline["h0_value"])
        delta_error = float(result["h0_error"] - baseline["h0_error"])
        output.update(
            {
                "delta_h0": delta_h0,
                "absolute_delta_h0": abs(delta_h0),
                "delta_h0_in_baseline_sigma": delta_h0
                / float(baseline["h0_error"]),
                "delta_sigma_h0": delta_error,
                "absolute_delta_sigma_h0": abs(delta_error),
            }
        )
    return output


def covariance_model_status(result: dict[str, Any]) -> str:
    """Classify only the ablated covariance, separately from solver success."""

    if result.get("covar_materially_indefinite") is True:
        return "INDEFINITE"
    rank = result.get("covar_rank")
    nrows = result.get("nrows")
    if isinstance(rank, (int, np.integer)) and isinstance(
        nrows, (int, np.integer)
    ):
        return "PSD" if int(rank) == int(nrows) else "SINGULAR_PSD"
    return "HOLD"


def ablation_interpretation_status(
    result: dict[str, Any],
    *,
    zero_precision_row_count: int,
) -> str:
    """Separate numerical completion from the scientific/algebraic meaning."""

    solver_status = str(result.get("status", ""))
    if solver_status == "HOLD_UNIDENTIFIED":
        return "HOLD_UNIDENTIFIED"
    if not solver_status.startswith("OK"):
        return "HOLD_NUMERICAL_FAILURE"
    if bool(result.get("covar_materially_indefinite")):
        return "INDEFINITE_ALGEBRAIC_DIAGNOSTIC"
    if zero_precision_row_count:
        return "PSEUDOINVERSE_DISCARDED_CONSTRAINT"
    return "PSD_ALGEBRAIC_SENSITIVITY"


def run_component_ablations(
    captured: dict[str, Any],
    components: Iterable[MatrixComponent],
    baseline: dict[str, Any],
) -> list[dict[str, Any]]:
    equation_data = captured["equation_data"]
    coeffs = np.asarray(equation_data["coeffs"], dtype=float)
    yval = np.asarray(equation_data["yval"], dtype=float)
    covar = np.asarray(equation_data["covar"], dtype=float)
    output: list[dict[str, Any]] = []
    for component in components:
        ablated = covar - component.matrix
        ablated = 0.5 * (ablated + ablated.T)
        result = solve_gls(
            coeffs,
            yval,
            ablated,
            ihub=equation_data["ihub"],
            iabs=equation_data["iabs"],
            policy="official_after_component_ablation",
        )
        diagonal = np.diag(ablated)
        zero_diagonal_indices = np.flatnonzero(
            np.abs(diagonal) <= ZERO_DIAGONAL_ATOL
        )
        precision = result.get("_inv_covar")
        if isinstance(precision, np.ndarray):
            precision_row_l2 = np.linalg.norm(precision, axis=1)
            discarded = np.flatnonzero(
                precision_row_l2 <= ZERO_PRECISION_ROW_ATOL
            )
        else:
            discarded = np.asarray([], dtype=int)
        solver_status = str(result.get("status", ""))
        model_status = covariance_model_status(result)
        interpretation_status = ablation_interpretation_status(
            result,
            zero_precision_row_count=int(len(discarded)),
        )
        row = {
            "component_id": component.identifier,
            "family": component.family,
            "label": component.label,
            "is_aggregate": component.aggregate,
            "removed_row_count": len(component.rows),
            "removed_trace": float(np.trace(component.matrix)),
            "removed_frobenius_norm": float(
                np.linalg.norm(component.matrix, ord="fro")
            ),
            "interpretation": component.note,
            "solver_status": solver_status,
            "interpretation_status": interpretation_status,
            "rank_change_from_baseline": (
                int(result["covar_rank"]) - int(baseline["covar_rank"])
                if result.get("covar_rank") is not None
                else None
            ),
            "zero_diagonal_count": int(len(zero_diagonal_indices)),
            "zero_precision_row_count": int(len(discarded)),
            "discarded_equation_indices": discarded.tolist(),
            "matched_leave_one_block_out_id": "",
            "matched_leave_one_block_out_delta_h0": None,
            "matched_leave_one_block_out_baseline_delta_h0": None,
            "matched_leave_one_block_out_delta_h0_error": None,
            "matched_leave_one_block_out_parameter_max_absolute_difference": (
                None
            ),
            "matched_leave_one_block_out_match_status": "NO_EXACT_ROW_BLOCK",
            "covariance_model_status": model_status,
            "zero_diagonal_atol": ZERO_DIAGONAL_ATOL,
            "zero_precision_row_l2_atol": ZERO_PRECISION_ROW_ATOL,
        }
        output_row = with_baseline_deltas(row, result, baseline)
        if "_params" in result:
            output_row["_params"] = result["_params"]
        output.append(output_row)
    return output


def run_leave_one_block_out(
    captured: dict[str, Any],
    blocks: Iterable[EquationBlock],
    baseline: dict[str, Any],
) -> list[dict[str, Any]]:
    equation_data = captured["equation_data"]
    coeffs = np.asarray(equation_data["coeffs"], dtype=float)
    yval = np.asarray(equation_data["yval"], dtype=float)
    covar = np.asarray(equation_data["covar"], dtype=float)
    output: list[dict[str, Any]] = []
    for block in blocks:
        keep = np.ones(equation_data["neq"], dtype=bool)
        keep[block.rows] = False
        result = solve_gls(
            coeffs[keep],
            yval[keep],
            covar[np.ix_(keep, keep)],
            ihub=equation_data["ihub"],
            iabs=equation_data["iabs"],
            policy="official_leave_one_block_out",
        )
        row = {
            "block_id": block.identifier,
            "family": block.family,
            "label": block.label,
            "removed_row_count": len(block.rows),
            "retained_row_count": int(np.sum(keep)),
            "removed_row_indices": block.rows.tolist(),
            "interpretation": block.note,
        }
        output_row = with_baseline_deltas(row, result, baseline)
        if "_params" in result:
            output_row["_params"] = result["_params"]
        output.append(output_row)
    return output


def match_component_ablations_to_leave_one_out(
    component_rows: list[dict[str, Any]],
    leave_one_out_rows: list[dict[str, Any]],
    *,
    tolerance: float = LEAVE_ONE_OUT_MATCH_ATOL,
) -> None:
    """Annotate exact discarded-row matches without changing numeric results."""

    for component in component_rows:
        discarded = {
            int(value)
            for value in component.get("discarded_equation_indices", [])
        }
        if not discarded:
            continue
        candidates = [
            row
            for row in leave_one_out_rows
            if {
                int(value)
                for value in row.get("removed_row_indices", [])
            }
            == discarded
        ]
        if not candidates:
            continue
        candidate = candidates[0]
        component["matched_leave_one_block_out_id"] = candidate["block_id"]
        if not str(component.get("solver_status", "")).startswith(
            "OK"
        ) or not str(candidate.get("status", "")).startswith("OK"):
            component["matched_leave_one_block_out_match_status"] = (
                "HOLD_SOLVER_STATUS"
            )
            continue

        h0_difference = float(
            component["h0_value"] - candidate["h0_value"]
        )
        h0_error_difference = float(
            component["h0_error"] - candidate["h0_error"]
        )
        component_params = np.asarray(component["_params"], dtype=float)
        candidate_params = np.asarray(candidate["_params"], dtype=float)
        parameter_difference = float(
            np.max(np.abs(component_params - candidate_params))
        )
        component["matched_leave_one_block_out_delta_h0"] = h0_difference
        component["matched_leave_one_block_out_baseline_delta_h0"] = float(
            candidate["delta_h0"]
        )
        component[
            "matched_leave_one_block_out_delta_h0_error"
        ] = h0_error_difference
        component[
            "matched_leave_one_block_out_parameter_max_absolute_difference"
        ] = parameter_difference
        component["matched_leave_one_block_out_match_status"] = (
            "PASS"
            if max(
                abs(h0_difference),
                abs(h0_error_difference),
                parameter_difference,
            )
            <= tolerance
            else "FAIL"
        )


def run_solver_sensitivity(
    captured: dict[str, Any], baseline: dict[str, Any]
) -> list[dict[str, Any]]:
    equation_data = captured["equation_data"]
    coeffs = np.asarray(equation_data["coeffs"], dtype=float)
    yval = np.asarray(equation_data["yval"], dtype=float)
    covar = np.asarray(equation_data["covar"], dtype=float)
    cases: list[tuple[str, float | None, float | None, bool]] = [
        ("official", OFFICIAL_ATOL, OFFICIAL_RTOL, False)
    ]
    for exponent in range(-14, -5):
        cases.append(
            (
                f"absolute_atol_1e{exponent}",
                10.0**exponent,
                0.0,
                False,
            )
        )
    eps_scaled = max(covar.shape) * np.finfo(float).eps
    for name, rtol in [
        ("relative_shape_times_eps", eps_scaled),
        ("relative_rtol_1e-14", 1.0e-14),
        ("relative_rtol_1e-12", 1.0e-12),
        ("relative_rtol_1e-10", 1.0e-10),
        ("relative_rtol_1e-8", 1.0e-8),
    ]:
        cases.append((name, 0.0, rtol, False))
    cases.append(("scipy_default", None, None, True))

    output: list[dict[str, Any]] = []
    for name, atol, rtol, default in cases:
        result = solve_gls(
            coeffs,
            yval,
            covar,
            ihub=equation_data["ihub"],
            iabs=equation_data["iabs"],
            policy=name,
            atol=atol,
            rtol=rtol,
            use_default=default,
        )
        output.append(
            with_baseline_deltas(
                {"sensitivity_family": "pseudoinverse_cutoff"},
                result,
                baseline,
            )
        )
    return output


def run_representation_invariance(
    captured: dict[str, Any], baseline: dict[str, Any]
) -> list[dict[str, Any]]:
    equation_data = captured["equation_data"]
    coeffs = np.asarray(equation_data["coeffs"], dtype=float)
    yval = np.asarray(equation_data["yval"], dtype=float)
    covar = np.asarray(equation_data["covar"], dtype=float)
    output: list[dict[str, Any]] = []

    diagonal = np.diag(covar)
    if np.any(diagonal <= 0):
        raise AuditFailure("Cannot row-standardize a nonpositive covariance diagonal.")
    scaling = 1.0 / np.sqrt(diagonal)
    standardized_coeffs = scaling[:, None] * coeffs
    standardized_y = scaling * yval
    standardized_covar = scaling[:, None] * covar * scaling[None, :]
    standardized = solve_gls(
        standardized_coeffs,
        standardized_y,
        standardized_covar,
        ihub=equation_data["ihub"],
        iabs=equation_data["iabs"],
        policy="official_after_diagonal_row_standardization",
    )
    row = with_baseline_deltas(
        {
            "representation_family": "diagonal_row_standardization",
            "case_index": 0,
            "case_digest": "",
        },
        standardized,
        baseline,
    )
    row["invariance_status"] = (
        "PASS"
        if row.get("absolute_delta_h0", math.inf) < 1.0e-6
        and row.get("absolute_delta_sigma_h0", math.inf) < 1.0e-6
        else "FAIL"
    )
    output.append(row)

    rng = np.random.default_rng(PERMUTATION_SEED)
    for index in range(PERMUTATION_COUNT):
        permutation = rng.permutation(equation_data["neq"])
        result = solve_gls(
            coeffs[permutation],
            yval[permutation],
            covar[np.ix_(permutation, permutation)],
            ihub=equation_data["ihub"],
            iabs=equation_data["iabs"],
            policy="official_after_simultaneous_permutation",
        )
        row = with_baseline_deltas(
            {
                "representation_family": "simultaneous_row_column_permutation",
                "case_index": index,
                "case_digest": hashlib.sha256(permutation.tobytes()).hexdigest(),
            },
            result,
            baseline,
        )
        row["invariance_status"] = (
            "PASS"
            if row.get("absolute_delta_h0", math.inf) < 1.0e-6
            and row.get("absolute_delta_sigma_h0", math.inf) < 1.0e-6
            else "FAIL"
        )
        output.append(row)
    return output


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


def build_sn1a_hubble_flow_system(
    captured: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild the exact advanced-mode SN-Ia intercept system."""

    args = captured["build_args"]
    kwargs = captured["build_kwargs"]
    dataframe: pd.DataFrame = kwargs["sn1a_hf_df"]
    covariance_mag = np.asarray(kwargs["sn1a_hf_cov"], dtype=float)
    vpec_column = kwargs["sn1a_vp_column"]
    q0 = float(args[5])
    j0 = float(args[6])
    velocity_dispersion = float(args[7])
    speed_of_light = C_METRES_PER_SECOND / 1000.0

    zcmb = dataframe["zcmb"].to_numpy(dtype=float)
    zhel = dataframe["zhel"].to_numpy(dtype=float)
    vcmb = _z_to_vel(zcmb, speed_of_light)
    vhel = _z_to_vel(zhel, speed_of_light)
    vpec = dataframe[vpec_column].to_numpy(dtype=float)
    zpec = _vel_to_z(vpec, speed_of_light)
    zcorrected = (1.0 + zcmb) / (1.0 + zpec) - 1.0
    vcorrected = _z_to_vel(zcorrected, speed_of_light)
    t1 = (1.0 + zhel) / (1.0 + zcorrected)
    t2 = speed_of_light * zcorrected
    t3 = _kz(zcorrected, q0, j0)
    magnitude_model = 5.0 * np.log10(t1 * t2 * t3)
    data = 0.2 * (
        magnitude_model - dataframe["mb"].to_numpy(dtype=float)
    )
    velocity_variance = (
        np.log10(vcorrected + velocity_dispersion)
        - np.log10(vcorrected)
    ) ** 2
    covariance_alpha_full = (
        covariance_mag / 25.0 + np.diag(velocity_variance)
    )
    covariance_alpha_diagonal = (
        np.diag(np.diag(covariance_mag)) / 25.0
        + np.diag(velocity_variance)
    )
    return {
        "data": data,
        "ones": np.ones(len(data), dtype=float),
        "covariance_mag": covariance_mag,
        "velocity_variance": velocity_variance,
        "covariance_alpha_full": covariance_alpha_full,
        "covariance_alpha_diagonal": covariance_alpha_diagonal,
        "vpec_column": vpec_column,
        "object_count": len(data),
    }


def solve_intercept_direct(
    data: np.ndarray, covariance: np.ndarray, *, policy: str
) -> dict[str, Any]:
    inverse = np.linalg.inv(covariance)
    ones = np.ones(len(data), dtype=float)
    denominator = float(ones @ inverse @ ones)
    variance = 1.0 / denominator
    alpha = float(variance * (ones @ inverse @ data))
    residual = data - alpha
    chi2 = float(residual @ inverse @ residual)
    return {
        "policy": policy,
        "status": "OK",
        "object_count": len(data),
        "covar_rank": int(np.linalg.matrix_rank(covariance)),
        "covar_condition_number": finite_or_none(np.linalg.cond(covariance)),
        "alpha": alpha,
        "alpha_error": math.sqrt(variance),
        "chi2": chi2,
        "ndof": len(data) - 1,
    }


def solve_intercept_pinv(
    data: np.ndarray,
    covariance: np.ndarray,
    *,
    policy: str,
    atol: float | None,
    rtol: float | None,
    use_default: bool = False,
) -> dict[str, Any]:
    inverse, rank = _pinv_with_rank(
        covariance, atol=atol, rtol=rtol, use_default=use_default
    )
    ones = np.ones(len(data), dtype=float)
    denominator = float(ones @ inverse @ ones)
    if not math.isfinite(denominator) or denominator <= 0:
        return {
            "policy": policy,
            "status": "HOLD_NONPOSITIVE_INFORMATION",
            "object_count": len(data),
            "covar_rank": rank,
            "atol": None if use_default else atol,
            "rtol": None if use_default else rtol,
        }
    variance = 1.0 / denominator
    alpha = float(variance * (ones @ inverse @ data))
    residual = data - alpha
    return {
        "policy": policy,
        "status": "OK",
        "object_count": len(data),
        "covar_rank": rank,
        "atol": None if use_default else atol,
        "rtol": None if use_default else rtol,
        "alpha": alpha,
        "alpha_error": math.sqrt(variance),
        "chi2": float(residual @ inverse @ residual),
        "ndof": rank - 1,
    }


def run_hubble_flow_covariance_audit(
    captured: dict[str, Any],
    baseline: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    system = build_sn1a_hubble_flow_system(captured)
    data = system["data"]
    full = system["covariance_alpha_full"]
    diagonal = system["covariance_alpha_diagonal"]
    direct_full = solve_intercept_direct(
        data, full, policy="upstream_direct_inverse_full_covariance"
    )
    direct_diagonal = solve_intercept_direct(
        data, diagonal, policy="direct_inverse_diagonal_only_covariance"
    )

    equation_data = captured["equation_data"]
    upstream_alpha = float(equation_data["a_sn1a"])
    upstream_alpha_error = float(equation_data["a_sn1a_err"])
    full_match = {
        "alpha_absolute_difference": abs(direct_full["alpha"] - upstream_alpha),
        "alpha_error_absolute_difference": abs(
            direct_full["alpha_error"] - upstream_alpha_error
        ),
    }
    full_match["status"] = (
        "PASS"
        if full_match["alpha_absolute_difference"] < 1.0e-14
        and full_match["alpha_error_absolute_difference"] < 1.0e-14
        else "FAIL"
    )

    network_y = np.array(equation_data["yval"], copy=True)
    network_covar = np.array(equation_data["covar"], copy=True)
    link_row = int(equation_data["ieq_h0_m1a"])
    network_y[link_row] = direct_diagonal["alpha"] + 5.0
    network_covar[link_row, link_row] = direct_diagonal["alpha_error"] ** 2
    diagonal_network = solve_gls(
        equation_data["coeffs"],
        network_y,
        network_covar,
        ihub=equation_data["ihub"],
        iabs=equation_data["iabs"],
        policy="network_with_diagonal_only_sn1a_hubble_flow_covariance",
    )
    diagonal_network_public = with_baseline_deltas(
        {"case": "diagonal_only_sn1a_hubble_flow_covariance"},
        diagonal_network,
        baseline,
    )

    sensitivity: list[dict[str, Any]] = []
    sensitivity.append(
        {
            "covariance_case": "full",
            "sensitivity_family": "direct_inverse",
            **direct_full,
            "delta_alpha_from_full": 0.0,
            "delta_alpha_error_from_full": 0.0,
        }
    )
    sensitivity.append(
        {
            "covariance_case": "diagonal_only",
            "sensitivity_family": "structural_offdiagonal_ablation",
            **direct_diagonal,
            "delta_alpha_from_full": direct_diagonal["alpha"]
            - direct_full["alpha"],
            "delta_alpha_error_from_full": direct_diagonal["alpha_error"]
            - direct_full["alpha_error"],
        }
    )

    for exponent in range(-14, -5):
        result = solve_intercept_pinv(
            data,
            full,
            policy=f"full_absolute_atol_1e{exponent}",
            atol=10.0**exponent,
            rtol=0.0,
        )
        result.update(
            {
                "covariance_case": "full",
                "sensitivity_family": "pseudoinverse_cutoff",
                "delta_alpha_from_full": result.get("alpha", math.nan)
                - direct_full["alpha"],
                "delta_alpha_error_from_full": result.get(
                    "alpha_error", math.nan
                )
                - direct_full["alpha_error"],
            }
        )
        sensitivity.append(result)

    eps_scaled = max(full.shape) * np.finfo(float).eps
    for name, rtol in [
        ("shape_times_eps", eps_scaled),
        ("1e-14", 1.0e-14),
        ("1e-12", 1.0e-12),
        ("1e-10", 1.0e-10),
        ("1e-8", 1.0e-8),
    ]:
        result = solve_intercept_pinv(
            data,
            full,
            policy=f"full_relative_rtol_{name}",
            atol=0.0,
            rtol=rtol,
        )
        result.update(
            {
                "covariance_case": "full",
                "sensitivity_family": "pseudoinverse_cutoff",
                "delta_alpha_from_full": result.get("alpha", math.nan)
                - direct_full["alpha"],
                "delta_alpha_error_from_full": result.get(
                    "alpha_error", math.nan
                )
                - direct_full["alpha_error"],
            }
        )
        sensitivity.append(result)

    standardized_scale = 1.0 / np.sqrt(np.diag(full))
    standardized_data = standardized_scale * data
    standardized_design = standardized_scale
    standardized_covar = (
        standardized_scale[:, None]
        * full
        * standardized_scale[None, :]
    )
    inverse = np.linalg.inv(standardized_covar)
    denominator = float(standardized_design @ inverse @ standardized_design)
    variance = 1.0 / denominator
    alpha = float(
        variance
        * (standardized_design @ inverse @ standardized_data)
    )
    residual = standardized_data - standardized_design * alpha
    standardized_result = {
        "covariance_case": "full",
        "sensitivity_family": "diagonal_row_standardization",
        "policy": "direct_inverse_after_equivalent_standardization",
        "status": "OK",
        "object_count": len(data),
        "covar_rank": int(np.linalg.matrix_rank(standardized_covar)),
        "alpha": alpha,
        "alpha_error": math.sqrt(variance),
        "chi2": float(residual @ inverse @ residual),
        "ndof": len(data) - 1,
        "delta_alpha_from_full": alpha - direct_full["alpha"],
        "delta_alpha_error_from_full": math.sqrt(variance)
        - direct_full["alpha_error"],
    }
    sensitivity.append(standardized_result)

    rng = np.random.default_rng(PERMUTATION_SEED)
    for index in range(PERMUTATION_COUNT):
        permutation = rng.permutation(len(data))
        result = solve_intercept_direct(
            data[permutation],
            full[np.ix_(permutation, permutation)],
            policy="direct_inverse_after_simultaneous_permutation",
        )
        result.update(
            {
                "covariance_case": "full",
                "sensitivity_family": "simultaneous_permutation",
                "case_index": index,
                "case_digest": hashlib.sha256(
                    permutation.tobytes()
                ).hexdigest(),
                "delta_alpha_from_full": result["alpha"]
                - direct_full["alpha"],
                "delta_alpha_error_from_full": result["alpha_error"]
                - direct_full["alpha_error"],
            }
        )
        sensitivity.append(result)

    summary = {
        "object_count": system["object_count"],
        "peculiar_velocity_column": system["vpec_column"],
        "upstream_alpha": upstream_alpha,
        "upstream_alpha_error": upstream_alpha_error,
        "independent_full_covariance_result": direct_full,
        "upstream_match": full_match,
        "diagonal_only_result": direct_diagonal,
        "diagonal_only_network_result": diagonal_network_public,
        "magnitude_covariance_diagnostics": matrix_diagnostics(
            system["covariance_mag"],
            name="Pantheon+ magnitude covariance",
        ),
        "full_alpha_covariance_diagnostics": matrix_diagnostics(
            full,
            name="Pantheon+ alpha covariance plus velocity variance",
        ),
        "diagonal_alpha_covariance_diagnostics": matrix_diagnostics(
            diagonal,
            name="Pantheon+ diagonal-only alpha covariance plus velocity variance",
        ),
    }
    return summary, sensitivity


def run_metadata(
    project_root: pathlib.Path,
    upstream: pathlib.Path,
    source_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "project": "h0dn-covariance-influence-audit",
        "contract_version": "0.1.0",
        "contract_git_commit": git_output(
            project_root, "rev-list", "--max-parents=0", "HEAD"
        ),
        "project_git_commit_at_execution": git_output(
            project_root, "rev-parse", "HEAD"
        ),
        "project_git_status_at_execution": git_output(
            project_root, "status", "--short"
        ),
        "upstream_path": str(upstream),
        "upstream_commit": UPSTREAM_COMMIT,
        "source_verification": source_result,
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "pandas_version": pd.__version__,
        "blas_lapack_configuration": {
            "note": "Use `python -m numpy.__config__` for the full local build report."
        },
        "permutation_seed": PERMUTATION_SEED,
        "permutation_count": PERMUTATION_COUNT,
        "official_pinv_atol": OFFICIAL_ATOL,
        "official_pinv_rtol": OFFICIAL_RTOL,
        "contract_sha256": sha256_file(project_root / "AUDIT_CONTRACT.md"),
    }
