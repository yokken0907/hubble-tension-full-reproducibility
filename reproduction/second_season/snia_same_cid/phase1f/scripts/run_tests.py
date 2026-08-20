#!/usr/bin/env python3
"""Run the Phase 1F unit suite and record its machine-readable outcome."""

from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import sys
import unittest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    os.environ["PANTHEONPLUS_REPO"] = str(args.pantheonplus.resolve())

    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(project / "tests"))
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    log = stream.getvalue()
    (project / "results/unit_tests.log").write_text(log, encoding="utf-8")
    summary = {
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "test_count": result.testsRun,
        "failure_count": len(result.failures),
        "error_count": len(result.errors),
        "skipped_count": len(result.skipped),
        "expected_failure_count": len(result.expectedFailures),
        "unexpected_success_count": len(result.unexpectedSuccesses),
        "scope": "UNIT_AND_FIXED-SOURCE_INTEGRATION_TESTS",
    }
    (project / "results/unit_tests_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sys.stdout.write(log)
    print(json.dumps(summary, sort_keys=True))
    return 0 if result.wasSuccessful() and result.testsRun == 50 else 2


if __name__ == "__main__":
    raise SystemExit(main())
