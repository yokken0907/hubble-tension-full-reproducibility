#!/usr/bin/env python3
"""Freeze the post-hoc negative-control contract and protected main outputs."""

from __future__ import annotations

import hashlib
import json
import pathlib
from datetime import datetime, timezone


PROTECTED = (
    "results/EXECUTION_STATUS.json",
    "results/audit_summary.json",
    "results/input_candidate_map.tsv",
    "results/row_input_profile.tsv",
    "results/pair_dependency_classification.tsv",
    "results/observation_match_evidence.tsv",
    "results/filter_calibration_mapping.tsv",
    "results/series_configuration_lineage.tsv",
    "results/public_asset_availability.tsv",
    "results/shared_dependency_ledger.tsv",
)


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    project = pathlib.Path(__file__).resolve().parents[1]
    contract = project / "POSTHOC_PAYLOAD_COLLISION_NEGATIVE_CONTROL_CONTRACT.md"
    main_summary = json.loads((project / "results/audit_summary.json").read_text(encoding="utf-8"))
    value = {
        "freeze_timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "PROJECT_INTERNAL_POSTHOC_NEGATIVE_CONTROL_FREEZE_AFTER_MAIN_RESULT",
        "main_result_observed_before_freeze": True,
        "negative_control_result_observed_before_freeze": False,
        "contract": {"path": contract.name, "bytes": contract.stat().st_size, "sha256": sha(contract)},
        "observed_main_counts": main_summary["pair_comparison"],
        "protected_main_results": {relative: {"bytes": (project / relative).stat().st_size, "sha256": sha(project / relative)} for relative in PROTECTED},
    }
    output = project / "provenance/POSTHOC_PAYLOAD_COLLISION_NEGATIVE_CONTROL_FREEZE.json"
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha(output)
    output.with_suffix(".sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(json.dumps({"status": value["status"], "sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

