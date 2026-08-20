#!/usr/bin/env python3
"""Core, deterministic functions for the frozen Phase 1B audit."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import subprocess
from collections import Counter, defaultdict
from typing import Any, Iterable

import numpy as np


CONTRACT_FREEZE_SHA256 = (
    "14608b5c9068940f16f5d43b4f7a3fcfa718b3d4c54a0c3c712487572dcc6792"
)
SUCCESS_STATUS = (
    "AUDIT_COMPLETE_PROVENANCE_AND_COVARIANCE_LINEAGE_TRACED"
)
BOUNDARY_MARKER = (
    "PROVENANCE_ONLY_NO_ROW_MODIFICATION_NO_COVARIANCE_CORRECTION_"
    "NO_CORRECTED_H0_NO_TENSION_RESOLUTION"
)


class AuditFailure(RuntimeError):
    """A frozen audit gate failed."""


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_tsv(
    path: pathlib.Path,
    rows: Iterable[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(project: pathlib.Path) -> dict[str, Any]:
    config = read_json(project / "provenance" / "DECISION_CONFIG.json")
    amendment_path = (
        project / "provenance" / "DECISION_CONFIG_AMENDMENTS.json"
    )
    if amendment_path.is_file():
        amendment = read_json(amendment_path)
        expected = {
            "amendment_id": "AMEND-002",
            "contract_id": config["contract_id"],
            "interpretation_affected": False,
            "mapping_or_lineage_results_observed": False,
            "official_full_covariance_symmetry": {
                "action": "record_diagnostic_without_modifying_values",
                "require_exact_symmetry": False,
            },
            "schema_diagnostic_observed": True,
        }
        for key, value in expected.items():
            if amendment.get(key) != value:
                raise AuditFailure(
                    "DECISION_CONFIG_AMENDMENTS.json is invalid"
                )
        config["covariance"][
            "require_official_symmetric_exact"
        ] = False
        config["covariance"]["require_h0dn_symmetric_exact"] = True
        config["applied_decision_amendments"] = ["AMEND-002"]
    matching_amendment_path = (
        project / "provenance" / "MATCHING_RULE_AMENDMENT.json"
    )
    if matching_amendment_path.is_file():
        matching_amendment = read_json(matching_amendment_path)
        if (
            matching_amendment.get("amendment_id") != "AMEND-003"
            or matching_amendment.get("contract_id") != config["contract_id"]
            or matching_amendment.get("interpretation_affected") is not True
            or matching_amendment.get(
                "corrected_rule_results_observed_before_freeze"
            )
            is not False
            or matching_amendment.get("corrected_rule", {}).get(
                "maximum_absolute_difference"
            )
            != config["matching"]["maximum_absolute_differences"][
                "err_m_b__m_b_corr_err_DIAG"
            ]
        ):
            raise AuditFailure("MATCHING_RULE_AMENDMENT.json is invalid")
        config["matching"][
            "error_reference"
        ] = "sqrt_official_stat_sys_covariance_diagonal"
        config["applied_decision_amendments"] = [
            *config.get("applied_decision_amendments", []),
            "AMEND-003",
        ]
    active_matching_path = (
        project / "provenance" / "ACTIVE_MATCHING_CONFIG.json"
    )
    if active_matching_path.is_file():
        active_matching = read_json(active_matching_path)
        expected_active = {
            "amendment_id": "AMEND-004",
            "contract_id": config["contract_id"],
            "interpretation_affected": False,
            "results_observed": True,
        }
        for key, value in expected_active.items():
            if active_matching.get(key) != value:
                raise AuditFailure("ACTIVE_MATCHING_CONFIG.json is invalid")
        catalog_stage = active_matching.get("catalog_only_stage", {})
        covariance_stage = active_matching.get(
            "covariance_assisted_stage", {}
        )
        if (
            catalog_stage.get("prohibited_inputs")
            != [
                "m_b_corr_err_DIAG",
                "Pantheon+SH0ES_STAT+SYS covariance diagonal",
            ]
            or covariance_stage.get("apply_only_to")
            != "CATALOG_ONLY_AMBIGUOUS"
            or active_matching.get("deterministic_candidate_sort")
            != ["official_row_0based", "CID", "IDSURVEY"]
        ):
            raise AuditFailure("ACTIVE_MATCHING_CONFIG.json is invalid")
        config["active_matching"] = active_matching
        config["applied_decision_amendments"] = [
            *config.get("applied_decision_amendments", []),
            "AMEND-004",
        ]
    return config


def verify_contract_freeze(project: pathlib.Path) -> dict[str, Any]:
    freeze_path = project / "provenance" / "CONTRACT_FREEZE.json"
    checks: list[dict[str, str]] = []
    actual_freeze_hash = sha256_file(freeze_path)
    checks.append(
        {
            "path": "provenance/CONTRACT_FREEZE.json",
            "expected_sha256": CONTRACT_FREEZE_SHA256,
            "actual_sha256": actual_freeze_hash,
            "status": (
                "PASS"
                if actual_freeze_hash == CONTRACT_FREEZE_SHA256
                else "FAIL"
            ),
        }
    )
    freeze = read_json(freeze_path)
    for relative, record in sorted(freeze["files"].items()):
        path = project / relative
        if relative == "provenance/CONTRACT_AMENDMENTS.tsv":
            lines = path.read_bytes().splitlines(keepends=True)
            actual = hashlib.sha256(lines[0] if lines else b"").hexdigest()
            verification_scope = "frozen_header_plus_append_only_ledger"
        else:
            actual = sha256_file(path)
            verification_scope = "whole_file"
        expected = record["sha256"]
        checks.append(
            {
                "path": relative,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "verification_scope": verification_scope,
                "status": "PASS" if actual == expected else "FAIL",
            }
        )
    chronology_ok = (
        freeze["status"] == "FROZEN_BEFORE_PHASE1B_EXECUTION"
        and not freeze["full_mapping_results_observed_before_freeze"]
        and not freeze["full_multirow_classification_observed_before_freeze"]
        and not freeze["covariance_lineage_result_observed_before_freeze"]
    )
    return {
        "contract_id": freeze["contract_id"],
        "contract_freeze_sha256": actual_freeze_hash,
        "chronology_status": "PASS" if chronology_ok else "FAIL",
        "checks": checks,
        "status": (
            "PASS"
            if chronology_ok
            and all(row["status"] == "PASS" for row in checks)
            else "FAIL"
        ),
    }


def run_git(repo: pathlib.Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def read_source_lock(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        expected = [
            "source_id",
            "repository",
            "commit",
            "path",
            "git_blob_sha1",
            "bytes",
            "sha256",
        ]
        if reader.fieldnames != expected:
            raise AuditFailure("SOURCE_LOCK.tsv has an unexpected schema")
        rows = list(reader)
    if not rows:
        raise AuditFailure("SOURCE_LOCK.tsv is empty")
    corrections_path = path.parent / "SOURCE_LOCK_CORRECTIONS.tsv"
    if corrections_path.is_file():
        with corrections_path.open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            correction_reader = csv.DictReader(handle, delimiter="\t")
            expected_correction_fields = [
                "correction_id",
                "source_id",
                "path",
                "field",
                "frozen_value",
                "corrected_value",
                "results_observed",
                "interpretation_affected",
                "reason",
            ]
            if correction_reader.fieldnames != expected_correction_fields:
                raise AuditFailure(
                    "SOURCE_LOCK_CORRECTIONS.tsv has an unexpected schema"
                )
            corrections = list(correction_reader)
        identifiers = [row["correction_id"] for row in corrections]
        if len(identifiers) != len(set(identifiers)):
            raise AuditFailure("duplicate source-lock correction identifier")
        for correction in corrections:
            if (
                not all(correction.values())
                or correction["results_observed"] != "NO"
                or correction["interpretation_affected"] != "NO"
            ):
                raise AuditFailure("invalid source-lock correction record")
            matched = [
                row
                for row in rows
                if row["source_id"] == correction["source_id"]
                and row["path"] == correction["path"]
            ]
            if len(matched) != 1:
                raise AuditFailure("source-lock correction target is not unique")
            target = matched[0]
            field = correction["field"]
            if field not in target:
                raise AuditFailure("source-lock correction field is unknown")
            if target[field] != correction["frozen_value"]:
                raise AuditFailure("source-lock correction frozen value mismatch")
            target[field] = correction["corrected_value"]
    return rows


def verify_sources(
    project: pathlib.Path,
    source_roots: dict[str, pathlib.Path],
) -> dict[str, Any]:
    rows = read_source_lock(project / "provenance" / "SOURCE_LOCK.tsv")
    failures: list[str] = []
    repositories: dict[str, Any] = {}
    for source_id in sorted({row["source_id"] for row in rows}):
        source_rows = [row for row in rows if row["source_id"] == source_id]
        root = source_roots[source_id].resolve()
        expected_commit = source_rows[0]["commit"]
        expected_repository = source_rows[0]["repository"]
        if any(row["commit"] != expected_commit for row in source_rows):
            failures.append(f"inconsistent_commit:{source_id}")
        if any(row["repository"] != expected_repository for row in source_rows):
            failures.append(f"inconsistent_repository:{source_id}")
        try:
            head = run_git(root, "rev-parse", "HEAD")
        except (OSError, subprocess.CalledProcessError):
            head = "UNAVAILABLE"
        if head != expected_commit:
            failures.append(f"commit:{source_id}:{head}")
        file_records: list[dict[str, Any]] = []
        for row in source_rows:
            candidate = root / row["path"]
            exists = candidate.is_file()
            size = candidate.stat().st_size if exists else None
            digest = sha256_file(candidate) if exists else None
            try:
                blob = (
                    run_git(root, "hash-object", row["path"])
                    if exists
                    else None
                )
            except (OSError, subprocess.CalledProcessError):
                blob = None
            status = (
                "PASS"
                if exists
                and size == int(row["bytes"])
                and digest == row["sha256"]
                and blob == row["git_blob_sha1"]
                else "FAIL"
            )
            if status == "FAIL":
                failures.append(f"file:{source_id}:{row['path']}")
            file_records.append(
                {
                    "path": row["path"],
                    "expected_bytes": int(row["bytes"]),
                    "actual_bytes": size,
                    "expected_sha256": row["sha256"],
                    "actual_sha256": digest,
                    "expected_git_blob_sha1": row["git_blob_sha1"],
                    "actual_git_blob_sha1": blob,
                    "status": status,
                }
            )
        repositories[source_id] = {
            "repository": expected_repository,
            "expected_commit": expected_commit,
            "actual_commit": head,
            "locked_file_count": len(source_rows),
            "files": file_records,
            "working_tree_status": (
                run_git(root, "status", "--short")
                if head != "UNAVAILABLE"
                else "UNAVAILABLE"
            ),
            "status": (
                "PASS"
                if head == expected_commit
                and all(row["status"] == "PASS" for row in file_records)
                else "FAIL"
            ),
        }
    return {
        "repositories": repositories,
        "failure_count": len(failures),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def parse_h0dn_table(path: pathlib.Path) -> list[dict[str, Any]]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines or not lines[0].startswith("#"):
        raise AuditFailure("H0DN table header is missing")
    header = lines[0].lstrip("#").split()
    required = {"name", "m_b", "err_m_b", "zhel", "zcmb"}
    if not required.issubset(header):
        raise AuditFailure("H0DN table lacks required columns")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines[1:]):
        values = line.split()
        if len(values) != len(header):
            raise AuditFailure(f"H0DN row {index + 1} has wrong field count")
        raw = dict(zip(header, values))
        try:
            row = {
                **raw,
                "h0dn_row_0based": index,
                "h0dn_row_1based": index + 1,
                "m_b": float(raw["m_b"]),
                "err_m_b": float(raw["err_m_b"]),
                "zhel": float(raw["zhel"]),
                "zcmb": float(raw["zcmb"]),
            }
        except ValueError as exc:
            raise AuditFailure(f"non-numeric H0DN row {index + 1}") from exc
        if not all(
            np.isfinite(row[field])
            for field in ("m_b", "err_m_b", "zhel", "zcmb")
        ):
            raise AuditFailure(f"non-finite H0DN row {index + 1}")
        rows.append(row)
    return rows


def parse_official_table(path: pathlib.Path) -> list[dict[str, Any]]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        raise AuditFailure("official catalog is empty")
    header = lines[0].split()
    required = {
        "CID",
        "IDSURVEY",
        "zCMB",
        "zHEL",
        "m_b_corr",
        "m_b_corr_err_DIAG",
        "USED_IN_SH0ES_HF",
    }
    if not required.issubset(header):
        raise AuditFailure("official catalog lacks required columns")
    rows: list[dict[str, Any]] = []
    numeric = (
        "IDSURVEY",
        "zCMB",
        "zHEL",
        "m_b_corr",
        "m_b_corr_err_DIAG",
        "USED_IN_SH0ES_HF",
    )
    for index, line in enumerate(lines[1:]):
        values = line.split()
        if len(values) != len(header):
            raise AuditFailure(
                f"official catalog row {index + 1} has wrong field count"
            )
        raw = dict(zip(header, values))
        try:
            parsed: dict[str, Any] = {
                **raw,
                "official_row_0based": index,
                "official_row_1based": index + 1,
            }
            for field in numeric:
                parsed[field] = float(raw[field])
            parsed["IDSURVEY"] = int(parsed["IDSURVEY"])
        except ValueError as exc:
            raise AuditFailure(
                f"non-numeric official catalog row {index + 1}"
            ) from exc
        if not all(np.isfinite(parsed[field]) for field in numeric):
            raise AuditFailure(f"non-finite official row {index + 1}")
        rows.append(parsed)
    return rows


def parse_covariance(
    path: pathlib.Path,
    expected_dimension: int,
    *,
    require_exact_symmetry: bool = True,
) -> np.ndarray:
    values = np.fromstring(path.read_text(encoding="utf-8"), sep=" ")
    if values.size < 1:
        raise AuditFailure(f"empty covariance: {path}")
    dimension_float = values[0]
    dimension = int(dimension_float)
    if float(dimension) != dimension_float:
        raise AuditFailure(f"non-integer covariance dimension: {path}")
    if dimension != expected_dimension:
        raise AuditFailure(
            f"covariance dimension {dimension}; expected {expected_dimension}"
        )
    payload = values[1:]
    if payload.size != dimension * dimension:
        raise AuditFailure(
            f"covariance has {payload.size} values; "
            f"expected {dimension * dimension}"
        )
    matrix = payload.reshape((dimension, dimension))
    if not np.isfinite(matrix).all():
        raise AuditFailure(f"covariance contains non-finite values: {path}")
    if require_exact_symmetry and not np.array_equal(matrix, matrix.T):
        raise AuditFailure(f"covariance is not exactly symmetric: {path}")
    return matrix


def covariance_symmetry_diagnostics(matrix: np.ndarray) -> dict[str, Any]:
    differences = np.abs(matrix - matrix.T)
    mismatch_count = int(np.count_nonzero(differences))
    return {
        "dimension": int(matrix.shape[0]),
        "exactly_symmetric": mismatch_count == 0,
        "asymmetric_element_count": mismatch_count,
        "maximum_absolute_transpose_difference": float(
            np.max(differences)
        ),
    }


def attach_covariance_diagonal_fingerprints(
    official_rows: list[dict[str, Any]],
    official_covariance: np.ndarray,
) -> list[dict[str, Any]]:
    """Attach the printed STAT+SYS diagonal and its square root by row."""
    expected_shape = (len(official_rows), len(official_rows))
    if official_covariance.shape != expected_shape:
        raise AuditFailure(
            "official covariance and catalog dimensions do not align"
        )
    diagonal = np.diag(official_covariance)
    if not np.isfinite(diagonal).all():
        raise AuditFailure("non-finite official covariance diagonal")
    if np.any(diagonal < 0):
        raise AuditFailure("negative official covariance diagonal")
    for row in official_rows:
        index = row["official_row_0based"]
        value = float(diagonal[index])
        row["stat_sys_covariance_diagonal"] = value
        row["stat_sys_covariance_diagonal_sqrt"] = float(np.sqrt(value))
    return official_rows


def catalog_candidate_deltas(
    h0dn_row: dict[str, Any],
    official_row: dict[str, Any],
) -> dict[str, float]:
    """Return only the catalog fields permitted in matching stage one."""
    return {
        "delta_m_b": abs(h0dn_row["m_b"] - official_row["m_b_corr"]),
        "delta_zhel": abs(h0dn_row["zhel"] - official_row["zHEL"]),
        "delta_zcmb": abs(h0dn_row["zcmb"] - official_row["zCMB"]),
    }


def find_catalog_only_candidates(
    h0dn_rows: list[dict[str, Any]],
    official_rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Apply exact CID plus m_b/z tolerances without any error input."""
    active = config["active_matching"]
    stage = active["catalog_only_stage"]
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    filter_value = stage["candidate_filter_numeric_value"]
    for row in official_rows:
        if row["USED_IN_SH0ES_HF"] == filter_value:
            by_name[row["CID"]].append(row)
    for rows in by_name.values():
        rows.sort(
            key=lambda row: (
                row["official_row_0based"],
                row["CID"],
                row["IDSURVEY"],
            )
        )
    tolerances = stage["maximum_absolute_differences"]
    candidate_sets: list[dict[str, Any]] = []
    for hrow in h0dn_rows:
        matches: list[dict[str, Any]] = []
        for orow in by_name.get(hrow["name"], []):
            deltas = catalog_candidate_deltas(hrow, orow)
            if (
                deltas["delta_m_b"]
                <= tolerances["m_b__m_b_corr"]
                and deltas["delta_zhel"]
                <= tolerances["zhel__zHEL"]
                and deltas["delta_zcmb"]
                <= tolerances["zcmb__zCMB"]
            ):
                enriched = {**orow, **deltas}
                matches.append(enriched)
        if len(matches) == 1:
            classification = "CATALOG_ONLY_UNIQUE"
        elif matches:
            classification = "CATALOG_ONLY_AMBIGUOUS"
        else:
            classification = "CATALOG_ONLY_UNMATCHED"
        candidate_sets.append(
            {
                "h0dn": hrow,
                "catalog_candidates": matches,
                "catalog_only_classification": classification,
            }
        )
    return candidate_sets


def resolve_catalog_candidates_with_covariance(
    catalog_candidate_sets: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Use the covariance diagonal only for catalog-only ambiguities."""
    tolerance = config["active_matching"]["covariance_assisted_stage"][
        "maximum_absolute_difference"
    ]
    resolved: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for item in catalog_candidate_sets:
        hrow = item["h0dn"]
        catalog_candidates = item["catalog_candidates"]
        catalog_class = item["catalog_only_classification"]
        covariance_used = catalog_class == "CATALOG_ONLY_AMBIGUOUS"
        candidates_with_diagnostic: list[dict[str, Any]] = []
        assisted_candidates: list[dict[str, Any]] = []
        for candidate in catalog_candidates:
            error_delta = abs(
                hrow["err_m_b"]
                - candidate["stat_sys_covariance_diagonal_sqrt"]
            )
            assist_pass = error_delta <= tolerance
            enriched = {
                **candidate,
                "delta_err_m_b": error_delta,
                "covariance_assist_pass": assist_pass,
            }
            candidates_with_diagnostic.append(enriched)
            if covariance_used and assist_pass:
                assisted_candidates.append(enriched)
        if catalog_class == "CATALOG_ONLY_UNIQUE":
            final_candidates = candidates_with_diagnostic
            final_class = "CATALOG_ONLY_UNIQUE"
        elif catalog_class == "CATALOG_ONLY_AMBIGUOUS":
            final_candidates = assisted_candidates
            if len(assisted_candidates) == 1:
                final_class = "COVARIANCE_DIAGONAL_REQUIRED"
            elif assisted_candidates:
                final_class = "AMBIGUOUS_AFTER_ALL_RULES"
            else:
                final_class = "UNMATCHED_AFTER_ALL_RULES"
        else:
            final_candidates = []
            final_class = "UNMATCHED_AFTER_ALL_RULES"
        final_indices = {
            row["official_row_0based"] for row in final_candidates
        }
        resolved_item = {
            **item,
            "catalog_candidates": candidates_with_diagnostic,
            "covariance_assisted_candidates": assisted_candidates,
            "covariance_diagonal_used": covariance_used,
            "candidates": final_candidates,
            "final_dependency_classification": final_class,
        }
        resolved.append(resolved_item)
        for candidate in candidates_with_diagnostic:
            evidence.append(
                {
                    "h0dn_row_1based": hrow["h0dn_row_1based"],
                    "name": hrow["name"],
                    "official_row_1based": candidate[
                        "official_row_1based"
                    ],
                    "official_CID": candidate["CID"],
                    "IDSURVEY": candidate["IDSURVEY"],
                    "catalog_only_classification": catalog_class,
                    "delta_m_b": format(candidate["delta_m_b"], ".17g"),
                    "delta_zhel": format(candidate["delta_zhel"], ".17g"),
                    "delta_zcmb": format(candidate["delta_zcmb"], ".17g"),
                    "covariance_diagonal_used_for_mapping": (
                        "YES" if covariance_used else "NO"
                    ),
                    "delta_err_m_b": (
                        format(candidate["delta_err_m_b"], ".17g")
                    ),
                    "covariance_assist_pass": (
                        "YES"
                        if covariance_used
                        and candidate["covariance_assist_pass"]
                        else "NO"
                        if covariance_used
                        else ""
                    ),
                    "final_candidate": (
                        "YES"
                        if candidate["official_row_0based"] in final_indices
                        else "NO"
                    ),
                    "final_dependency_classification": final_class,
                }
            )
    return resolved, evidence


def build_mapping_dependency_rows(
    candidate_sets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in candidate_sets:
        catalog_candidates = item["catalog_candidates"]
        assisted = item["covariance_assisted_candidates"]
        final_candidates = item["candidates"]
        details = []
        for candidate in catalog_candidates:
            details.append(
                {
                    "CID": candidate["CID"],
                    "IDSURVEY": candidate["IDSURVEY"],
                    "covariance_assist_pass": (
                        candidate["covariance_assist_pass"]
                        if item["covariance_diagonal_used"]
                        else None
                    ),
                    "delta_err_m_b": (
                        candidate["delta_err_m_b"]
                    ),
                    "delta_m_b": candidate["delta_m_b"],
                    "delta_zcmb": candidate["delta_zcmb"],
                    "delta_zhel": candidate["delta_zhel"],
                    "official_row_1based": candidate[
                        "official_row_1based"
                    ],
                }
            )
        final = final_candidates[0] if len(final_candidates) == 1 else None
        rows.append(
            {
                "h0dn_row_1based": item["h0dn"]["h0dn_row_1based"],
                "name": item["h0dn"]["name"],
                "catalog_only_classification": item[
                    "catalog_only_classification"
                ],
                "catalog_candidate_count": len(catalog_candidates),
                "catalog_candidate_official_rows_1based": ";".join(
                    str(row["official_row_1based"])
                    for row in catalog_candidates
                ),
                "catalog_candidate_details_json": json.dumps(
                    details,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "covariance_diagonal_used": (
                    "YES" if item["covariance_diagonal_used"] else "NO"
                ),
                "covariance_assisted_candidate_count": (
                    len(assisted)
                    if item["covariance_diagonal_used"]
                    else ""
                ),
                "covariance_assisted_candidate_official_rows_1based": (
                    ";".join(
                        str(row["official_row_1based"]) for row in assisted
                    )
                    if item["covariance_diagonal_used"]
                    else ""
                ),
                "final_dependency_classification": item[
                    "final_dependency_classification"
                ],
                "final_candidate_count": len(final_candidates),
                "final_official_row_1based": (
                    final["official_row_1based"] if final else ""
                ),
                "final_IDSURVEY": final["IDSURVEY"] if final else "",
            }
        )
    return rows


def build_error_field_discrepancy(
    candidate_sets: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostic = config["active_matching"][
        "error_field_discrepancy_diagnostic"
    ]
    catalog_tolerance = diagnostic[
        "catalog_vs_matrix_maximum_absolute_difference"
    ]
    h0dn_tolerance = diagnostic[
        "h0dn_vs_matrix_maximum_absolute_difference"
    ]
    rows: list[dict[str, Any]] = []
    for item in candidate_sets:
        if len(item["candidates"]) != 1:
            raise AuditFailure(
                "error-field discrepancy diagnostic requires unique mapping"
            )
        hrow = item["h0dn"]
        match = item["candidates"][0]
        catalog_value = match["m_b_corr_err_DIAG"]
        matrix_value = match["stat_sys_covariance_diagonal_sqrt"]
        diagonal = match["stat_sys_covariance_diagonal"]
        values = (hrow["err_m_b"], catalog_value, matrix_value, diagonal)
        if not all(np.isfinite(value) for value in values) or diagonal < 0:
            raise AuditFailure("invalid error-field diagnostic input")
        catalog_difference = abs(catalog_value - matrix_value)
        h0dn_difference = abs(hrow["err_m_b"] - matrix_value)
        rows.append(
            {
                "h0dn_row_1based": hrow["h0dn_row_1based"],
                "name": hrow["name"],
                "official_row_1based": match["official_row_1based"],
                "official_CID": match["CID"],
                "IDSURVEY": match["IDSURVEY"],
                "h0dn_err_m_b": format(hrow["err_m_b"], ".17g"),
                "official_m_b_corr_err_DIAG": format(
                    catalog_value, ".17g"
                ),
                "official_STAT_SYS_diagonal": format(diagonal, ".17g"),
                "official_STAT_SYS_diagonal_sqrt": format(
                    matrix_value, ".17g"
                ),
                "catalog_vs_matrix_absolute_difference": format(
                    catalog_difference, ".17g"
                ),
                "catalog_vs_matrix_within_tolerance": (
                    "YES"
                    if catalog_difference <= catalog_tolerance
                    else "NO"
                ),
                "h0dn_vs_matrix_absolute_difference": format(
                    h0dn_difference, ".17g"
                ),
                "h0dn_vs_matrix_within_tolerance": (
                    "YES" if h0dn_difference <= h0dn_tolerance else "NO"
                ),
            }
        )
    catalog_differences = [
        float(row["catalog_vs_matrix_absolute_difference"]) for row in rows
    ]
    h0dn_differences = [
        float(row["h0dn_vs_matrix_absolute_difference"]) for row in rows
    ]
    catalog_within = sum(
        row["catalog_vs_matrix_within_tolerance"] == "YES" for row in rows
    )
    h0dn_within = sum(
        row["h0dn_vs_matrix_within_tolerance"] == "YES" for row in rows
    )
    summary = {
        "row_count": len(rows),
        "catalog_field": diagnostic["catalog_field"],
        "matrix_reference": diagnostic["matrix_reference"],
        "h0dn_field": diagnostic["h0dn_field"],
        "fixed_readme_description": diagnostic[
            "fixed_readme_description"
        ],
        "cause_classification": diagnostic["cause_classification"],
        "catalog_vs_matrix_maximum_absolute_difference_tolerance": (
            catalog_tolerance
        ),
        "catalog_vs_matrix_exact_equal_count": sum(
            value == 0.0 for value in catalog_differences
        ),
        "catalog_vs_matrix_within_tolerance_count": catalog_within,
        "catalog_vs_matrix_outside_tolerance_count": (
            len(rows) - catalog_within
        ),
        "catalog_vs_matrix_max_abs_difference": (
            max(catalog_differences, default=None)
        ),
        "h0dn_vs_matrix_maximum_absolute_difference_tolerance": (
            h0dn_tolerance
        ),
        "h0dn_vs_matrix_exact_equal_count": sum(
            value == 0.0 for value in h0dn_differences
        ),
        "h0dn_vs_matrix_within_h0dn_print_tolerance_count": h0dn_within,
        "h0dn_vs_matrix_outside_tolerance_count": len(rows) - h0dn_within,
        "h0dn_vs_matrix_max_abs_difference": max(
            h0dn_differences, default=None
        ),
        "status": (
            "PASS_DIAGNOSTIC_RECORDED"
            if rows and h0dn_within == len(rows)
            else "FAIL"
        ),
    }
    return rows, summary


def build_mapping_rows(
    candidate_sets: list[dict[str, Any]],
    survey_labels: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    uniquely_assigned = [
        item["candidates"][0]["official_row_0based"]
        for item in candidate_sets
        if len(item["candidates"]) == 1
    ]
    assignment_counts = Counter(uniquely_assigned)
    reused = {index for index, count in assignment_counts.items() if count > 1}
    rows: list[dict[str, Any]] = []
    for item in candidate_sets:
        hrow = item["h0dn"]
        candidates = item["candidates"]
        if not candidates:
            match_status = "NO_MATCH"
            match = None
        elif len(candidates) > 1:
            match_status = "AMBIGUOUS_MATCH"
            match = None
        elif candidates[0]["official_row_0based"] in reused:
            match_status = "REUSED_OFFICIAL_ROW"
            match = candidates[0]
        else:
            match_status = "UNIQUE_MATCH"
            match = candidates[0]
        rows.append(
            {
                "h0dn_row_1based": hrow["h0dn_row_1based"],
                "name": hrow["name"],
                "h0dn_m_b": format(hrow["m_b"], ".17g"),
                "h0dn_err_m_b": format(hrow["err_m_b"], ".17g"),
                "h0dn_zhel": format(hrow["zhel"], ".17g"),
                "h0dn_zcmb": format(hrow["zcmb"], ".17g"),
                "catalog_only_classification": item[
                    "catalog_only_classification"
                ],
                "catalog_candidate_count": len(
                    item["catalog_candidates"]
                ),
                "catalog_candidate_official_rows_1based": ";".join(
                    str(row["official_row_1based"])
                    for row in item["catalog_candidates"]
                ),
                "covariance_diagonal_used_for_mapping": (
                    "YES" if item["covariance_diagonal_used"] else "NO"
                ),
                "final_dependency_classification": item[
                    "final_dependency_classification"
                ],
                "candidate_count": len(candidates),
                "candidate_official_rows_1based": ";".join(
                    str(row["official_row_1based"]) for row in candidates
                ),
                "match_status": match_status,
                "official_row_1based": (
                    match["official_row_1based"] if match else ""
                ),
                "official_CID": match["CID"] if match else "",
                "IDSURVEY": match["IDSURVEY"] if match else "",
                "survey_label": (
                    survey_labels.get(str(match["IDSURVEY"]), "UNRESOLVED")
                    if match
                    else ""
                ),
                "official_m_b_corr": (
                    format(match["m_b_corr"], ".17g") if match else ""
                ),
                "official_m_b_corr_err_DIAG": (
                    format(match["m_b_corr_err_DIAG"], ".17g")
                    if match
                    else ""
                ),
                "official_STAT_SYS_diagonal_sqrt": (
                    format(
                        match["stat_sys_covariance_diagonal_sqrt"], ".17g"
                    )
                    if match
                    else ""
                ),
                "official_zHEL": (
                    format(match["zHEL"], ".17g") if match else ""
                ),
                "official_zCMB": (
                    format(match["zCMB"], ".17g") if match else ""
                ),
                "delta_m_b": (
                    format(match["delta_m_b"], ".17g") if match else ""
                ),
                "delta_err_m_b": (
                    format(match["delta_err_m_b"], ".17g") if match else ""
                ),
                "delta_err_m_b_role": (
                    (
                        "AMBIGUITY_RESOLUTION_INPUT"
                        if item["covariance_diagonal_used"]
                        else "POST_MAPPING_DIAGNOSTIC"
                    )
                    if match
                    else ""
                ),
                "delta_zhel": (
                    format(match["delta_zhel"], ".17g") if match else ""
                ),
                "delta_zcmb": (
                    format(match["delta_zcmb"], ".17g") if match else ""
                ),
            }
        )
    counts = Counter(row["match_status"] for row in rows)
    return rows, {
        "unique_match_count": counts["UNIQUE_MATCH"],
        "no_match_count": counts["NO_MATCH"],
        "ambiguous_match_count": counts["AMBIGUOUS_MATCH"],
        "reused_official_row_count": len(reused),
        "rows_assigned_to_reused_official_rows": counts[
            "REUSED_OFFICIAL_ROW"
        ],
    }


def classify_multirow_groups(
    h0dn_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for row in h0dn_rows:
        groups[row["name"]].append(row["h0dn_row_0based"])
    summaries: list[dict[str, Any]] = []
    for name, indices in groups.items():
        if len(indices) <= 1:
            continue
        selected = [mapping_rows[index] for index in indices]
        fully_mapped = all(
            row["match_status"] == "UNIQUE_MATCH" for row in selected
        )
        codes = [int(row["IDSURVEY"]) for row in selected] if fully_mapped else []
        if not fully_mapped:
            classification = "UNCLASSIFIED_MAPPING_HOLD"
        else:
            counts = Counter(codes)
            if len(counts) == 1:
                classification = "SAME_SURVEY_REPEATED"
            elif all(count == 1 for count in counts.values()):
                classification = "MULTI_SURVEY_ONLY"
            else:
                classification = "MIXED_SURVEY_MULTIPLICITY"
        summaries.append(
            {
                "name": name,
                "h0dn_row_count": len(indices),
                "h0dn_rows_1based": ";".join(str(index + 1) for index in indices),
                "official_rows_1based": ";".join(
                    str(row["official_row_1based"])
                    for row in selected
                    if row["official_row_1based"] != ""
                ),
                "IDSURVEY_codes": ";".join(str(code) for code in codes),
                "survey_labels": ";".join(
                    str(row["survey_label"]) for row in selected
                ),
                "distinct_survey_count": len(set(codes)),
                "survey_multiplicity_class": classification,
            }
        )
    class_counts = Counter(
        row["survey_multiplicity_class"] for row in summaries
    )
    return summaries, dict(sorted(class_counts.items()))


def compare_covariance_lineage(
    official_covariance: np.ndarray,
    h0dn_covariance: np.ndarray,
    mapping_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not all(row["match_status"] == "UNIQUE_MATCH" for row in mapping_rows):
        return {
            "comparison_performed": False,
            "reason": "mapping_not_complete_and_unique",
            "status": "NOT_RUN_MAPPING_HOLD",
        }
    indices = np.array(
        [int(row["official_row_1based"]) - 1 for row in mapping_rows],
        dtype=np.int64,
    )
    submatrix = official_covariance[np.ix_(indices, indices)]
    equality = submatrix == h0dn_covariance
    mismatch_locations = np.argwhere(~equality)
    differences = np.abs(submatrix - h0dn_covariance)
    mismatch_count = int(mismatch_locations.shape[0])
    first_mismatch: dict[str, Any] | None = None
    if mismatch_count:
        row_index, column_index = (
            int(mismatch_locations[0, 0]),
            int(mismatch_locations[0, 1]),
        )
        first_mismatch = {
            "h0dn_row_1based": row_index + 1,
            "h0dn_column_1based": column_index + 1,
            "official_row_1based": int(indices[row_index]) + 1,
            "official_column_1based": int(indices[column_index]) + 1,
            "h0dn_value": float(h0dn_covariance[row_index, column_index]),
            "official_value": float(submatrix[row_index, column_index]),
            "absolute_difference": float(differences[row_index, column_index]),
        }
    return {
        "comparison_performed": True,
        "comparison_rule": "elementwise_float64_exact",
        "dependency_disclosure": (
            "JOINT_CATALOG_AND_COVARIANCE_LINEAGE_WHERE_DIAGONAL_"
            "AMBIGUITY_RESOLUTION_WAS_REQUIRED"
        ),
        "evidentiary_limit": (
            "Exact equality is numerical evidence against loss, "
            "transcription, additional rounding, or ordering mismatch in "
            "the mapped submatrix; it does not by itself establish how the "
            "H0DN covariance was constructed."
        ),
        "h0dn_dimension": int(h0dn_covariance.shape[0]),
        "official_dimension": int(official_covariance.shape[0]),
        "compared_element_count": int(equality.size),
        "exact_equal_element_count": int(np.count_nonzero(equality)),
        "mismatch_count": mismatch_count,
        "maximum_absolute_difference": float(np.max(differences)),
        "first_mismatch": first_mismatch,
        "official_index_sequence_sha256": hashlib.sha256(
            indices.astype("<i8", copy=False).tobytes()
        ).hexdigest(),
        "status": "PASS" if mismatch_count == 0 else "FAIL",
    }


MAPPING_FIELDS = [
    "h0dn_row_1based",
    "name",
    "h0dn_m_b",
    "h0dn_err_m_b",
    "h0dn_zhel",
    "h0dn_zcmb",
    "catalog_only_classification",
    "catalog_candidate_count",
    "catalog_candidate_official_rows_1based",
    "covariance_diagonal_used_for_mapping",
    "final_dependency_classification",
    "candidate_count",
    "candidate_official_rows_1based",
    "match_status",
    "official_row_1based",
    "official_CID",
    "IDSURVEY",
    "survey_label",
    "official_m_b_corr",
    "official_m_b_corr_err_DIAG",
    "official_STAT_SYS_diagonal_sqrt",
    "official_zHEL",
    "official_zCMB",
    "delta_m_b",
    "delta_err_m_b",
    "delta_err_m_b_role",
    "delta_zhel",
    "delta_zcmb",
]

CANDIDATE_FIELDS = [
    "h0dn_row_1based",
    "name",
    "official_row_1based",
    "official_CID",
    "IDSURVEY",
    "catalog_only_classification",
    "delta_m_b",
    "delta_zhel",
    "delta_zcmb",
    "covariance_diagonal_used_for_mapping",
    "delta_err_m_b",
    "covariance_assist_pass",
    "final_candidate",
    "final_dependency_classification",
]

DEPENDENCY_FIELDS = [
    "h0dn_row_1based",
    "name",
    "catalog_only_classification",
    "catalog_candidate_count",
    "catalog_candidate_official_rows_1based",
    "catalog_candidate_details_json",
    "covariance_diagonal_used",
    "covariance_assisted_candidate_count",
    "covariance_assisted_candidate_official_rows_1based",
    "final_dependency_classification",
    "final_candidate_count",
    "final_official_row_1based",
    "final_IDSURVEY",
]

ERROR_DISCREPANCY_FIELDS = [
    "h0dn_row_1based",
    "name",
    "official_row_1based",
    "official_CID",
    "IDSURVEY",
    "h0dn_err_m_b",
    "official_m_b_corr_err_DIAG",
    "official_STAT_SYS_diagonal",
    "official_STAT_SYS_diagonal_sqrt",
    "catalog_vs_matrix_absolute_difference",
    "catalog_vs_matrix_within_tolerance",
    "h0dn_vs_matrix_absolute_difference",
    "h0dn_vs_matrix_within_tolerance",
]

GROUP_FIELDS = [
    "name",
    "h0dn_row_count",
    "h0dn_rows_1based",
    "official_rows_1based",
    "IDSURVEY_codes",
    "survey_labels",
    "distinct_survey_count",
    "survey_multiplicity_class",
]
