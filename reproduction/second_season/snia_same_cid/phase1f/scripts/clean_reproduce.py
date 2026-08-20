#!/usr/bin/env python3
"""Reproduce all scientific outputs in a clean copy and compare bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile


GENERATED_OUTPUTS = (
    "results/EXECUTION_STATUS.json",
    "results/audit_summary.json",
    "results/contract_verification.json",
    "results/evidence_semantics.json",
    "results/filter_calibration_mapping.tsv",
    "results/input_candidate_map.tsv",
    "results/input_inventory.json",
    "results/observation_match_evidence.tsv",
    "results/pair_dependency_classification.tsv",
    "results/public_asset_availability.tsv",
    "results/row_input_profile.tsv",
    "results/run_environment.json",
    "results/series_configuration_lineage.tsv",
    "results/shared_dependency_ledger.tsv",
    "results/source_verification.json",
    "results/posthoc_cross_cid_negative_control_pairs.tsv",
    "results/posthoc_cross_cid_negative_control_by_directory_pair.tsv",
    "results/posthoc_cross_cid_negative_control_summary.json",
    "results/independent_verification.json",
    "results/unit_tests_summary.json",
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    source_repo = args.pantheonplus.resolve()
    project = pathlib.Path(__file__).resolve().parents[1]

    missing = [relative for relative in GENERATED_OUTPUTS if not (project / relative).is_file()]
    if missing:
        print(json.dumps({"status": "FAIL", "missing_expected_outputs": missing}, sort_keys=True))
        return 2
    original_hashes = {relative: digest(project / relative) for relative in GENERATED_OUTPUTS}

    command_specs = (
        ("main_audit", "scripts/run_audit.py"),
        ("posthoc_negative_control", "scripts/run_posthoc_negative_control.py"),
        ("second_implementation", "scripts/independent_verify.py"),
        ("unit_tests", "scripts/run_tests.py"),
    )
    command_records: list[dict[str, object]] = []
    log_sections: list[str] = []
    with tempfile.TemporaryDirectory(prefix="phase1f-clean-reproduction-") as temporary:
        clean_project = pathlib.Path(temporary) / project.name
        shutil.copytree(
            project,
            clean_project,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        for relative in GENERATED_OUTPUTS:
            (clean_project / relative).unlink()

        for name, script in command_specs:
            process = subprocess.run(
                [sys.executable, script, "--pantheonplus", str(source_repo)],
                cwd=clean_project,
                text=True,
                capture_output=True,
                check=False,
            )
            command_records.append({
                "name": name,
                "returncode": process.returncode,
                "status": "PASS" if process.returncode == 0 else "FAIL",
            })
            log_sections.extend((
                f"[{name}] returncode={process.returncode}",
                process.stdout.rstrip(),
                process.stderr.rstrip(),
            ))
            if process.returncode != 0:
                break

        comparisons = []
        for relative in GENERATED_OUTPUTS:
            reproduced = clean_project / relative
            clean_hash = digest(reproduced) if reproduced.is_file() else None
            comparisons.append({
                "path": relative,
                "original_sha256": original_hashes[relative],
                "reproduced_sha256": clean_hash,
                "status": "PASS" if clean_hash == original_hashes[relative] else "FAIL",
            })

    command_pass = len(command_records) == len(command_specs) and all(
        record["status"] == "PASS" for record in command_records
    )
    identical_count = sum(record["status"] == "PASS" for record in comparisons)
    summary = {
        "status": "PASS" if command_pass and identical_count == len(GENERATED_OUTPUTS) else "FAIL",
        "verification_type": "CLEAN_DIRECTORY_FULL_PIPELINE_BYTE_REPRODUCTION",
        "external_source_repository_not_copied": True,
        "generated_output_count": len(GENERATED_OUTPUTS),
        "byte_identical_output_count": identical_count,
        "commands": command_records,
        "outputs": comparisons,
    }
    (project / "results/clean_reproduction.log").write_text(
        "\n".join(section for section in log_sections if section) + "\n", encoding="utf-8"
    )
    (project / "results/clean_reproduction_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": summary["status"],
        "byte_identical_output_count": identical_count,
        "generated_output_count": len(GENERATED_OUTPUTS),
    }, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
