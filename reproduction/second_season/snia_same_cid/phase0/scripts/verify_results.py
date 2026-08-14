#!/usr/bin/env python3
"""Adversarial verifier for Phase 0 results, boundaries, and package closure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Callable

from package_tools import package_files, sha256_file, verify_manifests
from phase0lib import (
    CONTRACT_ID,
    EXPECTED_OBJECT_COUNT,
    FINAL_PASS_STATUS,
    PERMUTATION_COUNT,
    PERMUTATION_SEED,
    PROFILE_OFFSETS_SIGMA,
    TOLERANCES,
    write_json,
)
from source_tools import UPSTREAM_COMMIT, verify_source


DELIVERY_ID = "H0DN-SNIA-COMP-0.1.0-PHASE0-FINAL-20260730-01"
EXPECTED_ARCHIVE = (
    "H0DN_SNIA_COMPRESSION_SUFFICIENCY_AUDIT_"
    "v0.1.0_PHASE0_FINAL_20260730_01.zip"
)
BOUNDARY_MARKER = (
    "FROZEN_MODEL_ONLY_NO_CORRECTED_H0_NO_TENSION_RESOLUTION"
)
CONTRACT_SHA256 = (
    "bf49b620dd08a2c4a3f3dfdc33965914df83fdb460290e7a7bcf6b64e6597820"
)
SOURCE_LOCK_SHA256 = (
    "136602b45fef7629e920628cbd53a6135532ef8f174421d2db49ac21a79eb502"
)


def strict_json(path: pathlib.Path) -> Any:
    def reject(token: str) -> None:
        raise ValueError(f"Non-standard JSON constant {token} in {path}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


def read_tsv(path: pathlib.Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"Missing TSV header: {path}")
        return list(reader.fieldnames), list(reader)


def gate(
    gate_id: str,
    check: Callable[[], str],
    *,
    skipped: bool = False,
    skip_detail: str = "",
) -> dict[str, str]:
    if skipped:
        return {"gate_id": gate_id, "status": "SKIP", "detail": skip_detail}
    try:
        detail = check()
    except Exception as exc:
        return {
            "gate_id": gate_id,
            "status": "FAIL",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    return {"gate_id": gate_id, "status": "PASS", "detail": detail}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def contract_gate(project: pathlib.Path) -> str:
    freeze = strict_json(project / "provenance" / "CONTRACT_FREEZE.json")
    require(freeze["contract_id"] == CONTRACT_ID, "contract ID mismatch")
    require(freeze["status"] == "FROZEN", "contract is not frozen")
    require(
        freeze["results_observed_before_freeze"] is False,
        "contract says results were observed before freeze",
    )
    require(
        sha256_file(project / "PHASE0_CONTRACT.md") == CONTRACT_SHA256,
        "frozen contract hash mismatch",
    )
    require(
        freeze["contract_sha256"] == CONTRACT_SHA256,
        "freeze record contract hash mismatch",
    )
    require(
        sha256_file(project / "provenance" / "SOURCE_LOCK.tsv")
        == SOURCE_LOCK_SHA256,
        "source-lock hash mismatch",
    )
    require(
        freeze["source_lock_sha256"] == SOURCE_LOCK_SHA256,
        "freeze record source-lock hash mismatch",
    )
    fields, amendments = read_tsv(
        project / "provenance" / "CONTRACT_AMENDMENTS.tsv"
    )
    require(
        fields
        == [
            "amendment_id",
            "date_utc",
            "changed_file",
            "reason",
            "results_seen",
            "interpretation_impact",
        ],
        "amendment schema mismatch",
    )
    require(len(amendments) == 1, "unexpected amendment count")
    amendment = amendments[0]
    require(amendment["amendment_id"] == "A001", "unexpected amendment ID")
    require(
        amendment["changed_file"] == "requirements-lock.txt",
        "amendment changed an unexpected file",
    )
    require(amendment["results_seen"] == "true", "results-seen disclosure mismatch")
    require(
        amendment["interpretation_impact"].startswith("none;"),
        "amendment interpretation impact is not none",
    )
    require(
        "transitive packages" in amendment["reason"],
        "amendment reason does not identify dependency pinning",
    )
    return "frozen contract and one disclosed non-scientific amendment"


def strict_json_gate(project: pathlib.Path) -> str:
    json_paths = sorted((project / "results").glob("*.json"))
    json_paths += [
        project / "provenance" / "CONTRACT_FREEZE.json",
    ]
    require(len(json_paths) >= 10, "too few JSON artifacts")
    for path in json_paths:
        strict_json(path)
    return f"{len(json_paths)} strict JSON files"


def execution_gate(project: pathlib.Path) -> str:
    execution = strict_json(project / "results" / "EXECUTION_STATUS.json")
    require(execution["authoritative"] is True, "status is not authoritative")
    require(execution["contract_id"] == CONTRACT_ID, "execution contract mismatch")
    require(execution["status"] == FINAL_PASS_STATUS, "scientific status is not PASS")
    require(execution["scientific_gate_count"] == 14, "unexpected scientific gate count")
    require(
        execution["scientific_gate_pass_count"] == 14,
        "not all scientific gates passed",
    )
    require(not execution["failed_gate_ids"], "failed gate list is nonempty")
    ids = [item["gate_id"] for item in execution["gates"]]
    require(len(ids) == len(set(ids)) == 14, "scientific gate IDs not unique")
    require(
        all(item["status"] == "PASS" for item in execution["gates"]),
        "a scientific gate is not PASS",
    )
    return "authoritative status and 14/14 scientific gates"


def input_intercept_gate(project: pathlib.Path) -> str:
    inventory = strict_json(project / "results" / "input_inventory.json")
    alpha = strict_json(
        project / "results" / "intercept_reconstruction.json"
    )
    require(inventory["status"] == "PASS", "input inventory failed")
    require(
        inventory["object_count"] == EXPECTED_OBJECT_COUNT,
        "object count mismatch",
    )
    require(
        inventory["magnitude_covariance"]["shape"]
        == [EXPECTED_OBJECT_COUNT, EXPECTED_OBJECT_COUNT],
        "magnitude covariance shape mismatch",
    )
    require(alpha["cholesky_succeeded"] is True, "Cholesky did not succeed")
    require(
        alpha["alpha_covariance"]["eigenvalue_min"]
        > TOLERANCES["covariance_min_eigenvalue"],
        "alpha covariance fails SPD threshold",
    )
    upstream_match = max(
        alpha["upstream_match"]["alpha_absolute_difference"],
        alpha["upstream_match"]["alpha_error_absolute_difference"],
    )
    require(
        upstream_match <= TOLERANCES["alpha_reconstruction"],
        "independent alpha reconstruction mismatch",
    )
    crosscheck = max(
        alpha["solver_crosscheck"]["alpha_absolute_difference"],
        alpha["solver_crosscheck"]["alpha_error_absolute_difference"],
        alpha["solver_crosscheck"]["chi2_absolute_difference"],
    )
    require(
        crosscheck <= TOLERANCES["solver_crosscheck"],
        "inverse/Cholesky cross-check mismatch",
    )
    require(
        alpha["independent_cholesky"]["object_count"]
        == EXPECTED_OBJECT_COUNT,
        "intercept object count mismatch",
    )
    return "277-row input, SPD covariance, alpha reconstruction"


def profile_gate(project: pathlib.Path) -> str:
    path = project / "results" / "compression_identity_grid.tsv"
    fields, rows = read_tsv(path)
    expected_fields = [
        "offset_sigma",
        "trial_alpha",
        "full_chi2",
        "full_delta_chi2",
        "scalar_delta_chi2",
        "identity_residual",
        "absolute_identity_residual",
        "tolerance",
        "status",
    ]
    require(fields == expected_fields, "profile TSV schema mismatch")
    require(len(rows) == len(PROFILE_OFFSETS_SIGMA), "profile row count mismatch")
    offsets = [float(row["offset_sigma"]) for row in rows]
    require(offsets == list(PROFILE_OFFSETS_SIGMA), "profile grid changed")
    residual_max = max(float(row["absolute_identity_residual"]) for row in rows)
    require(
        residual_max <= TOLERANCES["profile_identity"],
        "compression identity failed",
    )
    require(all(row["status"] == "PASS" for row in rows), "profile row failure")
    for row in rows:
        require(
            abs(
                float(row["full_delta_chi2"])
                - float(row["scalar_delta_chi2"])
                - float(row["identity_residual"])
            )
            <= 5.0e-13,
            "profile arithmetic is not self-consistent",
        )
    return f"11 fixed profile points; max residual {residual_max:.3e}"


def comparison_max(comparison: dict[str, Any]) -> float:
    return max(
        comparison["max_abs_parameter_difference"],
        comparison["max_abs_parameter_covariance_difference"],
        comparison["absolute_h0_difference"],
        comparison["absolute_h0_error_difference"],
    )


def network_gate(project: pathlib.Path) -> str:
    network = strict_json(
        project / "results" / "network_embedding_equivalence.json"
    )
    require(
        network["hubble_flow_row_count"] == EXPECTED_OBJECT_COUNT,
        "expanded HF row count mismatch",
    )
    require(network["original_row_count"] == 255, "original row count mismatch")
    require(network["expanded_row_count"] == 531, "expanded row count mismatch")
    require(
        comparison_max(network["scalar_vs_upstream"])
        <= TOLERANCES["network"],
        "independently recompressed scalar network mismatch",
    )
    require(
        comparison_max(network["expanded_vs_scalar"])
        <= TOLERANCES["network"],
        "expanded network mismatch",
    )
    require(
        comparison_max(network["blockwise_vs_expanded"])
        <= TOLERANCES["network"],
        "blockwise solver mismatch",
    )
    normal_max = max(
        network["normal_equation_closure"][
            "max_abs_normal_matrix_difference"
        ],
        network["normal_equation_closure"][
            "max_abs_normal_rhs_difference"
        ],
    )
    require(
        normal_max <= TOLERANCES["normal_closure"],
        "normal-equation closure failed",
    )
    require(
        abs(network["chi2_closure_residual"])
        <= TOLERANCES["chi2_closure"],
        "chi-square closure failed",
    )
    require(
        network["covariance_rank_increase"]
        == network["ndof_increase"]
        == EXPECTED_OBJECT_COUNT - 1,
        "rank/dof closure failed",
    )
    require(
        network["independently_recompressed_scalar"]["covar_rank"] == 183,
        "scalar covariance rank mismatch",
    )
    require(
        network["expanded_full_block"]["covar_rank"] == 459,
        "expanded covariance rank mismatch",
    )
    return (
        "all parameters/covariances, normal equations, chi2, rank/dof, "
        "and blockwise solver"
    )


def permutation_gate(project: pathlib.Path) -> str:
    fields, rows = read_tsv(
        project / "results" / "permutation_invariance.tsv"
    )
    expected_fields = [
        "iteration",
        "seed",
        "permutation_sha256",
        "max_abs_parameter_difference",
        "max_abs_parameter_covariance_difference",
        "absolute_h0_difference",
        "absolute_h0_error_difference",
        "absolute_logh0_difference",
        "absolute_mzero_difference",
        "maximum_tested_difference",
        "tolerance",
        "status",
    ]
    require(fields == expected_fields, "permutation TSV schema mismatch")
    require(len(rows) == PERMUTATION_COUNT, "permutation count mismatch")
    require(
        [int(row["iteration"]) for row in rows]
        == list(range(PERMUTATION_COUNT)),
        "permutation iterations mismatch",
    )
    require(
        all(int(row["seed"]) == PERMUTATION_SEED for row in rows),
        "permutation seed mismatch",
    )
    require(
        all(
            re.fullmatch(r"[0-9a-f]{64}", row["permutation_sha256"])
            for row in rows
        ),
        "invalid permutation hashes",
    )
    require(
        len({row["permutation_sha256"] for row in rows}) == PERMUTATION_COUNT,
        "duplicate permutations",
    )
    maximum = max(float(row["maximum_tested_difference"]) for row in rows)
    require(maximum <= TOLERANCES["permutation"], "permutation invariance failed")
    require(all(row["status"] == "PASS" for row in rows), "permutation row failure")
    return f"16 fixed-seed permutations; max difference {maximum:.3e}"


def report_boundary_gate(project: pathlib.Path) -> str:
    generated = strict_json(project / "results" / "report_generation.json")
    report = project / "PHASE0_REPORT.md"
    report_ja = project / "PHASE0_REPORT_JA.md"
    require(generated["status"] == "PASS", "report generation failed")
    require(
        sha256_file(report) == generated["report_sha256"],
        "English report hash mismatch",
    )
    require(
        sha256_file(report_ja) == generated["report_ja_sha256"],
        "Japanese report hash mismatch",
    )
    for path in (report, report_ja):
        text = path.read_text(encoding="utf-8")
        require(BOUNDARY_MARKER in text, f"boundary marker missing from {path.name}")
        require(FINAL_PASS_STATUS in text, f"status missing from {path.name}")
    english = report.read_text(encoding="utf-8")
    japanese = report_ja.read_text(encoding="utf-8")
    require(
        re.search(
            r"not a new\s+or corrected H0 estimate", english
        )
        is not None,
        "English corrected-H0 non-claim missing",
    )
    require("does not validate the physical adequacy" in english, "English model non-claim missing")
    require("補正値でもない" in japanese, "Japanese corrected-H0 non-claim missing")
    require("テンションが解消したとも主張しない" in japanese, "Japanese tension non-claim missing")
    summary = strict_json(project / "results" / "phase0_summary.json")
    require(summary["boundary_marker"] == BOUNDARY_MARKER, "summary boundary mismatch")
    require(
        "No corrected H0" in summary["non_claim"],
        "summary corrected-H0 non-claim missing",
    )
    return "generated report hashes and scientific non-claim boundary"


def authorship_gate(project: pathlib.Path) -> str:
    cff = (project / "CITATION.cff").read_text(encoding="utf-8")
    require("family-names: Yoshimura" in cff, "CFF family name mismatch")
    require("given-names: Keiji" in cff, "CFF given name mismatch")
    author_section = cff.split("authors:", 1)[1].split("license:", 1)[0]
    require("OpenAI" not in author_section, "AI listed as a CFF author")
    disclosure = (project / "AI_ASSISTANCE_DISCLOSURE.md").read_text(
        encoding="utf-8"
    )
    require("OpenAI Codex assisted" in disclosure, "AI disclosure missing")
    require(
        "Keiji Yoshimura directed" in disclosure,
        "human scientific direction missing",
    )
    require((project / "LICENSE").is_file(), "license missing")
    require((project / "THIRD_PARTY_NOTICES.md").is_file(), "third-party notice missing")
    return "Keiji Yoshimura authorship, CFF, license, AI disclosure"


def delivery_gate(project: pathlib.Path) -> str:
    text = (project / "DELIVERY_ID.md").read_text(encoding="utf-8")
    require(DELIVERY_ID in text, "delivery ID mismatch")
    require(EXPECTED_ARCHIVE in text, "expected archive name mismatch")
    require(
        "not any revision of" in text
        and "h0dn-covariance-influence-audit" in text,
        "old-project exclusion missing",
    )
    require(
        (project / "VERSION").read_text(encoding="utf-8").strip() == "0.1.0",
        "version mismatch",
    )
    return DELIVERY_ID


def no_upstream_bytes_gate(project: pathlib.Path) -> str:
    _, rows = read_tsv(project / "provenance" / "SOURCE_LOCK.tsv")
    upstream_hashes = {row["sha256"] for row in rows}
    forbidden_roots = {"data", "h0_constrainer", "idlcode", "upstream"}
    delivered = package_files(project)
    for path in delivered:
        relative = path.relative_to(project)
        require(
            not relative.parts or relative.parts[0] not in forbidden_roots,
            f"forbidden upstream path included: {relative}",
        )
        require(
            sha256_file(path) not in upstream_hashes,
            f"byte-identical upstream file included: {relative}",
        )
    notice = (project / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    require("does not redistribute upstream source or" in notice, "non-redistribution notice missing")
    return f"{len(delivered)} delivered files checked against 69 upstream hashes"


def root_closure_gate(project: pathlib.Path) -> str:
    allowed = {
        ".gitignore",
        "AI_ASSISTANCE_DISCLOSURE.md",
        "CHANGELOG.md",
        "CITATION.cff",
        "DELIVERY_ID.md",
        "LICENSE",
        "MANIFEST.tsv",
        "PHASE0_CONTRACT.md",
        "PHASE0_REPORT.md",
        "PHASE0_REPORT_JA.md",
        "README.md",
        "REPRODUCIBILITY.md",
        "SHA256SUMS.txt",
        "THIRD_PARTY_NOTICES.md",
        "VERSION",
        "provenance",
        "requirements-lock.txt",
        "results",
        "scripts",
        "tests",
    }
    actual = {
        path.name
        for path in project.iterdir()
        if path.name not in {".git", ".venv", "__pycache__"}
    }
    require(actual <= allowed, f"unexpected root entries: {sorted(actual - allowed)}")
    required = allowed - {"MANIFEST.tsv", "SHA256SUMS.txt"}
    require(required <= actual, f"missing root entries: {sorted(required - actual)}")
    result_allowed = {
        "EXECUTION_STATUS.json",
        "clean_reproduction_summary.json",
        "compression_identity_grid.tsv",
        "final_verification_summary.json",
        "full_clean_reproduction.log",
        "input_inventory.json",
        "intercept_reconstruction.json",
        "network_embedding_equivalence.json",
        "permutation_invariance.tsv",
        "phase0_summary.json",
        "report_generation.json",
        "run_environment.json",
        "source_verification.json",
        "upstream_baseline_reproduction.json",
        "upstream_stderr.log",
        "upstream_stdout.log",
    }
    result_actual = {
        path.name
        for path in (project / "results").iterdir()
        if path.is_file()
    }
    require(
        result_actual <= result_allowed,
        f"unexpected result files: {sorted(result_actual - result_allowed)}",
    )
    required_results = result_allowed - {
        "clean_reproduction_summary.json",
        "final_verification_summary.json",
        "full_clean_reproduction.log",
    }
    require(
        required_results <= result_actual,
        f"missing result files: {sorted(required_results - result_actual)}",
    )
    return "project and result allowlists"


def unit_test_gate(project: pathlib.Path) -> str:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(project / "tests"),
            "-v",
        ],
        cwd=project,
        text=True,
        capture_output=True,
    )
    require(completed.returncode == 0, completed.stdout + completed.stderr)
    combined = completed.stdout + completed.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    require(match is not None, "unit-test count not found")
    require(int(match.group(1)) == 8, "unexpected unit-test count")
    require("\nOK" in combined, "unit tests did not report OK")
    return "8 unit tests"


def clean_record_gate(project: pathlib.Path) -> str:
    summary = strict_json(
        project / "results" / "clean_reproduction_summary.json"
    )
    require(summary["status"] == "PASS", "clean reproduction did not pass")
    require(summary["upstream_commit"] == UPSTREAM_COMMIT, "clean upstream mismatch")
    require(summary["scientific_status"] == FINAL_PASS_STATUS, "clean scientific status mismatch")
    require(summary["comparison_status"] == "PASS", "clean/reference comparison failed")
    require(summary["unit_test_count"] == 8, "clean unit-test count mismatch")
    log = (project / "results" / "full_clean_reproduction.log").read_text(
        encoding="utf-8"
    )
    require(FINAL_PASS_STATUS in log, "clean log lacks scientific PASS")
    require("Ran 8 tests" in log and "\nOK" in log, "clean log lacks test PASS")
    return "fresh workspace/upstream rerun and reference comparison"


def upstream_gate(project: pathlib.Path, upstream: pathlib.Path) -> str:
    result = verify_source(
        upstream.resolve(), project / "provenance" / "SOURCE_LOCK.tsv"
    )
    require(result["commit"] == UPSTREAM_COMMIT, "upstream commit mismatch")
    require(result["locked_file_count"] == 69, "upstream file count mismatch")
    return "69 frozen upstream files"


def package_gate(project: pathlib.Path) -> str:
    result = verify_manifests(project)
    return f"{result['manifested_file_count']} manifested files"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=pathlib.Path)
    parser.add_argument("--skip-package-integrity", action="store_true")
    parser.add_argument("--skip-clean-record", action="store_true")
    parser.add_argument("--no-write-summary", action="store_true")
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]

    gates = [
        gate("contract_freeze", lambda: contract_gate(project)),
        gate("strict_json", lambda: strict_json_gate(project)),
        gate("authoritative_execution", lambda: execution_gate(project)),
        gate("input_and_intercept", lambda: input_intercept_gate(project)),
        gate("compression_profile_schema", lambda: profile_gate(project)),
        gate("network_embedding_closure", lambda: network_gate(project)),
        gate("permutation_schema", lambda: permutation_gate(project)),
        gate("report_and_scientific_boundary", lambda: report_boundary_gate(project)),
        gate("authorship_and_disclosure", lambda: authorship_gate(project)),
        gate("delivery_identity", lambda: delivery_gate(project)),
        gate("no_upstream_bytes", lambda: no_upstream_bytes_gate(project)),
        gate("root_closure", lambda: root_closure_gate(project)),
        gate("unit_tests", lambda: unit_test_gate(project)),
        gate(
            "clean_reproduction_record",
            lambda: clean_record_gate(project),
            skipped=args.skip_clean_record,
            skip_detail="explicitly skipped for an in-progress clean-room copy",
        ),
        gate(
            "live_upstream_source_lock",
            lambda: upstream_gate(project, args.upstream),
            skipped=args.upstream is None,
            skip_detail="no --upstream supplied",
        ),
        gate(
            "package_integrity",
            lambda: package_gate(project),
            skipped=args.skip_package_integrity,
            skip_detail="explicitly skipped before manifest finalization",
        ),
    ]
    failures = [item for item in gates if item["status"] == "FAIL"]
    skips = [item for item in gates if item["status"] == "SKIP"]
    overall = (
        "FAIL"
        if failures
        else ("PASS_WITH_PENDING_GATES" if skips else "PASS")
    )
    summary = {
        "overall_status": overall,
        "gate_count": len(gates),
        "pass_count": sum(item["status"] == "PASS" for item in gates),
        "fail_count": len(failures),
        "skip_count": len(skips),
        "gates": gates,
    }
    if not args.no_write_summary:
        write_json(
            project / "results" / "final_verification_summary.json",
            summary,
        )
    for item in gates:
        print(f"{item['status']}: {item['gate_id']}: {item['detail']}")
    print(f"OVERALL: {overall}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
