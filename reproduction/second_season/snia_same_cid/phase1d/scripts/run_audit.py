#!/usr/bin/env python3
"""Execute the frozen Phase 1D audit."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

from auditlib import AuditFailure, run_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        summary = run_audit(
            project, args.h0dn.resolve(), args.pantheonplus.resolve()
        )
    except (
        AuditFailure,
        OSError,
        UnicodeError,
        subprocess.CalledProcessError,
        ValueError,
    ) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": summary["status"],
                "release_sufficiency_classification": summary[
                    "release_sufficiency_classification"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
