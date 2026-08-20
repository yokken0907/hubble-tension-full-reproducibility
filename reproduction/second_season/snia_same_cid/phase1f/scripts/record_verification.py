#!/usr/bin/env python3
"""Run the read-only verifier and persist its JSON result."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    process = subprocess.run(
        [sys.executable, "scripts/verify_results.py", "--pantheonplus", str(args.pantheonplus.resolve())],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        print(f"FAIL: verifier did not emit JSON: {exc}", file=sys.stderr)
        if process.stderr:
            print(process.stderr, file=sys.stderr)
        return 2
    (project / "results/final_verification_summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": result.get("status"),
        "pass_count": result.get("pass_count"),
        "check_count": result.get("check_count"),
    }, sort_keys=True))
    return 0 if process.returncode == 0 and result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
