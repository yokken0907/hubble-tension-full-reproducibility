#!/usr/bin/env python3
"""Run the audit from a clean package copy and compare result bytes."""

from __future__ import annotations

import argparse
import filecmp
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile


RESULTS = (
    "EXECUTION_STATUS.json",
    "alternative_basis_checks.json",
    "audit_summary.json",
    "component_diagnostics.json",
    "contrast_definition.tsv",
    "contract_verification.json",
    "covariance_baselines.json",
    "covariance_lineage.json",
    "dependency_mapping_verification.json",
    "input_inventory.json",
    "known_phase1a_reproduction.json",
    "numerical_crosschecks.json",
    "orthogonal_invariance.tsv",
    "orthogonal_invariance_summary.json",
    "quadratic_forms.tsv",
    "run_environment.json",
    "source_verification.json",
    "upstream_audit_dependency_verification.json",
    "mapped_submatrix_asymmetry_diagnostic.json",
    "mapped_submatrix_asymmetry_sensitivity.tsv",
    "printed_vs_high_precision_contrast_diagnostic.json",
    "printed_vs_high_precision_contrast_diagnostic.tsv",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--phase1a-archive", type=pathlib.Path, required=True)
    parser.add_argument("--phase1b-archive", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    output_results = project / "results"
    with tempfile.TemporaryDirectory(prefix="h0dn_phase1c_clean_") as temp:
        replica = pathlib.Path(temp) / project.name
        shutil.copytree(
            project,
            replica,
            ignore=shutil.ignore_patterns(
                ".git",
                ".pytest_cache",
                "__pycache__",
                "*.pyc",
                "MANIFEST.tsv",
                "SHA256SUMS.txt",
            ),
        )
        shutil.rmtree(replica / "results")
        (replica / "results").mkdir()
        command = [
            sys.executable,
            str(replica / "scripts" / "run_audit.py"),
            "--h0dn",
            str(args.h0dn.resolve()),
            "--pantheonplus",
            str(args.pantheonplus.resolve()),
            "--phase1a-archive",
            str(args.phase1a_archive.resolve()),
            "--phase1b-archive",
            str(args.phase1b_archive.resolve()),
        ]
        main_completed = subprocess.run(
            command, capture_output=True, text=True, check=False
        )
        posthoc_command = [
            sys.executable,
            str(
                replica
                / "scripts"
                / "run_posthoc_precision_asymmetry.py"
            ),
            "--h0dn",
            str(args.h0dn.resolve()),
            "--pantheonplus",
            str(args.pantheonplus.resolve()),
        ]
        posthoc_completed = subprocess.run(
            posthoc_command,
            capture_output=True,
            text=True,
            check=False,
        )
        log = (
            f"main_return_code={main_completed.returncode}\n"
            f"main_stdout:\n{main_completed.stdout}"
            f"main_stderr:\n{main_completed.stderr}"
            f"posthoc_return_code={posthoc_completed.returncode}\n"
            f"posthoc_stdout:\n{posthoc_completed.stdout}"
            f"posthoc_stderr:\n{posthoc_completed.stderr}"
        )
        (output_results / "clean_reproduction.log").write_text(
            log, encoding="utf-8"
        )
        comparisons = []
        for filename in RESULTS:
            original = output_results / filename
            reproduced = replica / "results" / filename
            identical = (
                original.is_file()
                and reproduced.is_file()
                and filecmp.cmp(original, reproduced, shallow=False)
            )
            comparisons.append(
                {"path": f"results/{filename}", "byte_identical": identical}
            )
        status = (
            "PASS"
            if main_completed.returncode == 0
            and posthoc_completed.returncode == 0
            and all(row["byte_identical"] for row in comparisons)
            else "FAIL"
        )
        summary = {
            "clean_main_run_return_code": main_completed.returncode,
            "clean_posthoc_run_return_code": posthoc_completed.returncode,
            "compared_file_count": len(comparisons),
            "byte_identical_file_count": sum(
                row["byte_identical"] for row in comparisons
            ),
            "comparisons": comparisons,
            "status": status,
        }
        (output_results / "clean_reproduction_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"status": status}, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
