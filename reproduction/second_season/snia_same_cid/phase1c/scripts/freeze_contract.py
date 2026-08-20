#!/usr/bin/env python3
"""Create the Phase 1C contract-freeze record before component execution."""

from __future__ import annotations

import hashlib
import json
import pathlib


FROZEN_PATHS = [
    "AUDIT_CONTRACT.md",
    "provenance/CONTRACT_AMENDMENTS.tsv",
    "provenance/DECISION_CONFIG.json",
    "provenance/PHASE1B_ROW_MAP.tsv",
    "provenance/PREEXECUTION_SCHEMA_HOLD.json",
    "provenance/RETIRED_CONTRACT_01.md",
    "provenance/RETIRED_CONTRACT_FREEZE_01.json",
    "provenance/RETIRED_DECISION_CONFIG_01.json",
    "provenance/SOURCE_LOCK.tsv",
    "provenance/UPSTREAM_AUDIT_DEPENDENCIES.json",
    "requirements-lock.txt",
]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    project = pathlib.Path(__file__).resolve().parents[1]
    files = {
        relative: {
            "bytes": (project / relative).stat().st_size,
            "sha256": sha256(project / relative),
        }
        for relative in FROZEN_PATHS
    }
    record = {
        "component_diagnostics_observed_before_freeze": False,
        "contract_id": (
            "H0DN-SNIA-CONTRAST-COVARIANCE-PHASE1C-20260730-02"
        ),
        "files": files,
        "contract_01_preexecution_schema_hold_observed_before_freeze": True,
        "freeze_timestamp_utc": "2026-07-30T05:14:00Z",
        "known_phase1a_baseline_observed_before_freeze": True,
        "phase1b_mapping_observed_before_freeze": True,
        "stat_sys_without_velocity_result_observed_before_freeze": False,
        "statonly_contrast_result_observed_before_freeze": False,
        "status": "FROZEN_BEFORE_PHASE1C_COMPONENT_EXECUTION",
    }
    target = project / "provenance" / "CONTRACT_FREEZE.json"
    target.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
