#!/usr/bin/env python3
"""Build the post-result AMEND-001 crosswalk-evidence ledger."""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys

import auditlib


def read_candidate_rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not args.write:
        parser.error("--write is required for this explicit correction step")
    project = pathlib.Path(__file__).resolve().parents[1]
    config = auditlib.load_config(project)
    candidates = read_candidate_rows(
        project / "results" / "candidate_file_evidence.tsv"
    )
    rows = auditlib.expected_crosswalk_evidence_rows(
        project, config, args.pantheonplus.resolve(), candidates
    )
    auditlib.write_tsv(
        project / "provenance" / "SURVEY_CROSSWALK_EVIDENCE.tsv",
        rows,
        auditlib.CROSSWALK_EVIDENCE_FIELDS,
    )
    print(
        "wrote provenance/SURVEY_CROSSWALK_EVIDENCE.tsv "
        f"with {len(rows)} rows"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (auditlib.AuditFailure, OSError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
