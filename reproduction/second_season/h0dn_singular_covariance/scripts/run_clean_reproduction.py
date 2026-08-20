#!/usr/bin/env python3
"""Run the entire audit in a new checkout with fresh inputs and results."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import pathlib
import shutil
import subprocess
import sys
from typing import Any, TextIO


EXPECTED_UPSTREAM_COMMIT = "cc0a4b9f36e65470d514f254a3c5cffa463fbd94"


class CleanRunFailure(RuntimeError):
    """Raised when an isolated reproduction stage fails."""


class NumericalDrift(CleanRunFailure):
    """Raised when a scientific value exceeds its fixed tolerance."""


def read_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise CleanRunFailure(f"Expected JSON object: {path}")
    return value


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t", strict=True))


def run_stage(
    name: str,
    command: list[str],
    *,
    cwd: pathlib.Path,
    log: TextIO,
) -> None:
    rendered = " ".join(command)
    print(f"START {name}", flush=True)
    log.write(f"\n===== START {name} =====\n")
    log.write(f"cwd: {cwd}\n")
    log.write(f"command: {rendered}\n")
    log.flush()
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    log.write(f"exit_code: {completed.returncode}\n")
    log.write(f"===== END {name} =====\n")
    log.flush()
    if completed.returncode != 0:
        raise CleanRunFailure(
            f"{name} failed with exit code {completed.returncode}"
        )
    print(f"PASS {name}", flush=True)


def require_close(
    name: str, actual: float, expected: float, tolerance: float
) -> None:
    if not math.isfinite(actual) or abs(actual - expected) > tolerance:
        raise NumericalDrift(
            f"{name}: actual={actual!r}, expected={expected!r}, "
            f"absolute_tolerance={tolerance!r}"
        )


def check_fixed_values(project: pathlib.Path) -> dict[str, Any]:
    results = project / "results"
    baseline = read_json(results / "baseline_reproduction.json")["upstream"]
    require_close(
        "baseline_h0", float(baseline["h0_value"]), 73.49875364, 5.0e-8
    )
    require_close(
        "baseline_h0_error",
        float(baseline["h0_error"]),
        0.80880003,
        5.0e-8,
    )
    if (
        int(baseline["neq"]),
        int(baseline["npars"]),
        int(baseline["covar_rank"]),
        int(baseline["covar_nullity"]),
    ) != (255, 64, 183, 72):
        raise NumericalDrift("baseline dimensions/rank/nullity changed")

    representations = read_tsv(
        results / "representation_invariance.tsv"
    )
    standardization = next(
        row
        for row in representations
        if row["representation_family"] == "diagonal_row_standardization"
    )
    require_close(
        "row_standardization_delta_h0",
        float(standardization["delta_h0"]),
        -0.05244542,
        5.0e-8,
    )
    if standardization["invariance_status"] != "FAIL":
        raise NumericalDrift("row-standardization FAIL was not retained")

    posthoc = read_json(results / "posthoc_row_scaling_diagnostic.json")
    support = posthoc["support_constraint"]
    require_close(
        "nullspace_projection_norm",
        float(support["constraint_target_l2_norm"]),
        0.18874908,
        5.0e-8,
    )
    interaction = posthoc["cepheid_interaction_decomposition"]
    if (
        int(interaction["host_count"]),
        int(interaction["anchor_count"]),
        int(interaction["cell_count"]),
    ) != (37, 3, 111):
        raise NumericalDrift("interaction-table dimensions changed")
    if (
        float(interaction["projection_closure_max_absolute_error"])
        >= 1.0e-10
    ):
        raise NumericalDrift("interaction closure exceeded 1e-10 mag")

    exploratory = read_json(
        results / "exploratory_variance_component_summary.json"
    )
    reml = exploratory["original_representation"]["reml_fit"]
    require_close(
        "reml_tau", float(reml["tau"]), 0.02224362, 5.0e-8
    )
    delta_h0 = float(reml["h0_value"]) - float(baseline["h0_value"])
    require_close(
        "exploratory_conditional_delta_h0",
        delta_h0,
        -0.00442767,
        5.0e-8,
    )

    ablations = read_tsv(
        results / "covariance_component_ablation.tsv"
    )
    sn_link = next(
        row
        for row in ablations
        if row["component_id"] == "sn1a_hubble_flow_link_variance"
    )
    if (
        sn_link["interpretation_status"]
        != "PSEUDOINVERSE_DISCARDED_CONSTRAINT"
        or int(sn_link["covar_rank"]) != 182
        or sn_link["matched_leave_one_block_out_match_status"] != "PASS"
    ):
        raise NumericalDrift(
            "SN-Ia link rank/drop/leave-one-out classification changed"
        )

    permutations = [
        row
        for row in representations
        if row["representation_family"]
        == "simultaneous_row_column_permutation"
    ]
    maximum_permutation_delta = max(
        float(row["absolute_delta_h0"]) for row in permutations
    )
    if len(permutations) != 32 or maximum_permutation_delta >= 1.0e-8:
        raise NumericalDrift("permutation gate changed")

    return {
        "baseline_h0": float(baseline["h0_value"]),
        "baseline_h0_error": float(baseline["h0_error"]),
        "equation_count": int(baseline["neq"]),
        "parameter_count": int(baseline["npars"]),
        "covariance_rank": int(baseline["covar_rank"]),
        "covariance_nullity": int(baseline["covar_nullity"]),
        "row_standardization_delta_h0": float(
            standardization["delta_h0"]
        ),
        "row_standardization_status": standardization[
            "invariance_status"
        ],
        "permutation_pass_count": sum(
            row["invariance_status"] == "PASS" for row in permutations
        ),
        "permutation_maximum_absolute_delta_h0": (
            maximum_permutation_delta
        ),
        "nullspace_projection_norm": float(
            support["constraint_target_l2_norm"]
        ),
        "support_status": support["status"],
        "interaction_dimensions": [37, 3, 111],
        "interaction_maximum_closure_error": float(
            interaction["projection_closure_max_absolute_error"]
        ),
        "reml_tau": float(reml["tau"]),
        "exploratory_conditional_delta_h0": delta_h0,
        "sn1a_link_interpretation_status": sn_link[
            "interpretation_status"
        ],
        "sn1a_link_covariance_rank": int(sn_link["covar_rank"]),
        "sn1a_link_leave_one_out_match": sn_link[
            "matched_leave_one_block_out_match_status"
        ],
    }


def write_summary(path: pathlib.Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        handle.write("\n")


def export_results(
    clean_project: pathlib.Path,
    target_project: pathlib.Path,
    log_path: pathlib.Path,
    summary_path: pathlib.Path,
) -> None:
    target_results = target_project / "results"
    target_results.mkdir(parents=True, exist_ok=True)
    for source in sorted((clean_project / "results").iterdir()):
        if source.is_file():
            shutil.copy2(source, target_results / source.name)
    for report in ["REPORT.md", "POSTHOC_REPORT.md", "EXPLORATORY_REPORT.md"]:
        shutil.copy2(clean_project / report, target_project / report)
    shutil.copy2(log_path, target_results / "full_clean_reproduction.log")
    shutil.copy2(
        summary_path,
        target_results / "clean_reproduction_summary.json",
    )


def main() -> int:
    source_project = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace",
        required=True,
        type=pathlib.Path,
        help="A nonexistent path for the isolated clean run.",
    )
    parser.add_argument(
        "--export-to",
        type=pathlib.Path,
        help="Copy verified generated reports/results into this project.",
    )
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if workspace.exists():
        print(
            f"FAIL: clean workspace already exists: {workspace}",
            file=sys.stderr,
        )
        return 2
    workspace.mkdir(parents=True)
    clean_project = workspace / "work"
    clean_upstream = workspace / "H0DN_CLEAN"
    log_path = workspace / "full_clean_reproduction.log"
    summary_path = workspace / "clean_reproduction_summary.json"
    created = dt.datetime.now(dt.timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "status": "RUNNING",
        "created_utc": created,
        "source_project": str(source_project),
        "clean_workspace": str(workspace),
        "clean_project": str(clean_project),
        "clean_upstream": str(clean_upstream),
        "existing_results_used": False,
        "expected_upstream_commit": EXPECTED_UPSTREAM_COMMIT,
    }

    try:
        with log_path.open("w", encoding="utf-8") as log:
            log.write("H0DN audit full clean reproduction log\n")
            log.write(f"created_utc: {created}\n")
            run_stage(
                "clone-audit-worktree",
                [
                    "git",
                    "clone",
                    "--no-hardlinks",
                    str(source_project),
                    str(clean_project),
                ],
                cwd=workspace,
                log=log,
            )
            source_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=clean_project,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            payload["audit_source_commit"] = source_commit

            results = clean_project / "results"
            hidden_generated_paths = subprocess.run(
                [
                    "git",
                    "ls-files",
                    "results",
                    "MANIFEST.tsv",
                    "SHA256SUMS.txt",
                ],
                cwd=clean_project,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            if hidden_generated_paths:
                subprocess.run(
                    [
                        "git",
                        "update-index",
                        "--assume-unchanged",
                        "--",
                        *hidden_generated_paths,
                    ],
                    cwd=clean_project,
                    check=True,
                )
            if results.exists():
                shutil.rmtree(results)
            results.mkdir()
            for checksum_file in ["MANIFEST.tsv", "SHA256SUMS.txt"]:
                target = clean_project / checksum_file
                if target.exists():
                    target.unlink()
            log.write(
                "clean_start: removed cloned results and package checksums; "
                "created an empty results directory\n"
            )
            clean_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=clean_project,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if clean_status:
                raise CleanRunFailure(
                    "Clean input worktree is not status-clean after hiding "
                    f"generated paths: {clean_status}"
                )
            log.write(
                "clean_input_git_status: clean (generated paths were marked "
                "assume-unchanged only inside the isolated clone)\n"
            )
            log.flush()

            system_python = pathlib.Path(sys.executable).resolve()
            run_stage(
                "create-fresh-venv",
                [str(system_python), "-m", "venv", ".venv"],
                cwd=clean_project,
                log=log,
            )
            python = clean_project / ".venv" / "bin" / "python"
            run_stage(
                "install-exact-dependencies",
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    "requirements-lock.txt",
                ],
                cwd=clean_project,
                log=log,
            )
            run_stage(
                "acquire-fresh-upstream",
                [
                    str(python),
                    "scripts/acquire_upstream.py",
                    "--destination",
                    str(clean_upstream),
                ],
                cwd=clean_project,
                log=log,
            )
            run_stage(
                "primary-audit",
                [
                    str(python),
                    "scripts/run_audit.py",
                    "--upstream",
                    str(clean_upstream),
                ],
                cwd=clean_project,
                log=log,
            )
            run_stage(
                "posthoc-diagnostics",
                [
                    str(python),
                    "scripts/run_posthoc_diagnostics.py",
                    "--upstream",
                    str(clean_upstream),
                ],
                cwd=clean_project,
                log=log,
            )
            run_stage(
                "exploratory-variance-component",
                [
                    str(python),
                    "scripts/run_exploratory_variance_component.py",
                    "--upstream",
                    str(clean_upstream),
                ],
                cwd=clean_project,
                log=log,
            )
            run_stage(
                "unit-tests",
                [
                    str(python),
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-v",
                ],
                cwd=clean_project,
                log=log,
            )

            fixed_values = check_fixed_values(clean_project)
            payload["fixed_values"] = fixed_values
            log.write("PASS fixed-scientific-value-comparison\n")
            log.flush()
            print("PASS fixed-scientific-value-comparison", flush=True)

            run_stage(
                "verify-results-before-manifest",
                [
                    str(python),
                    "scripts/verify_results.py",
                    "--upstream",
                    str(clean_upstream),
                    "--skip-package-integrity",
                ],
                cwd=clean_project,
                log=log,
            )
            run_stage(
                "regenerate-and-check-manifests",
                [
                    str(python),
                    "scripts/finalize_package.py",
                    "--write-manifests",
                    "--check",
                ],
                cwd=clean_project,
                log=log,
            )
            run_stage(
                "verify-results-with-root-closure",
                [
                    str(python),
                    "scripts/verify_results.py",
                    "--upstream",
                    str(clean_upstream),
                ],
                cwd=clean_project,
                log=log,
            )

        payload["status"] = "PASS"
        payload["message"] = (
            "Fresh upstream, worktree, environment, and empty results "
            "reproduced all fixed scientific values and verification gates."
        )
        write_summary(summary_path, payload)
        if args.export_to is not None:
            target = args.export_to.resolve()
            if not (target / "scripts" / "run_audit.py").is_file():
                raise CleanRunFailure(
                    f"Export target is not an audit project: {target}"
                )
            export_results(
                clean_project,
                target,
                log_path,
                summary_path,
            )
            print(f"PASS exported verified outputs to {target}", flush=True)
    except NumericalDrift as exc:
        payload["status"] = "HOLD_NUMERICAL_DRIFT"
        payload["message"] = str(exc)
        write_summary(summary_path, payload)
        print(f"HOLD_NUMERICAL_DRIFT: {exc}", file=sys.stderr)
        return 3
    except (
        CleanRunFailure,
        json.JSONDecodeError,
        OSError,
        subprocess.CalledProcessError,
        ValueError,
    ) as exc:
        payload["status"] = "FAIL"
        payload["message"] = str(exc)
        write_summary(summary_path, payload)
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    print(f"PASS clean reproduction log: {log_path}")
    print(f"PASS clean reproduction summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
