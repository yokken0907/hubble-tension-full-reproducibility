#!/usr/bin/env python3
"""Freeze Phase 1E governance and input-ledger files before outcome scanning."""

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
    "provenance/REPOSITORY_LOCK.json",
    "provenance/UPSTREAM_AUDIT_DEPENDENCIES.json",
    "provenance/PHASE1B_ROW_MAP.tsv",
    "provenance/PHASE1D_ROW_LINEAGE.tsv",
    "provenance/PHASE1D_AUDIT_SUMMARY.json",
)


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    project = pathlib.Path(__file__).resolve().parents[1]
    config = json.loads((project / "provenance/DECISION_CONFIG.json").read_text())
    records = {}
    for rel in FILES:
        path = project / rel
        records[rel] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    value = {
        "contract_id": config["contract_id"],
        "freeze_timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "PROJECT_INTERNAL_PROSPECTIVE_HASH_FREEZE_BEFORE_COMPLETE_PHASE1E_SCAN",
        "complete_target_excluded_anchor_scan_observed_before_freeze": False,
        "complete_target_application_observed_before_freeze": False,
        "independent_verification_observed_before_freeze": False,
        "known_posthoc_hypotheses_disclosed": True,
        "files": records,
    }
    out = project / "provenance/CONTRACT_FREEZE.json"
    out.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha(out)
    out.with_suffix(".sha256").write_text(f"{digest}  {out.name}\n", encoding="utf-8")
    print(json.dumps({"status": value["status"], "sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
