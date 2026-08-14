#!/usr/bin/env python3
"""Execute the frozen H0DN SN Ia Phase 1C audit."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import traceback

import numpy as np

from auditlib import (
    BASELINE_ORDER,
    BOUNDARY_MARKER,
    DIAGNOSTIC_ORDER,
    SUCCESS_STATUS,
    AuditFailure,
    assemble_analysis,
    build_alpha_data,
    build_group_structure,
    environment_summary,
    load_config,
    load_mapping,
    numerical_gate_summary,
    parse_covariance,
    parse_h0dn_table,
    parse_official_table,
    probability_reference_questions,
    verify_contract_freeze,
    verify_sources,
    verify_upstream_audit_dependencies,
    write_json,
    write_tsv,
)


def execution_status(
    results: pathlib.Path,
    status: str,
    stage: str,
    detail: str,
    released: bool,
) -> None:
    write_json(
        results / "EXECUTION_STATUS.json",
        {
            "status": status,
            "stage": stage,
            "detail": detail,
            "scientific_interpretation_released": released,
        },
    )


def require(condition: bool, status: str, message: str) -> None:
    if not condition:
        raise AuditFailure(f"{status}: {message}")


def execute(
    project: pathlib.Path,
    h0dn_root: pathlib.Path,
    pantheon_root: pathlib.Path,
    phase1a_archive: pathlib.Path,
    phase1b_archive: pathlib.Path,
) -> str:
    results = project / "results"
    results.mkdir(parents=True, exist_ok=True)
    config = load_config(project)
    write_json(results / "run_environment.json", environment_summary())

    contract = verify_contract_freeze(project)
    write_json(results / "contract_verification.json", contract)
    if contract["status"] != "PASS":
        execution_status(
            results,
            "HOLD_CONTRACT_MISMATCH",
            "contract",
            "contract freeze or chronology gate failed",
            False,
        )
        raise AuditFailure("contract gate failed")

    source = verify_sources(
        project, {"h0dn": h0dn_root, "pantheonplus": pantheon_root}
    )
    write_json(results / "source_verification.json", source)
    if source["status"] != "PASS":
        execution_status(
            results,
            "HOLD_SOURCE_MISMATCH",
            "sources",
            "one or more source-lock checks failed",
            False,
        )
        raise AuditFailure("source gate failed")

    upstream = verify_upstream_audit_dependencies(
        project,
        {
            "phase1a": phase1a_archive,
            "phase1b": phase1b_archive,
        },
    )
    write_json(
        results / "upstream_audit_dependency_verification.json",
        upstream,
    )
    if upstream["status"] != "PASS":
        execution_status(
            results,
            "HOLD_UPSTREAM_AUDIT_DEPENDENCY_MISMATCH",
            "upstream_audit_dependencies",
            "Phase 1A or Phase 1B canonical ZIP, sidecar, or CRC failed",
            False,
        )
        raise AuditFailure("upstream audit dependency gate failed")

    h0dn_rows = parse_h0dn_table(h0dn_root / "data" / "sn1a_hf_pp.dat")
    official_directory = (
        pantheon_root / "Pantheon+_Data" / "4_DISTANCES_AND_COVAR"
    )
    official_rows = parse_official_table(
        official_directory / "Pantheon+SH0ES.dat"
    )
    mapping, mapping_status = load_mapping(
        project / "provenance" / "PHASE1B_ROW_MAP.tsv",
        h0dn_rows,
        official_rows,
    )
    write_json(
        results / "dependency_mapping_verification.json", mapping_status
    )
    if mapping_status["status"] != "PASS":
        execution_status(
            results,
            "HOLD_DEPENDENCY_MAPPING_MISMATCH",
            "mapping",
            "Phase 1B compact mapping failed verification",
            False,
        )
        raise AuditFailure("mapping dependency gate failed")

    expected = config["expected"]
    h0dn_covariance, h0dn_covariance_schema = parse_covariance(
        h0dn_root / "data" / "sn1a_covar_pp.dat",
        int(expected["h0dn_dimension"]),
    )
    stat_sys, stat_sys_schema = parse_covariance(
        official_directory / "Pantheon+SH0ES_STAT+SYS.cov",
        int(expected["official_dimension"]),
    )
    stat_only, stat_only_schema = parse_covariance(
        official_directory / "Pantheon+SH0ES_STATONLY.cov",
        int(expected["official_dimension"]),
    )

    names = [row["name"] for row in h0dn_rows]
    group = build_group_structure(names, mapping)
    identity_tolerance = float(
        config["tolerances"]["contrast_identity_absolute"]
    )
    group_checks = {
        "h0dn_row_count": len(h0dn_rows) == int(expected["h0dn_dimension"]),
        "official_row_count": (
            len(official_rows) == int(expected["official_dimension"])
        ),
        "unique_exact_names": (
            group["unique_exact_name_count"]
            == int(expected["unique_exact_names"])
        ),
        "multirow_exact_name_groups": (
            group["multirow_exact_name_group_count"]
            == int(expected["multirow_exact_name_groups"])
        ),
        "rows_in_multirow_groups": (
            group["rows_in_multirow_groups"]
            == int(expected["rows_in_multirow_groups"])
        ),
        "contrast_degrees_of_freedom": (
            group["contrast_degrees_of_freedom"]
            == int(expected["contrast_degrees_of_freedom"])
        ),
        "contrast_rank": (
            group["contrast_rank"]
            == int(expected["contrast_degrees_of_freedom"])
        ),
        "all_multirow_groups_cross_survey": group[
            "all_multirow_groups_cross_survey"
        ],
        "contrast_orthogonality": (
            group["contrast_orthogonality_max_absolute_error"]
            <= identity_tolerance
        ),
        "group_annihilation": (
            group["group_annihilation_max_absolute_error"]
            <= identity_tolerance
        ),
        "h0dn_covariance_exact_symmetry": h0dn_covariance_schema[
            "exactly_symmetric"
        ],
        "stat_sys_transpose_tolerance": (
            stat_sys_schema["maximum_absolute_transpose_difference"]
            <= float(config["tolerances"]["official_transpose_absolute"])
        ),
        "stat_only_transpose_tolerance": (
            stat_only_schema["maximum_absolute_transpose_difference"]
            <= float(config["tolerances"]["official_transpose_absolute"])
        ),
    }
    inventory = {
        "h0dn_row_count": len(h0dn_rows),
        "official_row_count": len(official_rows),
        "unique_exact_name_count": group["unique_exact_name_count"],
        "multirow_exact_name_group_count": group[
            "multirow_exact_name_group_count"
        ],
        "rows_in_multirow_groups": group["rows_in_multirow_groups"],
        "contrast_degrees_of_freedom": group[
            "contrast_degrees_of_freedom"
        ],
        "contrast_rank": group["contrast_rank"],
        "multiplicity_histogram": group["multiplicity_histogram"],
        "all_multirow_groups_cross_survey": group[
            "all_multirow_groups_cross_survey"
        ],
        "contrast_orthogonality_max_absolute_error": group[
            "contrast_orthogonality_max_absolute_error"
        ],
        "group_annihilation_max_absolute_error": group[
            "group_annihilation_max_absolute_error"
        ],
        "covariance_schemas": {
            "H0DN": h0dn_covariance_schema,
            "STAT_SYS": stat_sys_schema,
            "STAT_ONLY": stat_only_schema,
        },
        "checks": group_checks,
        "status": "PASS" if all(group_checks.values()) else "FAIL",
    }
    write_json(results / "input_inventory.json", inventory)
    write_tsv(
        results / "contrast_definition.tsv",
        group["contrast_definition"],
        (
            "contrast_index_1based",
            "group_first_h0dn_row_1based",
            "CID",
            "within_group_contrast_index_1based",
            "h0dn_row_1based",
            "official_row_1based",
            "IDSURVEY",
            "weight",
        ),
    )
    if inventory["status"] != "PASS":
        execution_status(
            results,
            "HOLD_INPUT_OR_GROUP_MISMATCH",
            "input_and_group",
            "input schema, covariance, or contrast identity gate failed",
            False,
        )
        raise AuditFailure("input/group gate failed")

    alpha = build_alpha_data(h0dn_rows, config)
    analysis = assemble_analysis(
        h0dn_rows,
        official_rows,
        mapping,
        h0dn_covariance,
        stat_sys,
        stat_only,
        group,
        alpha,
        config,
    )
    write_json(results / "covariance_lineage.json", analysis["lineage"])
    if analysis["lineage"]["status"] != "PASS":
        execution_status(
            results,
            "HOLD_COVARIANCE_LINEAGE_MISMATCH",
            "covariance_lineage",
            "mapped official STAT+SYS does not equal H0DN",
            False,
        )
        raise AuditFailure("covariance lineage gate failed")

    baseline_rows = [
        {
            key: result[key]
            for key in (
                "baseline",
                "chi2",
                "degrees_of_freedom",
                "lower_tail_probability",
                "dispersion_label",
                "low_flag_at_alpha_0_01",
                "scalar_scale_estimate_q_over_df",
                "scalar_scale_95_percent_interval_lower",
                "scalar_scale_95_percent_interval_upper",
                "reference_eigendecomposition_chi2",
                "reference_chi2_absolute_difference",
                "cdf_gammainc_absolute_difference",
            )
        }
        for result in (
            analysis["baseline_results"][name]
            for name in (*BASELINE_ORDER, *DIAGNOSTIC_ORDER)
        )
    ]
    write_tsv(
        results / "quadratic_forms.tsv",
        baseline_rows,
        tuple(baseline_rows[0].keys()),
    )
    write_json(
        results / "covariance_baselines.json",
        {
            name: analysis["baseline_results"][name]
            for name in (*BASELINE_ORDER, *DIAGNOSTIC_ORDER)
        },
    )
    write_json(
        results / "known_phase1a_reproduction.json",
        analysis["known_reproduction"],
    )
    write_json(
        results / "component_diagnostics.json",
        {
            "components": analysis["component_diagnostics"],
            "model_term_contrast": analysis["model_term_contrast"],
        },
    )
    write_json(
        results / "alternative_basis_checks.json",
        analysis["alternative_basis"],
    )
    write_tsv(
        results / "orthogonal_invariance.tsv",
        analysis["orthogonal_invariance"]["rows"],
        (
            "trial_1based",
            "baseline",
            "chi2",
            "reference_chi2",
            "absolute_difference",
        ),
    )
    write_json(
        results / "orthogonal_invariance_summary.json",
        {
            key: value
            for key, value in analysis["orthogonal_invariance"].items()
            if key != "rows"
        },
    )
    numerical = numerical_gate_summary(analysis, config)
    write_json(results / "numerical_crosschecks.json", numerical)
    if numerical["status"] != "PASS":
        execution_status(
            results,
            "HOLD_NUMERICAL_CROSSCHECK_FAILURE",
            "numerical_crosschecks",
            "one or more numerical gates failed",
            False,
        )
        raise AuditFailure("numerical crosscheck gate failed")

    ordered_results = {
        name: {
            "chi2": analysis["baseline_results"][name]["chi2"],
            "degrees_of_freedom": analysis["baseline_results"][name][
                "degrees_of_freedom"
            ],
            "lower_tail_probability": analysis["baseline_results"][name][
                "lower_tail_probability"
            ],
            "dispersion_label": analysis["baseline_results"][name][
                "dispersion_label"
            ],
            "low_flag_at_alpha_0_01": analysis["baseline_results"][name][
                "low_flag_at_alpha_0_01"
            ],
        }
        for name in BASELINE_ORDER
    }
    summary = {
        "contract_id": config["contract_id"],
        "status": SUCCESS_STATUS,
        "sensitivity_classification": analysis[
            "sensitivity_classification"
        ],
        "ordered_baseline_results": ordered_results,
        "contrast_degrees_of_freedom": group[
            "contrast_degrees_of_freedom"
        ],
        "multirow_exact_name_group_count": group[
            "multirow_exact_name_group_count"
        ],
        "rows_in_multirow_groups": group["rows_in_multirow_groups"],
        "all_multirow_groups_cross_survey": group[
            "all_multirow_groups_cross_survey"
        ],
        "source_status": source["status"],
        "upstream_audit_dependency_status": upstream["status"],
        "dependency_mapping_status": mapping_status["status"],
        "input_status": inventory["status"],
        "covariance_lineage_status": analysis["lineage"]["status"],
        "known_phase1a_reproduction_status": analysis[
            "known_reproduction"
        ]["status"],
        "numerical_crosscheck_status": numerical["status"],
        "probability_reference_questions": (
            probability_reference_questions(
                ordered_results["PHASE1A_FULL"][
                    "lower_tail_probability"
                ]
            )
        ),
        "classification_thresholds": {
            "strong_low_dispersion_label_alpha": 0.001,
            "ordered_sensitivity_flag_alpha": 0.01,
            "all_three_main_baselines_meet_strong_low_label": all(
                ordered_results[name]["lower_tail_probability"] < 0.001
                for name in BASELINE_ORDER
            ),
            "all_three_main_baselines_meet_ordered_sensitivity_flag": all(
                ordered_results[name]["lower_tail_probability"] < 0.01
                for name in BASELINE_ORDER
            ),
            "thresholds_are_distinct": True,
        },
        "boundary_marker": BOUNDARY_MARKER,
        "nonclaims": [
            "NO_COVARIANCE_CORRECTION_OR_RESCALE",
            "NO_OBJECT_OR_SURVEY_RANKING",
            "NO_CORRECTED_A_B_M_B_OR_H0",
            "NO_HUBBLE_TENSION_RECALCULATION",
            "NO_PHYSICAL_CAUSE_ASSIGNMENT",
        ],
    }
    write_json(results / "audit_summary.json", summary)
    execution_status(
        results,
        SUCCESS_STATUS,
        "complete",
        "all frozen provenance and numerical gates passed",
        True,
    )
    return SUCCESS_STATUS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--phase1a-archive", type=pathlib.Path, required=True)
    parser.add_argument("--phase1b-archive", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        status = execute(
            project,
            args.h0dn.resolve(),
            args.pantheonplus.resolve(),
            args.phase1a_archive.resolve(),
            args.phase1b_archive.resolve(),
        )
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 2
    print(json.dumps({"status": status}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
