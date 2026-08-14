#!/usr/bin/env python3
"""Verify scientific invariants, interpretation gates, and package closure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import subprocess
import sys
from typing import Any

import yaml

from source_tools import UPSTREAM_COMMIT, verify_source


PROFILE_MINIMUM_ROWS = 161
LOO_MATCH_TOLERANCE = 1.0e-9
EXPECTED_CONTRACT_AMENDMENT_FIELDS = [
    "timestamp_utc",
    "contract_version",
    "affected_section",
    "change",
    "reason",
    "results_seen",
]
INTERPRETATION_STATUSES = {
    "PSD_ALGEBRAIC_SENSITIVITY",
    "PSEUDOINVERSE_DISCARDED_CONSTRAINT",
    "INDEFINITE_ALGEBRAIC_DIAGNOSTIC",
    "HOLD_UNIDENTIFIED",
    "HOLD_NUMERICAL_FAILURE",
}
COVARIANCE_MODEL_STATUSES = {
    "PSD",
    "SINGULAR_PSD",
    "INDEFINITE",
    "HOLD",
}
MANIFEST_EXCLUSIONS = {"MANIFEST.tsv", "SHA256SUMS.txt"}
RUNTIME_PATH_EXCLUSIONS = {
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".DS_Store",
}


class VerificationFailure(RuntimeError):
    """Raised when a delivered result violates a fixed gate."""


class GateRecorder:
    """Collect deterministic evidence for the final verification summary."""

    def __init__(self) -> None:
        self.gates: list[dict[str, str]] = []

    def passed(self, name: str, evidence: str) -> None:
        self.gates.append(
            {"gate": name, "status": "PASS", "evidence": evidence}
        )
        print(f"PASS {name}: {evidence}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationFailure(message)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def read_tsv_with_header(
    path: pathlib.Path,
) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t", strict=True)
        fields = list(reader.fieldnames or [])
        require(fields, f"{path} has no TSV header")
        require(
            len(fields) == len(set(fields)),
            f"{path} has duplicate TSV header fields",
        )
        rows = list(reader)
    for line_number, row in enumerate(rows, start=2):
        require(
            None not in row,
            f"{path}:{line_number} has more fields than its header",
        )
        require(
            all(row.get(field) is not None for field in fields),
            f"{path}:{line_number} has fewer fields than its header",
        )
    return fields, rows


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    return read_tsv_with_header(path)[1]


def numeric(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationFailure(
            f"Missing/non-numeric {key!r} in TSV row"
        ) from exc
    require(math.isfinite(value), f"Non-finite {key!r} in TSV row")
    return value


def integer(row: dict[str, str], key: str) -> int:
    value = numeric(row, key)
    require(value.is_integer(), f"{key!r} is not an integer")
    return int(value)


def git_tracked_paths(project_root: pathlib.Path) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(project_root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return sorted(
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    )


def packaged_paths(project_root: pathlib.Path) -> list[str]:
    """Resolve deliverable paths both in a Git worktree and an extracted ZIP."""

    if (project_root / ".git").exists():
        return git_tracked_paths(project_root)
    return sorted(
        path.relative_to(project_root).as_posix()
        for path in project_root.rglob("*")
        if path.is_file()
        and not any(
            part in RUNTIME_PATH_EXCLUSIONS
            for part in path.relative_to(project_root).parts
        )
    )


def verify_tsv_schema(project_root: pathlib.Path) -> int:
    tsv_paths = sorted(
        [
            *project_root.glob("*.tsv"),
            *(project_root / "provenance").rglob("*.tsv"),
            *(project_root / "results").rglob("*.tsv"),
        ]
    )
    require(tsv_paths, "TSV_SCHEMA: no TSV files found")
    for path in tsv_paths:
        read_tsv_with_header(path)
    amendment_fields, amendments = read_tsv_with_header(
        project_root / "provenance" / "CONTRACT_AMENDMENTS.tsv"
    )
    require(
        amendment_fields == EXPECTED_CONTRACT_AMENDMENT_FIELDS,
        "TSV_SCHEMA: CONTRACT_AMENDMENTS.tsv must have the fixed six fields",
    )
    require(
        len(amendments) == 2,
        "TSV_SCHEMA: CONTRACT_AMENDMENTS.tsv must have two data rows",
    )
    require(
        amendments[0]["reason"]
        == (
            "diagnose the unexpected primary-audit failure without "
            "modifying the primary contract"
        ),
        "TSV_SCHEMA: first amendment reason/results_seen separation changed",
    )
    require(
        amendments[1]["results_seen"]
        == (
            "yes: all-equation nullspace projection inspected; no "
            "interaction-decomposition output seen"
        ),
        "TSV_SCHEMA: second amendment reason/results_seen separation changed",
    )
    return len(tsv_paths)


def verify_authorship(project_root: pathlib.Path) -> None:
    citation_text = (project_root / "CITATION.cff").read_text(
        encoding="utf-8"
    )
    license_text = (project_root / "LICENSE").read_text(encoding="utf-8")
    disclosure = (project_root / "AI_ASSISTANCE_DISCLOSURE.md").read_text(
        encoding="utf-8"
    )
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.split())
    require(
        "given-names: Keiji" in citation_text
        and "family-names: Yoshimura" in citation_text,
        "AUTHORSHIP_SYNC: CITATION.cff does not identify Keiji Yoshimura",
    )
    for name, text in [
        ("LICENSE", license_text),
        ("AI_ASSISTANCE_DISCLOSURE.md", disclosure),
        ("README.md", readme),
    ]:
        require(
            "Keiji Yoshimura" in text,
            f"AUTHORSHIP_SYNC: {name} does not name Keiji Yoshimura",
        )
    require(
        "AI systems are not authors" in disclosure
        and "has not undergone independent expert peer review" in disclosure,
        "AUTHORSHIP_SYNC: AI responsibility boundary is incomplete",
    )
    require(
        (
            "This is not an official H0DN product and is not affiliated "
            "with or endorsed by the H0DN authors."
        )
        in normalized_readme,
        "AUTHORSHIP_SYNC: independent-audit disclaimer is missing",
    )
    require(
        "AI_ASSISTANCE_DISCLOSURE.md" in readme,
        "AUTHORSHIP_SYNC: README does not link the AI disclosure",
    )


def verify_cff(project_root: pathlib.Path) -> None:
    with (project_root / "CITATION.cff").open(
        "r", encoding="utf-8"
    ) as handle:
        citation = yaml.safe_load(handle)
    require(isinstance(citation, dict), "CFF_PARSE: CFF is not a mapping")
    require(
        str(citation.get("cff-version")) == "1.2.0",
        "CFF_PARSE: cff-version must be 1.2.0",
    )
    require(
        citation.get("version") == "0.1.0",
        "CFF_PARSE: version must remain 0.1.0",
    )
    require(
        citation.get("title")
        == (
            "Independent audit of H0DN covariance-block influence and "
            "numerical stability"
        ),
        "CFF_PARSE: title changed",
    )
    authors = citation.get("authors")
    require(
        isinstance(authors, list) and len(authors) == 1,
        "CFF_PARSE: expected one human author",
    )
    author = authors[0]
    require(
        author.get("family-names") == "Yoshimura"
        and author.get("given-names") == "Keiji"
        and author.get("affiliation") == "Independent Researcher",
        "CFF_PARSE: author fields changed",
    )
    require(
        "date-released" not in citation,
        "CFF_PARSE: unpublished package must not assert date-released",
    )


def verify_source_lock(
    project_root: pathlib.Path, upstream: pathlib.Path | None
) -> None:
    source_lock = read_tsv(project_root / "provenance/SOURCE_LOCK.tsv")
    require(
        len(source_lock) == 69,
        "SOURCE_LOCK: source lock must contain 69 files",
    )
    require(
        len({row["path"] for row in source_lock}) == 69,
        "SOURCE_LOCK: paths are not unique",
    )
    for row in source_lock:
        require(
            len(row.get("git_blob_sha1", "")) == 40,
            f"SOURCE_LOCK: invalid Git blob id for {row.get('path')}",
        )
        require(
            len(row.get("sha256", "")) == 64,
            f"SOURCE_LOCK: invalid SHA-256 for {row.get('path')}",
        )
        require(
            integer(row, "bytes") >= 0,
            f"SOURCE_LOCK: invalid byte count for {row.get('path')}",
        )
    if upstream is not None:
        source = verify_source(
            upstream.resolve(), project_root / "provenance/SOURCE_LOCK.tsv"
        )
        require(
            source["commit"] == UPSTREAM_COMMIT,
            "SOURCE_LOCK: wrong upstream commit",
        )


def verify_execution_statuses(results: pathlib.Path) -> None:
    execution = read_json(results / "EXECUTION_STATUS.json")
    posthoc = read_json(results / "POSTHOC_EXECUTION_STATUS.json")
    exploratory = read_json(results / "EXPLORATORY_EXECUTION_STATUS.json")
    require(
        str(execution.get("status", "")).startswith("PASS"),
        "EXECUTION_STATUS: primary run did not pass",
    )
    require(
        posthoc.get("status") == "PASS",
        "EXECUTION_STATUS: post-hoc run did not pass",
    )
    require(
        str(exploratory.get("status", "")).startswith("PASS"),
        "EXECUTION_STATUS: exploratory run did not pass",
    )


def verify_core_science(project_root: pathlib.Path) -> None:
    results = project_root / "results"
    baseline_record = read_json(results / "baseline_reproduction.json")
    baseline = baseline_record["upstream"]
    require(
        baseline_record["fidelity_gate"]["status"] == "PASS",
        "CORE_SCIENTIFIC_VALUES: baseline gate failed",
    )
    require(
        baseline_record["independent_solver_match"]["status"] == "PASS",
        "CORE_SCIENTIFIC_VALUES: independent solver mismatch",
    )
    require(
        int(baseline["neq"]) == 255
        and int(baseline["npars"]) == 64
        and int(baseline["covar_rank"]) == 183
        and int(baseline["covar_nullity"]) == 72,
        "CORE_SCIENTIFIC_VALUES: matrix dimensions/rank changed",
    )
    require(
        abs(float(baseline["h0_value"]) - 73.49875364) < 5.0e-8
        and abs(float(baseline["h0_error"]) - 0.80880003) < 5.0e-8,
        "CORE_SCIENTIFIC_VALUES: baseline H0 or uncertainty drifted",
    )

    closure = read_json(results / "component_decomposition_closure.json")
    require(
        closure["status"] == "PASS"
        and float(closure["relative_frobenius_error"]) <= 1.0e-12,
        "CORE_SCIENTIFIC_VALUES: covariance decomposition did not close",
    )

    representation = read_tsv(results / "representation_invariance.tsv")
    standardized = [
        row
        for row in representation
        if row["representation_family"] == "diagonal_row_standardization"
    ]
    permutations = [
        row
        for row in representation
        if row["representation_family"]
        == "simultaneous_row_column_permutation"
    ]
    require(
        len(standardized) == 1 and len(permutations) == 32,
        "CORE_SCIENTIFIC_VALUES: expected one scaling and 32 permutations",
    )
    require(
        standardized[0]["invariance_status"] == "FAIL"
        and integer(standardized[0], "covar_rank") == 183
        and abs(numeric(standardized[0], "delta_h0") + 0.05244542)
        < 5.0e-8,
        "CORE_SCIENTIFIC_VALUES: row-standardization result changed",
    )
    require(
        all(row["invariance_status"] == "PASS" for row in permutations)
        and max(
            numeric(row, "absolute_delta_h0") for row in permutations
        )
        < 1.0e-8,
        "CORE_SCIENTIFIC_VALUES: permutation gate changed",
    )

    cutoff_rows = read_tsv(results / "solver_cutoff_sensitivity.tsv")
    require(cutoff_rows, "CORE_SCIENTIFIC_VALUES: cutoff table is empty")
    require(
        all(
            row["status"].startswith("OK")
            and integer(row, "covar_rank") == 183
            for row in cutoff_rows
        ),
        "CORE_SCIENTIFIC_VALUES: cutoff status/rank changed",
    )
    cutoff_h0 = [numeric(row, "h0_value") for row in cutoff_rows]
    require(
        max(cutoff_h0) - min(cutoff_h0) < 1.0e-8,
        "CORE_SCIENTIFIC_VALUES: cutoff H0 spread changed",
    )

    posthoc = read_json(results / "posthoc_row_scaling_diagnostic.json")
    support = posthoc["support_constraint"]
    require(
        posthoc["status"] == "DIAGNOSED"
        and support["status"] == "HOLD_INCONSISTENT_SUPPORT"
        and abs(
            float(support["constraint_target_l2_norm"]) - 0.18874908
        )
        < 5.0e-8,
        "CORE_SCIENTIFIC_VALUES: nullspace-support diagnosis changed",
    )
    interaction = posthoc["cepheid_interaction_decomposition"]
    require(
        interaction["status"] == "PASS"
        and (
            int(interaction["host_count"]),
            int(interaction["anchor_count"]),
            int(interaction["cell_count"]),
        )
        == (37, 3, 111)
        and float(interaction["projection_closure_max_absolute_error"])
        < 1.0e-10,
        "CORE_SCIENTIFIC_VALUES: interaction closure changed",
    )
    cells = read_tsv(results / "posthoc_cepheid_interaction_cells.tsv")
    require(
        len(cells) == 111
        and len({row["host"] for row in cells}) == 37
        and len({row["anchor"] for row in cells}) == 3
        and max(
            abs(numeric(row, "interaction_minus_projection"))
            for row in cells
        )
        < 1.0e-10,
        "CORE_SCIENTIFIC_VALUES: cell-level interaction closure changed",
    )

    exploratory = read_json(
        results / "exploratory_variance_component_summary.json"
    )
    require(
        str(exploratory["status"]).startswith("PASS"),
        "CORE_SCIENTIFIC_VALUES: exploratory run did not pass",
    )
    checks = exploratory["invariance_and_structure_checks"]
    for key in [
        "reml_fit",
        "ml_fit",
        "moment_conditional_fit",
        "rank",
        "structure",
    ]:
        require(
            checks[key]["status"] == "PASS",
            f"CORE_SCIENTIFIC_VALUES: exploratory {key} changed",
        )
    reml = exploratory["original_representation"]["reml_fit"]
    require(
        abs(float(reml["tau"]) - 0.02224362) < 5.0e-8
        and int(reml["covariance_rank_at_public_cutoff"]) == 255
        and abs(
            (
                float(reml["h0_value"]) - float(baseline["h0_value"])
            )
            + 0.00442767
        )
        < 5.0e-8,
        "CORE_SCIENTIFIC_VALUES: exploratory tau or conditional H0 drifted",
    )
    profile = read_tsv(
        results / "exploratory_variance_component_profile.tsv"
    )
    require(
        len(profile) >= PROFILE_MINIMUM_ROWS,
        "CORE_SCIENTIFIC_VALUES: profile grid is incomplete",
    )


def verify_ablation_classification(
    project_root: pathlib.Path,
) -> tuple[dict[str, str], int]:
    path = project_root / "results" / "covariance_component_ablation.tsv"
    fields, rows = read_tsv_with_header(path)
    required_fields = {
        "solver_status",
        "interpretation_status",
        "rank_change_from_baseline",
        "zero_diagonal_count",
        "zero_precision_row_count",
        "discarded_equation_indices",
        "matched_leave_one_block_out_id",
        "matched_leave_one_block_out_delta_h0",
        "covariance_model_status",
    }
    require(
        required_fields.issubset(fields),
        "ABLATION_CLASSIFICATION: required fields are missing",
    )
    require(
        len(rows) == 64,
        "ABLATION_CLASSIFICATION: expected all 64 component/aggregate rows",
    )
    for row in rows:
        require(
            bool(row["solver_status"]),
            "ABLATION_CLASSIFICATION: empty solver_status",
        )
        require(
            row["interpretation_status"] in INTERPRETATION_STATUSES,
            "ABLATION_CLASSIFICATION: unknown interpretation_status",
        )
        require(
            row["covariance_model_status"] in COVARIANCE_MODEL_STATUSES,
            "ABLATION_CLASSIFICATION: unknown covariance_model_status",
        )
    sn_rows = [
        row
        for row in rows
        if row["component_id"] == "sn1a_hubble_flow_link_variance"
    ]
    require(
        len(sn_rows) == 1,
        "SNIA_LINK_DROP: expected one SN-Ia Hubble-flow link row",
    )
    return sn_rows[0], len(rows)


def verify_snia_link(
    project_root: pathlib.Path, sn_link: dict[str, str]
) -> None:
    require(
        sn_link["interpretation_status"]
        == "PSEUDOINVERSE_DISCARDED_CONSTRAINT"
        and integer(sn_link, "covar_rank") == 182
        and integer(sn_link, "rank_change_from_baseline") == -1
        and integer(sn_link, "zero_diagonal_count") >= 1
        and integer(sn_link, "zero_precision_row_count") >= 1,
        "SNIA_LINK_DROP: rank drop or constraint-discard classification changed",
    )
    try:
        discarded = json.loads(sn_link["discarded_equation_indices"])
    except json.JSONDecodeError as exc:
        raise VerificationFailure(
            "SNIA_LINK_DROP: discarded indices are not JSON"
        ) from exc
    require(
        discarded == [248],
        "SNIA_LINK_DROP: expected discarded equation index 248",
    )

    loo_rows = read_tsv(
        project_root / "results" / "leave_one_block_out.tsv"
    )
    matches = [
        row
        for row in loo_rows
        if row["block_id"] == "sn1a_hubble_flow_link"
    ]
    require(
        len(matches) == 1,
        "LOO_MATCH: missing sn1a_hubble_flow_link row",
    )
    loo = matches[0]
    require(
        sn_link["matched_leave_one_block_out_id"]
        == "sn1a_hubble_flow_link"
        and sn_link["matched_leave_one_block_out_match_status"] == "PASS",
        "LOO_MATCH: recorded match status changed",
    )
    differences = [
        abs(numeric(sn_link, "h0_value") - numeric(loo, "h0_value")),
        abs(numeric(sn_link, "h0_error") - numeric(loo, "h0_error")),
        abs(numeric(sn_link, "matched_leave_one_block_out_delta_h0")),
        abs(
            numeric(
                sn_link,
                "matched_leave_one_block_out_delta_h0_error",
            )
        ),
        abs(
            numeric(
                sn_link,
                (
                    "matched_leave_one_block_out_parameter_"
                    "max_absolute_difference"
                ),
            )
        ),
    ]
    require(
        max(differences) <= LOO_MATCH_TOLERANCE,
        "LOO_MATCH: H0, uncertainty, or parameter match exceeded tolerance",
    )


def verify_indefinite_separation(project_root: pathlib.Path) -> None:
    rows = read_tsv(
        project_root / "results" / "covariance_component_ablation.tsv"
    )
    indefinite = [
        row
        for row in rows
        if row["covariance_model_status"] == "INDEFINITE"
    ]
    require(
        indefinite
        and all(
            row["interpretation_status"]
            == "INDEFINITE_ALGEBRAIC_DIAGNOSTIC"
            for row in indefinite
        ),
        "INDEFINITE_SEPARATION: indefinite rows are misclassified",
    )
    summary = read_json(project_root / "results" / "audit_summary.json")
    main = summary.get("top_component_influences", [])
    flagged = summary.get("flagged_component_diagnostics", [])
    require(
        main
        and all(
            row.get("interpretation_status")
            == "PSD_ALGEBRAIC_SENSITIVITY"
            for row in main
        ),
        "INDEFINITE_SEPARATION: main ranking contains a flagged class",
    )
    flagged_ids = {row.get("identifier") for row in flagged}
    require(
        "sn1a_hubble_flow_link_variance" in flagged_ids
        and all(
            row["component_id"] not in {
                item.get("identifier") for item in main
            }
            for row in indefinite
        ),
        "INDEFINITE_SEPARATION: flagged diagnostics were not separated",
    )


def verify_report_generation(project_root: pathlib.Path) -> None:
    report_path = project_root / "REPORT.md"
    report = report_path.read_text(encoding="utf-8")
    generation = read_json(
        project_root / "results" / "report_generation.json"
    )
    caution = (
        "These rows measure the behavior of the encoded solver after "
        "subtracting one\nadditive covariance component. Some ablations "
        "create zero-variance or\nindefinite directions, so the resulting "
        "pseudoinverse solution may discard\nconstraints and must not be "
        "interpreted as a supported alternative covariance\nmodel or as "
        "evidence that the removed component is erroneous."
    )
    require(
        generation.get("status") == "PASS"
        and generation.get("generator") == "scripts/run_audit.py"
        and generation.get("sha256") == sha256_file(report_path),
        "REPORT_GENERATION: report provenance/hash changed",
    )
    require(
        "## Largest covariance-component algebraic sensitivities" in report
        and caution in report
        and "## Constraint-discarding and indefinite ablation diagnostics"
        in report,
        "REPORT_GENERATION: classification explanation is incomplete",
    )
    main_section = report.split(
        "## Largest covariance-component algebraic sensitivities", 1
    )[1].split(
        "## Constraint-discarding and indefinite ablation diagnostics", 1
    )[0]
    require(
        "sn1a_hubble_flow_link_variance" not in main_section,
        "REPORT_GENERATION: SN-Ia link appears in the normal ranking",
    )
    source = (project_root / "scripts" / "run_audit.py").read_text(
        encoding="utf-8"
    )
    require(
        caution in source,
        "REPORT_GENERATION: generated text is absent from run_audit.py",
    )


def verify_scientific_boundary(project_root: pathlib.Path) -> None:
    required = {
        "README.md": "None of these diagnostics is a corrected H0",
        "REPORT.md": "does **not** show",
        "REPORT_JA.md": "ハッブルテンション",
        "POSTHOC_REPORT.md": "does not report a corrected H0",
        "EXPLORATORY_REPORT.md": "does not resolve the Hubble tension",
    }
    for relative, phrase in required.items():
        text = (project_root / relative).read_text(encoding="utf-8")
        require(
            phrase in text,
            f"SCIENTIFIC_BOUNDARY: {relative} lost its interpretation boundary",
        )
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in project_root.glob("*.md")
    ).lower()
    for prohibited in [
        "independently validated",
        "confirmed flaw",
    ]:
        require(
            prohibited not in combined,
            f"SCIENTIFIC_BOUNDARY: prohibited claim {prohibited!r}",
        )


def verify_no_upstream_bytes(project_root: pathlib.Path) -> None:
    tracked = packaged_paths(project_root)
    forbidden_roots = {
        "data",
        "h0_constrainer",
        "idlcode",
        "H0DN",
        "H0DN_CLEAN",
    }
    bundled = [
        path
        for path in tracked
        if pathlib.PurePosixPath(path).parts
        and pathlib.PurePosixPath(path).parts[0] in forbidden_roots
    ]
    require(
        not bundled,
        "NO_UPSTREAM_BYTES: bundled upstream paths: " + ", ".join(bundled),
    )


def verify_root_closure(project_root: pathlib.Path) -> int:
    manifest_path = project_root / "MANIFEST.tsv"
    sums_path = project_root / "SHA256SUMS.txt"
    require(
        manifest_path.is_file() and sums_path.is_file(),
        "ROOT_CLOSURE: manifest/checksum file is missing",
    )
    fields, rows = read_tsv_with_header(manifest_path)
    require(
        fields == ["path", "bytes", "sha256"],
        "ROOT_CLOSURE: manifest fields changed",
    )
    actual_paths = [row["path"] for row in rows]
    expected_paths = [
        path
        for path in packaged_paths(project_root)
        if path not in MANIFEST_EXCLUSIONS
    ]
    require(
        actual_paths == expected_paths,
        "ROOT_CLOSURE: manifest does not exactly cover packaged tracked files",
    )
    expected_sum_lines: list[str] = []
    for row in rows:
        target = project_root / row["path"]
        require(
            target.is_file(),
            f"ROOT_CLOSURE: missing file {row['path']}",
        )
        require(
            target.stat().st_size == integer(row, "bytes"),
            f"ROOT_CLOSURE: size mismatch for {row['path']}",
        )
        require(
            sha256_file(target) == row["sha256"],
            f"ROOT_CLOSURE: SHA-256 mismatch for {row['path']}",
        )
        expected_sum_lines.append(f"{row['sha256']}  {row['path']}\n")
    actual_sum_lines = sums_path.read_text(encoding="utf-8").splitlines(
        keepends=True
    )
    require(
        actual_sum_lines == expected_sum_lines,
        "ROOT_CLOSURE: SHA256SUMS.txt differs from MANIFEST.tsv",
    )
    return len(rows)


def verify(
    project_root: pathlib.Path,
    upstream: pathlib.Path | None,
    *,
    skip_package_integrity: bool,
) -> GateRecorder:
    results = project_root / "results"
    required = [
        "AUDIT_CONTRACT.md",
        "POSTHOC_DIAGNOSTIC_CONTRACT.md",
        "POSTHOC_INTERACTION_DECOMPOSITION_CONTRACT.md",
        "EXPLORATORY_VARIANCE_COMPONENT_CONTRACT.md",
        "REPORT.md",
        "REPORT_JA.md",
        "POSTHOC_REPORT.md",
        "EXPLORATORY_REPORT.md",
        "CORRECTED_BUILD_MARKER.md",
        "AI_ASSISTANCE_DISCLOSURE.md",
        "provenance/SOURCE_LOCK.tsv",
        "results/EXECUTION_STATUS.json",
        "results/POSTHOC_EXECUTION_STATUS.json",
        "results/EXPLORATORY_EXECUTION_STATUS.json",
        "results/baseline_reproduction.json",
        "results/component_decomposition_closure.json",
        "results/covariance_component_ablation.tsv",
        "results/leave_one_block_out.tsv",
        "results/representation_invariance.tsv",
        "results/solver_cutoff_sensitivity.tsv",
        "results/posthoc_row_scaling_diagnostic.json",
        "results/posthoc_cepheid_interaction_cells.tsv",
        "results/exploratory_variance_component_summary.json",
        "results/exploratory_variance_component_profile.tsv",
        "results/report_generation.json",
    ]
    missing = [name for name in required if not (project_root / name).is_file()]
    require(not missing, "REQUIRED_OUTPUTS: " + ", ".join(missing))

    recorder = GateRecorder()
    recorder.passed("REQUIRED_OUTPUTS", f"{len(required)} required files")

    marker = (project_root / "CORRECTED_BUILD_MARKER.md").read_text(
        encoding="utf-8"
    )
    require(
        "H0DN-AUDIT-0.1.0-CORRECTED-FINAL-20260730-01" in marker
        and (
            "d037fe7a1278230df9b9a77142e3ebce37d2b615c9b3ac56db6204027fa78df0"
            in marker
        ),
        "DELIVERY_ID: corrected-build marker is missing or changed",
    )
    recorder.passed(
        "DELIVERY_ID",
        "corrected delivery ID present; stale d037 archive identified",
    )

    tsv_count = verify_tsv_schema(project_root)
    recorder.passed("TSV_SCHEMA", f"{tsv_count} TSV files")

    verify_authorship(project_root)
    recorder.passed(
        "AUTHORSHIP_SYNC",
        "CFF, LICENSE, README, and AI disclosure name Keiji Yoshimura",
    )

    verify_cff(project_root)
    recorder.passed(
        "CFF_PARSE", "valid CFF 1.2.0; unpublished version 0.1.0"
    )

    verify_source_lock(project_root, upstream)
    recorder.passed(
        "SOURCE_LOCK",
        (
            f"69 files at {UPSTREAM_COMMIT}"
            if upstream is not None
            else "69 locked source records"
        ),
    )

    verify_execution_statuses(results)
    recorder.passed("EXECUTION_STATUS", "all three runners completed")

    verify_core_science(project_root)
    recorder.passed(
        "CORE_SCIENTIFIC_VALUES",
        "baseline, scaling, nullspace, closure, and REML values unchanged",
    )

    sn_link, ablation_count = verify_ablation_classification(project_root)
    recorder.passed(
        "ABLATION_CLASSIFICATION",
        f"all {ablation_count} rows use fixed interpretation/model vocabularies",
    )

    verify_snia_link(project_root, sn_link)
    recorder.passed(
        "SNIA_LINK_DROP",
        "rank 183->182; equation 248 has zero variance/precision",
    )
    recorder.passed(
        "LOO_MATCH",
        "SN-Ia link ablation matches leave-one-block-out within 1e-9",
    )

    verify_indefinite_separation(project_root)
    recorder.passed(
        "INDEFINITE_SEPARATION",
        "main ranking contains PSD algebraic sensitivities only",
    )

    verify_report_generation(project_root)
    recorder.passed(
        "REPORT_GENERATION",
        "REPORT.md hash and generator classification text verified",
    )

    verify_scientific_boundary(project_root)
    recorder.passed(
        "SCIENTIFIC_BOUNDARY",
        "no corrected-H0, causal-systematic, or tension-resolution claim",
    )

    verify_no_upstream_bytes(project_root)
    recorder.passed(
        "NO_UPSTREAM_BYTES", "no upstream source/data root is packaged"
    )

    if not skip_package_integrity:
        closure_count = verify_root_closure(project_root)
        recorder.passed(
            "ROOT_CLOSURE",
            f"{closure_count} packaged files covered by hashes",
        )
    return recorder


def write_summary(
    project_root: pathlib.Path, recorder: GateRecorder
) -> pathlib.Path:
    target = project_root / "results" / "final_verification_summary.json"
    payload = {
        "status": "PASS",
        "upstream_commit": UPSTREAM_COMMIT,
        "gate_count": len(recorder.gates),
        "gates": recorder.gates,
        "scientific_values_changed": False,
        "correction_scope": [
            "classification",
            "wording",
            "metadata",
            "verification",
            "package closure",
        ],
    }
    with target.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        handle.write("\n")
    return target


def main() -> int:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--upstream",
        type=pathlib.Path,
        help="Optionally verify every frozen upstream source file.",
    )
    parser.add_argument(
        "--skip-package-integrity",
        action="store_true",
        help=(
            "Skip ROOT_CLOSURE only during a clean analysis run before "
            "manifests are regenerated."
        ),
    )
    parser.add_argument(
        "--write-summary",
        action="store_true",
        help="Write results/final_verification_summary.json after all gates.",
    )
    args = parser.parse_args()
    if args.write_summary and args.skip_package_integrity:
        parser.error("--write-summary requires the ROOT_CLOSURE gate")
    try:
        recorder = verify(
            project_root,
            args.upstream,
            skip_package_integrity=args.skip_package_integrity,
        )
        summary_path = (
            write_summary(project_root, recorder)
            if args.write_summary
            else None
        )
    except (
        csv.Error,
        json.JSONDecodeError,
        OSError,
        subprocess.CalledProcessError,
        TypeError,
        VerificationFailure,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    source_note = (
        f" and upstream {UPSTREAM_COMMIT}"
        if args.upstream is not None
        else ""
    )
    print(
        f"PASS: {len(recorder.gates)} verification gates{source_note}"
    )
    if summary_path is not None:
        print(f"PASS: wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
