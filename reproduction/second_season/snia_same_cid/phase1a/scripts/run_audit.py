#!/usr/bin/env python3
"""Execute the frozen H0DN SN Ia residual-deficit localization audit."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import traceback

from auditlib import (
    AuditFailure,
    baseline_checks,
    build_group_design,
    build_hubble_flow_system,
    environment_summary,
    input_inventory,
    load_config,
    load_hubble_flow_inputs,
    monte_carlo_null_check,
    numerical_crosschecks,
    permutation_checks,
    primary_partition,
    public_partition,
    reference_partition,
    statistical_interpretation,
    verify_contract_freeze,
    write_json,
    write_tsv,
)
from source_tools import SourceVerificationError, verify_source


def write_execution_status(
    results: pathlib.Path,
    *,
    status: str,
    stage: str,
    detail: str,
    scientific_interpretation_released: bool,
) -> None:
    write_json(
        results / "EXECUTION_STATUS.json",
        {
            "status": status,
            "stage": stage,
            "detail": detail,
            "scientific_interpretation_released": scientific_interpretation_released,
        },
    )


def execute(project: pathlib.Path, upstream: pathlib.Path) -> str:
    results = project / "results"
    results.mkdir(parents=True, exist_ok=True)
    config = load_config(project)
    write_json(results / "run_environment.json", environment_summary())

    try:
        contract = verify_contract_freeze(project)
    except (OSError, KeyError, ValueError, AuditFailure) as exc:
        write_execution_status(
            results,
            status="HOLD_VERIFICATION_FAILURE",
            stage="contract_freeze",
            detail=str(exc),
            scientific_interpretation_released=False,
        )
        raise
    write_json(results / "contract_verification.json", contract)

    try:
        source = verify_source(
            upstream, project / "provenance" / "SOURCE_LOCK.tsv"
        )
    except (OSError, SourceVerificationError) as exc:
        write_execution_status(
            results,
            status="HOLD_SOURCE_MISMATCH",
            stage="source_verification",
            detail=str(exc),
            scientific_interpretation_released=False,
        )
        raise
    write_json(results / "source_verification.json", source)

    inputs = load_hubble_flow_inputs(upstream)
    system = build_hubble_flow_system(inputs, config)
    groups = build_group_design(inputs.names)
    inventory = input_inventory(inputs, system, groups, config)
    write_json(results / "input_inventory.json", inventory)
    if inventory["status"] != "PASS":
        write_execution_status(
            results,
            status="HOLD_INPUT_OR_DESIGN_MISMATCH",
            stage="input_inventory",
            detail="One or more frozen input or design checks failed",
            scientific_interpretation_released=False,
        )
        raise AuditFailure("Input inventory gate failed")

    primary = primary_partition(
        system["data_alpha"],
        system["covariance_alpha"],
        groups["design"],
    )
    reference = reference_partition(
        system["data_alpha"],
        system["covariance_alpha"],
        groups["design"],
    )
    write_json(results / "primary_partition.json", public_partition(primary))
    write_json(results / "reference_partition.json", reference)

    baseline = baseline_checks(primary, config)
    write_json(results / "baseline_reproduction.json", baseline)
    write_tsv(
        results / "baseline_reproduction.tsv",
        baseline["comparisons"],
        (
            "quantity",
            "actual",
            "expected",
            "absolute_difference",
            "tolerance",
            "status",
        ),
    )
    if baseline["status"] != "PASS":
        write_execution_status(
            results,
            status="HOLD_BASELINE_REPRODUCTION_MISMATCH",
            stage="baseline_reproduction",
            detail="Known Phase 0 baseline did not reproduce",
            scientific_interpretation_released=False,
        )
        raise AuditFailure("Known baseline gate failed")

    crosschecks = numerical_crosschecks(primary, reference, config)
    write_json(results / "numerical_crosschecks.json", crosschecks)
    write_tsv(
        results / "numerical_crosschecks.tsv",
        crosschecks["checks"],
        ("check", "absolute_difference", "tolerance", "status"),
    )

    monte_carlo = monte_carlo_null_check(primary, config)
    write_json(results / "monte_carlo_null_check.json", monte_carlo)
    write_tsv(
        results / "monte_carlo_null_check.tsv",
        monte_carlo["metrics"],
        (
            "metric",
            "empirical_mean",
            "empirical_standard_deviation",
            "expected_mean",
            "analytic_mean_standard_error",
            "gate_standard_errors",
            "absolute_difference",
            "tolerance",
            "status",
        ),
    )

    permutations = permutation_checks(
        system["data_alpha"],
        system["covariance_alpha"],
        inputs.names,
        primary,
        config,
    )
    write_json(
        results / "permutation_invariance_summary.json",
        {key: value for key, value in permutations.items() if key != "rows"},
    )
    write_tsv(
        results / "permutation_invariance.tsv",
        permutations["rows"],
        (
            "permutation_index",
            "permutation_sha256",
            "total_chi2_absolute_difference",
            "duplicate_chi2_absolute_difference",
            "between_chi2_absolute_difference",
            "tolerance",
            "status",
        ),
    )

    if (
        crosschecks["status"] != "PASS"
        or monte_carlo["status"] != "PASS"
        or permutations["status"] != "PASS"
    ):
        write_execution_status(
            results,
            status="HOLD_NUMERICAL_CROSSCHECK_FAILURE",
            stage="numerical_verification",
            detail=(
                f"crosschecks={crosschecks['status']}; "
                f"monte_carlo={monte_carlo['status']}; "
                f"permutations={permutations['status']}"
            ),
            scientific_interpretation_released=False,
        )
        raise AuditFailure("Numerical verification gate failed")

    interpretation = statistical_interpretation(primary, config)
    write_json(results / "statistical_interpretation.json", interpretation)
    partition_rows = [
        {
            "component": "total",
            "chi2": primary["chi2_total"],
            "degrees_of_freedom": primary["df_total"],
            "lower_tail_probability": interpretation[
                "global_lower_tail_probability"
            ],
            "primary_or_secondary": "known_global_diagnostic",
        },
        {
            "component": "duplicate_name_contrasts",
            "chi2": primary["chi2_duplicate_name_contrasts"],
            "degrees_of_freedom": primary[
                "df_duplicate_name_contrasts"
            ],
            "lower_tail_probability": interpretation[
                "duplicate_component_lower_tail_probability_secondary"
            ],
            "primary_or_secondary": "secondary_marginal",
        },
        {
            "component": "between_name_modes",
            "chi2": primary["chi2_between_name_modes"],
            "degrees_of_freedom": primary["df_between_name_modes"],
            "lower_tail_probability": interpretation[
                "between_component_lower_tail_probability_secondary"
            ],
            "primary_or_secondary": "secondary_marginal",
        },
    ]
    write_tsv(
        results / "partition_summary.tsv",
        partition_rows,
        (
            "component",
            "chi2",
            "degrees_of_freedom",
            "lower_tail_probability",
            "primary_or_secondary",
        ),
    )

    status = interpretation["status"]
    audit_summary = {
        "contract_id": config["contract_id"],
        "status": status,
        "source_status": source["status"],
        "input_status": inventory["status"],
        "baseline_status": baseline["status"],
        "numerical_crosscheck_status": crosschecks["status"],
        "monte_carlo_status": monte_carlo["status"],
        "permutation_status": permutations["status"],
        "object_count": inventory["object_count"],
        "unique_exact_name_count": inventory["unique_exact_name_count"],
        "multi_row_exact_name_group_count": inventory[
            "multi_row_exact_name_group_count"
        ],
        "rows_in_multi_row_exact_name_groups": inventory[
            "rows_in_multi_row_exact_name_groups"
        ],
        "duplicate_name_excess_row_count": inventory[
            "duplicate_name_excess_row_count"
        ],
        "duplicate_name_contrast_df": inventory[
            "duplicate_name_contrast_df"
        ],
        "legacy_duplicate_name_row_count": inventory[
            "legacy_duplicate_name_row_count"
        ],
        "legacy_field_note": inventory["legacy_field_note"],
        "chi2_total": interpretation["chi2_total"],
        "chi2_duplicate_name_contrasts": interpretation[
            "chi2_duplicate_name_contrasts"
        ],
        "chi2_between_name_modes": interpretation[
            "chi2_between_name_modes"
        ],
        "df_total": interpretation["df_total"],
        "df_duplicate_name_contrasts": interpretation[
            "df_duplicate_name_contrasts"
        ],
        "df_between_name_modes": interpretation[
            "df_between_name_modes"
        ],
        "duplicate_share_ratio": interpretation["duplicate_share_ratio"],
        "global_lower_tail_probability": interpretation[
            "global_lower_tail_probability"
        ],
        "beta_lower_tail_probability": interpretation[
            "beta_lower_tail_probability"
        ],
        "beta_upper_tail_probability": interpretation[
            "beta_upper_tail_probability"
        ],
        "beta_two_sided_probability": interpretation[
            "beta_two_sided_probability"
        ],
        "localization_class": interpretation["localization_class"],
        "boundary_marker": (
            "FROZEN_MODEL_ONLY_NO_COVARIANCE_CORRECTION_"
            "NO_CORRECTED_H0_NO_TENSION_RESOLUTION"
        ),
    }
    write_json(results / "audit_summary.json", audit_summary)
    write_execution_status(
        results,
        status=status,
        stage="complete",
        detail="All required provenance and numerical gates passed",
        scientific_interpretation_released=True,
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        status = execute(project, args.upstream.resolve())
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 2
    print(json.dumps({"status": status}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
