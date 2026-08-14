#!/usr/bin/env python3
"""Acquire and verify the frozen H0DN checkout."""

from __future__ import annotations

import argparse
import pathlib
import sys

from source_tools import acquire, verify_source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True, type=pathlib.Path)
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1]
        / "provenance"
        / "SOURCE_LOCK.tsv",
    )
    args = parser.parse_args()
    try:
        acquire(args.destination.resolve())
        result = verify_source(args.destination.resolve(), args.manifest.resolve())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(
        f"PASS: frozen H0DN source acquired at {result['commit']} "
        f"({result['locked_file_count']} files)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

