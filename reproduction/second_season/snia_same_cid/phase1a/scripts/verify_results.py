#!/usr/bin/env python3
"""Read-only live verification and explicit closure-record generation."""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

import scipy.stats

from auditlib import (
    AuditFailure,
    CONTRACT_FREEZE_SHA256,
    LEGACY_DUPLICATE_NAME_ROW_NOTE,
    load_config,
    load_contract_amendments,
    sha256_file,
    verify_contract_freeze,
    write_json,
)
from package_tools import package_files, verify_manifests


EXPECTED_STATUS = (
    "AUDIT_COMPLETE_LOW_CHI2_LOCALIZED_TO_DUPLICATE_NAME_CONTRASTS"
)
BOUNDARY_MARKER = (
    "FROZEN_MODEL_ONLY_NO_COVARIANCE_CORRECTION_"
    "NO_CORRECTED_H0_NO_TENSION_RESOLUTION"
)
EXPECTED_UNIT_TEST_COUNT = 13
EXPECTED_COUNTS = {
    "object_count": 277,
    "unique_exact_name_count": 238,
    "multi_row_exact_name_group_count": 30,
    "rows_in_multi_row_exact_name_groups": 69,
    "duplicate_name_excess_row_count": 39,
    "duplicate_name_contrast_df": 39,
    "legacy_duplicate_name_row_count": 39,
}
EXPECTED_SCIENCE = {
    "chi2_total": 206.760636437324,
    "chi2_duplicate_name_contrasts": 11.209315063603,
    "chi2_between_name_modes": 195.551321373699,
    "beta_lower_tail_probability": 9.368362232281232e-05,
    "beta_two_sided_probability": 1.8736724464562464e-04,
}
READER_FACING_DOCUMENTS = (
    "README.md",
    "REPORT.md",
    "REPORT_JA.md",
    "REPRODUCIBILITY.md",
    "PACKAGE_VALIDATION.md",
    "CHANGELOG.md",
    "results/README.md",
)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    detail: str,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "detail": detail,
            "status": "PASS" if passed else "FAIL",
        }
    )


def finalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    checks = summary["checks"]
    summary["check_count"] = len(checks)
    summary["pass_count"] = sum(row["status"] == "PASS" for row in checks)
    summary["fail_count"] = sum(row["status"] == "FAIL" for row in checks)
    summary["status"] = (
        "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"
    )
    return summary


def run_unit_tests(project: pathlib.Path) -> tuple[subprocess.CompletedProcess[str], str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=project,
        capture_output=True,
        text=True,
        env=environment,
    )
    return completed, completed.stdout + completed.stderr


def tracked_tree_snapshot(project: pathlib.Path) -> dict[str, tuple[int, str]]:
    paths = package_files(project)
    for name in ("MANIFEST.tsv", "SHA256SUMS.txt"):
        path = project / name
        if path.is_file():
            paths.append(path)
    return {
        path.relative_to(project).as_posix(): (
            path.stat().st_size,
            sha256_file(path),
        )
        for path in sorted(
            set(paths), key=lambda item: item.relative_to(project).as_posix()
        )
    }


def write_record_results(
    project: pathlib.Path,
    unit_test_log: str,
    summary: dict[str, Any],
) -> None:
    results = project / "results"
    (results / "unit_tests.log").write_text(unit_test_log, encoding="utf-8")
    write_json(results / "final_verification_summary.json", summary)


def write_external_results(
    project: pathlib.Path,
    output_dir: pathlib.Path,
    unit_test_log: str,
    summary: dict[str, Any],
) -> None:
    resolved = output_dir.resolve()
    try:
        resolved.relative_to(project.resolve())
    except ValueError:
        pass
    else:
        raise AuditFailure("--output-dir must be outside the project tree")
    resolved.mkdir(parents=True, exist_ok=True)
    (resolved / "unit_tests.log").write_text(unit_test_log, encoding="utf-8")
    write_json(resolved / "live_verification_summary.json", summary)


def verify(
    project: pathlib.Path,
    *,
    tests: subprocess.CompletedProcess[str],
    test_log: str,
    include_manifest: bool,
    validate_saved_records: bool,
) -> dict[str, Any]:
    results = project / "results"
    required = [
        "EXECUTION_STATUS.json",
        "audit_summary.json",
        "baseline_reproduction.json",
        "clean_reproduction_summary.json",
        "contract_verification.json",
        "input_inventory.json",
        "monte_carlo_null_check.json",
        "numerical_crosschecks.json",
        "permutation_invariance_summary.json",
        "primary_partition.json",
        "reference_partition.json",
        "run_environment.json",
        "source_verification.json",
        "statistical_interpretation.json",
    ]
    checks: list[dict[str, Any]] = []
    for name in required:
        add_check(
            checks,
            f"required_result:{name}",
            (results / name).is_file(),
            name,
        )
    if any(row["status"] == "FAIL" for row in checks):
        return finalize_summary(
            {
                "verification_scope": (
                    "LIVE_READ_ONLY_COMPLETE"
                    if include_manifest
                    else "CLOSURE_RECORD_PRE_MANIFEST"
                ),
                "manifest_checked": include_manifest,
                "checks": checks,
            }
        )

    config = load_config(project)
    freeze = verify_contract_freeze(project)
    add_check(
        checks,
        "FROZEN_CONTRACT_INTEGRITY",
        freeze["status"] == "PASS"
        and not freeze["partition_results_observed_before_freeze"]
        and freeze["contract_freeze_sha256"] == CONTRACT_FREEZE_SHA256
        and freeze["contract_amendment_count"] >= 1,
        (
            f"{len(freeze['checks'])} frozen records; "
            f"{freeze['contract_amendment_count']} disclosed amendment"
        ),
    )

    amendments = load_contract_amendments(project)
    amendment = next(
        (row for row in amendments if row["amendment_id"] == "AMEND-001"),
        None,
    )
    amendment_ok = (
        amendment is not None
        and amendment["results_observed"] == "YES"
        and amendment["interpretation_affected"] == "NO"
        and amendment["timestamp_utc"].endswith("Z")
        and "duplicate-name contrast degrees of freedom"
        in amendment["reason"]
    )
    add_check(
        checks,
        "CONTRACT_AMENDMENT",
        amendment_ok,
        "AMEND-001; results_observed=YES; interpretation_affected=NO",
    )

    summary = load_json(results / "audit_summary.json")
    execution = load_json(results / "EXECUTION_STATUS.json")
    source = load_json(results / "source_verification.json")
    inventory = load_json(results / "input_inventory.json")
    baseline = load_json(results / "baseline_reproduction.json")
    crosschecks = load_json(results / "numerical_crosschecks.json")
    monte_carlo = load_json(results / "monte_carlo_null_check.json")
    permutations = load_json(results / "permutation_invariance_summary.json")
    primary = load_json(results / "primary_partition.json")
    reference = load_json(results / "reference_partition.json")
    interpretation = load_json(results / "statistical_interpretation.json")
    clean_reproduction = load_json(
        results / "clean_reproduction_summary.json"
    )

    add_check(
        checks,
        "formal_status",
        summary["status"] == EXPECTED_STATUS
        and execution["status"] == EXPECTED_STATUS
        and interpretation["status"] == EXPECTED_STATUS,
        summary["status"],
    )
    add_check(
        checks,
        "boundary_marker",
        summary["boundary_marker"] == BOUNDARY_MARKER,
        summary["boundary_marker"],
    )
    add_check(
        checks,
        "SOURCE_LOCK",
        source["status"] == "PASS"
        and source["locked_file_count"]
        == config["expected_inputs"]["source_lock_file_count"]
        == 69,
        f"{source['locked_file_count']}/69 locked files",
    )

    terminology_ok = all(
        inventory.get(key) == value and summary.get(key) == value
        for key, value in EXPECTED_COUNTS.items()
    )
    terminology_ok = (
        terminology_ok
        and inventory.get("legacy_field_note")
        == LEGACY_DUPLICATE_NAME_ROW_NOTE
        and summary.get("legacy_field_note")
        == LEGACY_DUPLICATE_NAME_ROW_NOTE
    )
    add_check(
        checks,
        "TERMINOLOGY_COUNTS",
        terminology_ok,
        "277 total; 238 groups; 30 multi-row groups; 69 rows; 39 contrast df",
    )
    add_check(
        checks,
        "input_inventory",
        inventory["status"] == "PASS"
        and all(inventory["checks"].values()),
        "canonical count fields and all frozen input checks PASS",
    )
    add_check(
        checks,
        "baseline_reproduction",
        baseline["status"] == "PASS",
        f"{len(baseline['comparisons'])} comparisons",
    )

    expected_df = config["analytic_null"]
    df_ok = (
        primary["df_total"] == expected_df["global_degrees_of_freedom"]
        and primary["df_duplicate_name_contrasts"]
        == expected_df["duplicate_degrees_of_freedom"]
        and primary["df_between_name_modes"]
        == expected_df["between_degrees_of_freedom"]
    )
    add_check(
        checks,
        "degrees_of_freedom",
        df_ok
        and primary["df_total"]
        == primary["df_duplicate_name_contrasts"]
        + primary["df_between_name_modes"],
        (
            f"{primary['df_total']}="
            f"{primary['df_duplicate_name_contrasts']}+"
            f"{primary['df_between_name_modes']}"
        ),
    )

    closure = abs(
        primary["chi2_total"]
        - primary["chi2_duplicate_name_contrasts"]
        - primary["chi2_between_name_modes"]
    )
    add_check(
        checks,
        "partition_closure",
        closure <= config["tolerances"]["partition_closure_absolute"],
        f"absolute residual {closure:.3e}",
    )

    maximum_solver_difference = max(
        abs(primary[key] - reference[key])
        for key in (
            "chi2_total",
            "chi2_duplicate_name_contrasts",
            "chi2_between_name_modes",
        )
    )
    add_check(
        checks,
        "independent_solver",
        crosschecks["status"] == "PASS"
        and maximum_solver_difference
        <= config["tolerances"]["reference_solver_absolute"],
        f"maximum absolute difference {maximum_solver_difference:.3e}",
    )
    add_check(
        checks,
        "permutations",
        permutations["status"] == "PASS"
        and permutations["count"] == config["permutations"]["count"],
        (
            f"{permutations['count']} permutations; max "
            f"{max(permutations['maximum_absolute_differences'].values()):.3e}"
        ),
    )
    add_check(
        checks,
        "monte_carlo",
        monte_carlo["status"] == "PASS"
        and monte_carlo["draw_count"] == config["monte_carlo"]["draw_count"],
        f"{monte_carlo['draw_count']} implementation-check draws",
    )

    science_ok = (
        math.isclose(
            primary["chi2_total"],
            EXPECTED_SCIENCE["chi2_total"],
            rel_tol=0.0,
            abs_tol=5e-12,
        )
        and math.isclose(
            primary["chi2_duplicate_name_contrasts"],
            EXPECTED_SCIENCE["chi2_duplicate_name_contrasts"],
            rel_tol=0.0,
            abs_tol=5e-12,
        )
        and math.isclose(
            primary["chi2_between_name_modes"],
            EXPECTED_SCIENCE["chi2_between_name_modes"],
            rel_tol=0.0,
            abs_tol=5e-12,
        )
        and math.isclose(
            interpretation["beta_lower_tail_probability"],
            EXPECTED_SCIENCE["beta_lower_tail_probability"],
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        and math.isclose(
            interpretation["beta_two_sided_probability"],
            EXPECTED_SCIENCE["beta_two_sided_probability"],
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        and interpretation["localization_class"]
        == "DUPLICATE_NAME_CONTRAST_DEFICIT"
    )
    add_check(
        checks,
        "SCIENCE_LOCK",
        science_ok,
        "fixed chi-square, df, Beta probabilities, class, and boundary",
    )

    total = float(primary["chi2_total"])
    duplicate = float(primary["chi2_duplicate_name_contrasts"])
    ratio = duplicate / total
    beta_a = primary["df_duplicate_name_contrasts"] / 2.0
    beta_b = primary["df_between_name_modes"] / 2.0
    lower = float(scipy.stats.beta.cdf(ratio, beta_a, beta_b))
    upper = float(scipy.stats.beta.sf(ratio, beta_a, beta_b))
    recomputed_status = (
        config["status_labels"]["duplicate_localized"]
        if lower <= config["analytic_null"]["lower_beta_tail_threshold"]
        else (
            config["status_labels"]["between_localized"]
            if upper <= config["analytic_null"]["upper_beta_tail_threshold"]
            else config["status_labels"]["proportional"]
        )
    )
    add_check(
        checks,
        "decision_rule_recomputation",
        recomputed_status == EXPECTED_STATUS
        and abs(lower - interpretation["beta_lower_tail_probability"]) <= 1e-15
        and abs(upper - interpretation["beta_upper_tail_probability"]) <= 1e-15,
        f"lower={lower:.12g}; upper={upper:.12g}",
    )

    reader_text = {
        name: (project / name).read_text(encoding="utf-8")
        for name in READER_FACING_DOCUMENTS
    }
    combined_reader_text = "\n".join(reader_text.values())
    misleading_patterns = (
        r"\b39 duplicate " + r"rows\b",
        r"39個の" + r"重複行",
    )
    misleading_hits = [
        pattern
        for pattern in misleading_patterns
        if re.search(pattern, combined_reader_text, flags=re.IGNORECASE)
    ]
    add_check(
        checks,
        "NO_MISLEADING_39_ROWS",
        not misleading_hits,
        "none" if not misleading_hits else ", ".join(misleading_hits),
    )
    external_registration_terms = (
        "pre-" + "registered",
        "pre" + "registered",
        "事前" + "登録",
    )
    internal_wording_ok = (
        not any(term in combined_reader_text for term in external_registration_terms)
        and "project-internal" in combined_reader_text
        and "プロジェクト内部" in combined_reader_text
    )
    add_check(
        checks,
        "INTERNAL_FREEZE_WORDING",
        internal_wording_ok,
        "project-internal pre-result hash freeze; no external registration claim",
    )
    for name in ("README.md", "REPORT.md", "REPORT_JA.md"):
        text = reader_text[name]
        add_check(
            checks,
            f"report_status:{name}",
            EXPECTED_STATUS in text,
            name,
        )
        add_check(
            checks,
            f"report_boundary:{name}",
            BOUNDARY_MARKER in text,
            name,
        )

    clean_required = {
        "audit_summary_semantically_identical",
        "audit_summary_bytes_identical",
        "original_audit_summary_sha256",
        "reproduced_audit_summary_sha256",
    }
    legacy_clean_field = "audit_summary_byte_" + "values_identical"
    clean_schema_ok = (
        clean_required.issubset(clean_reproduction)
        and legacy_clean_field not in clean_reproduction
        and isinstance(
            clean_reproduction["audit_summary_semantically_identical"], bool
        )
        and isinstance(clean_reproduction["audit_summary_bytes_identical"], bool)
        and len(clean_reproduction["original_audit_summary_sha256"]) == 64
        and len(clean_reproduction["reproduced_audit_summary_sha256"]) == 64
        and clean_reproduction["status"]
        == (
            "PASS"
            if clean_reproduction["audit_summary_semantically_identical"]
            else "FAIL"
        )
    )
    if (
        clean_schema_ok
        and not clean_reproduction["audit_summary_bytes_identical"]
    ):
        clean_schema_ok = bool(
            clean_reproduction.get("byte_equality_explanation")
        )
    add_check(
        checks,
        "CLEAN_REPRO_SCHEMA",
        clean_schema_ok,
        (
            "semantic="
            f"{clean_reproduction.get('audit_summary_semantically_identical')}; "
            f"bytes={clean_reproduction.get('audit_summary_bytes_identical')}"
        ),
    )

    forbidden_upstream = [
        project / "data" / "sn1a_hf_pp.dat",
        project / "data" / "sn1a_covar_pp.dat",
    ]
    add_check(
        checks,
        "upstream_bytes_not_redistributed",
        not any(path.exists() for path in forbidden_upstream),
        "public inputs remain separately distributed",
    )
    symlinks = [
        path.relative_to(project).as_posix()
        for path in project.rglob("*")
        if path.is_symlink()
    ]
    add_check(
        checks,
        "no_symlinks",
        not symlinks,
        "none" if not symlinks else ", ".join(symlinks),
    )

    expected_test_phrase = f"Ran {EXPECTED_UNIT_TEST_COUNT} tests"
    add_check(
        checks,
        "UNIT_TESTS",
        tests.returncode == 0
        and expected_test_phrase in test_log
        and "\nOK\n" in test_log,
        (
            f"{EXPECTED_UNIT_TEST_COUNT}/{EXPECTED_UNIT_TEST_COUNT} PASS"
            if tests.returncode == 0
            else "unit test failure"
        ),
    )
    add_check(
        checks,
        "RECORD_MODE_SCOPE",
        "test_record_result_writer_changes_only_authorized_files" in test_log,
        "regression test covers the two authorized closure-record files",
    )

    stderr_path = results / "run_stderr.log"
    add_check(
        checks,
        "execution_stderr",
        stderr_path.is_file() and stderr_path.stat().st_size == 0,
        "empty" if stderr_path.is_file() else "missing",
    )

    if validate_saved_records:
        stored_log_path = results / "unit_tests.log"
        stored_summary_path = results / "final_verification_summary.json"
        stored_log_ok = (
            stored_log_path.is_file()
            and expected_test_phrase
            in stored_log_path.read_text(encoding="utf-8")
        )
        add_check(
            checks,
            "stored_unit_test_record",
            stored_log_ok,
            "closure-time unit-test log",
        )
        stored_summary_ok = False
        if stored_summary_path.is_file():
            stored = load_json(stored_summary_path)
            stored_summary_ok = (
                stored.get("status") == "PASS"
                and stored.get("verification_scope")
                == "CLOSURE_RECORD_PRE_MANIFEST"
                and stored.get("manifest_checked") is False
            )
        add_check(
            checks,
            "stored_closure_verification_record",
            stored_summary_ok,
            "pre-manifest closure record",
        )

    if include_manifest:
        try:
            manifest_result = verify_manifests(project)
        except (OSError, RuntimeError, ValueError) as exc:
            add_check(
                checks,
                "MANIFEST_AND_SHA256",
                False,
                f"{type(exc).__name__}: {exc}",
            )
        else:
            add_check(
                checks,
                "MANIFEST_AND_SHA256",
                manifest_result["status"] == "PASS",
                f"{manifest_result['manifested_file_count']} manifested files",
            )

    return finalize_summary(
        {
            "scientific_status": summary["status"],
            "verification_scope": (
                "LIVE_READ_ONLY_COMPLETE"
                if include_manifest
                else "CLOSURE_RECORD_PRE_MANIFEST"
            ),
            "manifest_checked": include_manifest,
            "checks": checks,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--record-results", action="store_true")
    group.add_argument("--output-dir", type=pathlib.Path)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]

    include_manifest = not args.record_results
    validate_saved_records = not args.record_results
    before = None if args.record_results else tracked_tree_snapshot(project)

    try:
        tests, test_log = run_unit_tests(project)
        summary = verify(
            project,
            tests=tests,
            test_log=test_log,
            include_manifest=include_manifest,
            validate_saved_records=validate_saved_records,
        )
        if args.record_results:
            write_record_results(project, test_log, summary)
        else:
            after = tracked_tree_snapshot(project)
            add_check(
                summary["checks"],
                "READ_ONLY_VERIFIER",
                before == after,
                "tracked file list, byte counts, and SHA-256 values unchanged",
            )
            finalize_summary(summary)
            if args.output_dir is not None:
                write_external_results(
                    project,
                    args.output_dir,
                    test_log,
                    summary,
                )
    except (OSError, KeyError, ValueError, AuditFailure) as exc:
        summary = {
            "verification_scope": (
                "CLOSURE_RECORD_PRE_MANIFEST"
                if args.record_results
                else "LIVE_READ_ONLY_COMPLETE"
            ),
            "manifest_checked": include_manifest,
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }
        if args.record_results:
            write_json(
                project / "results" / "final_verification_summary.json",
                summary,
            )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
