#!/usr/bin/env python3
"""Read-only scientific and reproducibility verifier for Phase 1F."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import sys
from collections import Counter

from auditlib import CONTRACT_FREEZE_SHA256, verify_contract, verify_sources


EXPECTED_STATUS = "AUDIT_COMPLETE_PUBLIC_INPUT_DEPENDENCY_CLASSIFIED"
EXPECTED_SCIENCE = (
    "PUBLIC_INPUT_DEPENDENCIES_CLASSIFIED_REPEATED_PAYLOAD_PAIRS_0_OF_48_"
    "SINGLE_PAYLOAD_PAIRS_4_OF_48_FILTER_RECORDS_MAPPED_434_OF_434_"
    "CONFIG_SERIES_PASS_7_OF_7"
)
EXPECTED_RELEASE = (
    "PUBLIC_RELEASE_SUPPORTS_BOUNDED_INPUT_DEPENDENCY_CLASSIFICATION_"
    "EXECUTED_RUN_TO_FINAL_CATALOG_LINEAGE_NOT_ESTABLISHED"
)
EXPECTED_POSTHOC_FREEZE = "27f49229cafb42d3252bc57dd932e5c865fa37c65b65e779827e5e61962d6bc6"


def read_json(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def tsv_fields(path: pathlib.Path) -> tuple[str, ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle, delimiter="\t").fieldnames or ())


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    results = project / "results"
    provenance = project / "provenance"

    summary = read_json(results / "audit_summary.json")
    execution = read_json(results / "EXECUTION_STATUS.json")
    inventory = read_json(results / "input_inventory.json")
    contract_freeze = read_json(provenance / "CONTRACT_FREEZE.json")
    posthoc_freeze = read_json(provenance / "POSTHOC_PAYLOAD_COLLISION_NEGATIVE_CONTROL_FREEZE.json")
    upstream = read_json(provenance / "UPSTREAM_AUDIT_DEPENDENCIES.json")
    pairs = read_tsv(results / "pair_dependency_classification.tsv")
    matches = read_tsv(results / "observation_match_evidence.tsv")
    candidates = read_tsv(results / "input_candidate_map.tsv")
    profiles = read_tsv(results / "row_input_profile.tsv")
    filters = read_tsv(results / "filter_calibration_mapping.tsv")
    series = read_tsv(results / "series_configuration_lineage.tsv")
    assets = read_tsv(results / "public_asset_availability.tsv")
    dependencies = read_tsv(results / "shared_dependency_ledger.tsv")
    posthoc = read_json(results / "posthoc_cross_cid_negative_control_summary.json")
    control_pairs = read_tsv(results / "posthoc_cross_cid_negative_control_pairs.tsv")
    control_strata = read_tsv(results / "posthoc_cross_cid_negative_control_by_directory_pair.tsv")
    independent = read_json(results / "independent_verification.json")
    tests = read_json(results / "unit_tests_summary.json")
    clean = read_json(results / "clean_reproduction_summary.json")
    corrections = read_tsv(provenance / "IMPLEMENTATION_CORRECTIONS.tsv")

    checks: list[dict[str, object]] = []

    def json_safe(value: object) -> object:
        if isinstance(value, set):
            converted = [json_safe(item) for item in value]
            return sorted(converted, key=lambda item: json.dumps(item, sort_keys=True))
        if isinstance(value, tuple):
            return [json_safe(item) for item in value]
        if isinstance(value, list):
            return [json_safe(item) for item in value]
        if isinstance(value, dict):
            return {str(key): json_safe(item) for key, item in value.items()}
        return value

    def check(name: str, actual: object, expected: object) -> None:
        checks.append({
            "name": name,
            "actual": json_safe(actual),
            "expected": json_safe(expected),
            "status": "PASS" if actual == expected else "FAIL",
        })

    contract_result = verify_contract(project)
    source_result = verify_sources(project, args.pantheonplus.resolve())
    check("contract_verification_status", contract_result["status"], "PASS")
    check("contract_freeze_sha256", sha(provenance / "CONTRACT_FREEZE.json"), CONTRACT_FREEZE_SHA256)
    check("contract_sidecar", (provenance / "CONTRACT_FREEZE.sha256").read_text(encoding="utf-8"), f"{CONTRACT_FREEZE_SHA256}  CONTRACT_FREEZE.json\n")
    check("contract_complete_pair_scan_preobserved", contract_freeze["complete_48_pair_scan_observed_before_freeze"], False)
    check("contract_complete_profile_preobserved", contract_freeze["complete_69_candidate_profile_observed_before_freeze"], False)
    check("contract_limited_exposure_disclosed", contract_freeze["limited_examples_and_upstream_results_disclosed"], True)
    check("source_verification_status", source_result["status"], "PASS")
    check("source_lock_count", source_result["source_lock_row_count"], 45)
    check("tree_lock_count", source_result["tree_lock_row_count"], 20)
    check("source_repository_checks", all(source_result["repository_checks"].values()), True)
    check("upstream_phase1d_archive_sha256", upstream["phase1d"]["actual_sha256"], "6792886b8f1a8ac6397e6305931bfc750fdf1f1211c5e92b1f07ea1e7f0609bd")
    check("upstream_phase1e_archive_sha256", upstream["phase1e"]["actual_sha256"], "0c86bd916e5b54f3e97b810b868c793e2fdd564abd94d4f1687fb4f632f73ed3")
    check("upstream_raw_bytes_redistributed", upstream["raw_upstream_bytes_redistributed"], False)

    check("execution_status", execution["status"], EXPECTED_STATUS)
    check("execution_scientific_classification", execution["scientific_classification"], EXPECTED_SCIENCE)
    check("execution_release_classification", execution["public_release_classification"], EXPECTED_RELEASE)
    check("summary_status", summary["status"], EXPECTED_STATUS)
    check("summary_scientific_classification", summary["scientific_classification"], EXPECTED_SCIENCE)
    check("summary_release_classification", summary["public_release_classification"], EXPECTED_RELEASE)
    check("summary_partially_result_blind", summary["result_blindness"], "PARTIALLY_RESULT_BLIND_LIMITED_EXAMPLES_AND_UPSTREAM_RESULTS_DISCLOSED")
    check("phase1d_main_unchanged", summary["upstream_preservation"]["phase1d_main_result_changed"], False)
    check("phase1e_main_unchanged", summary["upstream_preservation"]["phase1e_main_result_changed"], False)

    check("candidate_row_count", len(candidates), 69)
    check("candidate_inventory_count", inventory["candidate_row_count"], 69)
    check("same_CID_group_count", inventory["same_CID_group_count"], 30)
    check("within_group_pair_count", inventory["within_group_pair_count"], 48)
    check("phase1d_candidate_count", sum(row["candidate_source_phase"] == "PHASE1D_ACCEPTED_CORRECTED" for row in candidates), 38)
    check("phase1e_candidate_count", sum(row["candidate_source_phase"] == "PHASE1E_ACCEPTED_CORRECTED" for row in candidates), 31)
    check("distinct_candidate_paths", len({row["candidate_path"] for row in candidates}), 69)
    check("candidate_labels_bounded", {row["candidate_evidence_label"] for row in candidates}, {"FROZEN_PUBLIC_INPUT_CANDIDATE_NOT_FINAL_MEASUREMENT_ANCESTRY"})
    check("candidate_final_ancestry_unestablished", {row["direct_final_measurement_ancestry"] for row in candidates}, {"NOT_ESTABLISHED"})
    check("profile_row_count", len(profiles), 69)
    check("profile_distinct_blob_count", len({row["git_blob_sha1"] for row in profiles}), 69)
    check("profile_observation_count", sum(int(row["observation_count"]) for row in profiles), 6744)
    check("candidate_series_present_count", len({row["source_directory"] for row in profiles}), 6)

    pair_classes = Counter(row["primary_pair_classification"] for row in pairs)
    check("pair_row_count", len(pairs), 48)
    check("pair_class_counts", dict(pair_classes), {
        "NO_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD": 44,
        "SINGLE_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD": 4,
    })
    check("byte_exact_positive_pair_count", sum(int(row["byte_exact_observation_row_match_count"]) > 0 for row in pairs), 0)
    check("rounding_compatible_edge_count", sum(int(row["rounding_compatible_edge_count"]) for row in pairs), 4)
    check("mutual_unique_rounding_match_count", sum(int(row["mutual_unique_rounding_compatible_match_count"]) for row in pairs), 4)
    check("ambiguous_rounding_edge_count", sum(int(row["ambiguous_rounding_compatible_edge_count"]) for row in pairs), 0)
    check("repeated_payload_positive_pair_count", sum(row["primary_pair_classification"].startswith("REPEATED_") for row in pairs), 0)
    check("all_pair_exposure_identity_unestablished", {row["physical_exposure_identity"] for row in pairs}, {"NOT_ESTABLISHED"})
    check("all_pair_statistical_independence_unestablished", {row["statistical_independence"] for row in pairs}, {"NOT_ESTABLISHED"})
    check("all_pair_final_ancestry_unestablished", {row["direct_final_measurement_ancestry"] for row in pairs}, {"NOT_ESTABLISHED"})
    check("match_evidence_count", len(matches), 4)
    check("matched_CIDs", {row["CID"] for row in matches}, {"2004as", "2005hc", "2007co", "2007qe"})
    check("matched_row_pairs", {(row["h0dn_row_a_1based"], row["h0dn_row_b_1based"]) for row in matches}, {("109", "110"), ("172", "173"), ("50", "52"), ("5", "6")})
    check("match_within_0p11_day_count", sum(row["absolute_mjd_delta_le_0p11_day"] == "YES" for row in matches), 1)
    check("match_within_0p11_day_CID", {row["CID"] for row in matches if row["absolute_mjd_delta_le_0p11_day"] == "YES"}, {"2007qe"})
    check("match_mjd_interval_overlap_count", sum(row["mjd_rounding_intervals_overlap"] == "YES" for row in matches), 0)
    check("match_equal_filter_count", sum(row["exact_filter_token_equal"] == "YES" for row in matches), 0)
    check("match_same_transmission_count", sum(row["same_public_transmission_blob"] == "YES" for row in matches), 0)
    check("match_same_kcor_definition_count", sum(row["same_kcor_filter_definition"] == "YES" for row in matches), 0)
    check("match_evidence_boundary", {row["evidence_boundary"] for row in matches}, {"PUBLISHED_NUMERIC_PAYLOAD_REUSE_OR_AGREEMENT_NOT_PHYSICAL_EXPOSURE_IDENTITY"})

    check("filter_mapping_row_count", len(filters), 434)
    check("filter_mapping_classes", {row["mapping_classification"] for row in filters}, {"PUBLIC_KCOR_TEXT_AND_TRANSMISSION_ASSET_MAPPED"})
    check("filter_mapping_observation_count", sum(int(row["observation_count_for_token"]) for row in filters), 6744)
    check("filter_mapping_kcor_input_count", len({row["kcor_input_path"] for row in filters}), 5)
    check("filter_mapping_transmission_blob_count", len({row["public_transmission_git_blob_sha1"] for row in filters}), 50)
    check("filter_mapping_definition_unique", {row["definition_count"] for row in filters}, {"1"})
    check("filter_executed_run_unestablished", {row["executed_run_lineage"] for row in filters}, {"NOT_ESTABLISHED"})
    check("configuration_series_count", len(series), 7)
    check("configuration_series_pass_count", sum(row["configuration_anchor_status"] == "PASS" for row in series), 7)
    check("configuration_aggregate_membership_count", sum(row["realdata_aggregation_membership"] == "YES" for row in series), 7)
    check("configuration_zero_candidate_series_count", sum(int(row["candidate_row_count"]) == 0 for row in series), 1)
    check("configuration_zero_candidate_series", {row["source_directory"] for row in series if int(row["candidate_row_count"]) == 0}, {"CSP_data2"})
    check("configuration_execution_lineage_unestablished", {row["executed_run_to_final_catalog_lineage"] for row in series}, {"NOT_ESTABLISHED"})

    asset_classes = Counter(row["availability_classification"] for row in assets)
    check("asset_record_count", len(assets), 16)
    check("asset_class_counts", dict(asset_classes), {
        "TRACKED_PUBLIC_BASENAME_CANDIDATE_NO_EXECUTION_IDENTITY": 8,
        "NOT_TRACKED_IN_FIXED_RELEASE_BY_BASENAME": 8,
    })
    check("asset_execution_identity_unestablished", {row["execution_identity"] for row in assets}, {"NOT_ESTABLISHED"})
    check("dependency_ledger_nonempty", len(dependencies) >= 1, True)
    check("dependency_execution_lineage_unestablished", {row["executed_run_to_final_catalog_lineage"] for row in dependencies}, {"NOT_ESTABLISHED"})

    check("posthoc_freeze_sha256", sha(provenance / "POSTHOC_PAYLOAD_COLLISION_NEGATIVE_CONTROL_FREEZE.json"), EXPECTED_POSTHOC_FREEZE)
    check("posthoc_freeze_sidecar", (provenance / "POSTHOC_PAYLOAD_COLLISION_NEGATIVE_CONTROL_FREEZE.sha256").read_text(encoding="utf-8"), f"{EXPECTED_POSTHOC_FREEZE}  POSTHOC_PAYLOAD_COLLISION_NEGATIVE_CONTROL_FREEZE.json\n")
    check("posthoc_main_observed_before_freeze", posthoc_freeze["main_result_observed_before_freeze"], True)
    check("posthoc_result_observed_before_freeze", posthoc_freeze["negative_control_result_observed_before_freeze"], False)
    check("posthoc_protected_main_hashes", all(
        (project / relative).is_file()
        and (project / relative).stat().st_size == record["bytes"]
        and sha(project / relative) == record["sha256"]
        for relative, record in posthoc_freeze["protected_main_results"].items()
    ), True)
    check("posthoc_status", posthoc["status"], "POSTHOC_NEGATIVE_CONTROL_COMPLETE")
    check("posthoc_chronology", posthoc["chronology"], "DESIGNED_AND_FROZEN_AFTER_MAIN_RESULT")
    check("posthoc_pair_count", len(control_pairs), 1523)
    check("posthoc_opportunity_count", sum(int(row["observation_pair_opportunity_count"]) for row in control_pairs), 14670999)
    check("posthoc_positive_pair_count", sum(row["negative_control_pair_classification"] == "CROSS_CID_POSITIVE" for row in control_pairs), 24)
    check("posthoc_mutual_match_count", sum(int(row["mutual_unique_rounding_compatible_match_count"]) for row in control_pairs), 24)
    check("posthoc_stratum_count", len(control_strata), 11)
    check("posthoc_summary_main_unchanged_before", posthoc["protected_main_results_unchanged_before_diagnostic"], True)
    check("posthoc_summary_main_unchanged_after", posthoc["protected_main_results_unchanged_after_diagnostic"], True)
    check("posthoc_no_pvalue_field", any("pvalue" in field.lower() or "p_value" in field.lower() for field in tsv_fields(results / "posthoc_cross_cid_negative_control_pairs.tsv")), False)
    check("posthoc_descriptive_boundary", posthoc["interpretive_boundary"], "NONEXCHANGEABLE_DESCRIPTIVE_COLLISION_SCREEN_NO_P_VALUE_NO_CAUSAL_INFERENCE_NO_MAIN_RESULT_CHANGE")

    check("independent_verification_status", independent["status"], "PASS")
    check("independent_check_count", independent["check_count"], 31)
    check("independent_pass_count", independent["pass_count"], 31)
    check("independent_scope", independent["verification_type"], "WITHIN_PROJECT_SECOND_IMPLEMENTATION_NOT_EXTERNAL_REPLICATION")
    check("unit_test_status", tests["status"], "PASS")
    check("unit_test_count", tests["test_count"], 50)
    check("unit_test_failures_and_errors", tests["failure_count"] + tests["error_count"], 0)
    test_log_match = re.search(r"Ran (\d+) tests", (results / "unit_tests.log").read_text(encoding="utf-8"))
    check("unit_test_log_count", int(test_log_match.group(1)) if test_log_match else None, 50)
    check("clean_reproduction_status", clean["status"], "PASS")
    check("clean_generated_output_count", clean["generated_output_count"], 20)
    check("clean_byte_identical_count", clean["byte_identical_output_count"], 20)
    check("clean_all_output_records_pass", all(row["status"] == "PASS" for row in clean["outputs"]), True)
    check("clean_all_commands_pass", all(row["status"] == "PASS" and row["returncode"] == 0 for row in clean["commands"]), True)

    check("implementation_correction_count", len(corrections), 1)
    check("implementation_correction_id", corrections[0]["correction_id"], "IMPL-001")
    check("implementation_correction_no_contract_change", corrections[0]["contract_or_scientific_rule_changed"], "NO")
    check("implementation_correction_before_main_result", corrections[0]["main_result_observed_before_correction"], "NO")

    main_table_paths = (
        results / "input_candidate_map.tsv",
        results / "row_input_profile.tsv",
        results / "pair_dependency_classification.tsv",
        results / "observation_match_evidence.tsv",
        results / "filter_calibration_mapping.tsv",
    )
    prohibited_fields = {"h0", "m_b_corr", "mu_sh0es", "residual", "resid", "covariance"}
    check("main_tables_no_prohibited_scientific_fields", any(
        field.lower() in prohibited_fields
        for path in main_table_paths
        for field in tsv_fields(path)
    ), False)

    reader_paths = (project / "README.md", project / "REPORT.md", project / "REPORT_JA.md", results / "README.md")
    reader_text = "\n".join(path.read_text(encoding="utf-8") for path in reader_paths)
    check("reader_docs_exposure_boundary", "not proof of a shared physical exposure" in reader_text, True)
    check("reader_docs_final_ancestry_boundary", "final `m_b_corr`" in reader_text and "未証明" in reader_text, True)
    check("reader_docs_posthoc_chronology", "after the main result" in reader_text and "post-hoc" in reader_text.lower(), True)
    check("reader_docs_no_H0_correction_claim", "corrected H0 =" in reader_text or "修正H0 =" in reader_text, False)
    check("reader_docs_no_tension_resolution_claim", "resolves the Hubble tension" in reader_text or "ハッブルテンションを解決した" in reader_text, False)

    excluded_names = {"MANIFEST.tsv", "SHA256SUMS.txt"}
    packaged_files = [
        path for path in project.rglob("*")
        if path.is_file()
        and path.name not in excluded_names
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    ]
    forbidden_upstream_files = [
        path.relative_to(project).as_posix() for path in packaged_files
        if path.suffix.lower() in {".fits", ".fitres", ".cov"}
        or path.name in {"PPLUS.yml", "Pantheon+SH0ES.dat"}
        or "Pantheon+_Data" in path.parts
    ]
    check("raw_upstream_files_absent", forbidden_upstream_files, [])
    check("packaged_symlink_count", sum(path.is_symlink() for path in project.rglob("*")), 0)
    check("packaged_bytecode_outside_cache_count", sum(
        path.suffix in {".pyc", ".pyo"} and "__pycache__" not in path.parts
        for path in project.rglob("*") if path.is_file()
    ), 0)
    scratch_marker = "/".join(("", "workspace", "scratch")) + "/"
    leaking_paths = [
        path.relative_to(project).as_posix() for path in packaged_files
        if scratch_marker.encode() in path.read_bytes()
    ]
    check("scratch_absolute_path_leak_count", len(leaking_paths), 0)
    check("python_scripts_compile", all(
        compile(path.read_text(encoding="utf-8"), str(path), "exec") is not None
        for path in sorted((project / "scripts").glob("*.py"))
    ), True)

    passed = sum(row["status"] == "PASS" for row in checks)
    result = {
        "status": "PASS" if passed == len(checks) else "FAIL",
        "closure": "ACCEPT_COMPLETE_WITH_SCOPE" if passed == len(checks) else "HOLD",
        "verification_type": "STRICT_READ_ONLY_SCIENTIFIC_AND_REPRODUCIBILITY_CLOSURE",
        "check_count": len(checks),
        "pass_count": passed,
        "checks": checks,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        raise SystemExit(2)
