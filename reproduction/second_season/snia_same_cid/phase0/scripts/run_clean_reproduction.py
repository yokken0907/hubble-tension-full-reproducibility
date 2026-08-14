#!/usr/bin/env python3
"""Run Phase 0 from a new audit copy, venv, and upstream checkout."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any, Sequence


PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from phase0lib import FINAL_PASS_STATUS, UPSTREAM_COMMIT, write_json  # noqa: E402


FLOAT_KEYS = {
    "alpha": 2.0e-12,
    "alpha_error": 2.0e-12,
    "baseline_h0_value": 2.0e-10,
    "baseline_h0_error": 2.0e-10,
    "expanded_h0_value": 2.0e-10,
    "expanded_h0_error": 2.0e-10,
    "hubble_flow_minimum_chi2": 2.0e-9,
    "chi2_constant_omitted_by_scalar_network": 2.0e-9,
    "profile_identity_max_absolute_residual": 2.0e-9,
    "expanded_vs_scalar_max_abs_parameter_difference": 2.0e-9,
    "expanded_vs_scalar_max_abs_parameter_covariance_difference": 2.0e-9,
    "permutation_maximum_tested_difference": 2.0e-9,
}


def run(
    command: Sequence[str],
    *,
    cwd: pathlib.Path,
    transcript: list[str],
) -> subprocess.CompletedProcess[str]:
    transcript.append("$ " + " ".join(command))
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    if completed.stdout:
        transcript.append(completed.stdout.rstrip())
    if completed.stderr:
        transcript.append(completed.stderr.rstrip())
    transcript.append(f"[exit {completed.returncode}]")
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit {completed.returncode}: "
            + " ".join(command)
        )
    return completed


def copy_audit_source(destination: pathlib.Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {
            name
            for name in names
            if name
            in {
                ".git",
                ".venv",
                "__pycache__",
                "MANIFEST.tsv",
                "SHA256SUMS.txt",
                "results",
            }
            or name.endswith(".pyc")
        }
        return ignored

    shutil.copytree(PROJECT, destination, ignore=ignore)
    (destination / "results").mkdir()


def compare_summaries(
    reference: dict[str, Any], clean: dict[str, Any]
) -> tuple[str, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    for key in ("status", "object_count", "hubble_flow_ndof", "boundary_marker"):
        matches = reference[key] == clean[key]
        checks.append(
            {
                "quantity": key,
                "reference": reference[key],
                "clean": clean[key],
                "tolerance": 0,
                "absolute_difference": 0 if matches else None,
                "status": "PASS" if matches else "FAIL",
            }
        )
    for key, tolerance in FLOAT_KEYS.items():
        difference = abs(float(reference[key]) - float(clean[key]))
        checks.append(
            {
                "quantity": key,
                "reference": reference[key],
                "clean": clean[key],
                "tolerance": tolerance,
                "absolute_difference": difference,
                "status": "PASS" if difference <= tolerance else "FAIL",
            }
        )
    status = (
        "PASS"
        if all(check["status"] == "PASS" for check in checks)
        else "FAIL"
    )
    return status, checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=pathlib.Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    result_dir = PROJECT / "results"
    transcript: list[str] = []
    summary: dict[str, Any] = {
        "status": "FAIL",
        "upstream_commit": UPSTREAM_COMMIT,
        "scientific_status": "NOT_RUN",
        "comparison_status": "NOT_RUN",
        "unit_test_count": 0,
    }
    try:
        if workspace.exists():
            raise RuntimeError(
                f"Refusing to overwrite existing clean workspace: {workspace}"
            )
        workspace.mkdir(parents=True)
        work = workspace / "audit"
        upstream = workspace / "H0DN_CLEAN"
        venv = workspace / ".venv"
        copy_audit_source(work)
        reference = json.loads(
            (PROJECT / "results" / "phase0_summary.json").read_text(
                encoding="utf-8"
            )
        )

        run(
            [sys.executable, "-m", "venv", str(venv)],
            cwd=workspace,
            transcript=transcript,
        )
        python = venv / "bin" / "python"
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(work / "requirements-lock.txt"),
            ],
            cwd=work,
            transcript=transcript,
        )
        version_check = run(
            [
                str(python),
                "-c",
                (
                    "import numpy,scipy,pandas;"
                    "print(numpy.__version__,scipy.__version__,pandas.__version__)"
                ),
            ],
            cwd=work,
            transcript=transcript,
        )
        if version_check.stdout.strip() != "2.4.2 1.17.0 3.0.0":
            raise RuntimeError(
                "Fresh environment versions differ from requirements-lock.txt"
            )
        run(
            [
                str(python),
                "scripts/acquire_upstream.py",
                "--destination",
                str(upstream),
            ],
            cwd=work,
            transcript=transcript,
        )
        phase = run(
            [
                str(python),
                "scripts/run_phase0.py",
                "--upstream",
                str(upstream),
            ],
            cwd=work,
            transcript=transcript,
        )
        tests = run(
            [
                str(python),
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ],
            cwd=work,
            transcript=transcript,
        )
        test_text = tests.stdout + tests.stderr
        match = re.search(r"Ran (\d+) tests?", test_text)
        if match is None or int(match.group(1)) != 8 or "\nOK" not in test_text:
            raise RuntimeError("Fresh unit-test record is incomplete")
        run(
            [
                str(python),
                "scripts/verify_results.py",
                "--upstream",
                str(upstream),
                "--skip-package-integrity",
                "--skip-clean-record",
                "--no-write-summary",
            ],
            cwd=work,
            transcript=transcript,
        )
        clean = json.loads(
            (work / "results" / "phase0_summary.json").read_text(
                encoding="utf-8"
            )
        )
        comparison_status, comparisons = compare_summaries(reference, clean)
        summary = {
            "status": (
                "PASS"
                if clean["status"] == FINAL_PASS_STATUS
                and comparison_status == "PASS"
                else "FAIL"
            ),
            "upstream_commit": UPSTREAM_COMMIT,
            "scientific_status": clean["status"],
            "comparison_status": comparison_status,
            "unit_test_count": int(match.group(1)),
            "environment_versions": version_check.stdout.strip(),
            "clean_workspace_policy": (
                "retained outside the delivered project for inspection"
            ),
            "comparisons": comparisons,
        }
        if summary["status"] != "PASS":
            raise RuntimeError("Clean/reference result comparison failed")
    except Exception as exc:
        summary["error_type"] = type(exc).__name__
        summary["error"] = str(exc)
        transcript.append(f"CLEAN_REPRODUCTION_FAIL: {type(exc).__name__}: {exc}")
        write_json(result_dir / "clean_reproduction_summary.json", summary)
        (result_dir / "full_clean_reproduction.log").write_text(
            "\n".join(transcript) + "\n", encoding="utf-8"
        )
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    transcript.append(
        f"CLEAN_REPRODUCTION_PASS: {summary['scientific_status']}"
    )
    write_json(result_dir / "clean_reproduction_summary.json", summary)
    (result_dir / "full_clean_reproduction.log").write_text(
        "\n".join(transcript) + "\n", encoding="utf-8"
    )
    print(
        f"PASS: fresh venv, fresh upstream, {summary['unit_test_count']} tests, "
        f"comparison {summary['comparison_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
