#!/usr/bin/env python3
"""Run Phase 1B in an isolated copy and compare deterministic artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

from auditlib import write_json


CORE_ARTIFACTS = (
    "EXECUTION_STATUS.json",
    "audit_summary.json",
    "candidate_evidence.tsv",
    "covariance_diagonal_required_rows.tsv",
    "covariance_lineage.json",
    "error_field_discrepancy_rows.tsv",
    "error_field_discrepancy_summary.json",
    "input_inventory.json",
    "multirow_group_summary.tsv",
    "multirow_row_evidence.tsv",
    "row_mapping.tsv",
    "row_mapping_dependency.tsv",
    "row_mapping_dependency_summary.json",
)


def run(command: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    environment = dict(__import__("os").environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def semantic_value(path: pathlib.Path) -> object:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix == ".tsv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))
    return path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=pathlib.Path, required=True)
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    source = pathlib.Path(__file__).resolve().parents[1]
    workdir = args.workdir.resolve()
    if workdir.exists():
        print(f"FAIL: workdir already exists: {workdir}", file=sys.stderr)
        return 2
    workdir.mkdir(parents=True)
    child = workdir / source.name
    shutil.copytree(
        source,
        child,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            ".pytest_cache",
            "__pycache__",
            "*.pyc",
            "MANIFEST.tsv",
            "SHA256SUMS.txt",
            "results",
        ),
    )
    (child / "results").mkdir()
    shutil.copy2(source / "results" / "README.md", child / "results" / "README.md")
    audit = run(
        [
            sys.executable,
            "scripts/run_audit.py",
            "--h0dn",
            str(args.h0dn.resolve()),
            "--pantheonplus",
            str(args.pantheonplus.resolve()),
        ],
        child,
    )
    tests = run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        child,
    )
    comparisons: dict[str, dict[str, str | bool]] = {}
    for filename in CORE_ARTIFACTS:
        original = (source / "results" / filename).read_bytes()
        reproduced_path = child / "results" / filename
        reproduced = reproduced_path.read_bytes() if reproduced_path.is_file() else b""
        comparisons[filename] = {
            "bytes_identical": original == reproduced,
            "semantic_identical": (
                reproduced_path.is_file()
                and semantic_value(source / "results" / filename)
                == semantic_value(reproduced_path)
            ),
            "original_sha256": sha256_bytes(original),
            "reproduced_sha256": sha256_bytes(reproduced),
        }
    all_identical = all(
        row["bytes_identical"] for row in comparisons.values()
    )
    all_semantically_identical = all(
        row["semantic_identical"] for row in comparisons.values()
    )
    status = (
        "PASS"
        if audit.returncode == 0
        and tests.returncode == 0
        and all_identical
        and all_semantically_identical
        else "FAIL"
    )
    summary = {
        "all_core_artifacts_bytes_identical": all_identical,
        "all_core_artifacts_semantically_identical": (
            all_semantically_identical
        ),
        "comparison_scope": (
            "semantic equality is recorded separately from byte equality "
            "for deterministic JSON/TSV outputs"
        ),
        "artifact_comparisons": comparisons,
        "audit_returncode": audit.returncode,
        "isolated_project_name": child.name,
        "source_inputs_reused_read_only": True,
        "status": status,
        "unit_test_returncode": tests.returncode,
    }
    write_json(source / "results" / "clean_reproduction_summary.json", summary)
    (source / "results" / "clean_reproduction.log").write_text(
        "AUDIT STDOUT\n"
        + audit.stdout
        + "\nAUDIT STDERR\n"
        + audit.stderr
        + "\nUNIT TESTS STDOUT\n"
        + tests.stdout
        + "\nUNIT TESTS STDERR\n"
        + tests.stderr,
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
