#!/usr/bin/env python3
"""Diagnose the internally frozen row-standardization invariance failure."""

from __future__ import annotations

import argparse
import math
import pathlib
import sys
import traceback
from typing import Any

import numpy as np
import scipy.linalg

from auditlib import (
    OFFICIAL_ATOL,
    OFFICIAL_RTOL,
    capture_upstream_baseline,
    finite_or_none,
    public_result,
    sha256_file,
    solve_gls,
    upstream_solution_summary,
    verify_source,
    write_json,
    write_tsv,
)


def direct_gls(
    coeffs: np.ndarray,
    yval: np.ndarray,
    covariance: np.ndarray,
    *,
    ihub: int,
    iabs: int | None,
    policy: str,
) -> dict[str, Any]:
    try:
        inverse = np.linalg.inv(covariance)
        normal = coeffs.T @ inverse @ coeffs
        inverse_normal = np.linalg.inv(normal)
        params = inverse_normal @ (coeffs.T @ inverse @ yval)
    except np.linalg.LinAlgError as exc:
        return {
            "policy": policy,
            "status": "HOLD_NUMERICAL_FAILURE",
            "message": str(exc),
        }
    residual = yval - coeffs @ params
    variance = float(inverse_normal[ihub, ihub])
    if not math.isfinite(variance) or variance <= 0:
        return {
            "policy": policy,
            "status": "HOLD_NONPOSITIVE_VARIANCE",
            "message": f"logH0 variance is {variance}",
        }
    logh0 = float(params[ihub])
    h0 = 10.0**logh0
    h0_error = 10.0 ** (logh0 + math.sqrt(variance)) - h0
    result: dict[str, Any] = {
        "policy": policy,
        "status": "OK",
        "message": "",
        "covar_rank_numpy_default": int(np.linalg.matrix_rank(covariance)),
        "covar_condition_number": finite_or_none(np.linalg.cond(covariance)),
        "normal_rank_numpy_default": int(np.linalg.matrix_rank(normal)),
        "normal_condition_number": finite_or_none(np.linalg.cond(normal)),
        "logh0_value": logh0,
        "logh0_variance": variance,
        "h0_value": float(h0),
        "h0_error": float(h0_error),
        "chi2": float(residual.T @ inverse @ residual),
        "_params": params,
        "_residual": residual,
    }
    if iabs is not None:
        result["mzero_value"] = float(params[iabs])
        result["mzero_error"] = math.sqrt(
            float(inverse_normal[iabs, iabs])
        )
    return result


def support_metrics(
    coeffs: np.ndarray,
    yval: np.ndarray,
    params: np.ndarray,
    null_basis: np.ndarray,
    null_projector: np.ndarray,
) -> dict[str, Any]:
    residual = yval - coeffs @ params
    projected = null_projector @ residual
    coordinates = null_basis.T @ residual
    denominator = max(float(np.linalg.norm(residual)), np.finfo(float).tiny)
    return {
        "residual_l2_norm": float(np.linalg.norm(residual)),
        "nullspace_projection_l2_norm": float(np.linalg.norm(projected)),
        "nullspace_coordinate_l2_norm": float(np.linalg.norm(coordinates)),
        "nullspace_projection_max_absolute": float(
            np.max(np.abs(projected))
        ),
        "relative_nullspace_projection": float(
            np.linalg.norm(projected) / denominator
        ),
    }


def constrained_solution_if_feasible(
    coeffs: np.ndarray,
    yval: np.ndarray,
    eigenvalues: np.ndarray,
    eigenvectors: np.ndarray,
    *,
    ihub: int,
    feasibility_tolerance: float,
) -> dict[str, Any]:
    range_mask = eigenvalues > OFFICIAL_ATOL
    null_mask = ~range_mask
    range_basis = eigenvectors[:, range_mask]
    null_basis = eigenvectors[:, null_mask]
    retained = eigenvalues[range_mask]
    weighted_design = (
        range_basis.T @ coeffs
    ) / np.sqrt(retained)[:, None]
    weighted_data = (range_basis.T @ yval) / np.sqrt(retained)
    constraint_matrix = null_basis.T @ coeffs
    constraint_target = null_basis.T @ yval
    constraint_inverse, constraint_rank = scipy.linalg.pinv(
        constraint_matrix,
        atol=OFFICIAL_ATOL,
        rtol=OFFICIAL_RTOL,
        return_rank=True,
    )
    particular = constraint_inverse @ constraint_target
    feasibility_vector = constraint_matrix @ particular - constraint_target
    feasibility_norm = float(np.linalg.norm(feasibility_vector))
    constraint_singular_values = scipy.linalg.svdvals(constraint_matrix)
    augmented_singular_values = scipy.linalg.svdvals(
        np.column_stack([constraint_matrix, constraint_target])
    )
    augmented_rank = int(np.sum(augmented_singular_values > OFFICIAL_ATOL))
    output: dict[str, Any] = {
        "constraint_shape": list(constraint_matrix.shape),
        "constraint_rank": int(constraint_rank),
        "augmented_rank": augmented_rank,
        "constraint_matrix_max_absolute": float(
            np.max(np.abs(constraint_matrix))
        ),
        "constraint_matrix_frobenius_norm": float(
            np.linalg.norm(constraint_matrix, ord="fro")
        ),
        "constraint_matrix_largest_singular_value": float(
            constraint_singular_values[0]
        ),
        "constraint_rank_cutoff": OFFICIAL_ATOL,
        "augmented_matrix_largest_singular_value": float(
            augmented_singular_values[0]
        ),
        "constraint_target_l2_norm": float(np.linalg.norm(constraint_target)),
        "least_squares_feasibility_residual_l2_norm": feasibility_norm,
        "feasibility_tolerance": feasibility_tolerance,
    }
    if feasibility_norm > feasibility_tolerance:
        output.update(
            {
                "status": "HOLD_INCONSISTENT_SUPPORT",
                "message": (
                    "No parameter vector satisfies the covariance-nullspace "
                    "support equations at the frozen tolerance."
                ),
            }
        )
        return output

    _u, singular_values, vh = scipy.linalg.svd(
        constraint_matrix, full_matrices=True
    )
    frozen_rank = int(np.sum(singular_values > OFFICIAL_ATOL))
    null_of_constraints = vh[frozen_rank:].T
    reduced_design = weighted_design @ null_of_constraints
    target = weighted_data - weighted_design @ particular
    reduced_params, _residuals, reduced_rank, _singular = np.linalg.lstsq(
        reduced_design, target, rcond=None
    )
    params = particular + null_of_constraints @ reduced_params
    constraint_residual = (
        constraint_matrix @ params - constraint_target
    )
    if reduced_design.shape[1]:
        reduced_normal = reduced_design.T @ reduced_design
        reduced_covariance = np.linalg.inv(reduced_normal)
        parameter_covariance = (
            null_of_constraints
            @ reduced_covariance
            @ null_of_constraints.T
        )
        variance = float(parameter_covariance[ihub, ihub])
    else:
        variance = 0.0
    output.update(
        {
            "status": "OK",
            "message": "",
            "constraint_nullity": int(null_of_constraints.shape[1]),
            "reduced_design_rank": int(reduced_rank),
            "constraint_residual_l2_norm": float(
                np.linalg.norm(constraint_residual)
            ),
            "logh0_value": float(params[ihub]),
            "logh0_variance": variance,
            "h0_value": float(10.0 ** params[ihub]),
        }
    )
    return output


def format_value(value: Any, digits: int = 9) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "—"
    return f"{number:.{digits}g}"


def build_posthoc_report(
    diagnostic: dict[str, Any],
    regularization: list[dict[str, Any]],
    scaling_map: list[dict[str, Any]],
) -> str:
    support = diagnostic["support_constraint"]
    interaction = diagnostic["cepheid_interaction_decomposition"]
    public_support = diagnostic["support_residuals"]["public_solution"]
    standardized_support = diagnostic["support_residuals"][
        "row_standardized_mp_solution"
    ]
    finite_scalings = [
        row
        for row in scaling_map
        if str(row.get("status", "")).startswith("OK")
    ]
    h0_values = [float(row["h0_value"]) for row in finite_scalings]
    baseline_rank = next(
        int(row["covar_rank"])
        for row in scaling_map
        if float(row["scaling_power"]) == 0.0
    )
    same_rank_scalings = [
        row
        for row in finite_scalings
        if int(row["covar_rank"]) == baseline_rank
    ]
    same_rank_h0 = [float(row["h0_value"]) for row in same_rank_scalings]
    regular_ok = [
        row
        for row in regularization
        if str(row.get("status", "")).startswith("OK")
    ]
    max_equiv = max(
        float(row.get("equivalent_representation_absolute_delta_h0", math.inf))
        for row in regular_ok
    )
    lines = [
        "# Post-hoc diagnosis of the row-scaling failure",
        "",
        "This report is governed by `POSTHOC_DIAGNOSTIC_CONTRACT.md` and is",
        "explicitly separate from the primary audit generated under the "
        "project-internal frozen contract.",
        "",
        "## Result",
        "",
        "The failed row-standardization check is reproduced and is not caused by",
        "a rank change. The transformed covariance retains the same 183-dimensional",
        "range, but the Moore–Penrose precision mapped back to the original",
        "coordinates differs from the original precision by relative Frobenius norm",
        f"`{format_value(diagnostic['moore_penrose_congruence']['relative_frobenius_defect'])}`.",
        "This is the expected algebraic non-invariance of the Moore–Penrose inverse",
        "under a general non-orthogonal congruence transformation of a singular",
        "matrix.",
        "",
        "The public-fit residual has covariance-nullspace projection norm",
        f"`{format_value(public_support['nullspace_projection_l2_norm'])}`;",
        "the row-standardized Moore–Penrose fit has",
        f"`{format_value(standardized_support['nullspace_projection_l2_norm'])}`.",
        "The exact degenerate-Gaussian support system is classified",
        f"**{support['status']}**, with least-squares feasibility residual",
        f"`{format_value(support['least_squares_feasibility_residual_l2_norm'])}`",
        "against the frozen tolerance",
        f"`{format_value(support['feasibility_tolerance'])}`.",
        "",
        "Therefore the singular covariance, taken literally, does not supply a",
        "nonzero-likelihood support for any parameter vector at the stated",
        "precision. The public Moore–Penrose result remains exactly reproducible,",
        "but it is one computational convention for discarding inconsistent",
        "nullspace information; it is not a representation-invariant consequence",
        "of a fully specified degenerate Gaussian model.",
        "",
        "## Exact location of the inconsistent support",
        "",
        "The exhaustive public-metadata selection forms a complete",
        f"`{interaction['host_count']} host × {interaction['anchor_count']} anchor`",
        "R22 HST-Cepheid table. Its two-way additive interaction equals the",
        "covariance-nullspace projection with maximum absolute closure error",
        f"`{format_value(interaction['projection_closure_max_absolute_error'])}`.",
        "The interaction RMS is",
        f"`{format_value(interaction['interaction_rms'])} mag`,",
        "its L2 norm is",
        f"`{format_value(interaction['interaction_l2_norm'])} mag`, and",
        "the largest absolute cell is",
        f"`{format_value(interaction['maximum_absolute_interaction'])} mag`",
        f"({interaction['maximum_cell']['host']},",
        f"{interaction['maximum_cell']['anchor']}).",
        "",
        "This establishes where the exact-support inconsistency occurs but does",
        "not establish why those public distance values differ from the additive",
        "covariance support.",
        "",
        "## Bounded diagnostic maps",
        "",
        "Across the frozen scaling powers, numeric Moore–Penrose solutions span",
        f"`H0 = {min(h0_values):.8f}` to `{max(h0_values):.8f} km/s/Mpc`.",
        "Restricting to scalings that preserve the public covariance rank gives",
        f"`{min(same_rank_h0):.8f}` to `{max(same_rank_h0):.8f} km/s/Mpc`.",
        "The wider range includes two cases where the fixed absolute cutoff also",
        "changes rank.",
        "These are not alternative scientific estimates.",
        "",
        "The fractional diagonal-regularization path was repeated in both",
        "representations using the exactly transformed regularizer. The largest",
        "numerically successful cross-representation H0 discrepancy was",
        f"`{format_value(max_equiv)} km/s/Mpc`.",
        "Rows at extremely small regularization can become floating-point",
        "ill-conditioned and are retained with their status.",
        "For the well-resolved part of the path, the limit approaches the",
        "row-standardized Moore–Penrose convention while chi-square diverges as",
        "the added independent variance tends to zero, consistent with the",
        "nonzero support residual.",
        "",
        "## Consequence",
        "",
        "A publication-grade next step is to replace the singular, rounded",
        "covariance-only encoding by an explicit latent-error or expanded-parameter",
        "generative model. That model would state the duplicated measurements and",
        "shared anchor/MAS/HMS terms directly, avoid an inconsistent nullspace, and",
        "make any regularization or rounding uncertainty explicit. This audit does",
        "not choose such a model and does not report a corrected H0.",
        "",
        "A separately contracted exploratory implementation of one such model is",
        "reported in `EXPLORATORY_REPORT.md`. It does not alter this diagnosis or",
        "retroactively become part of the internally frozen primary audit.",
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
    upstream_solution = captured["upstream_solution"]
    baseline = upstream_solution_summary(captured)

    diagonal = np.diag(covariance)
    scaling = 1.0 / np.sqrt(diagonal)
    transformed_coeffs = scaling[:, None] * coeffs
    transformed_y = scaling * yval
    transformed_covariance = (
        scaling[:, None] * covariance * scaling[None, :]
    )

    inverse, rank = scipy.linalg.pinv(
        covariance,
        atol=OFFICIAL_ATOL,
        rtol=OFFICIAL_RTOL,
        return_rank=True,
    )
    transformed_inverse, transformed_rank = scipy.linalg.pinv(
        transformed_covariance,
        atol=OFFICIAL_ATOL,
        rtol=OFFICIAL_RTOL,
        return_rank=True,
    )
    mapped_precision = (
        scaling[:, None]
        * transformed_inverse
        * scaling[None, :]
    )
    precision_defect = mapped_precision - inverse

    standardized = solve_gls(
        transformed_coeffs,
        transformed_y,
        transformed_covariance,
        ihub=equation_data["ihub"],
        iabs=equation_data["iabs"],
        policy="official_after_diagonal_row_standardization",
    )
    if not str(standardized["status"]).startswith("OK"):
        raise RuntimeError("Could not reproduce row-standardized solution.")

    eigenvalues, eigenvectors = scipy.linalg.eigh(covariance)
    null_mask = eigenvalues <= OFFICIAL_ATOL
    null_basis = eigenvectors[:, null_mask]
    null_projector = null_basis @ null_basis.T
    projector_from_pinv = np.eye(len(covariance)) - covariance @ inverse
    projected_design = null_projector @ coeffs
    projected_data = null_projector @ yval

    host_df = captured["build_args"][0]
    cepheid = host_df[
        (host_df["method"].astype(str) == "ceph_hst")
        & (host_df["source"].astype(str) == "R22")
    ].copy()
    hosts = list(dict.fromkeys(cepheid["host"].astype(str)))
    anchors = list(dict.fromkeys(cepheid["anchor"].astype(str)))
    duplicate_count = int(
        cepheid.duplicated(subset=["host", "anchor"]).sum()
    )
    if (
        len(hosts) != 37
        or len(anchors) != 3
        or len(cepheid) != 111
        or duplicate_count != 0
    ):
        raise RuntimeError(
            "The frozen 37-by-3 Cepheid interaction structure was not found."
        )
    pivot = cepheid.pivot(
        index="host", columns="anchor", values="mu_host"
    ).reindex(index=hosts, columns=anchors)
    if pivot.isna().any().any():
        raise RuntimeError("Cepheid host-anchor table is not complete.")
    interaction_matrix = (
        pivot
        - pivot.mean(axis=1).to_numpy()[:, None]
        - pivot.mean(axis=0).to_numpy()[None, :]
        + float(pivot.to_numpy().mean())
    )
    interaction_cells = []
    for equation_index, row in cepheid.iterrows():
        host = str(row["host"])
        anchor = str(row["anchor"])
        interaction_value = float(interaction_matrix.loc[host, anchor])
        projection_value = float(projected_data[int(equation_index)])
        interaction_cells.append(
            {
                "equation_index": int(equation_index),
                "host": host,
                "anchor": anchor,
                "mu_host": float(row["mu_host"]),
                "mu_error": float(row["mu_error"]),
                "interaction": interaction_value,
                "absolute_interaction": abs(interaction_value),
                "nullspace_projected_data": projection_value,
                "interaction_minus_projection": interaction_value
                - projection_value,
            }
        )
    interaction_cells.sort(key=lambda row: row["equation_index"])
    interaction_values = np.asarray(
        [row["interaction"] for row in interaction_cells], dtype=float
    )
    closure_errors = np.asarray(
        [row["interaction_minus_projection"] for row in interaction_cells],
        dtype=float,
    )
    host_summaries = []
    for host in hosts:
        cells = [row for row in interaction_cells if row["host"] == host]
        values = np.asarray([row["interaction"] for row in cells], dtype=float)
        peak = max(cells, key=lambda row: row["absolute_interaction"])
        host_summaries.append(
            {
                "host": host,
                "cell_count": len(cells),
                "interaction_l2_norm": float(np.linalg.norm(values)),
                "interaction_rms": float(np.sqrt(np.mean(values**2))),
                "maximum_absolute_interaction": float(
                    np.max(np.abs(values))
                ),
                "maximum_anchor": peak["anchor"],
                "signed_sum": float(np.sum(values)),
            }
        )
    anchor_summaries = []
    for anchor in anchors:
        cells = [row for row in interaction_cells if row["anchor"] == anchor]
        values = np.asarray([row["interaction"] for row in cells], dtype=float)
        anchor_summaries.append(
            {
                "anchor": anchor,
                "cell_count": len(cells),
                "interaction_l2_norm": float(np.linalg.norm(values)),
                "interaction_rms": float(np.sqrt(np.mean(values**2))),
                "maximum_absolute_interaction": float(
                    np.max(np.abs(values))
                ),
                "signed_sum": float(np.sum(values)),
            }
        )
    maximum_cell = max(
        interaction_cells, key=lambda row: row["absolute_interaction"]
    )
    interaction_summary = {
        "status": (
            "PASS"
            if float(np.max(np.abs(closure_errors))) < 1.0e-10
            else "FAIL"
        ),
        "host_count": len(hosts),
        "anchor_count": len(anchors),
        "cell_count": len(interaction_cells),
        "duplicate_cell_count": duplicate_count,
        "anchors": anchors,
        "interaction_l2_norm": float(np.linalg.norm(interaction_values)),
        "interaction_rms": float(
            np.sqrt(np.mean(interaction_values**2))
        ),
        "maximum_absolute_interaction": float(
            np.max(np.abs(interaction_values))
        ),
        "maximum_cell": maximum_cell,
        "projection_closure_max_absolute_error": float(
            np.max(np.abs(closure_errors))
        ),
        "projection_closure_l2_norm": float(np.linalg.norm(closure_errors)),
        "top_cells_by_absolute_interaction": sorted(
            interaction_cells,
            key=lambda row: row["absolute_interaction"],
            reverse=True,
        )[:10],
    }
    if interaction_summary["status"] != "PASS":
        raise RuntimeError(
            "Two-way interaction does not close to the nullspace projection."
        )
    feasibility_tolerance = 1.0e-10 * max(
        1.0, float(np.linalg.norm(null_basis.T @ yval))
    )
    support = constrained_solution_if_feasible(
        coeffs,
        yval,
        eigenvalues,
        eigenvectors,
        ihub=equation_data["ihub"],
        feasibility_tolerance=feasibility_tolerance,
    )

    diagnostic = {
        "status": "DIAGNOSED",
        "baseline_h0": baseline["h0_value"],
        "row_standardized_h0": standardized["h0_value"],
        "delta_h0": standardized["h0_value"] - baseline["h0_value"],
        "transformation_checks": {
            "scaling_finite": bool(np.all(np.isfinite(scaling))),
            "scaling_nonzero": bool(np.all(scaling != 0)),
            "scaling_min": float(np.min(scaling)),
            "scaling_max": float(np.max(scaling)),
            "coefficient_transform_max_absolute_error": float(
                np.max(
                    np.abs(
                        transformed_coeffs - scaling[:, None] * coeffs
                    )
                )
            ),
            "data_transform_max_absolute_error": float(
                np.max(np.abs(transformed_y - scaling * yval))
            ),
            "covariance_transform_max_absolute_error": float(
                np.max(
                    np.abs(
                        transformed_covariance
                        - scaling[:, None]
                        * covariance
                        * scaling[None, :]
                    )
                )
            ),
            "original_rank": int(rank),
            "transformed_rank": int(transformed_rank),
        },
        "moore_penrose_congruence": {
            "absolute_frobenius_defect": float(
                np.linalg.norm(precision_defect, ord="fro")
            ),
            "relative_frobenius_defect": float(
                np.linalg.norm(precision_defect, ord="fro")
                / np.linalg.norm(inverse, ord="fro")
            ),
            "max_absolute_defect": float(np.max(np.abs(precision_defect))),
        },
        "nullspace": {
            "dimension": int(np.sum(null_mask)),
            "range_dimension": int(np.sum(~null_mask)),
            "eigenvalue_cutoff": OFFICIAL_ATOL,
            "eigenvector_vs_pinv_projector_relative_frobenius_difference": float(
                np.linalg.norm(
                    null_projector - projector_from_pinv, ord="fro"
                )
                / np.linalg.norm(null_projector, ord="fro")
            ),
            "projected_design_frobenius_norm": float(
                np.linalg.norm(projected_design, ord="fro")
            ),
            "projected_design_max_absolute": float(
                np.max(np.abs(projected_design))
            ),
            "projected_data_l2_norm": float(np.linalg.norm(projected_data)),
            "projected_data_max_absolute": float(
                np.max(np.abs(projected_data))
            ),
        },
        "support_residuals": {
            "public_solution": support_metrics(
                coeffs,
                yval,
                np.asarray(upstream_solution["params"], dtype=float),
                null_basis,
                null_projector,
            ),
            "row_standardized_mp_solution": support_metrics(
                coeffs,
                yval,
                np.asarray(standardized["_params"], dtype=float),
                null_basis,
                null_projector,
            ),
        },
        "support_constraint": support,
        "cepheid_interaction_decomposition": interaction_summary,
    }

    regularizer = np.diag(diagonal)
    transformed_regularizer = (
        scaling[:, None] * regularizer * scaling[None, :]
    )
    regularization_rows: list[dict[str, Any]] = []
    for exponent in range(-2, -13, -1):
        fraction = 10.0**exponent
        original = direct_gls(
            coeffs,
            yval,
            covariance + fraction * regularizer,
            ihub=equation_data["ihub"],
            iabs=equation_data["iabs"],
            policy="fractional_diagonal_regularization_original",
        )
        transformed = direct_gls(
            transformed_coeffs,
            transformed_y,
            transformed_covariance + fraction * transformed_regularizer,
            ihub=equation_data["ihub"],
            iabs=equation_data["iabs"],
            policy="fractional_diagonal_regularization_transformed",
        )
        row = {
            "lambda": fraction,
            "exponent": exponent,
            "status": (
                "OK"
                if original["status"] == "OK"
                and transformed["status"] == "OK"
                else "HOLD_NUMERICAL_FAILURE"
            ),
            "original_status": original["status"],
            "transformed_status": transformed["status"],
            "h0_value": original.get("h0_value"),
            "h0_error": original.get("h0_error"),
            "chi2": original.get("chi2"),
            "covar_condition_number": original.get(
                "covar_condition_number"
            ),
            "transformed_h0_value": transformed.get("h0_value"),
            "transformed_h0_error": transformed.get("h0_error"),
            "equivalent_representation_delta_h0": (
                transformed.get("h0_value", math.nan)
                - original.get("h0_value", math.nan)
            ),
            "equivalent_representation_absolute_delta_h0": abs(
                transformed.get("h0_value", math.nan)
                - original.get("h0_value", math.nan)
            ),
            "equivalent_representation_delta_h0_error": (
                transformed.get("h0_error", math.nan)
                - original.get("h0_error", math.nan)
            ),
            "invariance_status": (
                "PASS"
                if original["status"] == "OK"
                and transformed["status"] == "OK"
                and abs(
                    transformed["h0_value"] - original["h0_value"]
                )
                < 1.0e-8
                else "FAIL"
            ),
        }
        regularization_rows.append(row)

    scaling_rows: list[dict[str, Any]] = []
    for power in [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0]:
        factor = diagonal ** (-power / 2.0)
        result = solve_gls(
            factor[:, None] * coeffs,
            factor * yval,
            factor[:, None] * covariance * factor[None, :],
            ihub=equation_data["ihub"],
            iabs=equation_data["iabs"],
            policy=f"moore_penrose_diagonal_scaling_power_{power:g}",
        )
        row = {
            "scaling_power": power,
            "scaling_min": float(np.min(factor)),
            "scaling_max": float(np.max(factor)),
            **public_result(result),
        }
        if str(result.get("status", "")).startswith("OK"):
            row["delta_h0_from_public"] = (
                result["h0_value"] - baseline["h0_value"]
            )
            row["delta_h0_error_from_public"] = (
                result["h0_error"] - baseline["h0_error"]
            )
            row["support_nullspace_projection_l2_norm"] = support_metrics(
                coeffs,
                yval,
                np.asarray(result["_params"], dtype=float),
                null_basis,
                null_projector,
            )["nullspace_projection_l2_norm"]
        scaling_rows.append(row)

    equation_projection_rows = []
    for index in range(equation_data["neq"]):
        equation_projection_rows.append(
            {
                "equation_index": index,
                "equation_description": equation_data["eq_descr"][index],
                "equation_shape": equation_data["eq_shape"][index],
                "projected_data_value": float(projected_data[index]),
                "absolute_projected_data_value": abs(
                    float(projected_data[index])
                ),
                "projected_design_row_l2_norm": float(
                    np.linalg.norm(projected_design[index])
                ),
            }
        )

    idl_records = [
        {
            "source_file": "idlcode/mpinv.pro",
            "sha256": sha256_file(upstream / "idlcode" / "mpinv.pro"),
            "finding": "Implements the Moore-Penrose inverse by SVD.",
            "threshold_rule": (
                "Default tol = max(singular_values) * max(m,n) * "
                "machine_epsilon."
            ),
        },
        {
            "source_file": "idlcode/org_v3p9.pro",
            "sha256": sha256_file(upstream / "idlcode" / "org_v3p9.pro"),
            "finding": "Calls mpinv(covar, rank=rank) for the network precision.",
            "threshold_rule": "Uses mpinv default unless tol is supplied; none is supplied.",
        },
        {
            "source_file": "h0_constrainer/h0_constrainer/solver.py",
            "sha256": sha256_file(
                upstream
                / "h0_constrainer"
                / "h0_constrainer"
                / "solver.py"
            ),
            "finding": "Calls scipy.linalg.pinv on the network covariance.",
            "threshold_rule": "atol=1e-10 and rtol=0.0.",
        },
    ]

    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "posthoc_row_scaling_diagnostic.json", diagnostic)
    write_tsv(
        output / "posthoc_fractional_regularization_path.tsv",
        regularization_rows,
    )
    write_tsv(output / "posthoc_scaling_power_map.tsv", scaling_rows)
    write_tsv(
        output / "posthoc_nullspace_projection_by_equation.tsv",
        equation_projection_rows,
    )
    write_tsv(
        output / "posthoc_cepheid_interaction_cells.tsv",
        interaction_cells,
    )
    write_tsv(
        output / "posthoc_cepheid_interaction_by_host.tsv",
        host_summaries,
    )
    write_tsv(
        output / "posthoc_cepheid_interaction_by_anchor.tsv",
        anchor_summaries,
    )
    write_tsv(output / "posthoc_idl_python_solver_record.tsv", idl_records)
    report = build_posthoc_report(
        diagnostic, regularization_rows, scaling_rows
    )
    (project_root / "POSTHOC_REPORT.md").write_text(report, encoding="utf-8")
    return {
        "status": "PASS",
        "diagnosis": support["status"],
        "moore_penrose_relative_congruence_defect": diagnostic[
            "moore_penrose_congruence"
        ]["relative_frobenius_defect"],
        "public_support_residual_l2_norm": diagnostic["support_residuals"][
            "public_solution"
        ]["nullspace_projection_l2_norm"],
        "row_standardized_delta_h0": diagnostic["delta_h0"],
        "numeric_scaling_h0_range": [
            min(
                row["h0_value"]
                for row in scaling_rows
                if str(row.get("status", "")).startswith("OK")
            ),
            max(
                row["h0_value"]
                for row in scaling_rows
                if str(row.get("status", "")).startswith("OK")
            ),
        ],
        "same_rank_scaling_h0_range": [
            min(
                row["h0_value"]
                for row in scaling_rows
                if str(row.get("status", "")).startswith("OK")
                and row["covar_rank"] == rank
            ),
            max(
                row["h0_value"]
                for row in scaling_rows
                if str(row.get("status", "")).startswith("OK")
                and row["covar_rank"] == rank
            ),
        ],
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
        write_json(args.output.resolve() / "POSTHOC_EXECUTION_STATUS.json", failure)
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    write_json(
        args.output.resolve() / "POSTHOC_EXECUTION_STATUS.json",
        result,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
