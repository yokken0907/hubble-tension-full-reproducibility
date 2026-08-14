#!/usr/bin/env python3
"""Read-only live verifier for Phase 1C results; optionally record closure."""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import re
import sys

from auditlib import (
    BASELINE_ORDER,
    CONTRACT_FREEZE_SHA256,
    POSTHOC_CONTRACT_SHA256,
    SUCCESS_STATUS,
    load_config,
    sha256_file,
    verify_contract_freeze,
    verify_sources,
    verify_upstream_audit_dependencies,
)
from independent_verify import execute as independent_execute


def gate(identifier: str, description: str, passed: bool) -> dict[str, str]:
    return {
        "gate": identifier,
        "description": description,
        "status": "PASS" if passed else "FAIL",
    }


def read_json(path: pathlib.Path) -> dict:
    def reject_nonfinite(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_nonfinite,
    )


def manifest_target_hashes(project: pathlib.Path) -> dict[str, str]:
    manifest = project / "MANIFEST.tsv"
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    hashes: dict[str, str] = {}
    for row in rows:
        path = project / row["path"]
        if path.is_file():
            hashes[row["path"]] = sha256_file(path)
    return hashes


def verify(
    project: pathlib.Path,
    h0dn: pathlib.Path,
    pantheonplus: pathlib.Path,
    phase1a_archive: pathlib.Path,
    phase1b_archive: pathlib.Path,
) -> dict:
    config = load_config(project)
    results = project / "results"
    gates: list[dict[str, str]] = []
    manifest_hashes_before = manifest_target_hashes(project)

    contract = verify_contract_freeze(project)
    gates.append(
        gate(
            "GATE-P1C-01",
            "active contract-02 freeze and chronology",
            contract["status"] == "PASS"
            and contract["contract_freeze_sha256"]
            == CONTRACT_FREEZE_SHA256,
        )
    )

    hold = read_json(project / "provenance" / "PREEXECUTION_SCHEMA_HOLD.json")
    retired = project / "provenance" / "RETIRED_CONTRACT_FREEZE_01.json"
    gates.append(
        gate(
            "GATE-P1C-02",
            "preserved contract-01 pre-execution schema HOLD",
            hold["new_contrast_chi2_values_observed"] is False
            and hold["new_sensitivity_classification_observed"] is False
            and retired.is_file()
            and hold["contract_01_freeze_sha256"]
            == "0d6a767c116d8c7ae17fc4c89234ff4d76a1aa894cf1b0bd78300c9b64490964",
        )
    )

    source = verify_sources(
        project, {"h0dn": h0dn, "pantheonplus": pantheonplus}
    )
    gates.append(
        gate(
            "GATE-P1C-03",
            "two commits and thirteen source-lock files",
            source["status"] == "PASS"
            and sum(
                item["locked_file_count"]
                for item in source["repositories"].values()
            )
            == 13,
        )
    )

    upstream = verify_upstream_audit_dependencies(
        project,
        {
            "phase1a": phase1a_archive,
            "phase1b": phase1b_archive,
        },
    )
    recorded_upstream = read_json(
        results / "upstream_audit_dependency_verification.json"
    )
    gates.append(
        gate(
            "GATE-P1C-03A",
            "canonical Phase 1A and Phase 1B ZIP SHA-256, sidecar, and CRC",
            upstream["status"] == "PASS"
            and recorded_upstream == upstream
            and upstream["dependencies"]["phase1a"][
                "expected_archive_sha256"
            ]
            == "38bb6e55c66ec3442e465cfe4367c1b75e5ecb369933df6de71b75c6182e8333",
        )
    )

    mapping = read_json(results / "dependency_mapping_verification.json")
    gates.append(
        gate(
            "GATE-P1C-04",
            "277 ordered one-to-one mapping rows",
            mapping["status"] == "PASS"
            and mapping["row_count"] == 277
            and mapping["unique_official_target_count"] == 277,
        )
    )

    inventory = read_json(results / "input_inventory.json")
    gates.append(
        gate(
            "GATE-P1C-05",
            "30 groups, 69 rows, 39 cross-survey modes",
            inventory["status"] == "PASS"
            and inventory["multirow_exact_name_group_count"] == 30
            and inventory["rows_in_multirow_groups"] == 69
            and inventory["contrast_degrees_of_freedom"] == 39
            and inventory["all_multirow_groups_cross_survey"] is True,
        )
    )

    schemas = inventory["covariance_schemas"]
    schema_tolerance = float(
        config["tolerances"]["official_transpose_absolute"]
    )
    gates.append(
        gate(
            "GATE-P1C-06",
            "raw covariance dimensions, finiteness, and transpose bound",
            schemas["H0DN"]["dimension"] == 277
            and schemas["H0DN"]["exactly_symmetric"] is True
            and schemas["STAT_SYS"]["dimension"] == 1701
            and schemas["STAT_ONLY"]["dimension"] == 1701
            and schemas["STAT_SYS"][
                "maximum_absolute_transpose_difference"
            ]
            <= schema_tolerance
            and schemas["STAT_ONLY"][
                "maximum_absolute_transpose_difference"
            ]
            <= schema_tolerance,
        )
    )

    lineage = read_json(results / "covariance_lineage.json")
    gates.append(
        gate(
            "GATE-P1C-07",
            "76,729 exact STAT+SYS versus H0DN elements",
            lineage["status"] == "PASS"
            and lineage["compared_element_count"] == 76729
            and lineage["exact_equal_element_count"] == 76729
            and lineage["maximum_absolute_difference"] == 0.0,
        )
    )

    baselines = read_json(results / "covariance_baselines.json")
    gates.append(
        gate(
            "GATE-P1C-08",
            "five positive-definite projected covariance matrices",
            len(baselines) == 5
            and all(
                item["covariance"]["cholesky_success"] is True
                and item["covariance"]["eigenvalue_minimum"]
                > float(
                    config["tolerances"][
                        "projected_covariance_minimum_eigenvalue"
                    ]
                )
                for item in baselines.values()
            ),
        )
    )

    known = read_json(results / "known_phase1a_reproduction.json")
    gates.append(
        gate(
            "GATE-P1C-09",
            "known Phase 1A contrast value",
            known["status"] == "PASS"
            and known["absolute_difference"]
            <= float(
                config["tolerances"]["known_phase1a_chi2_absolute"]
            ),
        )
    )

    numerical = read_json(results / "numerical_crosschecks.json")
    reference_checks = [
        row
        for row in numerical["checks"]
        if row["check"].endswith(":reference_chi2")
    ]
    gates.append(
        gate(
            "GATE-P1C-10",
            "Cholesky and eigendecomposition agreement",
            len(reference_checks) == 5
            and all(row["status"] == "PASS" for row in reference_checks),
        )
    )

    alternative = read_json(results / "alternative_basis_checks.json")
    gates.append(
        gate(
            "GATE-P1C-11",
            "independent null-space basis agreement",
            len(alternative["rows"]) == 5
            and all(
                row["absolute_difference"]
                <= float(
                    config["tolerances"][
                        "alternative_basis_chi2_absolute"
                    ]
                )
                for row in alternative["rows"]
            ),
        )
    )

    invariance = read_json(results / "orthogonal_invariance_summary.json")
    gates.append(
        gate(
            "GATE-P1C-12",
            "32 orthogonal-coordinate trials across five baselines",
            invariance["trial_count"] == 32
            and invariance["comparison_count"] == 160
            and invariance["maximum_absolute_difference"]
            <= float(
                config["tolerances"][
                    "orthogonal_invariance_chi2_absolute"
                ]
            ),
        )
    )

    probability_checks = [
        row
        for row in numerical["checks"]
        if row["check"].endswith(":probability_implementation")
    ]
    gates.append(
        gate(
            "GATE-P1C-13",
            "CDF/gamma agreement, distinct thresholds, and classification",
            len(probability_checks) == 5
            and all(row["status"] == "PASS" for row in probability_checks)
            and read_json(results / "audit_summary.json")[
                "sensitivity_classification"
            ]
            == "LOW_FLAG_PERSISTS_THROUGH_STATONLY"
            and all(
                baselines[name]["low_flag_at_alpha_0_01"] is True
                for name in BASELINE_ORDER
            )
            and abs(
                baselines["PHASE1A_FULL"]["chi2"]
                - 11.209315063602716
            )
            <= 1e-12
            and abs(
                baselines["STAT_SYS_NO_ROWWISE_VELOCITY"]["chi2"]
                - 14.734235950587198
            )
            <= 1e-12
            and abs(
                baselines["STAT_ONLY"]["chi2"]
                - 16.233447508593247
            )
            <= 1e-12
            and abs(
                baselines["PHASE1A_FULL"]["lower_tail_probability"]
                - 3.6795245876638087e-06
            )
            <= 1e-15
            and abs(
                baselines["STAT_SYS_NO_ROWWISE_VELOCITY"][
                    "lower_tail_probability"
                ]
                - 0.00014711328968576817
            )
            <= 1e-15
            and abs(
                baselines["STAT_ONLY"]["lower_tail_probability"]
                - 0.0004856832550848106
            )
            <= 1e-15
            and read_json(results / "audit_summary.json")[
                "classification_thresholds"
            ]["strong_low_dispersion_label_alpha"]
            == 0.001
            and read_json(results / "audit_summary.json")[
                "classification_thresholds"
            ]["ordered_sensitivity_flag_alpha"]
            == 0.01,
        )
    )

    audit_probability = read_json(results / "audit_summary.json")[
        "probability_reference_questions"
    ]
    gates.append(
        gate(
            "GATE-P1C-13A",
            "conditional Beta and marginal chi-square probabilities separated",
            abs(
                audit_probability[
                    "phase1a_conditional_beta_probability"
                ]["value"]
                - 9.368362232281232e-05
            )
            <= 1e-18
            and audit_probability[
                "phase1a_conditional_beta_probability"
            ]["display_value"]
            == 9.3683622e-05
            and abs(
                audit_probability[
                    "phase1c_marginal_chi2_39_lower_tail_probability"
                ]["value"]
                - baselines["PHASE1A_FULL"]["lower_tail_probability"]
            )
            <= 2e-14
            and audit_probability["relationship"]
            == "DISTINCT_REFERENCE_QUESTIONS_NOT_A_NUMERICAL_INCONSISTENCY",
        )
    )

    independent = independent_execute(project, h0dn, pantheonplus)
    gates.append(
        gate(
            "GATE-P1C-14",
            "separate parser/null-space/eigendecomposition verifier",
            independent["status"] == "PASS"
            and independent["classification_match"] is True
            and len(independent["comparisons"]) == 5,
        )
    )

    unit_log = (results / "unit_tests.log").read_text(encoding="utf-8")
    match = re.search(r"Ran (\d+) tests", unit_log)
    gates.append(
        gate(
            "GATE-P1C-15",
            "33 unit and adversarial tests",
            bool(match)
            and int(match.group(1)) == 33
            and unit_log.rstrip().endswith("OK"),
        )
    )

    clean = read_json(results / "clean_reproduction_summary.json")
    gates.append(
        gate(
            "GATE-P1C-16",
            "clean-copy byte identity for 22 main and post-hoc artifacts",
            clean["status"] == "PASS"
            and clean["compared_file_count"] == 22
            and clean["byte_identical_file_count"] == 22,
        )
    )

    audit = read_json(results / "audit_summary.json")
    execution = read_json(results / "EXECUTION_STATUS.json")
    internal_status = (
        audit["status"] == SUCCESS_STATUS
        and execution["status"] == SUCCESS_STATUS
        and numerical["status"] == "PASS"
        and numerical["check_count"] == 27
        and numerical["pass_count"] == 27
    )
    gates.append(
        gate(
            "GATE-P1C-17",
            "formal status and 27 internal numerical checks",
            internal_status,
        )
    )

    required_docs = (
        "README.md",
        "AUDIT_CONTRACT.md",
        "REPORT.md",
        "REPORT_JA.md",
        "REPRODUCIBILITY.md",
        "PACKAGE_VALIDATION.md",
        "AI_ASSISTANCE_DISCLOSURE.md",
        "THIRD_PARTY_NOTICES.md",
        "CITATION.cff",
        "LICENSE",
        "VERSION",
        "DELIVERY_ID.md",
        "POSTHOC_PRECISION_AND_ASYMMETRY_DIAGNOSTIC_CONTRACT.md",
        "POSTHOC_PRECISION_AND_ASYMMETRY_DIAGNOSTIC_CONTRACT.sha256",
    )
    gates.append(
        gate(
            "GATE-P1C-18",
            "required documentation and explicit boundary marker",
            all((project / path).is_file() for path in required_docs)
            and "CALIBRATION_DIAGNOSTIC_ONLY_NO_COVARIANCE_RESCALE"
            in (project / "DELIVERY_ID.md").read_text(encoding="utf-8"),
        )
    )

    posthoc = read_json(
        results / "printed_vs_high_precision_contrast_diagnostic.json"
    )
    gates.append(
        gate(
            "GATE-P1C-19",
            "frozen high-precision diagnostic uses the same mapping and basis",
            posthoc["contract_sha256"] == POSTHOC_CONTRACT_SHA256
            and posthoc["status"] == "POSTHOC_DIAGNOSTIC_COMPLETE"
            and posthoc["mapping_row_count"] == 277
            and posthoc["contrast_basis_shape"] == [39, 277]
            and posthoc["same_mapping_and_basis"] is True
            and posthoc["main_result_invariance"][
                "protected_artifacts_byte_unchanged"
            ]
            is True
            and posthoc["main_result_invariance"][
                "protected_artifact_count"
            ]
            == 18
            and all(
                posthoc["ordered_baseline_comparisons"][name][
                    "printed_main_result_reproduction_status"
                ]
                == "PASS"
                for name in BASELINE_ORDER
            ),
        )
    )

    vector_diagnostics = posthoc["vectors"]
    gates.append(
        gate(
            "GATE-P1C-20",
            "high-precision contrast outputs are finite and post-hoc only",
            math.isfinite(
                vector_diagnostics[
                    "maximum_absolute_contrast_difference"
                ]
            )
            and math.isfinite(
                vector_diagnostics["euclidean_norm_contrast_difference"]
            )
            and posthoc["promotion_status"]
            == "POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE"
            and posthoc["probability_reference_questions"]
            == audit_probability,
        )
    )

    asymmetry = read_json(
        results / "mapped_submatrix_asymmetry_diagnostic.json"
    )
    sensitivity_path = (
        results / "mapped_submatrix_asymmetry_sensitivity.tsv"
    )
    with sensitivity_path.open("r", encoding="utf-8", newline="") as handle:
        sensitivity_rows = list(csv.DictReader(handle, delimiter="\t"))
    expected_sensitivity_rows = 0
    asymmetry_valid = True
    for source_name, applicable_count in (("STAT_SYS", 2), ("STAT_ONLY", 1)):
        row = asymmetry["sources"][source_name]
        raw = row["raw_selected_submatrix"]
        triggered = row["sensitivity_triggered"]
        asymmetry_valid = (
            asymmetry_valid
            and raw["asymmetric_offdiagonal_element_count"]
            == 2 * raw["asymmetric_offdiagonal_pair_count"]
            and triggered
            == (raw["asymmetric_offdiagonal_pair_count"] > 0)
            and (
                raw["maximum_location"] is not None
                if triggered
                else raw["maximum_location"] is None
            )
        )
        if triggered:
            expected_sensitivity_rows += 3 * applicable_count
            asymmetry_valid = (
                asymmetry_valid
                and len(row["representations"]) == applicable_count
                and all(
                    set(representations)
                    == {
                        "SYMMETRIC_AVERAGE",
                        "UPPER_TRIANGLE_MIRRORED",
                        "LOWER_TRIANGLE_MIRRORED",
                    }
                    for representations in row["representations"].values()
                )
            )
        elif row["full_1701_source_schema"]["asymmetric_element_count"] > 0:
            asymmetry_valid = (
                asymmetry_valid
                and row["interpretive_statement"]
                == "FULL_1701_ASYMMETRY_LIES_OUTSIDE_SELECTED_MAPPING"
            )
    sensitivity_numeric_fields = (
        "chi2",
        "lower_tail_probability",
        "q_over_df",
        "delta_chi2_from_symmetric_average",
        "delta_probability_from_symmetric_average",
    )
    sensitivity_finite = all(
        all(math.isfinite(float(row[field])) for field in sensitivity_numeric_fields)
        for row in sensitivity_rows
    )
    gates.append(
        gate(
            "GATE-P1C-21",
            "selected 277x277 asymmetry and upper/lower/symmetric sensitivity",
            asymmetry["contract_sha256"] == POSTHOC_CONTRACT_SHA256
            and asymmetry["mapping_row_count"] == 277
            and asymmetry["comparison_tolerance_absolute"] == 0.0
            and asymmetry_valid
            and len(sensitivity_rows) == expected_sensitivity_rows
            and sensitivity_finite,
        )
    )

    manifest_hashes_after = manifest_target_hashes(project)
    gates.append(
        gate(
            "GATE-P1C-22",
            "verify_results is read-only for every existing manifest target",
            manifest_hashes_before == manifest_hashes_after,
        )
    )

    passed = sum(row["status"] == "PASS" for row in gates)
    return {
        "verification_scope": "pre_manifest_scientific_and_package_closure",
        "gate_count": len(gates),
        "pass_count": passed,
        "gates": gates,
        "read_only_manifest_target_count": len(manifest_hashes_before),
        "closure_disposition": (
            "ACCEPT_COMPLETE_WITH_SCOPE"
            if passed == len(gates)
            else "HOLD"
        ),
        "manifest_and_archive_checks": (
            "performed externally after the manifested tree is fixed"
        ),
        "status": "PASS" if passed == len(gates) else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--phase1a-archive", type=pathlib.Path, required=True)
    parser.add_argument("--phase1b-archive", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        summary = verify(
            project,
            args.h0dn.resolve(),
            args.pantheonplus.resolve(),
            args.phase1a_archive.resolve(),
            args.phase1b_archive.resolve(),
        )
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
