#!/usr/bin/env python3
"""Finalize manifests and create a deterministic Phase 1E archive."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from package_tools import deterministic_archive, verify_manifests, write_manifests


def require_closure(project: pathlib.Path) -> None:
    final = json.loads((project / "results/final_verification_summary.json").read_text(encoding="utf-8"))
    execution = json.loads((project / "results/EXECUTION_STATUS.json").read_text(encoding="utf-8"))
    summary = json.loads((project / "results/audit_summary.json").read_text(encoding="utf-8"))
    semantics = json.loads((project / "results/status_semantics.json").read_text(encoding="utf-8"))
    supersession = json.loads(
        (project / "provenance/UPSTREAM_DEPENDENCY_SUPERSESSION.json").read_text(encoding="utf-8")
    )
    universe = summary["crosswalk_universe"]
    interpretive = summary["interpretive_scope"]
    required_new_files = (
        project / "provenance/UPSTREAM_DEPENDENCY_SUPERSESSION.json",
        project / "provenance/PHASE1D_ACCEPTED_CORRECTED_ROW_LINEAGE.tsv",
        project / "provenance/PHASE1D_ACCEPTED_CORRECTED_AUDIT_SUMMARY.json",
        project / "results/status_semantics.json",
    )
    if (
        not all(path.is_file() for path in required_new_files)
        or final["status"] != "PASS"
        or final["closure"] != "ACCEPT_COMPLETE_WITH_SCOPE"
        or final["pass_count"] != final["check_count"]
        or execution["status"] != "AUDIT_COMPLETE_TARGET_EXCLUDED_PUBLIC_INTERNAL_CROSSWALK_CLASSIFIED"
        or execution["scientific_classification"] != "PUBLIC_INTERNAL_CROSSWALK_SUPPORTED_3_OF_3_TARGET_ROWS_UNIQUE_31_OF_31"
        or supersession["status"] != "PASS"
        or supersession["prospective_freeze_claim"] is not False
        or supersession["target_driving_row_ledger_byte_identical"] is not True
        or supersession["target_population_31_rows_identical"] is not True
        or supersession["phase1e_scientific_results_changed"] is not False
        or summary["target_excluded_inference"]["eligible_row_count"] != 74
        or summary["target_excluded_inference"]["anchor_row_count"] != 62
        or summary["target_excluded_inference"]["crosswalk_count"] != 3
        or summary["target_application"]["target_row_count"] != 31
        or summary["target_application"]["unique_target_row_count"] != 31
        or summary["photometry_scan"]["active_file_count"] != 847
        or summary["photometry_scan"]["parse_failure_count"] != 0
        or universe["configured_directory_count"] != 7
        or universe["full_public_photometry_tree_uniqueness_claim"] is not False
        or universe["external_archive_uniqueness_claim"] is not False
        or interpretive["direct_final_measurement_ancestry_proven"] is not False
        or interpretive["fit_output_lineage_proven"] is not False
        or interpretive["bias_correction_run_lineage_proven"] is not False
        or interpretive["executed_run_to_final_catalog_lineage_proven"] is not False
        or interpretive["statistical_independence_proven"] is not False
        or semantics["UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK"]["preferred_label"]
        != "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_PUBLIC_INPUT_CANDIDATE"
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
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
