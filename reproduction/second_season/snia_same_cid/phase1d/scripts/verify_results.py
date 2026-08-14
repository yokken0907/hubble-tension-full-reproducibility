#!/usr/bin/env python3
"""Read-only closure checks for the corrected Phase 1D package."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

import auditlib


READER_DOCUMENTS = (
    "README.md",
    "REPORT.md",
    "REPORT_JA.md",
    "REPRODUCIBILITY.md",
    "PACKAGE_VALIDATION.md",
    "DELIVERY_ID.md",
    "CHANGELOG.md",
    "results/README.md",
)


def strict_json(path: pathlib.Path) -> Any:
    """Load UTF-8 JSON while rejecting non-finite JSON extensions."""

    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON token {token} in {path}")
        ),
    )


def load_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or ())
        if not fields or len(fields) != len(set(fields)):
            raise ValueError(f"invalid or duplicate TSV header in {path}")
        rows = list(reader)
        if any(None in row for row in rows):
            raise ValueError(f"ragged TSV row in {path}")
        return rows


def tree_snapshot(project: pathlib.Path) -> dict[str, str]:
    """Return path-keyed hashes without following package symlinks."""

    snapshot: dict[str, str] = {}
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project).as_posix()
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            snapshot[relative] = "SYMLINK:" + str(path.readlink())
        elif path.is_file():
            snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def snapshot_digest(snapshot: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, value in sorted(snapshot.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii", errors="strict"))
        digest.update(b"\0")
    return digest.hexdigest()


def amendment_is_exact(project: pathlib.Path) -> bool:
    rows = load_tsv(project / "provenance" / "CONTRACT_AMENDMENTS.tsv")
    if len(rows) != 1:
        return False
    row = rows[0]
    return (
        row["amendment_id"] == "AMEND-001"
        and row["new_results_observed"] == "YES"
        and row["interpretation_affected"] == "YES"
        and row["reason"]
        == "Post-result clarification of lineage terminology and evidence level"
        and "SURVEY_CROSSWALK_EVIDENCE.tsv" in row["changed_file"]
    )


def all_json_and_tsv_are_strict(project: pathlib.Path) -> tuple[bool, bool]:
    json_ok = True
    tsv_ok = True
    for path in sorted(project.rglob("*.json")):
        if "__pycache__" in path.parts:
            continue
        try:
            strict_json(path)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            json_ok = False
    for path in sorted(project.rglob("*.tsv")):
        try:
            load_tsv(path)
        except (OSError, UnicodeError, ValueError, csv.Error):
            tsv_ok = False
    return json_ok, tsv_ok


def evaluate(project: pathlib.Path) -> dict[str, Any]:
    """Evaluate closure without writing any package file."""

    results = project / "results"
    summary = strict_json(results / "audit_summary.json")
    execution = strict_json(results / "EXECUTION_STATUS.json")
    second = strict_json(results / "independent_verification.json")
    posthoc = strict_json(results / "posthoc_cid_only_crosswalk_summary.json")
    posthoc_second = strict_json(
        results
        / "posthoc_cid_only_crosswalk_independent_verification.json"
    )
    clean = strict_json(results / "clean_reproduction_summary.json")
    rows = load_tsv(results / "row_lineage.tsv")
    candidates = load_tsv(results / "candidate_file_evidence.tsv")
    groups = load_tsv(results / "group_lineage.tsv")
    pairs = load_tsv(results / "pair_observation_overlap.tsv")
    anchors = load_tsv(results / "pipeline_anchor_evidence.tsv")
    assets = load_tsv(results / "referenced_asset_availability.tsv")
    dependencies = load_tsv(results / "shared_dependency_ledger.tsv")
    crosswalk = load_tsv(
        project / "provenance" / "SURVEY_CROSSWALK_EVIDENCE.tsv"
    )
    correction = strict_json(
        project / "provenance" / "CORRECTION_CONFIG.json"
    )
    posthoc_rows = load_tsv(
        results / "posthoc_cid_only_crosswalk_diagnostic.tsv"
    )
    posthoc_candidates = load_tsv(
        results / "posthoc_cid_only_candidate_files.tsv"
    )

    checks: dict[str, bool] = {}
    checks["frozen_contract_and_prefix"] = (
        auditlib.verify_contract_freeze(project)["status"] == "PASS"
    )
    checks["amend_001_recorded"] = amendment_is_exact(project)
    checks["correction_configuration"] = (
        correction.get("amendment_id") == "AMEND-001"
        and correction.get("contract_id") == auditlib.CONTRACT_ID
        and correction.get("direct_final_measurement_ancestry")
        == auditlib.DIRECT_FINAL_MEASUREMENT_ANCESTRY
    )
    checks["source_verification"] = (
        strict_json(results / "source_verification.json")["status"]
        == "PASS"
    )
    checks["formal_status_unchanged"] = (
        summary["status"] == auditlib.SUCCESS_STATUS
        and execution["status"] == auditlib.SUCCESS_STATUS
    )
    checks["release_classification_unchanged"] = (
        summary["release_sufficiency_classification"]
        == "PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE"
        and execution["release_sufficiency_classification"]
        == "PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE"
    )
    checks["population_30_groups_69_rows"] = (
        summary["population"]["same_cid_group_count"] == 30
        and summary["population"]["same_cid_row_count"] == 69
        and len(rows) == 69
        and len(groups) == 30
    )
    checks["legacy_row_counts_38_and_31"] = (
        summary["row_lineage"]["classification_counts"]
        == {
            "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE": 31,
            "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE": 38,
        }
        and len(candidates) == 38
    )
    checks["row_interpretation_aliases"] = all(
        row["lineage_status_legacy"] == row["lineage_status"]
        and row["lineage_status_interpretation"]
        == auditlib.ROW_STATUS_INTERPRETATIONS[row["lineage_status"]]
        and row["evidence_level"]
        == auditlib.INPUT_CANDIDATE_EVIDENCE_LEVEL
        and row["direct_final_measurement_ancestry"]
        == auditlib.DIRECT_FINAL_MEASUREMENT_ANCESTRY
        for row in rows
    )
    checks["candidate_evidence_boundary"] = all(
        row["evidence_level"] == auditlib.INPUT_CANDIDATE_EVIDENCE_LEVEL
        and row["direct_final_measurement_ancestry"]
        == auditlib.DIRECT_FINAL_MEASUREMENT_ANCESTRY
        for row in candidates
    )
    checks["legacy_group_counts_3_and_27"] = (
        summary["group_lineage"]["classification_counts"]
        == {
            "ALL_ROWS_UNIQUE_DISTINCT_PUBLIC_PHOTOMETRY_FILES": 3,
            "PUBLIC_PHOTOMETRY_LINEAGE_UNRESOLVED": 27,
        }
    )
    checks["group_interpretation_aliases"] = all(
        row["group_lineage_classification_legacy"]
        == row["group_lineage_classification"]
        and row["group_lineage_interpretation"]
        == auditlib.GROUP_STATUS_INTERPRETATIONS[
            row["group_lineage_classification"]
        ]
        and row["unique_compatible_candidate_row_count"]
        == row["unique_resolved_row_count"]
        and row["distinct_compatible_candidate_sha256_count"]
        == row["distinct_resolved_file_sha256_count"]
        and row["compatible_candidate_pair_count"]
        == row["resolved_pair_count"]
        and row["evidence_level"]
        == auditlib.INPUT_CANDIDATE_EVIDENCE_LEVEL
        and row["direct_final_measurement_ancestry"]
        == auditlib.DIRECT_FINAL_MEASUREMENT_ANCESTRY
        for row in groups
    )
    checks["pair_counts_10_of_48_and_zero_overlap"] = (
        len(pairs) == 48
        and summary["group_lineage"]["resolved_pair_count"] == 10
        and summary["group_lineage"][
            "pairs_with_byte_identical_observation_lines"
        ]
        == 0
        and all(
            row["evidence_level"]
            == auditlib.INPUT_CANDIDATE_EVIDENCE_LEVEL
            and row["direct_final_measurement_ancestry"]
            == auditlib.DIRECT_FINAL_MEASUREMENT_ANCESTRY
            for row in pairs
        )
    )
    checks["fully_covered_group_ids"] = {
        row["CID"]
        for row in groups
        if row["group_lineage_classification"]
        == "ALL_ROWS_UNIQUE_DISTINCT_PUBLIC_PHOTOMETRY_FILES"
    } == {"2009cz", "2005iq", "2005hc"}
    checks["photometry_scan_847_zero_failures"] = (
        summary["photometry_scan"]
        == {
            "active_file_count": 847,
            "configured_directory_count": 7,
            "parse_failure_count": 0,
        }
    )
    checks["configuration_level_pipeline_anchors"] = (
        len(anchors) == 12
        and all(row["status"] == "PASS" for row in anchors)
        and all(
            row["evidence_level"] == auditlib.CONFIGURATION_EVIDENCE_LEVEL
            and row["executed_run_to_final_catalog_lineage"]
            == "NOT_ESTABLISHED"
            for row in anchors
        )
        and summary["shared_pipeline"]["anchor_pass_count"] == 12
        and summary["shared_pipeline"]["boundary_markers"]
        == [
            auditlib.CONFIGURATION_BOUNDARY_MARKER,
            auditlib.EXECUTED_RUN_BOUNDARY_MARKER,
        ]
    )
    checks["shared_dependency_boundaries"] = (
        len(dependencies) == 4
        and any(
            row["layer"] == "COMMON_LIGHT_CURVE_AND_BIASCOR_PIPELINE"
            and row["evidence_level"] == "CONFIGURATION_LEVEL"
            and row["executed_run_to_final_catalog_lineage"]
            == "NOT_ESTABLISHED"
            and auditlib.CONFIGURATION_BOUNDARY_MARKER
            in row["boundary_marker"]
            and auditlib.EXECUTED_RUN_BOUNDARY_MARKER
            in row["boundary_marker"]
            for row in dependencies
        )
    )
    checks["referenced_assets_frozen_release_boundary"] = (
        len(assets) == 3
        and all(
            row["availability_status"]
            == "REFERENCED_NOT_TRACKED_IN_FROZEN_RELEASE"
            and row["evidence_level"] == "REPOSITORY_TRACKING_CHECK"
            and row["original_analysis_asset_existence"]
            == "NOT_DETERMINED"
            for row in assets
        )
        and summary["referenced_assets"]["required_asset_present_count"] == 0
    )
    expected_crosswalk = correction[
        "crosswalk_evidence_classification_by_IDSURVEY"
    ]
    checks["survey_crosswalk_evidence_register"] = (
        len(crosswalk) == 8
        and {row["IDSURVEY"] for row in crosswalk} == set(expected_crosswalk)
        and all(
            row["evidence_classification"]
            == expected_crosswalk[row["IDSURVEY"]]
            and row["posthoc_candidate_promoted"] == "NO"
            and row["evidence_source"]
            and row["evidence_path_or_reference"]
            and row["evidence_git_blob_or_version"]
            and re.fullmatch(r"[0-9a-f]{64}", row["evidence_excerpt_sha256"])
            for row in crosswalk
        )
        and {
            row["IDSURVEY"]
            for row in crosswalk
            if row["evidence_classification"] == "UNRESOLVED_BRIDGE"
        }
        == {"51", "57", "65"}
    )
    checks["second_implementation_main_15_of_15"] = (
        second["status"] == "PASS"
        and second["check_count"] == second["pass_count"] == 15
        and second["verification_type"]
        == "SECOND_IMPLEMENTATION_CROSS_CHECK"
        and second["independent_external_replication"] == "NO"
        and second["peer_review_or_expert_endorsement"] == "NO"
    )
    checks["posthoc_scope_and_main_protection"] = (
        posthoc["status"] == "POSTHOC_DIAGNOSTIC_COMPLETE"
        and posthoc["promotion_status"]
        == "POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE"
        and posthoc["all_protected_main_results_byte_unchanged"] is True
    )
    checks["posthoc_counts_31_and_73"] = (
        len(posthoc_rows) == posthoc["unresolved_main_row_count"] == 31
        and len(posthoc_candidates)
        == posthoc["cid_only_candidate_ledger_row_count"]
        == 73
        and posthoc["classification_counts"]
        == {"MULTIPLE_CID_ONLY_PUBLIC_FILES_OUTSIDE_FROZEN_CROSSWALK": 31}
    )
    checks["posthoc_survey_localization"] = (
        posthoc["by_IDSURVEY"]["51"]["row_count"] == 7
        and posthoc["by_IDSURVEY"]["51"]["cid_only_candidate_count"] == 16
        and posthoc["by_IDSURVEY"]["57"]["row_count"] == 16
        and posthoc["by_IDSURVEY"]["57"]["cid_only_candidate_count"] == 39
        and posthoc["by_IDSURVEY"]["65"]["row_count"] == 8
        and posthoc["by_IDSURVEY"]["65"]["cid_only_candidate_count"] == 18
        and posthoc["survey_def"]["availability_status"]
        == "NOT_TRACKED_IN_FROZEN_RELEASE"
    )
    checks["second_implementation_posthoc_9_of_9"] = (
        posthoc_second["status"] == "PASS"
        and posthoc_second["check_count"]
        == posthoc_second["pass_count"]
        == 9
        and posthoc_second["verification_type"]
        == "SECOND_IMPLEMENTATION_CROSS_CHECK"
        and posthoc_second["independent_external_replication"] == "NO"
        and posthoc_second["peer_review_or_expert_endorsement"] == "NO"
    )
    checks["clean_reproduction_19_of_19"] = (
        clean["status"] == "PASS"
        and clean["checked_result_file_count"]
        == clean["byte_identical_file_count"]
        == 19
        and len(clean["checks"]) == 19
        and all(clean["checks"].values())
    )
    unit_log = (results / "unit_tests.log").read_text(encoding="utf-8")
    test_match = re.search(r"Ran (\d+) tests", unit_log)
    checks["unit_and_regression_tests"] = (
        bool(test_match)
        and int(test_match.group(1)) >= 40
        and unit_log.rstrip().endswith("OK")
    )

    required_docs = set(READER_DOCUMENTS) | {
        "AUDIT_CONTRACT.md",
        "POSTHOC_CID_ONLY_CROSSWALK_DIAGNOSTIC_CONTRACT.md",
        "THIRD_PARTY_NOTICES.md",
        "CITATION.cff",
        "AI_ASSISTANCE_DISCLOSURE.md",
        "LICENSE",
        "provenance/CORRECTION_CONFIG.json",
        "provenance/SURVEY_CROSSWALK_EVIDENCE.tsv",
    }
    checks["documentation_complete"] = all(
        (project / name).is_file() for name in required_docs
    )
    reader_text = {
        name: (project / name).read_text(encoding="utf-8")
        for name in READER_DOCUMENTS
    }
    combined_reader_text = "\n".join(reader_text.values())
    checks["reader_documents_state_candidate_boundary"] = all(
        (
            "FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE" in reader_text[name]
            or "凍結クロスウォーク適合入力候補" in reader_text[name]
        )
        and (
            "NOT_ESTABLISHED" in reader_text[name]
            or "確立していない" in reader_text[name]
        )
        for name in ("README.md", "REPORT.md", "REPORT_JA.md")
    )
    checks["reader_documents_state_configuration_boundary"] = all(
        auditlib.CONFIGURATION_BOUNDARY_MARKER in reader_text[name]
        and auditlib.EXECUTED_RUN_BOUNDARY_MARKER in reader_text[name]
        for name in ("README.md", "REPORT.md", "REPORT_JA.md")
    )
    forbidden_reader_phrases = (
        "preregistered",
        "事前登録済み",
        "REFERENCED_NOT_TRACKED_IN_RELEASE",
        "independent verifier passes",
        "独立検証：",
        "外部独立検証",
    )
    checks["reader_documents_avoid_overclaim_language"] = not any(
        phrase in combined_reader_text for phrase in forbidden_reader_phrases
    )
    checks["citation_has_no_internal_release_date"] = (
        "date-released:" not in (project / "CITATION.cff").read_text(
            encoding="utf-8"
        )
    )
    ai_text = (project / "AI_ASSISTANCE_DISCLOSURE.md").read_text(
        encoding="utf-8"
    )
    checks["ai_assistance_and_human_responsibility_disclosed"] = (
        "ChatGPT" in ai_text
        and "Work environment" in ai_text
        and "Keiji Yoshimura" in ai_text
        and "retains responsibility" in ai_text
        and "not an independent external replication" in ai_text
    )
    strict_json_ok, strict_tsv_ok = all_json_and_tsv_are_strict(project)
    checks["strict_json_no_nonfinite_values"] = strict_json_ok
    checks["strict_tsv_utf8_and_rectangular"] = strict_tsv_ok

    python_files = sorted(
        list((project / "scripts").glob("*.py"))
        + list((project / "tests").glob("*.py"))
    )
    try:
        for path in python_files:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        syntax_pass = True
    except SyntaxError:
        syntax_pass = False
    checks["python_syntax"] = syntax_pass and len(python_files) >= 12

    package_paths = [
        path
        for path in project.rglob("*")
        if "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    ]
    package_files = [path for path in package_paths if path.is_file()]
    checks["no_symlinks"] = not any(path.is_symlink() for path in package_paths)
    scratch_root_marker = b"/" + b"workspace" + b"/"
    session_marker = b"e688ee" + b"23bbb8"
    checks["no_workspace_path_leak"] = not any(
        scratch_root_marker in path.read_bytes()
        or session_marker in path.read_bytes()
        for path in package_files
    )
    checks["no_upstream_source_tree_redistribution"] = not any(
        "sources" in path.relative_to(project).parts
        or path.suffix.lower() in {".cov", ".fitres"}
        for path in package_files
    )

    return {
        "audit_id": auditlib.CONTRACT_ID,
        "check_count": len(checks),
        "pass_count": sum(checks.values()),
        "checks": checks,
        "closure": (
            "ACCEPT_COMPLETE_WITH_SCOPE"
            if all(checks.values())
            else "HOLD_VERIFICATION_FAILURE"
        ),
        "release_sufficiency_classification": summary[
            "release_sufficiency_classification"
        ],
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_scope": "INTERNAL_READ_ONLY_CLOSURE",
    }


def run_read_only(project: pathlib.Path) -> dict[str, Any]:
    """Run the verifier and prove that this invocation changed no tree byte."""

    before = tree_snapshot(project)
    result = evaluate(project)
    after = tree_snapshot(project)
    result["checks"]["default_verifier_tree_byte_unchanged"] = before == after
    result["check_count"] = len(result["checks"])
    result["pass_count"] = sum(result["checks"].values())
    result["closure"] = (
        "ACCEPT_COMPLETE_WITH_SCOPE"
        if all(result["checks"].values())
        else "HOLD_VERIFICATION_FAILURE"
    )
    result["read_only_verifier"] = before == after
    result["tree_snapshot_sha256_before"] = snapshot_digest(before)
    result["tree_snapshot_sha256_after"] = snapshot_digest(after)
    result["status"] = "PASS" if all(result["checks"].values()) else "FAIL"
    return result


def main() -> int:
    project = pathlib.Path(__file__).resolve().parents[1]
    result = run_read_only(project)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
