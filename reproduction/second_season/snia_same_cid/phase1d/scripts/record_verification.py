#!/usr/bin/env python3
"""Intentionally record one read-only closure evaluation before packaging."""

from __future__ import annotations

import json
import pathlib

import auditlib
import verify_results


def main() -> int:
    project = pathlib.Path(__file__).resolve().parents[1]
    result = verify_results.run_read_only(project)
    if result["status"] != "PASS":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    auditlib.write_json(
        project / "results" / "final_verification_summary.json", result
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
