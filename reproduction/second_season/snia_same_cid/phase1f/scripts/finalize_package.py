#!/usr/bin/env python3
"""Finalize manifests and create a deterministic Phase 1F archive."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from package_tools import deterministic_archive, verify_manifests, write_manifests


def load(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_closure(project: pathlib.Path) -> None:
    final = load(project / "results/final_verification_summary.json")
    execution = load(project / "results/EXECUTION_STATUS.json")
    summary = load(project / "results/audit_summary.json")
    posthoc = load(project / "results/posthoc_cross_cid_negative_control_summary.json")
    independent = load(project / "results/independent_verification.json")
    tests = load(project / "results/unit_tests_summary.json")
    clean = load(project / "results/clean_reproduction_summary.json")
    required = (
        project / "PACKAGE_VALIDATION.md",
        project / "REPORT.md",
        project / "REPORT_JA.md",
        project / "provenance/IMPLEMENTATION_CORRECTIONS.tsv",
    )
    if (
        not all(path.is_file() for path in required)
        or final["status"] != "PASS"
        or final["closure"] != "ACCEPT_COMPLETE_WITH_SCOPE"
        or final["pass_count"] != final["check_count"]
        or final["check_count"] != 117
        or execution["status"] != "AUDIT_COMPLETE_PUBLIC_INPUT_DEPENDENCY_CLASSIFIED"
        or summary["pair_comparison"]["pair_count"] != 48
        or summary["pair_comparison"]["byte_exact_positive_pair_count"] != 0
        or summary["pair_comparison"]["mutual_unique_rounding_match_record_count"] != 4
        or summary["pair_comparison"]["physical_exposure_identity_proven"] is not False
        or summary["pair_comparison"]["statistical_independence_proven"] is not False
        or summary["configuration_lineage"]["executed_run_to_final_catalog_lineage_proven"] is not False
        or posthoc["status"] != "POSTHOC_NEGATIVE_CONTROL_COMPLETE"
        or posthoc["chronology"] != "DESIGNED_AND_FROZEN_AFTER_MAIN_RESULT"
        or posthoc["protected_main_results_unchanged_after_diagnostic"] is not True
        or independent["status"] != "PASS"
        or independent["pass_count"] != independent["check_count"]
        or independent["check_count"] != 31
        or tests["status"] != "PASS"
        or tests["test_count"] != 50
        or clean["status"] != "PASS"
        or clean["byte_identical_output_count"] != clean["generated_output_count"]
        or clean["generated_output_count"] != 20
    ):
        raise RuntimeError("scientific or verification closure is not PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifests", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--archive", type=pathlib.Path)
    args = parser.parse_args()
    if not (args.write_manifests or args.check or args.archive):
        parser.error("choose --write-manifests, --check, or --archive")
    project = pathlib.Path(__file__).resolve().parents[1]
    require_closure(project)
    output: dict[str, object] = {}
    if args.write_manifests:
        output["manifested_file_count"] = len(write_manifests(project))
    if args.check or args.archive:
        output["manifest"] = verify_manifests(project)
    if args.archive:
        output["archive"] = deterministic_archive(project, args.archive.resolve())
    output["status"] = "PASS"
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, RuntimeError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
