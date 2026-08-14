#!/usr/bin/env python3
"""Run the audit in an isolated project copy and compare the summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

from auditlib import write_json


def run(command: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def compare_audit_summaries(
    original_bytes: bytes, reproduced_bytes: bytes
) -> dict[str, object]:
    original = json.loads(original_bytes)
    reproduced = json.loads(reproduced_bytes)
    semantically_identical = original == reproduced
    bytes_identical = original_bytes == reproduced_bytes
    return {
        "audit_summary_semantically_identical": semantically_identical,
        "audit_summary_bytes_identical": bytes_identical,
        "original_audit_summary_sha256": hashlib.sha256(
            original_bytes
        ).hexdigest(),
        "reproduced_audit_summary_sha256": hashlib.sha256(
            reproduced_bytes
        ).hexdigest(),
        "byte_equality_explanation": (
            "Deterministic serialized bytes are identical."
            if bytes_identical
            else (
                "Serialized bytes differ, but clean-reproduction status is "
                "gated by parsed JSON semantic equality; both hashes are "
                "recorded for diagnosis."
            )
        ),
        "original_status": original["status"],
        "reproduced_status": reproduced["status"],
        "status": "PASS" if semantically_identical else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=pathlib.Path, required=True)
    parser.add_argument("--upstream", type=pathlib.Path)
    args = parser.parse_args()
    source_project = pathlib.Path(__file__).resolve().parents[1]
    workdir = args.workdir.resolve()
    if workdir.exists():
        print(f"FAIL: workdir already exists: {workdir}", file=sys.stderr)
        return 2
    workdir.mkdir(parents=True)
    project = workdir / source_project.name
    shutil.copytree(
        source_project,
        project,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            "__pycache__",
            "*.pyc",
            "build",
            "dist",
            "MANIFEST.tsv",
            "SHA256SUMS.txt",
        ),
    )
    shutil.rmtree(project / "results")
    (project / "results").mkdir()
    shutil.copy2(
        source_project / "results" / "README.md",
        project / "results" / "README.md",
    )

    if args.upstream is None:
        upstream = workdir / "H0DN_FROZEN"
        acquisition = run(
            [
                sys.executable,
                "scripts/source_tools.py",
                "--destination",
                str(upstream),
                "--manifest",
                "provenance/SOURCE_LOCK.tsv",
            ],
            project,
        )
    else:
        upstream = args.upstream.resolve()
        acquisition = run(
            [
                sys.executable,
                "scripts/source_tools.py",
                "--upstream",
                str(upstream),
                "--manifest",
                "provenance/SOURCE_LOCK.tsv",
            ],
            project,
        )
    tests = run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        project,
    )
    audit = run(
        [
            sys.executable,
            "scripts/run_audit.py",
            "--upstream",
            str(upstream),
        ],
        project,
    )
    (project / "results" / "run_stdout.log").write_text(
        audit.stdout, encoding="utf-8"
    )
    (project / "results" / "run_stderr.log").write_text(
        audit.stderr, encoding="utf-8"
    )
    original_path = source_project / "results" / "audit_summary.json"
    reproduced_path = project / "results" / "audit_summary.json"
    comparison = compare_audit_summaries(
        original_path.read_bytes(), reproduced_path.read_bytes()
    )
    source_record = json.loads(
        (project / "results" / "source_verification.json").read_text(
            encoding="utf-8"
        )
    )
    record = {
        "isolated_project_root": project.name,
        "upstream_commit": source_record["commit"],
        "source_verification_returncode": acquisition.returncode,
        "unit_test_returncode": tests.returncode,
        "audit_returncode": audit.returncode,
        **comparison,
    }

    # The child copy needs the comparison record before its closure verifier
    # runs. The source copy is updated with the completed workflow below.
    write_json(
        project / "results" / "clean_reproduction_summary.json",
        record,
    )
    record_verification = run(
        [sys.executable, "scripts/verify_results.py", "--record-results"],
        project,
    )
    manifest_generation = run(
        [sys.executable, "scripts/finalize_package.py", "--write-manifests"],
        project,
    )
    live_verification = run(
        [sys.executable, "scripts/verify_results.py"],
        project,
    )
    record["record_verification_returncode"] = record_verification.returncode
    record["manifest_generation_returncode"] = manifest_generation.returncode
    record["live_verification_returncode"] = live_verification.returncode
    write_json(
        source_project / "results" / "clean_reproduction_summary.json",
        record,
    )
    log = (
        "SOURCE VERIFICATION\n"
        + acquisition.stdout
        + acquisition.stderr
        + "\nUNIT TESTS\n"
        + tests.stdout
        + tests.stderr
        + "\nAUDIT\n"
        + audit.stdout
        + audit.stderr
        + "\nCLOSURE RECORD VERIFICATION\n"
        + record_verification.stdout
        + record_verification.stderr
        + "\nMANIFEST GENERATION\n"
        + manifest_generation.stdout
        + manifest_generation.stderr
        + "\nREAD-ONLY LIVE VERIFICATION\n"
        + live_verification.stdout
        + live_verification.stderr
    )
    (
        source_project / "results" / "clean_reproduction.log"
    ).write_text(log, encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if comparison["audit_summary_semantically_identical"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
