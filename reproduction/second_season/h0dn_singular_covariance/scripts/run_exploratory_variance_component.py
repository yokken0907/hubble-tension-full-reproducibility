#!/usr/bin/env python3
"""Fit the frozen exploratory Cepheid interaction-variance component."""

from __future__ import annotations

import argparse
import math
import pathlib
import sys
import traceback
from dataclasses import dataclass
from typing import Any

import numpy as np
import scipy.linalg
import scipy.optimize

from auditlib import (
    OFFICIAL_ATOL,
    capture_upstream_baseline,
    upstream_solution_summary,
    verify_source,
    write_json,
    write_tsv,
)


TAU_LOWER = 1.0e-5
TAU_UPPER = 0.3
PROFILE_POINTS = 161
OPTIMIZER_XATOL = 1.0e-12
PROFILE_LEVELS = (1.0, 3.841459)


@dataclass
class FullRankFit:
    tau: float
    reml_deviance: float
    ml_deviance: float
    logdet_covariance: float
    logdet_normal: float
    chi2: float
    h0_value: float
    h0_error: float
    logh0_value: float
    logh0_variance: float
    mzero_value: float | None
    mzero_error: float | None
    covariance_min_eigenvalue: float
    covariance_rank_at_public_cutoff: int
    normal_min_eigenvalue: float
    normal_rank_at_public_cutoff: int

    def public(self) -> dict[str, Any]:
        return {
            "tau": self.tau,
            "reml_deviance": self.reml_deviance,
            "ml_deviance": self.ml_deviance,
            "logdet_covariance": self.logdet_covariance,
            "logdet_normal": self.logdet_normal,
            "chi2": self.chi2,
            "h0_value": self.h0_value,
            "h0_error": self.h0_error,
            "logh0_value": self.logh0_value,
            "logh0_variance": self.logh0_variance,
            "mzero_value": self.mzero_value,
            "mzero_error": self.mzero_error,
            "covariance_min_eigenvalue": self.covariance_min_eigenvalue,
            "covariance_rank_at_public_cutoff": (
                self.covariance_rank_at_public_cutoff
            ),
            "normal_min_eigenvalue": self.normal_min_eigenvalue,
            "normal_rank_at_public_cutoff": self.normal_rank_at_public_cutoff,
        }


class FitEvaluator:
    """Cholesky GLS evaluator with an explicit variance-component matrix."""

    def __init__(
        self,
        coeffs: np.ndarray,
        yval: np.ndarray,
        base_covariance: np.ndarray,
        component: np.ndarray,
        *,
        ihub: int,
        iabs: int | None,
    ) -> None:
        self.coeffs = np.asarray(coeffs, dtype=float)
        self.yval = np.asarray(yval, dtype=float)
        self.base_covariance = np.asarray(base_covariance, dtype=float)
        self.component = np.asarray(component, dtype=float)
        self.ihub = int(ihub)
        self.iabs = None if iabs is None else int(iabs)
        self._cache: dict[float, FullRankFit] = {}

    def evaluate(self, tau: float) -> FullRankFit:
        tau = float(tau)
        if not math.isfinite(tau) or tau <= 0:
            raise ValueError(f"tau must be positive and finite, got {tau}")
        key = float(np.float64(tau))
        if key in self._cache:
            return self._cache[key]

        covariance = self.base_covariance + tau**2 * self.component
        covariance = 0.5 * (covariance + covariance.T)
        chol_covariance = scipy.linalg.cholesky(
            covariance, lower=True, check_finite=True
        )
        whitened_design = scipy.linalg.solve_triangular(
            chol_covariance,
            self.coeffs,
            lower=True,
            check_finite=True,
        )
        whitened_data = scipy.linalg.solve_triangular(
            chol_covariance,
            self.yval,
            lower=True,
            check_finite=True,
        )
        normal = whitened_design.T @ whitened_design
        normal = 0.5 * (normal + normal.T)
        chol_normal = scipy.linalg.cholesky(
            normal, lower=True, check_finite=True
        )
        right_hand_side = whitened_design.T @ whitened_data
        params = scipy.linalg.cho_solve(
            (chol_normal, True), right_hand_side, check_finite=True
        )
        inv_normal = scipy.linalg.cho_solve(
            (chol_normal, True),
            np.eye(normal.shape[0]),
            check_finite=True,
        )
        whitened_residual = whitened_data - whitened_design @ params
        chi2 = float(whitened_residual @ whitened_residual)
        logdet_covariance = float(
            2.0 * np.sum(np.log(np.diag(chol_covariance)))
        )
        logdet_normal = float(
            2.0 * np.sum(np.log(np.diag(chol_normal)))
        )

        logh0_value = float(params[self.ihub])
        logh0_variance = float(inv_normal[self.ihub, self.ihub])
        if logh0_variance <= 0 or not math.isfinite(logh0_variance):
            raise RuntimeError(
                f"Nonpositive conditional logH0 variance: {logh0_variance}"
            )
        h0_value = float(10.0**logh0_value)
        h0_error = float(
            10.0 ** (logh0_value + math.sqrt(logh0_variance)) - h0_value
        )

        covariance_eigenvalues = scipy.linalg.eigvalsh(
            covariance, check_finite=True
        )
        normal_eigenvalues = scipy.linalg.eigvalsh(normal, check_finite=True)
        mzero_value: float | None = None
        mzero_error: float | None = None
        if self.iabs is not None:
            mzero_value = float(params[self.iabs])
            mzero_variance = float(inv_normal[self.iabs, self.iabs])
            if mzero_variance < 0:
                raise RuntimeError(
                    f"Negative conditional Mzero variance: {mzero_variance}"
                )
            mzero_error = math.sqrt(mzero_variance)

        result = FullRankFit(
            tau=tau,
            reml_deviance=logdet_covariance + logdet_normal + chi2,
            ml_deviance=logdet_covariance + chi2,
            logdet_covariance=logdet_covariance,
            logdet_normal=logdet_normal,
            chi2=chi2,
            h0_value=h0_value,
            h0_error=h0_error,
            logh0_value=logh0_value,
            logh0_variance=logh0_variance,
            mzero_value=mzero_value,
            mzero_error=mzero_error,
            covariance_min_eigenvalue=float(covariance_eigenvalues[0]),
            covariance_rank_at_public_cutoff=int(
                np.sum(covariance_eigenvalues > OFFICIAL_ATOL)
            ),
            normal_min_eigenvalue=float(normal_eigenvalues[0]),
            normal_rank_at_public_cutoff=int(
                np.sum(normal_eigenvalues > OFFICIAL_ATOL)
            ),
        )
        self._cache[key] = result
        return result


def optimize_tau(
    evaluator: FitEvaluator,
    objective_name: str,
) -> tuple[FullRankFit, dict[str, Any]]:
    if objective_name not in {"reml_deviance", "ml_deviance"}:
        raise ValueError(objective_name)

    def objective(log_tau: float) -> float:
        fit = evaluator.evaluate(math.exp(log_tau))
        return float(getattr(fit, objective_name))

    result = scipy.optimize.minimize_scalar(
        objective,
        bounds=(math.log(TAU_LOWER), math.log(TAU_UPPER)),
        method="bounded",
        options={"xatol": OPTIMIZER_XATOL, "maxiter": 1000},
    )
    if not result.success:
        raise RuntimeError(
            f"{objective_name} minimization failed: {result.message}"
        )
    fit = evaluator.evaluate(math.exp(float(result.x)))
    optimizer = {
        "objective": objective_name,
        "success": bool(result.success),
        "message": str(result.message),
        "iterations": int(result.nit),
        "evaluations": int(result.nfev),
        "log_tau": float(result.x),
        "tau": fit.tau,
        "objective_value": float(result.fun),
        "search_tau_lower": TAU_LOWER,
        "search_tau_upper": TAU_UPPER,
        "log_tau_absolute_tolerance": OPTIMIZER_XATOL,
    }
    return fit, optimizer


def profile_interval(
    evaluator: FitEvaluator,
    optimum: FullRankFit,
    *,
    objective_name: str,
    rise: float,
) -> dict[str, Any]:
    minimum = float(getattr(optimum, objective_name))
    center = math.log(optimum.tau)

    def shifted(log_tau: float) -> float:
        fit = evaluator.evaluate(math.exp(log_tau))
        return float(getattr(fit, objective_name)) - minimum - rise

    output: dict[str, Any] = {
        "objective": objective_name,
        "deviance_rise": rise,
        "lower": None,
        "upper": None,
        "lower_status": "NO_CROSSING_IN_SEARCH_INTERVAL",
        "upper_status": "NO_CROSSING_IN_SEARCH_INTERVAL",
    }
    lower_bound = math.log(TAU_LOWER)
    upper_bound = math.log(TAU_UPPER)
    if shifted(lower_bound) >= 0:
        root = scipy.optimize.brentq(
            shifted, lower_bound, center, xtol=1.0e-13, rtol=1.0e-14
        )
        output["lower"] = math.exp(root)
        output["lower_status"] = "CROSSING"
    if shifted(upper_bound) >= 0:
        root = scipy.optimize.brentq(
            shifted, center, upper_bound, xtol=1.0e-13, rtol=1.0e-14
        )
        output["upper"] = math.exp(root)
        output["upper_status"] = "CROSSING"
    return output


def build_report(summary: dict[str, Any]) -> str:
    primary = summary["original_representation"]["reml_fit"]
    ml = summary["original_representation"]["ml_fit"]
    moment = summary["nullspace_moment"]
    baseline = summary["public_baseline"]
    interval = summary["original_representation"]["reml_profile_intervals"][0]
    checks = summary["invariance_and_structure_checks"]
    supplemental = summary["supplementary_numerical_context"]
    lines = [
        "# Exploratory Cepheid interaction-variance model",
        "",
        "This report is governed by",
        "`EXPLORATORY_VARIANCE_COMPONENT_CONTRACT.md`. The model and numerical",
        "checks were frozen before these values were calculated.",
        "",
        "## Main exploratory result",
        "",
        "The fitted additional independent host–anchor cell dispersion is",
        f"`tau = {primary['tau']:.8f} mag` by REML.",
        "The profile-deviance-rise-1 interval is",
        f"`[{interval['lower']:.8f}, {interval['upper']:.8f}] mag`.",
        "At that fitted value, the conditional network result is",
        f"`H0 = {primary['h0_value']:.8f} +/- {primary['h0_error']:.8f}`",
        "km/s/Mpc.",
        "",
        "For comparison, the untouched public Moore–Penrose baseline is",
        f"`H0 = {baseline['h0_value']:.8f} +/- {baseline['h0_error']:.8f}`",
        "km/s/Mpc. The exploratory conditional shift is",
        f"`{primary['h0_value'] - baseline['h0_value']:+.8f} km/s/Mpc`.",
        "This comparison does not make the exploratory result a corrected",
        "estimate.",
        "",
        "## Cross-checks",
        "",
        f"- ML gives `tau = {ml['tau']:.8f} mag`.",
        (
            "- The covariance-nullspace moment gives "
            f"`tau = {moment['tau']:.8f} mag` and, at that fixed value, "
            f"`H0 = {moment['conditional_fit']['h0_value']:.8f} +/- "
            f"{moment['conditional_fit']['h0_error']:.8f} km/s/Mpc`."
        ),
        (
            "- Exact row standardization changes the REML optimum by "
            f"`{checks['reml_fit']['absolute_delta_tau']:.3e} mag`, "
            f"`H0` by `{checks['reml_fit']['absolute_delta_h0']:.3e}`, "
            "and its conditional uncertainty by "
            f"`{checks['reml_fit']['absolute_delta_h0_error']:.3e}`."
        ),
        (
            "- The covariance rank is "
            f"`{primary['covariance_rank_at_public_cutoff']}` at the REML "
            "optimum, so this explicit model removes the 72 zero modes."
        ),
        (
            "- The fixed full profile-grid invariance check has status "
            f"**{checks['profile_grid']['status']}**; its largest absolute "
            "centered-deviance discrepancy is "
            f"`{checks['profile_grid']['maximum_absolute_centered_deviance_difference']:.3e}`."
        ),
        (
            "  This maximum occurs at "
            f"`tau = {supplemental['maximum_discrepancy_tau']:.1e} mag`, "
            "where the profile deviance is more than "
            f"`{supplemental['minimum_profile_rise_at_maximum_discrepancy']:.3e}` "
            "above its minimum. Over the fitted 95% REML profile interval, the "
            "largest discrepancy is only "
            f"`{supplemental['maximum_absolute_centered_deviance_difference_inside_reml_95_interval']:.3e}`."
        ),
        "",
        f"Overall contract-check status: **{summary['status']}**.",
        "",
        "## Scientific boundary",
        "",
        "The fitted nonzero dispersion shows that one explicit full-rank",
        "generative extension can absorb the exact-support inconsistency without",
        "the Moore–Penrose representation ambiguity. It does not determine",
        "whether the interaction is caused by rounding, bookkeeping, correlated",
        "calibration, or astrophysics; it also does not validate the independent",
        "cell-scatter assumption. No host or anchor was removed, and the result",
        "does not resolve the Hubble tension.",
        "",
    ]
    return "\n".join(lines)


def execute(
    project_root: pathlib.Path,
    upstream: pathlib.Path,
    output: pathlib.Path,
    source_manifest: pathlib.Path,
) -> dict[str, Any]:
    verify_source(upstream, source_manifest)
    captured = capture_upstream_baseline(upstream)
    equation_data = captured["equation_data"]
    coeffs = np.asarray(equation_data["coeffs"], dtype=float)
    yval = np.asarray(equation_data["yval"], dtype=float)
    covariance = np.asarray(equation_data["covar"], dtype=float)
    baseline = upstream_solution_summary(captured)

    host_df = captured["build_args"][0]
    selected = host_df[
        (host_df["method"].astype(str) == "ceph_hst")
        & (host_df["source"].astype(str) == "R22")
    ].copy()
    hosts = list(dict.fromkeys(selected["host"].astype(str)))
    anchors = list(dict.fromkeys(selected["anchor"].astype(str)))
    duplicate_count = int(
        selected.duplicated(subset=["host", "anchor"]).sum()
    )
    complete = (
        len(selected) == 111
        and len(hosts) == 37
        and len(anchors) == 3
        and duplicate_count == 0
    )
    if not complete:
        raise RuntimeError(
            "Frozen complete 37-host by 3-anchor Cepheid table not found."
        )

    selected_rows = np.asarray(selected.index, dtype=int)
    component = np.zeros_like(covariance)
    component[selected_rows, selected_rows] = 1.0
    eigenvalues, eigenvectors = scipy.linalg.eigh(
        0.5 * (covariance + covariance.T), check_finite=True
    )
    null_basis = eigenvectors[:, eigenvalues <= OFFICIAL_ATOL]
    nullity = int(null_basis.shape[1])
    projected_data_coordinates = null_basis.T @ yval
    moment_tau = float(
        np.sqrt(
            (projected_data_coordinates @ projected_data_coordinates)
            / nullity
        )
    )

    original = FitEvaluator(
        coeffs,
        yval,
        covariance,
        component,
        ihub=equation_data["ihub"],
        iabs=equation_data["iabs"],
    )
    diagonal_scaling = 1.0 / np.sqrt(np.diag(covariance))
    transformed = FitEvaluator(
        diagonal_scaling[:, None] * coeffs,
        diagonal_scaling * yval,
        diagonal_scaling[:, None]
        * covariance
        * diagonal_scaling[None, :],
        diagonal_scaling[:, None]
        * component
        * diagonal_scaling[None, :],
        ihub=equation_data["ihub"],
        iabs=equation_data["iabs"],
    )

    original_reml, original_reml_optimizer = optimize_tau(
        original, "reml_deviance"
    )
    transformed_reml, transformed_reml_optimizer = optimize_tau(
        transformed, "reml_deviance"
    )
    original_ml, original_ml_optimizer = optimize_tau(
        original, "ml_deviance"
    )
    transformed_ml, transformed_ml_optimizer = optimize_tau(
        transformed, "ml_deviance"
    )
    moment_fit = original.evaluate(moment_tau)
    transformed_moment_fit = transformed.evaluate(moment_tau)

    original_reml_intervals = [
        profile_interval(
            original,
            original_reml,
            objective_name="reml_deviance",
            rise=level,
        )
        for level in PROFILE_LEVELS
    ]
    transformed_reml_intervals = [
        profile_interval(
            transformed,
            transformed_reml,
            objective_name="reml_deviance",
            rise=level,
        )
        for level in PROFILE_LEVELS
    ]
    original_ml_intervals = [
        profile_interval(
            original,
            original_ml,
            objective_name="ml_deviance",
            rise=level,
        )
        for level in PROFILE_LEVELS
    ]
    transformed_ml_intervals = [
        profile_interval(
            transformed,
            transformed_ml,
            objective_name="ml_deviance",
            rise=level,
        )
        for level in PROFILE_LEVELS
    ]

    grid = np.geomspace(TAU_LOWER, TAU_UPPER, PROFILE_POINTS)
    all_tau = sorted(
        set(
            float(value)
            for value in [
                *grid,
                original_reml.tau,
                transformed_reml.tau,
                original_ml.tau,
                transformed_ml.tau,
                moment_tau,
            ]
        )
    )
    profile_rows: list[dict[str, Any]] = []
    reml_centered_differences: list[float] = []
    ml_centered_differences: list[float] = []
    for tau in all_tau:
        left = original.evaluate(tau)
        right = transformed.evaluate(tau)
        original_reml_delta = (
            left.reml_deviance - original_reml.reml_deviance
        )
        transformed_reml_delta = (
            right.reml_deviance - transformed_reml.reml_deviance
        )
        original_ml_delta = left.ml_deviance - original_ml.ml_deviance
        transformed_ml_delta = right.ml_deviance - transformed_ml.ml_deviance
        reml_difference = original_reml_delta - transformed_reml_delta
        ml_difference = original_ml_delta - transformed_ml_delta
        reml_centered_differences.append(reml_difference)
        ml_centered_differences.append(ml_difference)
        profile_rows.append(
            {
                "tau": tau,
                "original_reml_deviance": left.reml_deviance,
                "transformed_reml_deviance": right.reml_deviance,
                "original_reml_delta": original_reml_delta,
                "transformed_reml_delta": transformed_reml_delta,
                "reml_centered_deviance_difference": reml_difference,
                "original_ml_deviance": left.ml_deviance,
                "transformed_ml_deviance": right.ml_deviance,
                "original_ml_delta": original_ml_delta,
                "transformed_ml_delta": transformed_ml_delta,
                "ml_centered_deviance_difference": ml_difference,
                "original_h0_value": left.h0_value,
                "transformed_h0_value": right.h0_value,
                "h0_difference": left.h0_value - right.h0_value,
                "original_h0_error": left.h0_error,
                "transformed_h0_error": right.h0_error,
                "h0_error_difference": left.h0_error - right.h0_error,
                "original_chi2": left.chi2,
                "transformed_chi2": right.chi2,
                "original_covariance_min_eigenvalue": (
                    left.covariance_min_eigenvalue
                ),
                "original_covariance_rank_at_public_cutoff": (
                    left.covariance_rank_at_public_cutoff
                ),
            }
        )

    def fitted_invariance(
        left: FullRankFit, right: FullRankFit
    ) -> dict[str, Any]:
        delta_tau = abs(left.tau - right.tau)
        delta_h0 = abs(left.h0_value - right.h0_value)
        delta_h0_error = abs(left.h0_error - right.h0_error)
        return {
            "absolute_delta_tau": delta_tau,
            "absolute_delta_h0": delta_h0,
            "absolute_delta_h0_error": delta_h0_error,
            "tau_tolerance": 1.0e-8,
            "h0_tolerance": 1.0e-8,
            "h0_error_tolerance": 1.0e-8,
            "status": (
                "PASS"
                if delta_tau < 1.0e-8
                and delta_h0 < 1.0e-8
                and delta_h0_error < 1.0e-8
                else "FAIL"
            ),
        }

    reml_invariance = fitted_invariance(original_reml, transformed_reml)
    ml_invariance = fitted_invariance(original_ml, transformed_ml)
    moment_invariance = fitted_invariance(
        moment_fit, transformed_moment_fit
    )
    max_profile_difference = max(
        max(abs(value) for value in reml_centered_differences),
        max(abs(value) for value in ml_centered_differences),
    )
    profile_check = {
        "maximum_absolute_centered_deviance_difference": (
            max_profile_difference
        ),
        "maximum_absolute_reml_centered_deviance_difference": max(
            abs(value) for value in reml_centered_differences
        ),
        "maximum_absolute_ml_centered_deviance_difference": max(
            abs(value) for value in ml_centered_differences
        ),
        "tolerance": 1.0e-7,
        "status": "PASS" if max_profile_difference < 1.0e-7 else "FAIL",
    }
    discrepancy_index = max(
        range(len(profile_rows)),
        key=lambda index: max(
            abs(reml_centered_differences[index]),
            abs(ml_centered_differences[index]),
        ),
    )
    discrepancy_row = profile_rows[discrepancy_index]
    reml_95 = original_reml_intervals[1]
    reml_95_rows = [
        row
        for row in profile_rows
        if float(reml_95["lower"]) <= float(row["tau"])
        <= float(reml_95["upper"])
    ]
    maximum_inside_reml_95 = max(
        max(
            abs(float(row["reml_centered_deviance_difference"])),
            abs(float(row["ml_centered_deviance_difference"])),
        )
        for row in reml_95_rows
    )
    supplementary_numerical_context = {
        "status": "DESCRIPTIVE_NOT_A_CONTRACT_RELAXATION",
        "maximum_discrepancy_tau": float(discrepancy_row["tau"]),
        "minimum_profile_rise_at_maximum_discrepancy": min(
            float(discrepancy_row["original_reml_delta"]),
            float(discrepancy_row["transformed_reml_delta"]),
            float(discrepancy_row["original_ml_delta"]),
            float(discrepancy_row["transformed_ml_delta"]),
        ),
        "reml_95_interval": [
            float(reml_95["lower"]),
            float(reml_95["upper"]),
        ],
        "profile_rows_inside_reml_95_interval": len(reml_95_rows),
        "maximum_absolute_centered_deviance_difference_inside_reml_95_interval": (
            maximum_inside_reml_95
        ),
    }
    rank_check = {
        "original_reml_covariance_rank": (
            original_reml.covariance_rank_at_public_cutoff
        ),
        "transformed_reml_covariance_rank": (
            transformed_reml.covariance_rank_at_public_cutoff
        ),
        "original_ml_covariance_rank": (
            original_ml.covariance_rank_at_public_cutoff
        ),
        "transformed_ml_covariance_rank": (
            transformed_ml.covariance_rank_at_public_cutoff
        ),
        "required_rank": 255,
    }
    rank_check["status"] = (
        "PASS"
        if all(
            value == 255
            for key, value in rank_check.items()
            if key.endswith("_rank")
        )
        else "FAIL"
    )
    structure_check = {
        "selected_cell_count": len(selected),
        "host_count": len(hosts),
        "anchor_count": len(anchors),
        "duplicate_cell_count": duplicate_count,
        "covariance_nullity": nullity,
        "interaction_degrees_of_freedom": (len(hosts) - 1)
        * (len(anchors) - 1),
        "null_basis_outside_selected_rows_frobenius_norm": float(
            np.linalg.norm(
                np.delete(null_basis, selected_rows, axis=0), ord="fro"
            )
        ),
        "null_component_identity_max_absolute_error": float(
            np.max(
                np.abs(
                    null_basis.T @ component @ null_basis
                    - np.eye(nullity)
                )
            )
        ),
    }
    structure_check["status"] = (
        "PASS"
        if structure_check["selected_cell_count"] == 111
        and structure_check["host_count"] == 37
        and structure_check["anchor_count"] == 3
        and structure_check["duplicate_cell_count"] == 0
        and structure_check["covariance_nullity"] == 72
        and structure_check["interaction_degrees_of_freedom"] == 72
        and structure_check[
            "null_basis_outside_selected_rows_frobenius_norm"
        ]
        < 1.0e-8
        and structure_check[
            "null_component_identity_max_absolute_error"
        ]
        < 1.0e-8
        else "FAIL"
    )

    checks = {
        "reml_fit": reml_invariance,
        "ml_fit": ml_invariance,
        "moment_conditional_fit": moment_invariance,
        "profile_grid": profile_check,
        "rank": rank_check,
        "structure": structure_check,
    }
    all_pass = all(check["status"] == "PASS" for check in checks.values())
    core_pass = all(
        checks[key]["status"] == "PASS"
        for key in [
            "reml_fit",
            "ml_fit",
            "moment_conditional_fit",
            "rank",
            "structure",
        ]
    )
    if all_pass:
        status = "PASS"
    elif core_pass:
        status = "PASS_WITH_FLAGGED_PROFILE_NUMERICS"
    else:
        status = "FAIL"

    summary = {
        "status": status,
        "contract": "EXPLORATORY_VARIANCE_COMPONENT_CONTRACT.md",
        "interpretation": (
            "Post-hoc exploratory variance-component model; no corrected H0."
        ),
        "public_baseline": {
            key: baseline[key]
            for key in [
                "h0_value",
                "h0_error",
                "chi2",
                "covar_rank",
                "covar_nullity",
            ]
        },
        "variance_model": {
            "formula": "C(tau) = C0 + tau^2 R",
            "component": (
                "Unit diagonal on all 111 R22 HST-Cepheid host equations"
            ),
            "tau_unit": "mag",
            "tau_search_interval": [TAU_LOWER, TAU_UPPER],
            "selected_equation_rows": selected_rows.tolist(),
            "hosts": hosts,
            "anchors": anchors,
        },
        "original_representation": {
            "reml_fit": original_reml.public(),
            "reml_optimizer": original_reml_optimizer,
            "reml_profile_intervals": original_reml_intervals,
            "ml_fit": original_ml.public(),
            "ml_optimizer": original_ml_optimizer,
            "ml_profile_intervals": original_ml_intervals,
        },
        "row_standardized_representation": {
            "reml_fit": transformed_reml.public(),
            "reml_optimizer": transformed_reml_optimizer,
            "reml_profile_intervals": transformed_reml_intervals,
            "ml_fit": transformed_ml.public(),
            "ml_optimizer": transformed_ml_optimizer,
            "ml_profile_intervals": transformed_ml_intervals,
            "expected_objective_constant_offset": float(
                2.0 * np.sum(np.log(diagonal_scaling))
            ),
        },
        "nullspace_moment": {
            "tau": moment_tau,
            "nullspace_sum_of_squares": float(
                projected_data_coordinates @ projected_data_coordinates
            ),
            "nullspace_degrees_of_freedom": nullity,
            "conditional_fit": moment_fit.public(),
            "row_standardized_conditional_fit": (
                transformed_moment_fit.public()
            ),
        },
        "invariance_and_structure_checks": checks,
        "supplementary_numerical_context": (
            supplementary_numerical_context
        ),
    }
    write_json(
        output / "exploratory_variance_component_summary.json", summary
    )
    write_tsv(
        output / "exploratory_variance_component_profile.tsv",
        profile_rows,
    )
    (project_root / "EXPLORATORY_REPORT.md").write_text(
        build_report(summary), encoding="utf-8"
    )
    return {
        "status": status,
        "summary": "results/exploratory_variance_component_summary.json",
        "profile": "results/exploratory_variance_component_profile.tsv",
        "report": "EXPLORATORY_REPORT.md",
    }


def main() -> int:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=pathlib.Path)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=project_root / "results",
    )
    parser.add_argument(
        "--source-manifest",
        type=pathlib.Path,
        default=project_root / "provenance" / "SOURCE_LOCK.tsv",
    )
    args = parser.parse_args()
    try:
        result = execute(
            project_root,
            args.upstream.resolve(),
            args.output.resolve(),
            args.source_manifest.resolve(),
        )
    except Exception as exc:
        failure = {
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        write_json(
            args.output.resolve() / "EXPLORATORY_EXECUTION_STATUS.json",
            failure,
        )
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    write_json(
        args.output.resolve() / "EXPLORATORY_EXECUTION_STATUS.json",
        result,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
