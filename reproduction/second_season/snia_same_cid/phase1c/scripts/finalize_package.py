#!/usr/bin/env python3
"""Validate, manifest, and deterministically archive Phase 1C."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from package_tools import (
    deterministic_archive,
    verify_manifests,
    write_manifests,
)


EXPECTED_STATUS = (
    "AUDIT_COMPLETE_CONTRAST_COVARIANCE_CALIBRATION_DIAGNOSTIC"
)


def check_core(project: pathlib.Path) -> dict[str, object]:
    results = project / "results"
    audit = json.loads(
        (results / "audit_summary.json").read_text(encoding="utf-8")
    )
    verification = json.loads(
        (results / "final_verification_summary.json").read_text(
            encoding="utf-8"
        )
    )
    independent = json.loads(
        (results / "independent_verification.json").read_text(
            encoding="utf-8"
        )
    )
    clean = json.loads(
        (results / "clean_reproduction_summary.json").read_text(
            encoding="utf-8"
        )
    )
    posthoc_precision = json.loads(
        (
            results
            / "printed_vs_high_precision_contrast_diagnostic.json"
        ).read_text(encoding="utf-8")
    )
    posthoc_asymmetry = json.loads(
        (
            results / "mapped_submatrix_asymmetry_diagnostic.json"
        ).read_text(encoding="utf-8")
    )
    checks = {
        "formal_status": audit["status"] == EXPECTED_STATUS,
        "classification": (
            audit["sensitivity_classification"]
            == "LOW_FLAG_PERSISTS_THROUGH_STATONLY"
        ),
        "pre_manifest_closure": (
            verification["status"] == "PASS"
            and verification["gate_count"] == 24
            and verification["pass_count"] == 24
            and verification["closure_disposition"]
            == "ACCEPT_COMPLETE_WITH_SCOPE"
        ),
        "independent_verification": independent["status"] == "PASS",
        "clean_reproduction": clean["status"] == "PASS",
        "posthoc_precision": (
            posthoc_precision["status"] == "POSTHOC_DIAGNOSTIC_COMPLETE"
            and posthoc_precision["main_result_invariance"][
                "protected_artifacts_byte_unchanged"
            ]
            is True
        ),
        "posthoc_asymmetry": (
            posthoc_asymmetry["status"] == "POSTHOC_DIAGNOSTIC_COMPLETE"
            and posthoc_asymmetry["promotion_status"]
            == "POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE"
        ),
        "posthoc_contract_sidecar": (
            project
            / "POSTHOC_PRECISION_AND_ASYMMETRY_DIAGNOSTIC_CONTRACT.sha256"
        ).is_file(),
        "contract_freeze": (
            project
            / "provenance"
            / "CONTRACT_FREEZE.json"
        ).is_file(),
        "retired_contract_preserved": (
            project
            / "provenance"
            / "RETIRED_CONTRACT_FREEZE_01.json"
        ).is_file(),
    }
    return {
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifests", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--archive", type=pathlib.Path)
    args = parser.parse_args()
    if not (args.write_manifests or args.check or args.archive):
        parser.error("choose --write-manifests, --check, or --archive")
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        core = check_core(project)
        if core["status"] != "PASS":
            raise RuntimeError("core closure check failed")
        if args.write_manifests:
            rows = write_manifests(project)
            print(f"PASS: wrote manifests for {len(rows)} files")
        if args.check:
            manifest = verify_manifests(project)
            print(
                "PASS: "
                f"{manifest['manifested_file_count']} manifested files"
            )
        if args.archive:
            archive = deterministic_archive(
                project, args.archive.resolve()
            )
            print(json.dumps(archive, indent=2, sort_keys=True))
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
