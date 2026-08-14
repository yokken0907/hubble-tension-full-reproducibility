#!/usr/bin/env python3
"""Freeze the result-governing Phase 1D files before full execution."""

from __future__ import annotations

import hashlib
import json
import pathlib


CONTRACT_ID = (
    "H0DN-SNIA-SAME-CID-MEASUREMENT-LINEAGE-"
    "PHASE1D-20260730-01"
)
FREEZE_TIME = "2026-07-30T07:26:17Z"
FILES = (
    "AUDIT_CONTRACT.md",
    "provenance/CONTRACT_AMENDMENTS.tsv",
    "provenance/DECISION_CONFIG.json",
    "provenance/PHASE1B_ROW_MAP.tsv",
    "provenance/PREEXECUTION_EXPOSURE.json",
    "provenance/REPOSITORY_LOCK.json",
    "provenance/SOURCE_LOCK.tsv",
    "provenance/UPSTREAM_AUDIT_DEPENDENCIES.json",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    project = pathlib.Path(__file__).resolve().parents[1]
    records = {}
    for relative in FILES:
        path = project / relative
        records[relative] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    freeze = {
        "contract_id": CONTRACT_ID,
        "freeze_timestamp_utc": FREEZE_TIME,
        "files": records,
        "known_phase1b_results_observed_before_freeze": True,
        "known_phase1c_results_observed_before_freeze": True,
        "partial_result_blindness": True,
        "complete_69_row_scan_observed_before_freeze": False,
        "complete_30_group_classification_observed_before_freeze": False,
        "independent_verification_observed_before_freeze": False,
        "release_sufficiency_classification_observed_before_freeze": False,
        "status": "FROZEN_BEFORE_COMPLETE_PHASE1D_SCAN"
    }
    path = project / "provenance" / "CONTRACT_FREEZE.json"
    path.write_text(
        json.dumps(freeze, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    digest = sha256(path)
    sidecar = path.with_suffix(".sha256")
    sidecar.write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    print(json.dumps({"sha256": digest, "status": "FROZEN"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
