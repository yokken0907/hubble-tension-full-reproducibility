#!/usr/bin/env python3
"""Strict scientific, dependency, and reproducibility verifier for Phase 1E."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import re
import sys
import zipfile

from auditlib import CONTRACT_FREEZE_SHA256, load_config, verify_contract, verify_sources


FROZEN_CROSSWALK_DIRECTORIES = (
    "CSPDR3_anthony",
    "CSP_data2",
    "SWIFT",
    "LOSS",
    "KAIT_DS15",
    "CfA3_DJ20",
    "PS1_LOWZ_COMBINED_TEXT_DS17",
)
TARGET_DRIVING_FIELDS = (
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "lineage_status",
)
PREFERRED_TARGET_LABEL = "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_PUBLIC_INPUT_CANDIDATE"
EXPECTED_UNIT_TEST_COUNT = 36
EXPECTED_SECOND_IMPLEMENTATION_CHECKS = 24
EXPECTED_CLEAN_RESULT_COUNT = 15


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def tsv_fields(path: pathlib.Path) -> tuple[str, ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle, delimiter="\t").fieldnames or ())


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_target_driving_bytes(rows: list[dict[str, str]]) -> bytes:
    selected = [
        row
        for row in rows
        if row["lineage_status"] == "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
    ]
    selected.sort(key=lambda row: int(row["h0dn_row_1based"]))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=list(TARGET_DRIVING_FIELDS),
        delimiter="\t",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(
        {field: row[field] for field in TARGET_DRIVING_FIELDS}
        for row in selected
    )
    return output.getvalue().encode("utf-8")


def unique_zip_member(handle: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in handle.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"expected one ZIP member ending in {suffix!r}; found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--phase1d-corrected-zip", type=pathlib.Path, required=True)
    parser.add_argument("--phase1d-corrected-sidecar", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    results = project / "results"
    provenance = project / "provenance"
    config = load_config(project)
    summary = json.loads((results / "audit_summary.json").read_text(encoding="utf-8"))
    execution = json.loads((results / "EXECUTION_STATUS.json").read_text(encoding="utf-8"))
    second_implementation = json.loads(
        (results / "independent_verification.json").read_text(encoding="utf-8")
    )
    clean = json.loads((results / "clean_reproduction_summary.json").read_text(encoding="utf-8"))
    semantics = json.loads((results / "status_semantics.json").read_text(encoding="utf-8"))
    supersession = json.loads(
        (provenance / "UPSTREAM_DEPENDENCY_SUPERSESSION.json").read_text(encoding="utf-8")
    )
    crosswalks = read_tsv(results / "inferred_crosswalk.tsv")
    targets = read_tsv(results / "target_row_application.tsv")
    target_files = read_tsv(results / "target_candidate_file_evidence.tsv")
    anchors = read_tsv(results / "holdout_anchor_evidence.tsv")
    holdout = read_tsv(results / "holdout_candidate_rows.tsv")
    label_rows = read_tsv(results / "label_header_diagnostic.tsv")
    phase1b = read_tsv(provenance / "PHASE1B_ROW_MAP.tsv")
    original_phase1d_path = provenance / "PHASE1D_ROW_LINEAGE.tsv"
    corrected_phase1d_path = provenance / "PHASE1D_ACCEPTED_CORRECTED_ROW_LINEAGE.tsv"
    original_phase1d = read_tsv(original_phase1d_path)
    corrected_phase1d = read_tsv(corrected_phase1d_path)

    phase1b_counts: dict[str, int] = {}
    for row in phase1b:
        phase1b_counts[row["CID"]] = phase1b_counts.get(row["CID"], 0) + 1
    excluded = {cid for cid, count in phase1b_counts.items() if count > 1}

    expected_crosswalks = {
        "51": ("LOSS1", "22", "19", "6", "LOSS", "KAIT"),
        "57": ("LOSS2", "39", "31", "8", "KAIT_DS15", "KAITM"),
        "65": (
            "CFA4p2",
            "13",
            "12",
            "8",
            "PS1_LOWZ_COMBINED_TEXT_DS17",
            "PS1_LOWZ_COMBINED(CFA4p1)",
        ),
    }
    actual_crosswalks = {
        row["IDSURVEY"]: (
            row["official_label"],
            row["eligible_row_count"],
            row["anchor_row_count"],
            row["hubble_flow_anchor_row_count"],
            row["inferred_source_directory"],
            row["inferred_SURVEY_headers"],
        )
        for row in crosswalks
    }
    target_by_code = {
        code: sum(row["IDSURVEY"] == code for row in targets)
        for code in ("51", "57", "65")
    }
    unique_marker = config["classification"]["target_unique"]
    unique_by_code = {
        code: sum(
            row["IDSURVEY"] == code
            and row["target_application_status"] == unique_marker
            for row in targets
        )
        for code in ("51", "57", "65")
    }

    source_result = verify_sources(project, args.pantheonplus.resolve())
    contract_result = verify_contract(project)
    test_log = (results / "unit_tests.log").read_text(encoding="utf-8")
    test_count_match = re.search(r"Ran (\d+) tests", test_log)
    registry = read_tsv(provenance / "PUBLIC_EVIDENCE_REGISTRY.tsv")

    corrected_zip = args.phase1d_corrected_zip.resolve()
    corrected_sidecar = args.phase1d_corrected_sidecar.resolve()
    corrected_archive_record = supersession["accepted_corrected_phase1d_archive"]
    corrected_zip_hash = sha(corrected_zip) if corrected_zip.is_file() else None
    expected_sidecar = (
        f"{corrected_zip_hash}  {corrected_zip.name}\n"
        if corrected_zip_hash is not None
        else None
    )
    corrected_zip_crc = False
    corrected_row_member_bytes = b""
    corrected_summary_member_bytes = b""
    corrected_final: dict[str, object] = {}
    corrected_single_root = False
    if corrected_zip.is_file():
        with zipfile.ZipFile(corrected_zip) as handle:
            corrected_zip_crc = handle.testzip() is None
            names = handle.namelist()
            roots = {name.split("/", 1)[0] for name in names if name}
            corrected_single_root = len(roots) == 1
            corrected_row_member_bytes = handle.read(
                unique_zip_member(handle, "/results/row_lineage.tsv")
            )
            corrected_summary_member_bytes = handle.read(
                unique_zip_member(handle, "/results/audit_summary.json")
            )
            corrected_final = json.loads(
                handle.read(
                    unique_zip_member(handle, "/results/final_verification_summary.json")
                ).decode("utf-8")
            )

    original_fields = tsv_fields(original_phase1d_path)
    original_columns_equal = (
        len(original_phase1d) == len(corrected_phase1d) == 69
        and all(
            all(old[field] == new[field] for field in original_fields)
            for old, new in zip(original_phase1d, corrected_phase1d, strict=True)
        )
    )
    original_target_bytes = canonical_target_driving_bytes(original_phase1d)
    corrected_target_bytes = canonical_target_driving_bytes(corrected_phase1d)
    target_ledger_record = supersession["target_driving_ledger_comparison"]

    frozen_hashes = supersession["phase1e_original_frozen_records_sha256"]
    frozen_records_unchanged = all(
        (project / relative).is_file()
        and sha(project / relative) == expected_hash
        for relative, expected_hash in frozen_hashes.items()
    )
    protected_hashes = supersession["phase1e_protected_primary_results_sha256"]
    protected_results_unchanged = all(
        (project / relative).is_file()
        and sha(project / relative) == expected_hash
        for relative, expected_hash in protected_hashes.items()
    )

    universe = summary["crosswalk_universe"]
    configured_directories = tuple(item["directory"] for item in config["directory_inventory"])
    legacy_semantics = semantics["UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK"]
    interpretive_scope = summary["interpretive_scope"]

    reader_paths = (
        project / "README.md",
        project / "REPORT.md",
        project / "REPORT_JA.md",
        results / "README.md",
    )
    reader_text = {path.name if path.parent == project else "results/README.md": path.read_text(encoding="utf-8") for path in reader_paths}
    english_scope_sentence = (
        "The uniqueness and crosswalk classifications hold within the prospectively "
        "frozen seven-directory public-photometry audit universe."
    )
    english_scope_present = all(
        english_scope_sentence in reader_text[name]
        for name in ("README.md", "REPORT.md", "results/README.md")
    )
    japanese_scope_present = (
        "結果閲覧前に固定した7つの公開測光ディレクトリ" in reader_text["REPORT_JA.md"]
        and "最終m_b_corr行への直接祖先は未証明" in reader_text["REPORT_JA.md"]
    )
    affirmative_overclaims = (
        "measurement lineage reconstructed",
        "active public file uniquely identified",
        "resolved all 31 rows left unresolved",
        "31/31行が各1個の有効な公開測光ファイルへ一意に接続した",
        "最終測定祖先を確定した",
    )
    reader_docs_avoid_overclaim = not any(
        phrase in text
        for text in reader_text.values()
        for phrase in affirmative_overclaims
    )

    text_files = [
        path
        for path in project.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".md", ".json", ".tsv", ".txt", ".py", ".cff"}
        and "__pycache__" not in path.parts
    ]
    scratch_leaks = []
    scratch_prefix = "/" + "/".join(("workspace", "scratch")) + "/"
    temporary_prefix = "/" + "tmp" + "/"
    for path in text_files:
        text = path.read_text(encoding="utf-8")
        if scratch_prefix in text or temporary_prefix in text:
            scratch_leaks.append(path.relative_to(project).as_posix())
    forbidden_packaged = [
        path.relative_to(project).as_posix()
        for path in project.rglob("*")
        if path.is_file()
        and (
            "Pantheon+_Data" in path.parts
            or "SH0ES_Data" in path.parts
            or path.suffix.lower() in {".fitres", ".cov"}
            or path.name in {"Pantheon+SH0ES.dat", "PPLUS.yml"}
        )
    ]

    checks = {
        "contract_freeze_hash": contract_result["contract_freeze_sha256"] == CONTRACT_FREEZE_SHA256,
        "contract_verification": contract_result["status"] == "PASS",
        "original_frozen_records_byte_unchanged": frozen_records_unchanged,
        "source_verification": source_result["status"] == "PASS",
        "source_lock_24": source_result["source_lock_row_count"] == 24,
        "corrected_phase1d_archive_name_and_hash": (
            corrected_zip.is_file()
            and corrected_zip.name == corrected_archive_record["name"]
            and corrected_zip_hash == corrected_archive_record["sha256"]
        ),
        "corrected_phase1d_sidecar": (
            corrected_sidecar.is_file()
            and expected_sidecar is not None
            and corrected_sidecar.read_text(encoding="utf-8") == expected_sidecar
            and corrected_archive_record["sidecar_status"] == "PASS"
        ),
        "corrected_phase1d_zip_crc_and_root": corrected_zip_crc and corrected_single_root,
        "corrected_phase1d_accepted_closure": (
            corrected_final.get("status") == "PASS"
            and corrected_final.get("closure") == "ACCEPT_COMPLETE_WITH_SCOPE"
            and corrected_final.get("pass_count") == corrected_final.get("check_count") == 39
        ),
        "corrected_phase1d_embedded_row_lineage_exact": (
            corrected_row_member_bytes == corrected_phase1d_path.read_bytes()
            and sha_bytes(corrected_row_member_bytes) == corrected_archive_record["accepted_corrected_row_lineage_sha256"]
        ),
        "corrected_phase1d_embedded_summary_exact": (
            corrected_summary_member_bytes == (provenance / "PHASE1D_ACCEPTED_CORRECTED_AUDIT_SUMMARY.json").read_bytes()
            and sha_bytes(corrected_summary_member_bytes) == corrected_archive_record["accepted_corrected_audit_summary_sha256"]
        ),
        "supersession_nonretroactive_status": (
            supersession["record_type"] == "POSTRESULT_ACCEPTED_UPSTREAM_SUPERSESSION"
            and supersession["created_after_phase1e_results"] is True
            and supersession["prospective_freeze_claim"] is False
            and supersession["phase1e_scientific_results_changed"] is False
            and supersession["status"] == "PASS"
        ),
        "original_phase1d_hash_preserved_in_supersession": (
            supersession["original_phase1d_archive"]["sha256"]
            == config["upstream"]["phase1d_archive_sha256"]
        ),
        "phase1d_original_columns_unchanged": original_columns_equal,
        "phase1d_target_driving_ledger_31_identical": (
            original_target_bytes == corrected_target_bytes
            and sha_bytes(original_target_bytes) == target_ledger_record["canonical_tsv_sha256_both_versions"]
            and target_ledger_record["row_count"] == 31
            and supersession["target_driving_row_ledger_byte_identical"] is True
            and supersession["target_population_31_rows_identical"] is True
        ),
        "protected_primary_results_byte_unchanged": protected_results_unchanged,
        "formal_status": execution["status"] == "AUDIT_COMPLETE_TARGET_EXCLUDED_PUBLIC_INTERNAL_CROSSWALK_CLASSIFIED",
        "scientific_classification": execution["scientific_classification"] == "PUBLIC_INTERNAL_CROSSWALK_SUPPORTED_3_OF_3_TARGET_ROWS_UNIQUE_31_OF_31",
        "summary_status_sync": summary["status"] == execution["status"],
        "catalog_1701": summary["catalog"]["row_count"] == 1701,
        "directory_count_7": summary["photometry_scan"]["configured_directory_count"] == 7,
        "crosswalk_universe_exact": (
            configured_directories == FROZEN_CROSSWALK_DIRECTORIES
            and universe["classification"] == "PROSPECTIVELY_FROZEN_SEVEN_PUBLIC_PHOTOMETRY_DIRECTORIES"
            and universe["configured_directory_count"] == 7
            and tuple(universe["directories"]) == FROZEN_CROSSWALK_DIRECTORIES
            and universe["uniqueness_scope"] == "WITHIN_FROZEN_SEVEN_DIRECTORY_UNIVERSE_ONLY"
        ),
        "broader_uniqueness_claims_false": (
            universe["full_public_photometry_tree_uniqueness_claim"] is False
            and universe["external_archive_uniqueness_claim"] is False
        ),
        "status_semantics_candidate_boundary": (
            legacy_semantics["preferred_label"] == PREFERRED_TARGET_LABEL
            and "direct ancestry to the final m_b_corr row" in legacy_semantics["does_not_establish"]
            and "identity of the exact light-curve fit output or FITRES row" in legacy_semantics["does_not_establish"]
            and "identity of the bias-correction run" in legacy_semantics["does_not_establish"]
            and "executed-run-to-final-catalog lineage" in legacy_semantics["does_not_establish"]
            and "statistical independence" in legacy_semantics["does_not_establish"]
        ),
        "interpretive_scope_false_boundaries": (
            interpretive_scope["target_application_preferred_label"] == PREFERRED_TARGET_LABEL
            and interpretive_scope["direct_final_measurement_ancestry_proven"] is False
            and interpretive_scope["fit_output_lineage_proven"] is False
            and interpretive_scope["bias_correction_run_lineage_proven"] is False
            and interpretive_scope["executed_run_to_final_catalog_lineage_proven"] is False
            and interpretive_scope["statistical_independence_proven"] is False
        ),
        "active_files_847": summary["photometry_scan"]["active_file_count"] == 847,
        "parse_failures_zero": summary["photometry_scan"]["parse_failure_count"] == 0,
        "excluded_multirow_CIDs_30": len(excluded) == 30,
        "holdout_rows_74": len(holdout) == 74,
        "anchor_rows_62": len(anchors) == 62,
        "anchor_target_disjoint": not ({row["CID"] for row in anchors} & excluded),
        "crosswalk_rows_3": len(crosswalks) == 3,
        "crosswalk_exact_values": actual_crosswalks == expected_crosswalks,
        "crosswalk_status_3_supported": all(
            row["support_status"] == config["classification"]["supported"]
            for row in crosswalks
        ),
        "target_rows_31": len(targets) == 31,
        "target_counts_by_code": target_by_code == {"51": 7, "57": 16, "65": 8},
        "target_unique_by_code": unique_by_code == {"51": 7, "57": 16, "65": 8},
        "target_evidence_rows_31": len(target_files) == 31,
        "target_candidate_counts_one": all(row["candidate_count"] == "1" for row in targets),
        "code65_label_header_mismatch": (
            len(label_rows) == 1
            and label_rows[0]["diagnostic_classification"]
            == "PUBLIC_LABEL_RAW_HEADER_CFA_TOKEN_MISMATCH"
            and label_rows[0]["interpretive_boundary"]
            == "DESCRIPTIVE_METADATA_TENSION_ONLY_NO_SOURCE_RELABELING"
        ),
        "second_implementation_24_of_24": (
            second_implementation["status"] == "PASS"
            and second_implementation["pass_count"]
            == second_implementation["check_count"]
            == EXPECTED_SECOND_IMPLEMENTATION_CHECKS
            and second_implementation["verification_scope"]
            == "SECOND_IMPLEMENTATION_INTERNAL_CROSSCHECK"
            and second_implementation["external_independent_replication"] is False
            and second_implementation["expert_review_or_endorsement"] is False
            and second_implementation["direct_final_measurement_ancestry_conclusion"] is False
        ),
        "unit_and_regression_tests_36": (
            test_count_match is not None
            and int(test_count_match.group(1)) == EXPECTED_UNIT_TEST_COUNT
            and test_log.rstrip().endswith("OK")
        ),
        "clean_reproduction_15_of_15": (
            clean["status"] == "PASS"
            and clean["byte_identical_result_count"]
            == clean["protected_result_count"]
            == EXPECTED_CLEAN_RESULT_COUNT
        ),
        "reader_documents_seven_directory_scope": english_scope_present and japanese_scope_present,
        "reader_documents_avoid_overclaim": reader_docs_avoid_overclaim,
        "reader_documents_dependency_supersession": (
            "post-result upstream supersession" in reader_text["README.md"]
            and "事後依存正本更新" in reader_text["REPORT_JA.md"]
        ),
        "evidence_registry_5": len(registry) == 5,
        "AI_disclosure_present": (
            "OpenAI ChatGPT Work (Codex)" in (project / "AI_ASSISTANCE_DISCLOSURE.md").read_text(encoding="utf-8")
            and "not an external independent replication" in (project / "AI_ASSISTANCE_DISCLOSURE.md").read_text(encoding="utf-8")
        ),
        "no_scratch_absolute_paths": not scratch_leaks,
        "upstream_bytes_not_redistributed": not forbidden_packaged,
        "version_0_1_0": (project / "VERSION").read_text(encoding="utf-8") == "0.1.0\n",
        "reports_preserve_scope": (
            "not an official `SURVEY.DEF` reconstruction" in reader_text["REPORT.md"]
            and "公式`SURVEY.DEF`の復元・確認ではない" in reader_text["REPORT_JA.md"]
        ),
    }
    result = {
        "check_count": len(checks),
        "pass_count": sum(checks.values()),
        "checks": checks,
        "dependency_verification": {
            "accepted_corrected_phase1d_archive_name": corrected_zip.name,
            "accepted_corrected_phase1d_archive_sha256": corrected_zip_hash,
            "target_driving_row_count": 31,
            "target_driving_selected_columns_sha256": sha_bytes(original_target_bytes),
        },
        "diagnostics": {
            "scratch_path_leaks": scratch_leaks,
            "forbidden_upstream_files": forbidden_packaged,
        },
        "read_only_default": True,
        "verification_scope": "INTERNAL_READ_ONLY_CLOSURE_WITH_ACCEPTED_UPSTREAM_DEPENDENCY",
        "closure": "ACCEPT_COMPLETE_WITH_SCOPE" if all(checks.values()) else "HOLD_FOR_VERIFICATION_FAILURE",
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    if args.output:
        args.output.resolve().write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "status": result["status"],
                "pass_count": result["pass_count"],
                "check_count": result["check_count"],
                "closure": result["closure"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
