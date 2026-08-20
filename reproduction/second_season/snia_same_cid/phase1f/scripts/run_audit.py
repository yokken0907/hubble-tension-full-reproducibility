#!/usr/bin/env python3
"""Execute the frozen Phase 1F audit."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

from auditlib import AuditFailure, run_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        summary = run_audit(project, args.pantheonplus.resolve())
    except (AuditFailure, OSError, UnicodeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": summary["status"], "scientific_classification": summary["scientific_classification"]}, sort_keys=True))
    return 0 if summary["status"] == "AUDIT_COMPLETE_PUBLIC_INPUT_DEPENDENCY_CLASSIFIED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
