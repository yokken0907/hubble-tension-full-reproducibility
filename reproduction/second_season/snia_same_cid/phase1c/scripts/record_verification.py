#!/usr/bin/env python3
"""Record the output of the otherwise read-only Phase 1C verifier."""

from __future__ import annotations

import argparse
import pathlib
import sys

from auditlib import write_json
from verify_results import verify


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--phase1a-archive", type=pathlib.Path, required=True)
    parser.add_argument("--phase1b-archive", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        summary = verify(
            project,
            args.h0dn.resolve(),
            args.pantheonplus.resolve(),
            args.phase1a_archive.resolve(),
            args.phase1b_archive.resolve(),
        )
        if summary["status"] != "PASS":
            raise RuntimeError("verification did not pass")
        write_json(
            project / "results" / "final_verification_summary.json",
            summary,
        )
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(
        "PASS: recorded "
        f"{summary['pass_count']}/{summary['gate_count']} verification gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
