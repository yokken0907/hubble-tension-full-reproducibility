#!/usr/bin/env python3
"""Run the frozen post-hoc precision and mapped-asymmetry diagnostics."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import traceback
from typing import Any

import numpy as np

from auditlib import (
    BASELINE_ORDER,
    POSTHOC_CONTRACT_ID,
    POSTHOC_CONTRACT_SHA256,
    SUCCESS_STATUS,
    AuditFailure,
    baseline_result,
    build_alpha_data,
    build_group_structure,
    covariance_representations,
    float64_matrix_sha256,
    load_config,
    load_mapping,
    parse_covariance,
    parse_h0dn_table,
    parse_official_table,
    probability_reference_questions,
    selected_submatrix_asymmetry,
    sha256_file,
    verify_contract_freeze,
    verify_sources,
    write_json,
    write_tsv,
)


POSTHOC_STATUS = "POSTHOC_DIAGNOSTIC_COMPLETE"
PROTECTED_MAIN_ARTIFACTS = (
    "results/EXECUTION_STATUS.json",
    "results/alternative_basis_checks.json",
    "results/audit_summary.json",
    "results/component_diagnostics.json",
    "results/contrast_definition.tsv",
    "results/contract_verification.json",
    "results/covariance_baselines.json",
    "results/covariance_lineage.json",
    "results/dependency_mapping_verification.json",
    "results/input_inventory.json",
    "results/known_phase1a_reproduction.json",
    "results/numerical_crosschecks.json",
    "results/orthogonal_invariance.tsv",
    "results/orthogonal_invariance_summary.json",
    "results/quadratic_forms.tsv",
    "results/run_environment.json",
    "results/source_verification.json",
    "results/upstream_audit_dependency_verification.json",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def protected_hashes(project: pathlib.Path) -> dict[str, str]:
    return {
        relative: sha256_file(project / relative)
        for relative in PROTECTED_MAIN_ARTIFACTS
    }


def compact_baseline(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "chi2": result["chi2"],
        "degrees_of_freedom": result["degrees_of_freedom"],
        "lower_tail_probability": result["lower_tail_probability"],
        "scalar_scale_estimate_q_over_df": result[
            "scalar_scale_estimate_q_over_df"
        ],
        "reference_chi2_absolute_difference": result[
            "reference_chi2_absolute_difference"
        ],
        "cdf_gammainc_absolute_difference": result[
            "cdf_gammainc_absolute_difference"
        ],
        "projected_covariance": result["covariance"],
    }


def execute(
    project: pathlib.Path,
    h0dn_root: pathlib.Path,
    pantheon_root: pathlib.Path,
) -> str:
    contract = verify_contract_freeze(project)
    require(contract["status"] == "PASS", "post-hoc contract gate failed")
    require(
        contract["posthoc_contract_sha256"] == POSTHOC_CONTRACT_SHA256,
        "post-hoc contract SHA-256 mismatch",
    )
    source = verify_sources(
        project, {"h0dn": h0dn_root, "pantheonplus": pantheon_root}
    )
    require(source["status"] == "PASS", "source-lock gate failed")
    require(
        sum(
            repository["locked_file_count"]
            for repository in source["repositories"].values()
        )
        == 13,
        "post-hoc execution requires 13 locked source files",
    )

    config = load_config(project)
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
    require(mapping_status["status"] == "PASS", "mapping gate failed")

    expected = config["expected"]
    h0dn_covariance, h0dn_schema = parse_covariance(
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
    group = build_group_structure(
        [row["name"] for row in h0dn_rows], mapping
    )
    require(
        group["multirow_exact_name_group_count"] == 30
        and group["rows_in_multirow_groups"] == 69
        and group["contrast_degrees_of_freedom"] == 39
        and group["contrast_rank"] == 39,
        "frozen group or contrast dimensions changed",
    )
    require(
        group["contrast_orthogonality_max_absolute_error"] <= 2e-14
        and group["group_annihilation_max_absolute_error"] <= 2e-14,
        "frozen contrast identity tolerance failed",
    )

    selected = np.asarray(
        [row["official_row_0based"] for row in mapping], dtype=int
    )
    raw_stat_sys = stat_sys[np.ix_(selected, selected)]
    raw_stat_only = stat_only[np.ix_(selected, selected)]
    require(
        np.array_equal(raw_stat_sys, h0dn_covariance),
        "mapped STAT+SYS lineage no longer equals H0DN",
    )

    alpha_printed = build_alpha_data(h0dn_rows, config)
    mapped_high_precision = np.asarray(
        [official_rows[index]["m_b_corr"] for index in selected], dtype=float
    )
    high_precision_data_alpha = (
        alpha_printed["model_term_alpha"] - 0.2 * mapped_high_precision
    )
    basis = group["A"]
    printed_contrast = basis @ alpha_printed["data_alpha"]
    high_precision_contrast = basis @ high_precision_data_alpha
    contrast_difference = high_precision_contrast - printed_contrast

    stat_sys_symmetric = 0.5 * (raw_stat_sys + raw_stat_sys.T)
    stat_only_symmetric = 0.5 * (raw_stat_only + raw_stat_only.T)
    row_covariances = {
        "PHASE1A_FULL": (
            h0dn_covariance / 25.0
            + np.diag(alpha_printed["velocity_variance_alpha"])
        ),
        "STAT_SYS_NO_ROWWISE_VELOCITY": stat_sys_symmetric / 25.0,
        "STAT_ONLY": stat_only_symmetric / 25.0,
    }

    main_summary = json.loads(
        (project / "results" / "audit_summary.json").read_text(
            encoding="utf-8"
        )
    )
    main_baselines = json.loads(
        (project / "results" / "covariance_baselines.json").read_text(
            encoding="utf-8"
        )
    )
    require(main_summary["status"] == SUCCESS_STATUS, "main status changed")
    require(
        main_summary["sensitivity_classification"]
        == "LOW_FLAG_PERSISTS_THROUGH_STATONLY",
        "main ordered classification changed",
    )

    baseline_comparisons: dict[str, Any] = {}
    precision_tsv_rows: list[dict[str, Any]] = []
    for name in BASELINE_ORDER:
        projected = basis @ row_covariances[name] @ basis.T
        printed = baseline_result(
            name, printed_contrast, projected, config
        )
        high_precision = baseline_result(
            name, high_precision_contrast, projected, config
        )
        reproduction_difference = abs(
            printed["chi2"] - main_baselines[name]["chi2"]
        )
        require(
            reproduction_difference <= 2e-8,
            f"printed-vector main reproduction failed for {name}",
        )
        delta_chi2 = high_precision["chi2"] - printed["chi2"]
        delta_probability = (
            high_precision["lower_tail_probability"]
            - printed["lower_tail_probability"]
        )
        baseline_comparisons[name] = {
            "printed_h0dn_m_b": compact_baseline(printed),
            "official_high_precision_m_b_corr": compact_baseline(
                high_precision
            ),
            "delta_chi2_high_precision_minus_printed": delta_chi2,
            "delta_lower_tail_probability_high_precision_minus_printed": (
                delta_probability
            ),
            "printed_main_result_reproduction_absolute_difference": (
                reproduction_difference
            ),
            "printed_main_result_reproduction_tolerance": 2e-8,
            "printed_main_result_reproduction_status": "PASS",
        }
        precision_tsv_rows.append(
            {
                "baseline": name,
                "degrees_of_freedom": 39,
                "printed_chi2": printed["chi2"],
                "high_precision_chi2": high_precision["chi2"],
                "delta_chi2_high_precision_minus_printed": delta_chi2,
                "printed_lower_tail_probability": printed[
                    "lower_tail_probability"
                ],
                "high_precision_lower_tail_probability": high_precision[
                    "lower_tail_probability"
                ],
                "delta_lower_tail_probability_high_precision_minus_printed": (
                    delta_probability
                ),
                "printed_q_over_df": printed[
                    "scalar_scale_estimate_q_over_df"
                ],
                "high_precision_q_over_df": high_precision[
                    "scalar_scale_estimate_q_over_df"
                ],
            }
        )

    protected_before = protected_hashes(project)
    asymmetry_sources = {
        "STAT_SYS": {
            "matrix": raw_stat_sys,
            "full_schema": stat_sys_schema,
            "applicable_baselines": (
                "PHASE1A_FULL",
                "STAT_SYS_NO_ROWWISE_VELOCITY",
            ),
        },
        "STAT_ONLY": {
            "matrix": raw_stat_only,
            "full_schema": stat_only_schema,
            "applicable_baselines": ("STAT_ONLY",),
        },
    }
    asymmetry_json: dict[str, Any] = {}
    sensitivity_rows: list[dict[str, Any]] = []
    for source_name, source_record in asymmetry_sources.items():
        matrix = source_record["matrix"]
        diagnostic = selected_submatrix_asymmetry(matrix, mapping)
        full_schema = source_record["full_schema"]
        if diagnostic["exactly_symmetric"]:
            statement = (
                "FULL_1701_ASYMMETRY_LIES_OUTSIDE_SELECTED_MAPPING"
                if full_schema["asymmetric_element_count"] > 0
                else "FULL_AND_SELECTED_MATRICES_ARE_EXACTLY_SYMMETRIC"
            )
        else:
            statement = (
                "SELECTED_MAPPING_CONTAINS_EXACT_RAW_ASYMMETRY; "
                "THREE_FROZEN_REPRESENTATIONS_EVALUATED"
            )
        source_output: dict[str, Any] = {
            "raw_selected_submatrix": diagnostic,
            "full_1701_source_schema": full_schema,
            "interpretive_statement": statement,
            "sensitivity_triggered": not diagnostic["exactly_symmetric"],
            "representations": {},
        }
        if not diagnostic["exactly_symmetric"]:
            representations = covariance_representations(matrix)
            for baseline_name in source_record["applicable_baselines"]:
                symmetric_result: dict[str, Any] | None = None
                for representation_name, representation in (
                    representations.items()
                ):
                    if baseline_name == "PHASE1A_FULL":
                        row_covariance = (
                            representation / 25.0
                            + np.diag(
                                alpha_printed["velocity_variance_alpha"]
                            )
                        )
                    else:
                        row_covariance = representation / 25.0
                    projected = basis @ row_covariance @ basis.T
                    result = baseline_result(
                        baseline_name,
                        printed_contrast,
                        projected,
                        config,
                    )
                    compact = compact_baseline(result)
                    source_output["representations"].setdefault(
                        baseline_name, {}
                    )[representation_name] = compact
                    if representation_name == "SYMMETRIC_AVERAGE":
                        symmetric_result = result
                    require(
                        symmetric_result is not None
                        or representation_name == "SYMMETRIC_AVERAGE",
                        "symmetric representation must be evaluated first",
                    )
                    reference = (
                        result
                        if representation_name == "SYMMETRIC_AVERAGE"
                        else symmetric_result
                    )
                    sensitivity_rows.append(
                        {
                            "source_covariance": source_name,
                            "baseline": baseline_name,
                            "representation": representation_name,
                            "chi2": result["chi2"],
                            "degrees_of_freedom": 39,
                            "lower_tail_probability": result[
                                "lower_tail_probability"
                            ],
                            "q_over_df": result[
                                "scalar_scale_estimate_q_over_df"
                            ],
                            "delta_chi2_from_symmetric_average": (
                                result["chi2"] - reference["chi2"]
                            ),
                            "delta_probability_from_symmetric_average": (
                                result["lower_tail_probability"]
                                - reference["lower_tail_probability"]
                            ),
                        }
                    )
        asymmetry_json[source_name] = source_output

    results = project / "results"
    write_json(
        results / "mapped_submatrix_asymmetry_diagnostic.json",
        {
            "contract_id": POSTHOC_CONTRACT_ID,
            "contract_sha256": POSTHOC_CONTRACT_SHA256,
            "status": POSTHOC_STATUS,
            "mapping_sha256": mapping_status["mapping_sha256"],
            "mapping_row_count": mapping_status["row_count"],
            "comparison_tolerance_absolute": 0.0,
            "sources": asymmetry_json,
            "promotion_status": "POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE",
        },
    )
    write_tsv(
        results / "mapped_submatrix_asymmetry_sensitivity.tsv",
        sensitivity_rows,
        (
            "source_covariance",
            "baseline",
            "representation",
            "chi2",
            "degrees_of_freedom",
            "lower_tail_probability",
            "q_over_df",
            "delta_chi2_from_symmetric_average",
            "delta_probability_from_symmetric_average",
        ),
    )
    write_tsv(
        results / "printed_vs_high_precision_contrast_diagnostic.tsv",
        precision_tsv_rows,
        (
            "baseline",
            "degrees_of_freedom",
            "printed_chi2",
            "high_precision_chi2",
            "delta_chi2_high_precision_minus_printed",
            "printed_lower_tail_probability",
            "high_precision_lower_tail_probability",
            "delta_lower_tail_probability_high_precision_minus_printed",
            "printed_q_over_df",
            "high_precision_q_over_df",
        ),
    )
    protected_after = protected_hashes(project)
    protected_unchanged = protected_before == protected_after
    require(protected_unchanged, "post-hoc run changed a main result artifact")
    main_phase1a_probability = main_baselines["PHASE1A_FULL"][
        "lower_tail_probability"
    ]
    thresholds = {
        "strong_low_dispersion_label_alpha": 0.001,
        "ordered_sensitivity_flag_alpha": 0.01,
        "all_three_main_baselines_meet_strong_low_label": all(
            main_baselines[name]["lower_tail_probability"] < 0.001
            for name in BASELINE_ORDER
        ),
        "all_three_main_baselines_meet_ordered_sensitivity_flag": all(
            main_baselines[name]["lower_tail_probability"] < 0.01
            for name in BASELINE_ORDER
        ),
        "thresholds_are_distinct": True,
    }
    write_json(
        results / "printed_vs_high_precision_contrast_diagnostic.json",
        {
            "contract_id": POSTHOC_CONTRACT_ID,
            "contract_sha256": POSTHOC_CONTRACT_SHA256,
            "status": POSTHOC_STATUS,
            "mapping_sha256": mapping_status["mapping_sha256"],
            "mapping_row_count": mapping_status["row_count"],
            "same_mapping_and_basis": True,
            "contrast_basis_sha256_float64_little_endian": (
                float64_matrix_sha256(basis)
            ),
            "contrast_basis_shape": list(basis.shape),
            "multirow_exact_name_group_count": group[
                "multirow_exact_name_group_count"
            ],
            "rows_in_multirow_groups": group["rows_in_multirow_groups"],
            "contrast_degrees_of_freedom": group[
                "contrast_degrees_of_freedom"
            ],
            "vectors": {
                "printed": "H0DN data/sn1a_hf_pp.dat field m_b",
                "high_precision": (
                    "mapped official Pantheon+SH0ES.dat field m_b_corr"
                ),
                "maximum_absolute_contrast_difference": float(
                    np.max(np.abs(contrast_difference))
                ),
                "euclidean_norm_contrast_difference": float(
                    np.linalg.norm(contrast_difference)
                ),
            },
            "ordered_baseline_comparisons": baseline_comparisons,
            "probability_reference_questions": (
                probability_reference_questions(main_phase1a_probability)
            ),
            "classification_thresholds": thresholds,
            "main_result_invariance": {
                "formal_status_before_and_after": SUCCESS_STATUS,
                "ordered_classification_before_and_after": (
                    "LOW_FLAG_PERSISTS_THROUGH_STATONLY"
                ),
                "protected_artifact_count": len(PROTECTED_MAIN_ARTIFACTS),
                "protected_artifact_sha256_before": protected_before,
                "protected_artifact_sha256_after": protected_after,
                "protected_artifacts_byte_unchanged": protected_unchanged,
            },
            "promotion_status": "POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE",
            "nonclaims": [
                "NO_MAIN_VECTOR_REPLACEMENT",
                "NO_COVARIANCE_CORRECTION_OR_RESCALE",
                "NO_STATISTICAL_ERROR_OVERESTIMATION_CLAIM",
                "NO_PHYSICAL_OR_PIPELINE_CAUSE_ASSIGNMENT",
                "NO_CORRECTED_A_B_M_B_OR_H0",
                "NO_HUBBLE_TENSION_RECALCULATION",
            ],
        },
    )
    return POSTHOC_STATUS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        status = execute(
            project, args.h0dn.resolve(), args.pantheonplus.resolve()
        )
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 2
    print(json.dumps({"status": status}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
