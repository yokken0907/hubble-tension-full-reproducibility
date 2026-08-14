#!/usr/bin/env python3
"""Freeze Phase 1F governance and compact inputs before the complete scan."""

from __future__ import annotations

import hashlib
import json
import pathlib
from datetime import datetime, timezone


FILES = (
    "AUDIT_CONTRACT.md",
    "provenance/DECISION_CONFIG.json",
    "provenance/PREEXECUTION_EXPOSURE.json",
    "provenance/SOURCE_LOCK.tsv",
    "provenance/TREE_LOCK.tsv",
    "provenance/REPOSITORY_LOCK.json",
    "provenance/UPSTREAM_AUDIT_DEPENDENCIES.json",
    "provenance/PHASE1B_ROW_MAP.tsv",
    "provenance/PHASE1D_ACCEPTED_CORRECTED_ROW_LINEAGE.tsv",
    "provenance/PHASE1D_ACCEPTED_CORRECTED_AUDIT_SUMMARY.json",
    "provenance/PHASE1E_TARGET_ROW_APPLICATION.tsv",
    "provenance/PHASE1E_TARGET_CANDIDATE_FILE_EVIDENCE.tsv",
    "provenance/PHASE1E_ACCEPTED_CORRECTED_AUDIT_SUMMARY.json"
)


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    project = pathlib.Path(__file__).resolve().parents[1]
    config = json.loads((project / "provenance/DECISION_CONFIG.json").read_text(encoding="utf-8"))
    records = {}
    for relative in FILES:
        path = project / relative
        records[relative] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    value = {
        "contract_id": config["contract_id"],
        "freeze_timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "PROJECT_INTERNAL_PROSPECTIVE_HASH_FREEZE_BEFORE_COMPLETE_PHASE1F_SCAN",
        "complete_69_candidate_profile_observed_before_freeze": False,
        "complete_48_pair_scan_observed_before_freeze": False,
        "complete_filter_mapping_observed_before_freeze": False,
        "independent_verification_observed_before_freeze": False,
        "limited_examples_and_upstream_results_disclosed": True,
        "files": records
    }
    output = project / "provenance/CONTRACT_FREEZE.json"
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha(output)
    output.with_suffix(".sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(json.dumps({"status": value["status"], "sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
