#!/usr/bin/env python3
"""Write/check manifests and create the deterministic Phase 1D archive."""

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


def require_scientific_closure(project: pathlib.Path) -> None:
    final = json.loads(
        (project / "results" / "final_verification_summary.json").read_text()
    )
    execution = json.loads(
        (project / "results" / "EXECUTION_STATUS.json").read_text()
    )
    if (
        final["status"] != "PASS"
        or final["closure"] != "ACCEPT_COMPLETE_WITH_SCOPE"
        or execution["status"]
        != "AUDIT_COMPLETE_SHARED_DEPENDENCY_AND_LINEAGE_CLASSIFIED"
        or execution["release_sufficiency_classification"]
        != "PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE"
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
    require_scientific_closure(project)
    output: dict[str, object] = {}
    if args.write_manifests:
        output["manifested_file_count"] = len(write_manifests(project))
    if args.check or args.archive:
        output["manifest"] = verify_manifests(project)
    if args.archive:
        output["archive"] = deterministic_archive(
            project, args.archive.resolve()
        )
    output["status"] = "PASS"
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
