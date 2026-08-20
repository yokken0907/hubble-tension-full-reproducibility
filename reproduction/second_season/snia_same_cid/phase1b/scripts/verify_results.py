#!/usr/bin/env python3
"""Independent, read-only reproduction of the delivered scientific gates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from typing import Any

import numpy as np

from auditlib import (
    BOUNDARY_MARKER,
    CONTRACT_FREEZE_SHA256,
    SUCCESS_STATUS,
    load_config,
    sha256_file,
    verify_contract_freeze,
    verify_sources,
    write_json,
)
from package_tools import package_files, verify_manifests
from package_tools import deterministic_archive


EXPECTED_TEST_COUNT = 18
EXPECTED_STATUS = SUCCESS_STATUS
EXPECTED_CORE = {
    "h0dn_rows": 277,
    "unique_names": 238,
    "multirow_groups": 30,
    "multirow_rows": 69,
    "eligible_official_rows": 277,
    "official_rows": 1701,
    "exact_covariance_elements": 76729,
    "official_asymmetric_elements": 778,
    "official_max_asymmetry": 3.0000000000038676e-08,
    "catalog_only_unique_rows": 275,
    "catalog_only_ambiguous_rows": 2,
    "covariance_diagonal_required_rows": 2,
    "catalog_candidate_evidence_rows": 279,
}
REQUIRED_READER_DOCUMENTS = (
    "README.md",
    "AUDIT_CONTRACT.md",
    "REPORT.md",
    "REPORT_JA.md",
    "REPRODUCIBILITY.md",
    "PACKAGE_VALIDATION.md",
)


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def add(
    checks: list[dict[str, str]],
    check_id: str,
    passed: bool,
    detail: str,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "detail": detail,
            "status": "PASS" if passed else "FAIL",
        }
    )


def run_tests(project: pathlib.Path) -> tuple[subprocess.CompletedProcess[str], str, int]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=project,
        capture_output=True,
        text=True,
        env=environment,
    )
    log = completed.stdout + completed.stderr
    match = re.search(r"Ran (\d+) tests?", log)
    return completed, log, int(match.group(1)) if match else -1


def independent_h0dn(path: pathlib.Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].removeprefix("#").split()
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines[1:]):
        if not line.strip():
            continue
        raw = dict(zip(header, line.split(), strict=True))
        rows.append(
            {
                "index": index,
                "name": raw["name"],
                "m_b": float(raw["m_b"]),
                "err": float(raw["err_m_b"]),
                "zhel": float(raw["zhel"]),
                "zcmb": float(raw["zcmb"]),
            }
        )
    return rows


def independent_official(path: pathlib.Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split()
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines[1:]):
        if not line.strip():
            continue
        raw = dict(zip(header, line.split(), strict=True))
        rows.append(
            {
                "index": index,
                "CID": raw["CID"],
                "IDSURVEY": int(raw["IDSURVEY"]),
                "m_b_corr": float(raw["m_b_corr"]),
                "m_b_corr_err_DIAG": float(
                    raw["m_b_corr_err_DIAG"]
                ),
                "zHEL": float(raw["zHEL"]),
                "zCMB": float(raw["zCMB"]),
                "used": float(raw["USED_IN_SH0ES_HF"]),
            }
        )
    return rows


def independent_covariance(path: pathlib.Path) -> np.ndarray:
    # Deliberately uses loadtxt rather than the audit runner's fromstring parser.
    values = np.loadtxt(path, dtype=np.float64)
    dimension = int(values[0])
    if values.size != dimension * dimension + 1:
        raise RuntimeError(f"wrong covariance payload length: {path}")
    return values[1:].reshape(dimension, dimension)


def independent_reproduction(
    h0dn_root: pathlib.Path,
    official_root: pathlib.Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    hrows = independent_h0dn(h0dn_root / "data/sn1a_hf_pp.dat")
    orows = independent_official(
        official_root
        / "Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat"
    )
    hcov = independent_covariance(h0dn_root / "data/sn1a_covar_pp.dat")
    ocov = independent_covariance(
        official_root
        / (
            "Pantheon+_Data/4_DISTANCES_AND_COVAR/"
            "Pantheon+SH0ES_STAT+SYS.cov"
        )
    )
    active = config["active_matching"]
    catalog_tolerance = active["catalog_only_stage"][
        "maximum_absolute_differences"
    ]
    error_tolerance = active["covariance_assisted_stage"][
        "maximum_absolute_difference"
    ]
    eligible = [row for row in orows if row["used"] == 1]
    catalog_candidate_sets: list[list[dict[str, Any]]] = []
    catalog_classes: list[str] = []
    candidate_sets: list[list[dict[str, Any]]] = []
    final_classes: list[str] = []
    for hrow in hrows:
        catalog_candidates: list[dict[str, Any]] = []
        for orow in eligible:
            if orow["CID"] != hrow["name"]:
                continue
            deltas = {
                "m_b": abs(hrow["m_b"] - orow["m_b_corr"]),
                "zhel": abs(hrow["zhel"] - orow["zHEL"]),
                "zcmb": abs(hrow["zcmb"] - orow["zCMB"]),
            }
            if (
                deltas["m_b"] <= catalog_tolerance["m_b__m_b_corr"]
                and deltas["zhel"]
                <= catalog_tolerance["zhel__zHEL"]
                and deltas["zcmb"]
                <= catalog_tolerance["zcmb__zCMB"]
            ):
                catalog_candidates.append(
                    {
                        **orow,
                        "deltas": deltas,
                    }
                )
        catalog_candidates.sort(
            key=lambda row: (row["index"], row["CID"], row["IDSURVEY"])
        )
        catalog_candidate_sets.append(catalog_candidates)
        if len(catalog_candidates) == 1:
            catalog_class = "CATALOG_ONLY_UNIQUE"
            final_candidates = catalog_candidates
            final_class = "CATALOG_ONLY_UNIQUE"
        elif len(catalog_candidates) > 1:
            catalog_class = "CATALOG_ONLY_AMBIGUOUS"
            assisted: list[dict[str, Any]] = []
            for candidate in catalog_candidates:
                official_error = math.sqrt(
                    ocov[candidate["index"], candidate["index"]]
                )
                candidate["official_error"] = official_error
                candidate["error_delta"] = abs(
                    hrow["err"] - official_error
                )
                if candidate["error_delta"] <= error_tolerance:
                    assisted.append(candidate)
            final_candidates = assisted
            if len(assisted) == 1:
                final_class = "COVARIANCE_DIAGONAL_REQUIRED"
            elif assisted:
                final_class = "AMBIGUOUS_AFTER_ALL_RULES"
            else:
                final_class = "UNMATCHED_AFTER_ALL_RULES"
        else:
            catalog_class = "CATALOG_ONLY_UNMATCHED"
            final_candidates = []
            final_class = "UNMATCHED_AFTER_ALL_RULES"
        catalog_classes.append(catalog_class)
        candidate_sets.append(final_candidates)
        final_classes.append(final_class)
    unique = all(len(rows) == 1 for rows in candidate_sets)
    indices = (
        [rows[0]["index"] for rows in candidate_sets] if unique else []
    )
    one_to_one = unique and len(indices) == len(set(indices))

    names: dict[str, list[int]] = defaultdict(list)
    for index, hrow in enumerate(hrows):
        names[hrow["name"]].append(index)
    multirow = {
        name: indices_for_name
        for name, indices_for_name in names.items()
        if len(indices_for_name) > 1
    }
    group_records: list[dict[str, Any]] = []
    if one_to_one:
        for name, hindices in multirow.items():
            codes = [candidate_sets[index][0]["IDSURVEY"] for index in hindices]
            counts = Counter(codes)
            if len(counts) == 1:
                classification = "SAME_SURVEY_REPEATED"
            elif all(count == 1 for count in counts.values()):
                classification = "MULTI_SURVEY_ONLY"
            else:
                classification = "MIXED_SURVEY_MULTIPLICITY"
            group_records.append(
                {
                    "name": name,
                    "hindices": hindices,
                    "official_indices": [
                        candidate_sets[index][0]["index"]
                        for index in hindices
                    ],
                    "codes": codes,
                    "classification": classification,
                }
            )
        submatrix = ocov[np.ix_(indices, indices)]
        equality = submatrix == hcov
        covariance_mismatch_count = int(np.count_nonzero(~equality))
        max_covariance_difference = float(np.max(np.abs(submatrix - hcov)))
    else:
        covariance_mismatch_count = -1
        max_covariance_difference = math.nan
    discrepancy_rows: list[dict[str, float]] = []
    if one_to_one:
        for hrow, candidates in zip(hrows, candidate_sets, strict=True):
            matched = candidates[0]
            matrix_error = math.sqrt(
                ocov[matched["index"], matched["index"]]
            )
            discrepancy_rows.append(
                {
                    "catalog_vs_matrix": abs(
                        matched["m_b_corr_err_DIAG"] - matrix_error
                    ),
                    "h0dn_vs_matrix": abs(hrow["err"] - matrix_error),
                }
            )
    transpose_difference = np.abs(ocov - ocov.T)
    return {
        "hrows": hrows,
        "orows": orows,
        "hcov": hcov,
        "ocov": ocov,
        "eligible": eligible,
        "catalog_candidate_sets": catalog_candidate_sets,
        "catalog_classes": catalog_classes,
        "candidate_sets": candidate_sets,
        "final_classes": final_classes,
        "one_to_one": one_to_one,
        "indices": indices,
        "multirow": multirow,
        "group_records": group_records,
        "covariance_mismatch_count": covariance_mismatch_count,
        "max_covariance_difference": max_covariance_difference,
        "discrepancy_rows": discrepancy_rows,
        "official_asymmetric_elements": int(
            np.count_nonzero(transpose_difference)
        ),
        "official_max_asymmetry": float(np.max(transpose_difference)),
    }


def tracked_snapshot(project: pathlib.Path) -> dict[str, tuple[int, str]]:
    paths = package_files(project)
    for filename in ("MANIFEST.tsv", "SHA256SUMS.txt"):
        path = project / filename
        if path.is_file():
            paths.append(path)
    return {
        path.relative_to(project).as_posix(): (
            path.stat().st_size,
            sha256_file(path),
        )
        for path in sorted(
            set(paths), key=lambda item: item.relative_to(project).as_posix()
        )
    }


def verify(
    project: pathlib.Path,
    h0dn_root: pathlib.Path,
    official_root: pathlib.Path,
    *,
    tests: subprocess.CompletedProcess[str],
    test_count: int,
    baseline_snapshot: dict[str, tuple[int, str]],
) -> dict[str, Any]:
    results = project / "results"
    checks: list[dict[str, str]] = []
    contract = verify_contract_freeze(project)
    source = verify_sources(
        project,
        {"h0dn": h0dn_root, "pantheonplus": official_root},
    )
    locked_file_count = sum(
        row["locked_file_count"]
        for row in source["repositories"].values()
    )
    expected_commits = {
        "h0dn": "cc0a4b9f36e65470d514f254a3c5cffa463fbd94",
        "pantheonplus": "c447f0fea703fcd0fff57de5000947b5ca81286b",
    }
    add(
        checks,
        "GATE-P1B-01",
        contract["status"] == "PASS"
        and contract["contract_freeze_sha256"] == CONTRACT_FREEZE_SHA256
        and source["status"] == "PASS"
        and locked_file_count == 9
        and all(
            source["repositories"][key]["actual_commit"] == value
            for key, value in expected_commits.items()
        ),
        (
            f"contract={contract['status']}; source={source['status']}; "
            f"locked_files={locked_file_count}"
        ),
    )

    amendments_path = project / "provenance" / "CONTRACT_AMENDMENTS.tsv"
    with amendments_path.open("r", encoding="utf-8", newline="") as handle:
        amendment_reader = csv.DictReader(handle, delimiter="\t")
        amendment_fields = amendment_reader.fieldnames
        amendments = list(amendment_reader)
    amendment_signature = [
        (
            row["amendment_id"],
            row["results_observed"],
            row["interpretation_affected"],
        )
        for row in amendments
    ]
    add(
        checks,
        "GATE-P1B-02",
        amendment_fields
        == [
            "amendment_id",
            "timestamp_utc",
            "files_changed",
            "results_observed",
            "interpretation_affected",
            "reason",
        ]
        and amendment_signature
        == [
            ("AMEND-001", "NO", "NO"),
            ("AMEND-002", "YES", "NO"),
            ("AMEND-003", "YES", "YES"),
            ("AMEND-004", "YES", "NO"),
        ]
        and [row["timestamp_utc"] for row in amendments]
        == sorted(row["timestamp_utc"] for row in amendments),
        str(amendment_signature),
    )

    config = load_config(project)
    reproduced = independent_reproduction(h0dn_root, official_root, config)
    reader_paths = [
        project / name
        for name in (
            "README.md",
            "REPORT.md",
            "REPORT_JA.md",
            "REPRODUCIBILITY.md",
            "PACKAGE_VALIDATION.md",
            "CHANGELOG.md",
        )
    ] + [results / "README.md"]
    reader_text = "\n".join(
        path.read_text(encoding="utf-8") for path in reader_paths
    )
    reader_lower = reader_text.lower()
    add(
        checks,
        "GATE-P1B-03",
        "different catalog uncertainty field" not in reader_lower
        and "共分散対角とは別種の誤差" not in reader_text
        and "公式文書上も別の誤差" not in reader_text,
        "reader-facing prohibited uncertainty-type assertions",
    )

    discrepancy_summary = read_json(
        results / "error_field_discrepancy_summary.json"
    )
    matching_amendment = read_json(
        project / "provenance" / "MATCHING_RULE_AMENDMENT.json"
    )
    add(
        checks,
        "GATE-P1B-04",
        discrepancy_summary["cause_classification"]
        == "UNRESOLVED_DOCUMENTATION_DATA_DISCREPANCY"
        and matching_amendment["reader_explanation_correction"][
            "cause_classification"
        ]
        == "UNRESOLVED_DOCUMENTATION_DATA_DISCREPANCY"
        and "frozen readme" in reader_lower
        and "do not numerically equal" in reader_lower
        and config["active_matching"][
            "error_field_discrepancy_diagnostic"
        ]["cause_classification"]
        == "UNRESOLVED_DOCUMENTATION_DATA_DISCREPANCY",
        discrepancy_summary["cause_classification"],
    )

    discrepancy_rows = read_tsv(
        results / "error_field_discrepancy_rows.tsv"
    )
    catalog_differences = [
        abs(
            float(row["official_m_b_corr_err_DIAG"])
            - float(row["official_STAT_SYS_diagonal_sqrt"])
        )
        for row in discrepancy_rows
    ]
    h0dn_differences = [
        abs(
            float(row["h0dn_err_m_b"])
            - float(row["official_STAT_SYS_diagonal_sqrt"])
        )
        for row in discrepancy_rows
    ]
    diagnostic_config = config["active_matching"][
        "error_field_discrepancy_diagnostic"
    ]
    catalog_within = sum(
        value
        <= diagnostic_config[
            "catalog_vs_matrix_maximum_absolute_difference"
        ]
        for value in catalog_differences
    )
    h0dn_within = sum(
        value
        <= diagnostic_config["h0dn_vs_matrix_maximum_absolute_difference"]
        for value in h0dn_differences
    )
    discrepancy_ok = (
        len(discrepancy_rows) == 277
        and discrepancy_summary["row_count"] == 277
        and discrepancy_summary[
            "catalog_vs_matrix_within_tolerance_count"
        ]
        == catalog_within
        and discrepancy_summary["catalog_vs_matrix_max_abs_difference"]
        == max(catalog_differences)
        and discrepancy_summary[
            "h0dn_vs_matrix_within_h0dn_print_tolerance_count"
        ]
        == h0dn_within
        and discrepancy_summary["h0dn_vs_matrix_max_abs_difference"]
        == max(h0dn_differences)
        and catalog_differences
        == [row["catalog_vs_matrix"] for row in reproduced["discrepancy_rows"]]
        and h0dn_differences
        == [row["h0dn_vs_matrix"] for row in reproduced["discrepancy_rows"]]
    )
    add(
        checks,
        "GATE-P1B-05",
        discrepancy_ok,
        (
            f"rows={len(discrepancy_rows)}; catalog_within="
            f"{catalog_within}; h0dn_within={h0dn_within}"
        ),
    )

    dependency_summary = read_json(
        results / "row_mapping_dependency_summary.json"
    )
    dependency_rows = read_tsv(results / "row_mapping_dependency.tsv")
    catalog_counts = Counter(
        row["catalog_only_classification"] for row in dependency_rows
    )
    group_class_counts = Counter(
        row["classification"] for row in reproduced["group_records"]
    )
    add(
        checks,
        "GATE-P1B-06",
        len(dependency_rows) == 277
        and sum(catalog_counts.values()) == 277
        and catalog_counts
        == {
            "CATALOG_ONLY_UNIQUE": EXPECTED_CORE[
                "catalog_only_unique_rows"
            ],
            "CATALOG_ONLY_AMBIGUOUS": EXPECTED_CORE[
                "catalog_only_ambiguous_rows"
            ],
        }
        and dependency_summary["catalog_only_unique_row_count"]
        == catalog_counts["CATALOG_ONLY_UNIQUE"]
        and dependency_summary["catalog_only_ambiguous_row_count"]
        == catalog_counts["CATALOG_ONLY_AMBIGUOUS"]
        and dependency_summary["catalog_only_unmatched_row_count"] == 0,
        str(dict(catalog_counts)),
    )

    final_counts = Counter(
        row["final_dependency_classification"]
        for row in dependency_rows
    )
    required_rows = read_tsv(
        results / "covariance_diagonal_required_rows.tsv"
    )
    add(
        checks,
        "GATE-P1B-07",
        final_counts["AMBIGUOUS_AFTER_ALL_RULES"] == 0
        and final_counts["UNMATCHED_AFTER_ALL_RULES"] == 0
        and final_counts["COVARIANCE_DIAGONAL_REQUIRED"]
        == EXPECTED_CORE["covariance_diagonal_required_rows"]
        and dependency_summary["ambiguous_after_all_rules_row_count"] == 0
        and dependency_summary["unmatched_after_all_rules_row_count"] == 0
        and len(required_rows)
        == EXPECTED_CORE["covariance_diagonal_required_rows"]
        and all(
            row["final_dependency_classification"]
            == "COVARIANCE_DIAGONAL_REQUIRED"
            for row in required_rows
        ),
        (
            f"covariance_required="
            f"{final_counts['COVARIANCE_DIAGONAL_REQUIRED']}; "
            f"ambiguous={final_counts['AMBIGUOUS_AFTER_ALL_RULES']}; "
            f"unmatched={final_counts['UNMATCHED_AFTER_ALL_RULES']}"
        ),
    )

    mapping = read_tsv(results / "row_mapping.tsv")
    mapping_ok = (
        len(reproduced["hrows"]) == EXPECTED_CORE["h0dn_rows"]
        and len({row["name"] for row in reproduced["hrows"]})
        == EXPECTED_CORE["unique_names"]
        and len(reproduced["orows"]) == EXPECTED_CORE["official_rows"]
        and len(reproduced["eligible"])
        == EXPECTED_CORE["eligible_official_rows"]
        and reproduced["one_to_one"]
        and len(reproduced["indices"]) == EXPECTED_CORE["h0dn_rows"]
        and set(reproduced["indices"])
        == {row["index"] for row in reproduced["eligible"]}
        and len(mapping) == len(reproduced["hrows"])
    )
    if mapping_ok:
        for index, recorded in enumerate(mapping):
            candidate = reproduced["candidate_sets"][index]
            if (
                len(candidate) != 1
                or recorded["match_status"] != "UNIQUE_MATCH"
                or int(recorded["h0dn_row_1based"]) != index + 1
                or recorded["name"] != reproduced["hrows"][index]["name"]
                or int(recorded["official_row_1based"])
                != candidate[0]["index"] + 1
                or int(recorded["IDSURVEY"]) != candidate[0]["IDSURVEY"]
            ):
                mapping_ok = False
                break
    audit_summary = read_json(results / "audit_summary.json")
    candidates = read_tsv(results / "candidate_evidence.tsv")
    add(
        checks,
        "GATE-P1B-08",
        mapping_ok
        and len(candidates)
        == EXPECTED_CORE["catalog_candidate_evidence_rows"]
        and audit_summary["mapping"]["unique_match_count"] == 277
        and audit_summary["mapping"]["reused_official_row_count"] == 0
        and audit_summary["mapping"][
            "official_candidate_pool_fully_covered"
        ]
        and dependency_summary["final_one_to_one_match_count"] == 277
        and dependency_summary["official_row_reuse_count"] == 0
        and dependency_summary["official_candidate_coverage_complete"],
        f"{len(mapping)}/277 mapping rows; {len(candidates)} candidates",
    )

    groups = read_tsv(results / "multirow_group_summary.tsv")
    groups_ok = len(groups) == len(reproduced["group_records"])
    if groups_ok:
        for recorded, expected in zip(
            groups, reproduced["group_records"], strict=True
        ):
            if (
                recorded["name"] != expected["name"]
                or recorded["h0dn_rows_1based"]
                != ";".join(str(value + 1) for value in expected["hindices"])
                or recorded["official_rows_1based"]
                != ";".join(
                    str(value + 1) for value in expected["official_indices"]
                )
                or recorded["IDSURVEY_codes"]
                != ";".join(str(value) for value in expected["codes"])
                or recorded["survey_multiplicity_class"]
                != expected["classification"]
            ):
                groups_ok = False
                break
    multirow_evidence = read_tsv(results / "multirow_row_evidence.tsv")
    add(
        checks,
        "GATE-P1B-09",
        groups_ok
        and len(reproduced["multirow"]) == EXPECTED_CORE["multirow_groups"]
        and sum(len(value) for value in reproduced["multirow"].values())
        == EXPECTED_CORE["multirow_rows"]
        and Counter(int(row["h0dn_row_count"]) for row in groups)
        == {2: 21, 3: 9}
        and len(multirow_evidence) == 69,
        f"{len(groups)} groups; {len(multirow_evidence)} rows",
    )
    add(
        checks,
        "GATE-P1B-10",
        group_class_counts == {"MULTI_SURVEY_ONLY": 30}
        and Counter(
            row["survey_multiplicity_class"] for row in groups
        )
        == {"MULTI_SURVEY_ONLY": 30},
        str(dict(group_class_counts)),
    )

    covariance = read_json(results / "covariance_lineage.json")
    add(
        checks,
        "GATE-P1B-11",
        reproduced["covariance_mismatch_count"] == 0
        and reproduced["max_covariance_difference"] == 0.0
        and reproduced["official_asymmetric_elements"]
        == EXPECTED_CORE["official_asymmetric_elements"]
        and reproduced["official_max_asymmetry"]
        == EXPECTED_CORE["official_max_asymmetry"]
        and covariance["status"] == "PASS"
        and covariance["mismatch_count"] == 0
        and covariance["maximum_absolute_difference"] == 0.0
        and covariance["exact_equal_element_count"]
        == EXPECTED_CORE["exact_covariance_elements"],
        (
            f"{covariance['exact_equal_element_count']}/"
            f"{EXPECTED_CORE['exact_covariance_elements']}; "
            f"max_abs={covariance['maximum_absolute_difference']}"
        ),
    )

    add(
        checks,
        "GATE-P1B-12",
        "did not rebuild" not in reader_lower
        and "did not lose, rebuild" not in reader_lower
        and "再構築していない" not in reader_text
        and not re.search(
            r"再構築したり.{0,24}していない", reader_text
        ),
        "reader-facing covariance-process overclaims",
    )

    joint_english = (
        "joint catalog-and-covariance lineage" in reader_lower
    )
    joint_japanese = "共同来歴" in reader_text and "完全に独立" in reader_text
    add(
        checks,
        "GATE-P1B-13",
        joint_english
        and joint_japanese
        and dependency_summary["lineage_classification"]
        == "JOINT_CATALOG_AND_COVARIANCE_LINEAGE"
        and audit_summary["row_mapping_dependency"][
            "lineage_classification"
        ]
        == "JOINT_CATALOG_AND_COVARIANCE_LINEAGE",
        "joint catalog-and-covariance lineage disclosure",
    )

    execution = read_json(results / "EXECUTION_STATUS.json")
    phase1c_results = [
        path
        for path in results.rglob("*")
        if path.is_file() and "phase1c" in path.name.lower()
    ]
    add(
        checks,
        "GATE-P1B-14",
        audit_summary["status"] == EXPECTED_STATUS
        and execution["formal_status"] == EXPECTED_STATUS
        and audit_summary["boundary_marker"] == BOUNDARY_MARKER
        and execution["boundary_marker"] == BOUNDARY_MARKER
        and (project / "VERSION").read_text(encoding="utf-8").strip()
        == "0.1.0"
        and not phase1c_results,
        f"status={audit_summary['status']}; boundary={BOUNDARY_MARKER}",
    )

    clean = read_json(results / "clean_reproduction_summary.json")
    add(
        checks,
        "GATE-P1B-15",
        tests.returncode == 0
        and test_count == EXPECTED_TEST_COUNT
        and clean["status"] == "PASS"
        and clean["all_core_artifacts_bytes_identical"]
        and clean["unit_test_returncode"] == 0
        and clean["audit_returncode"] == 0,
        (
            f"tests={test_count}; test_returncode={tests.returncode}; "
            f"clean={clean['status']}"
        ),
    )
    add(
        checks,
        "GATE-P1B-16",
        baseline_snapshot == tracked_snapshot(project),
        "default verification path left the project tree unchanged",
    )

    manifest_checked = (project / "MANIFEST.tsv").is_file()
    if manifest_checked:
        try:
            manifest = verify_manifests(project)
            manifest_ok = manifest["status"] == "PASS"
            manifest_detail = (
                f"{manifest['manifested_file_count']} manifested files"
            )
        except Exception as exc:
            manifest_ok = False
            manifest_detail = f"{type(exc).__name__}: {exc}"
        add(checks, "GATE-P1B-17", manifest_ok, manifest_detail)
        replica_ok = False
        replica_detail = "manifest verification failed"
        if manifest_ok:
            try:
                with tempfile.TemporaryDirectory() as raw:
                    temp = pathlib.Path(raw)
                    first = deterministic_archive(
                        project, temp / "replica-a.zip"
                    )
                    second = deterministic_archive(
                        project, temp / "replica-b.zip"
                    )
                    first_bytes = (temp / "replica-a.zip").read_bytes()
                    second_bytes = (temp / "replica-b.zip").read_bytes()
                    replica_ok = first_bytes == second_bytes
                    replica_detail = (
                        f"{first['archive_sha256']} == "
                        f"{second['archive_sha256']}"
                    )
            except Exception as exc:
                replica_detail = f"{type(exc).__name__}: {exc}"
        add(checks, "GATE-P1B-18", replica_ok, replica_detail)
    return finalize(checks, manifest_checked=manifest_checked)


def finalize(
    checks: list[dict[str, str]],
    *,
    manifest_checked: bool,
) -> dict[str, Any]:
    passed = sum(row["status"] == "PASS" for row in checks)
    return {
        "check_count": len(checks),
        "checks": checks,
        "fail_count": len(checks) - passed,
        "manifest_checked": manifest_checked,
        "pass_count": passed,
        "status": "PASS" if passed == len(checks) else "FAIL",
        "verification_scope": (
            "LIVE_READ_ONLY_COMPLETE"
            if manifest_checked
            else "CLOSURE_RECORD_PRE_MANIFEST"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--record-results", action="store_true")
    parser.add_argument("--output-dir", type=pathlib.Path)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    before = tracked_snapshot(project)
    tests, test_log, test_count = run_tests(project)
    try:
        summary = verify(
            project,
            args.h0dn.resolve(),
            args.pantheonplus.resolve(),
            tests=tests,
            test_count=test_count,
            baseline_snapshot=before,
        )
    except Exception as exc:
        summary = {
            "error": f"{type(exc).__name__}: {exc}",
            "status": "FAIL",
        }
    if args.record_results:
        (project / "results" / "unit_tests.log").write_text(
            test_log, encoding="utf-8"
        )
        write_json(
            project / "results" / "final_verification_summary.json",
            summary,
        )
    elif args.output_dir:
        output = args.output_dir.resolve()
        try:
            output.relative_to(project.resolve())
        except ValueError:
            pass
        else:
            print("FAIL: --output-dir must be outside the project", file=sys.stderr)
            return 2
        output.mkdir(parents=True, exist_ok=True)
        (output / "unit_tests.log").write_text(test_log, encoding="utf-8")
        write_json(output / "live_verification_summary.json", summary)
    after = tracked_snapshot(project)
    if not args.record_results and before != after:
        print("FAIL: read-only verifier changed the project tree", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
