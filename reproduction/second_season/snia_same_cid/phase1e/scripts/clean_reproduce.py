#!/usr/bin/env python3
"""Re-run Phase 1E in an isolated package copy and compare protected bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile


PROTECTED_RESULTS = (
    "EXECUTION_STATUS.json",
    "audit_summary.json",
    "catalog_and_target_inventory.json",
    "contract_verification.json",
    "holdout_anchor_evidence.tsv",
    "holdout_candidate_rows.tsv",
    "independent_verification.json",
    "inferred_crosswalk.tsv",
    "label_header_diagnostic.tsv",
    "photometry_scan_summary.json",
    "run_environment.json",
    "source_verification.json",
    "status_semantics.json",
    "target_candidate_file_evidence.tsv",
    "target_row_application.tsv",
)


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    source = args.pantheonplus.resolve()
    log = [
        "Phase 1E isolated clean reproduction",
        "copied package excludes prior results, manifests, and bytecode",
    ]

    def ignore(directory: str, names: list[str]) -> set[str]:
        if pathlib.Path(directory).name == "results":
            return {name for name in names if name != "README.md"}
        return {
            name
            for name in names
            if name in {"MANIFEST.tsv", "SHA256SUMS.txt", "__pycache__", ".pytest_cache"}
            or name.endswith((".pyc", ".pyo"))
        }

    checks: dict[str, bool] = {}
    hashes: dict[str, str] = {}
    test_pass = False
    try:
        with tempfile.TemporaryDirectory(prefix="h0dn-phase1e-clean-") as temp:
            replica = pathlib.Path(temp) / project.name
            shutil.copytree(project, replica, ignore=ignore)
            commands = (
                [sys.executable, str(replica / "scripts/run_audit.py"), "--pantheonplus", str(source)],
                [sys.executable, str(replica / "scripts/independent_verify.py"), "--pantheonplus", str(source)],
            )
            for command in commands:
                completed = subprocess.run(command, check=True, capture_output=True, text=True)
                log.append(f"{pathlib.Path(command[1]).name}: exit=0 stdout={completed.stdout.strip()}")
            tests = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", str(replica / "tests"), "-v"],
                check=False,
                capture_output=True,
                text=True,
            )
            test_pass = tests.returncode == 0
            log.append(f"unit_tests: exit={tests.returncode} passed={test_pass}")
            if tests.stdout.strip():
                log.append("unit_tests_stdout:")
                log.extend(tests.stdout.rstrip().splitlines())
            if tests.stderr.strip():
                log.append("unit_tests_stderr:")
                log.extend(tests.stderr.rstrip().splitlines())
            for name in PROTECTED_RESULTS:
                original = project / "results" / name
                regenerated = replica / "results" / name
                passed = original.is_file() and regenerated.is_file() and original.read_bytes() == regenerated.read_bytes()
                checks[name] = passed
                if regenerated.is_file():
                    hashes[name] = sha(regenerated)
                log.append(f"byte_identity {name}: {passed}")
    except (OSError, subprocess.CalledProcessError) as exc:
        log.append(f"execution_failure: {type(exc).__name__}: {exc}")

    passed = test_pass and len(checks) == len(PROTECTED_RESULTS) and all(checks.values())
    summary = {
        "protected_result_count": len(PROTECTED_RESULTS),
        "byte_identical_result_count": sum(checks.values()),
        "checks": checks,
        "regenerated_sha256": hashes,
        "unit_tests_pass": test_pass,
        "status": "PASS" if passed else "FAIL",
    }
    write_json(project / "results/clean_reproduction_summary.json", summary)
    (project / "results/clean_reproduction.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "byte_identical_result_count": summary["byte_identical_result_count"], "protected_result_count": summary["protected_result_count"]}, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
