#!/usr/bin/env python3
"""Execute the frozen H0DN covariance and influence audit."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import traceback
from typing import Any

import numpy as np

from auditlib import (
    AuditFailure,
    OFFICIAL_ATOL,
    OFFICIAL_RTOL,
    baseline_fidelity,
    build_equation_blocks,
    capture_upstream_baseline,
    covariance_component_inventory,
    equation_block_inventory,
    equation_inventory,
    matrix_diagnostics,
    match_component_ablations_to_leave_one_out,
    parameter_inventory,
    public_result,
    reconstruct_covariance_components,
    run_component_ablations,
    run_hubble_flow_covariance_audit,
    run_leave_one_block_out,
    run_metadata,
    run_representation_invariance,
    run_solver_sensitivity,
    sha256_file,
    solve_gls,
    upstream_solution_summary,
    verify_source,
    write_json,
    write_tsv,
)


def _numeric_rows(
    rows: list[dict[str, Any]],
    *,
    interpretation_statuses: set[str] | None = None,
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if str(row.get("solver_status", row.get("status", ""))).startswith(
            "OK"
        )
        and (
            interpretation_statuses is None
            or row.get("interpretation_status") in interpretation_statuses
        )
        and isinstance(row.get("absolute_delta_h0"), (int, float))
        and math.isfinite(float(row["absolute_delta_h0"]))
    ]


def _top_influence(
    rows: list[dict[str, Any]],
    identifier_key: str,
    count: int = 10,
    *,
    interpretation_statuses: set[str] | None = None,
) -> list[dict[str, Any]]:
    ranked = sorted(
        _numeric_rows(
            rows, interpretation_statuses=interpretation_statuses
        ),
        key=lambda row: float(row["absolute_delta_h0"]),
        reverse=True,
    )
    return [
        {
            "identifier": row[identifier_key],
            "label": row["label"],
            "delta_h0": row["delta_h0"],
            "delta_h0_in_baseline_sigma": row[
                "delta_h0_in_baseline_sigma"
            ],
            "delta_sigma_h0": row["delta_sigma_h0"],
            "status": row["status"],
            "solver_status": row.get("solver_status", row["status"]),
            "interpretation_status": row.get("interpretation_status"),
            "covariance_model_status": row.get(
                "covariance_model_status"
            ),
        }
        for row in ranked[:count]
    ]


def _format_number(value: Any, digits: int = 8) -> str:
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "—"
    return f"{number:.{digits}g}"


def _markdown_influence_table(
    rows: list[dict[str, Any]],
    identifier_key: str,
    count: int = 8,
    *,
    interpretation_statuses: set[str] | None = None,
    status_key: str = "status",
) -> str:
    ranked = sorted(
        _numeric_rows(
            rows, interpretation_statuses=interpretation_statuses
        ),
        key=lambda row: float(row["absolute_delta_h0"]),
        reverse=True,
    )[:count]
    lines = [
        "| Block | Removed/ablated | ΔH0 | ΔH0 / baseline σ | Δσ(H0) | Status |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in ranked:
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                row[identifier_key],
                str(row["label"]).replace("|", "\\|"),
                _format_number(row["delta_h0"], 7),
                _format_number(row["delta_h0_in_baseline_sigma"], 6),
                _format_number(row["delta_sigma_h0"], 7),
                row.get(status_key, row["status"]),
            )
        )
    return "\n".join(lines)


def build_report(
    baseline_record: dict[str, Any],
    matrix_record: dict[str, Any],
    solver_sensitivity: list[dict[str, Any]],
    representation: list[dict[str, Any]],
    component_ablation: list[dict[str, Any]],
    leave_one_out: list[dict[str, Any]],
    hubble_flow: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    baseline = baseline_record["upstream"]
    covariance = matrix_record["network_covariance"]
    normal = matrix_record["normal_matrix"]
    standardized = next(
        row
        for row in representation
        if row["representation_family"] == "diagonal_row_standardization"
    )
    permutations = [
        row
        for row in representation
        if row["representation_family"]
        == "simultaneous_row_column_permutation"
    ]
    max_perm_h0 = max(
        float(row.get("absolute_delta_h0", math.inf)) for row in permutations
    )
    max_perm_sigma = max(
        float(row.get("absolute_delta_sigma_h0", math.inf))
        for row in permutations
    )
    hf_full = hubble_flow["independent_full_covariance_result"]
    hf_diag = hubble_flow["diagonal_only_result"]
    hf_network = hubble_flow["diagonal_only_network_result"]
    sn_link = next(
        row
        for row in component_ablation
        if row["component_id"] == "sn1a_hubble_flow_link_variance"
    )

    cutoff_ranks = sorted(
        {
            int(row["covar_rank"])
            for row in solver_sensitivity
            if row.get("covar_rank") not in (None, "")
        }
    )
    cutoff_h0_values = [
        float(row["h0_value"])
        for row in solver_sensitivity
        if str(row.get("status", "")).startswith("OK")
    ]

    text = f"""# Independent audit of H0DN covariance-block influence and numerical stability

This is not an official H0DN product and is not affiliated with or endorsed by
the H0DN authors.

Execution status: **{summary['status']}**

Audit contract: version 0.1.0, frozen internally before influence outputs

Upstream commit: `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`

## Executive result

The untouched public Python pipeline was reproduced at
`H0 = {baseline['h0_value']:.8f} ± {baseline['h0_error']:.8f} km/s/Mpc`,
with `chi2 = {baseline['chi2']:.8f}`, adjusted `ndof = {baseline['ndof']}`,
and covariance rank `{baseline['covar_rank']}`. The frozen baseline gate
therefore **{baseline_record['fidelity_gate']['status']}**.

The 255-by-255 network covariance has rank
`{covariance['rank_at_absolute_cutoff']}` at the public absolute cutoff
`1e-10`, hence nullity `{covariance['nullity_at_absolute_cutoff']}`. Its
smallest eigenvalue is `{_format_number(covariance['eigenvalue_min'], 8)}`;
the fixed PSD check reports
`{covariance['material_negative_eigenvalue_count']}` materially negative
eigenvalues. The independently reconstructed covariance closes to relative
Frobenius error
`{_format_number(matrix_record['component_decomposition_closure']['relative_frobenius_error'], 8)}`
and **{matrix_record['component_decomposition_closure']['status']}**.

The normal matrix is rank `{normal['rank_at_absolute_cutoff']}` for
`{baseline['npars']}` parameters. This establishes numerical identifiability
for the untouched encoded network under the public cutoff; it does not establish
physical independence of the contributing measurements.

## Numerical stability

- The pre-specified cutoff sweep produced covariance ranks
  `{', '.join(map(str, cutoff_ranks))}` and numeric H0 values spanning
  `{min(cutoff_h0_values):.10f}` to `{max(cutoff_h0_values):.10f}`.
- Equivalent diagonal row standardization changed H0 by
  `{_format_number(standardized.get('delta_h0'), 8)} km/s/Mpc` and its
  reported uncertainty by
  `{_format_number(standardized.get('delta_sigma_h0'), 8)} km/s/Mpc`;
  classification: **{standardized['invariance_status']}**.
- Across 32 frozen simultaneous row/column permutations, the largest absolute
  H0 change was `{_format_number(max_perm_h0, 8)} km/s/Mpc` and the largest
  uncertainty change was `{_format_number(max_perm_sigma, 8)} km/s/Mpc`.

These checks isolate numerical representation effects. They do not test
unencoded astrophysical systematics.

The row-standardization failure is deliberately not explained inside this
primary report generated under the project-internal frozen contract. Its
separately contracted diagnosis is generated by
`scripts/run_posthoc_diagnostics.py` and written to `POSTHOC_REPORT.md`.

## Largest covariance-component algebraic sensitivities

{_markdown_influence_table(
    component_ablation,
    'component_id',
    interpretation_statuses={'PSD_ALGEBRAIC_SENSITIVITY'},
    status_key='interpretation_status',
)}

These rows measure the behavior of the encoded solver after subtracting one
additive covariance component. Some ablations create zero-variance or
indefinite directions, so the resulting pseudoinverse solution may discard
constraints and must not be interpreted as a supported alternative covariance
model or as evidence that the removed component is erroneous. The main table
contains only `PSD_ALGEBRAIC_SENSITIVITY` rows; overlapping shifts are not
additive.

## Constraint-discarding and indefinite ablation diagnostics

{_markdown_influence_table(
    component_ablation,
    'component_id',
    interpretation_statuses={
        'PSEUDOINVERSE_DISCARDED_CONSTRAINT',
        'INDEFINITE_ALGEBRAIC_DIAGNOSTIC',
    },
    status_key='interpretation_status',
)}

For `sn1a_hubble_flow_link_variance`, subtraction lowers the covariance rank
from `{baseline['covar_rank']}` to `{sn_link['covar_rank']}`, produces
`{sn_link['zero_precision_row_count']}` effectively zero precision row, and
matches leave-one-block-out block
`{sn_link['matched_leave_one_block_out_id']}` with
`ΔH0(ablation - LOO) =
{_format_number(sn_link['matched_leave_one_block_out_delta_h0'], 8)} km/s/Mpc`
and maximum absolute parameter difference
`{_format_number(
    sn_link['matched_leave_one_block_out_parameter_max_absolute_difference'],
    8,
)}`. It is therefore classified
`PSEUDOINVERSE_DISCARDED_CONSTRAINT`: a constraint-dropping algebraic
diagnostic, not a scientific removal of a supported variance model.

## Largest leave-one-block-out shifts

{_markdown_influence_table(leave_one_out, 'block_id')}

Rows and their covariance rows/columns were removed together. Every
`HOLD_UNIDENTIFIED` result is retained in the machine-readable table rather
than being forced through a pseudoinverse of the normal matrix.

## Pantheon+ Hubble-flow covariance

The independently rebuilt full-covariance intercept is
`alpha = {hf_full['alpha']:.10f} ± {hf_full['alpha_error']:.10f}` and matches
the value entering the public network with status
**{hubble_flow['upstream_match']['status']}**. Replacing the published
off-diagonal covariance by its diagonal gives
`alpha = {hf_diag['alpha']:.10f} ± {hf_diag['alpha_error']:.10f}`.
Propagating that structural sensitivity through the otherwise unchanged
network gives `H0 = {_format_number(hf_network.get('h0_value'), 10)}` and
`ΔH0 = {_format_number(hf_network.get('delta_h0'), 8)} km/s/Mpc`.

The diagonal-only case is not an endorsed alternative error model. It measures
dependence on the published off-diagonal covariance as encoded by the public
pipeline.

## Scientific interpretation boundary

This audit determines which blocks the encoded computation depends on and
whether its linear algebra is stable. It does **not** show that the largest
shifted block is wrong, causal, or responsible for the Hubble tension. The
blocks overlap through shared hosts and parameters, no missing cross-method
covariance was invented, and the baseline uncertainty is not model-averaged.

## Reproduction

```bash
python scripts/acquire_upstream.py --destination ../H0DN_CLEAN
python scripts/run_audit.py --upstream ../H0DN_CLEAN
python scripts/verify_results.py --upstream ../H0DN_CLEAN \\
  --skip-package-integrity
```

See `AUDIT_CONTRACT.md` for the frozen analysis rules and `results/` for all
machine-readable outputs. `REPRODUCIBILITY.md` gives the complete three-runner,
manifest-regeneration, and root-closure sequence. Follow-up analyses are
governed by their own post-hoc contracts and do not alter this primary result.
"""
    return text


def execute(
    project_root: pathlib.Path,
    upstream: pathlib.Path,
    output_dir: pathlib.Path,
    source_manifest: pathlib.Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_result = verify_source(upstream, source_manifest)
    metadata = run_metadata(project_root, upstream, source_result)
    write_json(output_dir / "run_environment.json", metadata)

    captured = capture_upstream_baseline(upstream)
    (output_dir / "upstream_stdout.log").write_text(
        captured["stdout"], encoding="utf-8"
    )
    (output_dir / "upstream_stderr.log").write_text(
        captured["stderr"], encoding="utf-8"
    )

    upstream_summary = upstream_solution_summary(captured)
    fidelity = baseline_fidelity(upstream_summary)
    equation_data = captured["equation_data"]
    independent = solve_gls(
        equation_data["coeffs"],
        equation_data["yval"],
        equation_data["covar"],
        ihub=equation_data["ihub"],
        iabs=equation_data["iabs"],
        policy="independent_reimplementation_of_official_policy",
        atol=OFFICIAL_ATOL,
        rtol=OFFICIAL_RTOL,
    )
    independent_match = {
        "delta_h0": independent.get("h0_value", math.nan)
        - upstream_summary["h0_value"],
        "delta_h0_error": independent.get("h0_error", math.nan)
        - upstream_summary["h0_error"],
        "delta_chi2": independent.get("chi2", math.nan)
        - upstream_summary["chi2"],
        "rank_matches": independent.get("covar_rank")
        == upstream_summary["covar_rank"],
    }
    independent_match["status"] = (
        "PASS"
        if max(
            abs(float(independent_match["delta_h0"])),
            abs(float(independent_match["delta_h0_error"])),
            abs(float(independent_match["delta_chi2"])),
        )
        < 1.0e-10
        and independent_match["rank_matches"]
        else "FAIL"
    )
    baseline_record = {
        "upstream": upstream_summary,
        "fidelity_gate": fidelity,
        "independent_solver": public_result(independent),
        "independent_solver_match": independent_match,
    }
    write_json(output_dir / "baseline_reproduction.json", baseline_record)
    write_tsv(output_dir / "baseline_fidelity_gate.tsv", fidelity["checks"])
    if fidelity["status"] != "PASS":
        raise AuditFailure("Untouched upstream baseline fidelity gate failed.")
    if independent_match["status"] != "PASS":
        raise AuditFailure("Independent matrix solver does not match upstream.")

    components, aggregates, closure = reconstruct_covariance_components(captured)
    write_tsv(
        output_dir / "covariance_component_inventory.tsv",
        covariance_component_inventory([*components, *aggregates]),
    )
    if closure["status"] != "PASS":
        write_json(output_dir / "component_decomposition_closure.json", closure)
        raise AuditFailure("Covariance-component reconstruction did not close.")

    matrix_record = {
        "network_covariance": matrix_diagnostics(
            equation_data["covar"], name="network covariance C"
        ),
        "normal_matrix": matrix_diagnostics(
            independent["_normal"], name="normal matrix A.T C+ A"
        ),
        "design_matrix": {
            "shape": list(equation_data["coeffs"].shape),
            "rank_numpy_default": int(
                np.linalg.matrix_rank(equation_data["coeffs"])
            ),
            "condition_number": float(
                np.linalg.cond(equation_data["coeffs"])
            ),
        },
        "component_decomposition_closure": closure,
    }
    write_json(output_dir / "matrix_diagnostics.json", matrix_record)
    write_json(output_dir / "component_decomposition_closure.json", closure)

    write_tsv(
        output_dir / "equation_inventory.tsv", equation_inventory(captured)
    )
    write_tsv(
        output_dir / "parameter_inventory.tsv", parameter_inventory(captured)
    )

    blocks = build_equation_blocks(captured)
    write_tsv(
        output_dir / "equation_block_inventory.tsv",
        equation_block_inventory(blocks),
    )

    solver_sensitivity = run_solver_sensitivity(
        captured, upstream_summary
    )
    write_tsv(
        output_dir / "solver_cutoff_sensitivity.tsv", solver_sensitivity
    )

    representation = run_representation_invariance(
        captured, upstream_summary
    )
    write_tsv(
        output_dir / "representation_invariance.tsv", representation
    )

    leave_one_out = run_leave_one_block_out(
        captured, blocks, upstream_summary
    )
    write_tsv(
        output_dir / "leave_one_block_out.tsv",
        [public_result(row) for row in leave_one_out],
    )

    component_ablation = run_component_ablations(
        captured, [*components, *aggregates], upstream_summary
    )
    match_component_ablations_to_leave_one_out(
        component_ablation, leave_one_out
    )
    sn_link_ablation = next(
        row
        for row in component_ablation
        if row["component_id"] == "sn1a_hubble_flow_link_variance"
    )
    if (
        sn_link_ablation["interpretation_status"]
        != "PSEUDOINVERSE_DISCARDED_CONSTRAINT"
        or int(sn_link_ablation["covar_rank"]) != 182
        or sn_link_ablation[
            "matched_leave_one_block_out_match_status"
        ]
        != "PASS"
    ):
        raise AuditFailure(
            "SN-Ia Hubble-flow link constraint-drop classification "
            "or leave-one-out match failed."
        )
    write_tsv(
        output_dir / "covariance_component_ablation.tsv",
        [public_result(row) for row in component_ablation],
    )

    hubble_flow, hubble_flow_sensitivity = run_hubble_flow_covariance_audit(
        captured, upstream_summary
    )
    write_json(output_dir / "hubble_flow_covariance_audit.json", hubble_flow)
    write_tsv(
        output_dir / "hubble_flow_solver_sensitivity.tsv",
        hubble_flow_sensitivity,
    )
    if hubble_flow["upstream_match"]["status"] != "PASS":
        raise AuditFailure("Independent Hubble-flow intercept did not match upstream.")

    rep_pass = all(
        row.get("invariance_status") == "PASS" for row in representation
    )
    summary = {
        "status": "PASS"
        if fidelity["status"] == "PASS"
        and independent_match["status"] == "PASS"
        and closure["status"] == "PASS"
        and rep_pass
        and hubble_flow["upstream_match"]["status"] == "PASS"
        else "PASS_WITH_FLAGGED_NUMERICAL_SENSITIVITY",
        "baseline_gate": fidelity["status"],
        "independent_solver_match": independent_match["status"],
        "covariance_decomposition_closure": closure["status"],
        "representation_invariance": "PASS" if rep_pass else "FAIL",
        "hubble_flow_reproduction": hubble_flow["upstream_match"]["status"],
        "covariance_component_count": len(components),
        "covariance_aggregate_count": len(aggregates),
        "equation_block_count": len(blocks),
        "component_ablation_status_counts": {
            status: sum(
                1 for row in component_ablation if row["status"] == status
            )
            for status in sorted({row["status"] for row in component_ablation})
        },
        "component_ablation_solver_status_counts": {
            status: sum(
                1
                for row in component_ablation
                if row["solver_status"] == status
            )
            for status in sorted(
                {row["solver_status"] for row in component_ablation}
            )
        },
        "component_ablation_interpretation_status_counts": {
            status: sum(
                1
                for row in component_ablation
                if row["interpretation_status"] == status
            )
            for status in sorted(
                {
                    row["interpretation_status"]
                    for row in component_ablation
                }
            )
        },
        "leave_one_out_status_counts": {
            status: sum(1 for row in leave_one_out if row["status"] == status)
            for status in sorted({row["status"] for row in leave_one_out})
        },
        "component_ranking_policy": (
            "Public ranking includes only "
            "PSD_ALGEBRAIC_SENSITIVITY rows."
        ),
        "top_component_influences": _top_influence(
            component_ablation,
            "component_id",
            interpretation_statuses={"PSD_ALGEBRAIC_SENSITIVITY"},
        ),
        "flagged_component_diagnostics": _top_influence(
            component_ablation,
            "component_id",
            interpretation_statuses={
                "PSEUDOINVERSE_DISCARDED_CONSTRAINT",
                "INDEFINITE_ALGEBRAIC_DIAGNOSTIC",
            },
        ),
        "largest_leave_one_block_out_shifts": _top_influence(
            leave_one_out, "block_id"
        ),
        "diagonal_only_hubble_flow_network_result": hubble_flow[
            "diagonal_only_network_result"
        ],
    }
    write_json(output_dir / "audit_summary.json", summary)

    report = build_report(
        baseline_record,
        matrix_record,
        solver_sensitivity,
        representation,
        component_ablation,
        leave_one_out,
        hubble_flow,
        summary,
    )
    report_path = project_root / "REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    write_json(
        output_dir / "report_generation.json",
        {
            "status": "PASS",
            "generator": "scripts/run_audit.py",
            "report": "REPORT.md",
            "sha256": sha256_file(report_path),
            "required_classification_phrase": (
                "PSEUDOINVERSE_DISCARDED_CONSTRAINT"
            ),
            "contains_required_classification_phrase": (
                "PSEUDOINVERSE_DISCARDED_CONSTRAINT" in report
            ),
        },
    )
    return summary


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
    output = args.output.resolve()
    try:
        summary = execute(
            project_root,
            args.upstream.resolve(),
            output,
            args.source_manifest.resolve(),
        )
    except Exception as exc:
        failure = {
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / "EXECUTION_STATUS.json", failure)
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    write_json(
        output / "EXECUTION_STATUS.json",
        {"status": summary["status"], "message": "Audit completed."},
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
