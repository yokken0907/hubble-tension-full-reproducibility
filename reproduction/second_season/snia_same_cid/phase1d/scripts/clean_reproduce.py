#!/usr/bin/env python3
"""Re-run Phase 1D in an isolated package copy and compare result bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile


RESULT_FILES = (
    "EXECUTION_STATUS.json",
    "audit_summary.json",
    "candidate_file_evidence.tsv",
    "contract_verification.json",
    "group_lineage.tsv",
    "independent_verification.json",
    "input_inventory.json",
    "pair_observation_overlap.tsv",
    "photometry_scan_summary.json",
    "pipeline_anchor_evidence.tsv",
    "posthoc_cid_only_candidate_files.tsv",
    "posthoc_cid_only_crosswalk_diagnostic.tsv",
    "posthoc_cid_only_crosswalk_independent_verification.json",
    "posthoc_cid_only_crosswalk_summary.json",
    "referenced_asset_availability.tsv",
    "row_lineage.tsv",
    "run_environment.json",
    "shared_dependency_ledger.tsv",
    "source_verification.json",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    original_results = project / "results"
    log_lines = [
        "Phase 1D isolated clean reproduction",
        "source package copied without prior results or manifests",
    ]
    commands = (
        (
            "run_audit.py",
            "--h0dn",
            str(args.h0dn.resolve()),
            "--pantheonplus",
            str(args.pantheonplus.resolve()),
        ),
        (
            "independent_verify.py",
            "--h0dn",
            str(args.h0dn.resolve()),
            "--pantheonplus",
            str(args.pantheonplus.resolve()),
        ),
        (
            "run_posthoc_cid_only_crosswalk.py",
            "--pantheonplus",
            str(args.pantheonplus.resolve()),
        ),
        (
            "verify_posthoc_cid_only_crosswalk.py",
            "--pantheonplus",
            str(args.pantheonplus.resolve()),
        ),
    )

    def ignore(_directory: str, names: list[str]) -> set[str]:
        excluded = {
            name
            for name in names
            if name in {
                "results",
                "MANIFEST.tsv",
                "SHA256SUMS.txt",
                "__pycache__",
                ".pytest_cache",
            }
            or name.endswith((".pyc", ".pyo"))
        }
        return excluded

    checks: dict[str, bool] = {}
    digests: dict[str, str] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="h0dn-phase1d-clean-") as tmp:
            reproduced = pathlib.Path(tmp) / project.name
            shutil.copytree(project, reproduced, ignore=ignore)
            for command in commands:
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(reproduced / "scripts" / command[0]),
                        *command[1:],
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                label = command[0]
                log_lines.append(
                    f"{label}: exit=0 stdout={completed.stdout.strip()}"
                )
            for name in RESULT_FILES:
                original = original_results / name
                regenerated = reproduced / "results" / name
                passed = (
                    original.is_file()
                    and regenerated.is_file()
                    and original.read_bytes() == regenerated.read_bytes()
                )
                checks[name] = passed
                if regenerated.is_file():
                    digests[name] = sha256(regenerated)
                log_lines.append(f"byte_identity {name}: {passed}")
    except (OSError, subprocess.CalledProcessError) as exc:
        log_lines.append(f"execution_failure: {type(exc).__name__}: {exc}")
        result = {
            "byte_identical_file_count": sum(checks.values()),
            "checked_result_file_count": len(RESULT_FILES),
            "checks": checks,
            "regenerated_sha256": digests,
            "status": "FAIL",
        }
        write_json(original_results / "clean_reproduction_summary.json", result)
        (original_results / "clean_reproduction.log").write_text(
            "\n".join(log_lines) + "\n", encoding="utf-8"
        )
        print(json.dumps({"status": "FAIL"}, sort_keys=True))
        return 2

    result = {
        "byte_identical_file_count": sum(checks.values()),
        "checked_result_file_count": len(RESULT_FILES),
        "checks": checks,
        "regenerated_sha256": digests,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    write_json(original_results / "clean_reproduction_summary.json", result)
    (original_results / "clean_reproduction.log").write_text(
        "\n".join(log_lines) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "byte_identical_file_count": result[
                    "byte_identical_file_count"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
