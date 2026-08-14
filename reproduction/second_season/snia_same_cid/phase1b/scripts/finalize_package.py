#!/usr/bin/env python3
"""Write/check manifests and build the deterministic delivery ZIP."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from package_tools import deterministic_archive, verify_manifests, write_manifests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifests", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--archive", type=pathlib.Path)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        if args.write_manifests:
            rows = write_manifests(project)
            print(f"WROTE: {len(rows)} manifested files")
        if args.check or args.archive:
            record = verify_manifests(project)
            print(f"PASS: {record['manifested_file_count']} manifested files")
        if args.archive:
            print(
                json.dumps(
                    deterministic_archive(project, args.archive.resolve()),
                    indent=2,
                    sort_keys=True,
                )
            )
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
