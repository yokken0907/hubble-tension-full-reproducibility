#!/usr/bin/env python3
"""Core routines for the frozen H0DN SN Ia Phase 1C audit."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import platform
import subprocess
import sys
import zipfile
from collections import Counter
from typing import Any, Iterable, Sequence

import numpy as np
import scipy
import scipy.linalg
import scipy.special
import scipy.stats
from scipy.constants import c as C_METRES_PER_SECOND


CONTRACT_ID = "H0DN-SNIA-CONTRAST-COVARIANCE-PHASE1C-20260730-02"
CONTRACT_FREEZE_SHA256 = (
    "d42ef07bac015432784cd89c81b2a271ea56408b7d6678b8df8df02a84b769ec"
)
POSTHOC_CONTRACT_ID = (
    "H0DN-SNIA-PHASE1C-POSTHOC-PRECISION-ASYMMETRY-20260730-01"
)
POSTHOC_CONTRACT_SHA256 = (
    "050272af008385d0f4d5e247d1a81a432411115f972bc6a52562a580d8f3d5b4"
)
SUCCESS_STATUS = (
    "AUDIT_COMPLETE_CONTRAST_COVARIANCE_CALIBRATION_DIAGNOSTIC"
)
BOUNDARY_MARKER = (
    "CALIBRATION_DIAGNOSTIC_ONLY_NO_COVARIANCE_RESCALE_"
    "NO_CORRECTED_H0_NO_TENSION_RESOLUTION"
)
BASELINE_ORDER = (
    "PHASE1A_FULL",
    "STAT_SYS_NO_ROWWISE_VELOCITY",
    "STAT_ONLY",
)
DIAGNOSTIC_ORDER = (
    "STAT_SYS_DIAGONAL_ONLY",
    "STAT_ONLY_DIAGONAL_ONLY",
)
AMENDMENT_FIELDS = (
    "amendment_id",
    "timestamp_utc",
    "changed_file",
    "reason",
    "new_results_observed",
    "interpretation_affected",
)
SOURCE_FIELDS = (
    "source_id",
    "repository",
    "commit",
    "path",
    "git_blob_sha1",
    "bytes",
    "sha256",
)
MAPPING_FIELDS = (
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "final_dependency_classification",
)


class AuditFailure(RuntimeError):
    """A required frozen audit gate failed."""


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AuditFailure(f"cannot serialize non-finite value: {value}")
        return value
    if isinstance(value, pathlib.Path):
        return str(value)
    return value


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            json_safe(value),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def write_tsv(
    path: pathlib.Path,
    rows: Iterable[dict[str, Any]],
    fieldnames: Sequence[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fieldnames),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: format(row[field], ".17g")
                    if isinstance(row.get(field), float)
                    else row.get(field, "")
                    for field in fieldnames
                }
            )


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def environment_summary() -> dict[str, Any]:
    return {
        "implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "scipy_version": scipy.__version__,
        "byteorder": sys.byteorder,
    }


def load_config(project: pathlib.Path) -> dict[str, Any]:
    config = read_json(project / "provenance" / "DECISION_CONFIG.json")
    if config.get("contract_id") != CONTRACT_ID:
        raise AuditFailure("decision config contract identifier mismatch")
    return config


def verify_contract_freeze(project: pathlib.Path) -> dict[str, Any]:
    freeze_path = project / "provenance" / "CONTRACT_FREEZE.json"
    actual_freeze_hash = sha256_file(freeze_path)
    freeze = read_json(freeze_path)
    checks: list[dict[str, Any]] = [
        {
            "path": "provenance/CONTRACT_FREEZE.json",
            "verification_scope": "whole_file",
            "expected_sha256": CONTRACT_FREEZE_SHA256,
            "actual_sha256": actual_freeze_hash,
            "status": (
                "PASS"
                if actual_freeze_hash == CONTRACT_FREEZE_SHA256
                else "FAIL"
            ),
        }
    ]
    if freeze.get("contract_id") != CONTRACT_ID:
        raise AuditFailure("contract-freeze identifier mismatch")
    for relative, record in sorted(freeze["files"].items()):
        path = project / relative
        if relative in {
            "provenance/CONTRACT_AMENDMENTS.tsv",
            "provenance/SOURCE_LOCK.tsv",
        }:
            frozen_bytes = path.read_bytes()[: int(record["bytes"])]
            actual = hashlib.sha256(frozen_bytes).hexdigest()
            scope = (
                "frozen_prefix_plus_append_only_ledger"
                if relative == "provenance/CONTRACT_AMENDMENTS.tsv"
                else "frozen_prefix_plus_append_only_source_lock"
            )
        elif relative == "provenance/UPSTREAM_AUDIT_DEPENDENCIES.json":
            snapshot = (
                project
                / "provenance"
                / "UPSTREAM_AUDIT_DEPENDENCIES_CONTRACT02_FROZEN.json"
            )
            actual = sha256_file(snapshot) if snapshot.is_file() else None
            scope = "preserved_contract02_snapshot_plus_amended_active_file"
        else:
            actual = sha256_file(path) if path.is_file() else None
            scope = "whole_file"
        checks.append(
            {
                "path": relative,
                "verification_scope": scope,
                "expected_sha256": record["sha256"],
                "actual_sha256": actual,
                "status": "PASS" if actual == record["sha256"] else "FAIL",
            }
        )
    amendment_path = project / "provenance" / "CONTRACT_AMENDMENTS.tsv"
    with amendment_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != AMENDMENT_FIELDS:
            raise AuditFailure("contract-amendment ledger schema mismatch")
        amendments = list(reader)
    identifiers = [row["amendment_id"] for row in amendments]
    required_amendments = {
        "CORR-P1C-001",
        "CORR-P1C-002",
        "CORR-P1C-003",
    }
    amendments_valid = (
        len(identifiers) == len(set(identifiers))
        and all(all(value for value in row.values()) for row in amendments)
        and required_amendments.issubset(identifiers)
        and all(
            row["new_results_observed"] == "YES"
            and row["interpretation_affected"] == "NO"
            for row in amendments
            if row["amendment_id"] in required_amendments
        )
    )
    posthoc_path = (
        project / "POSTHOC_PRECISION_AND_ASYMMETRY_DIAGNOSTIC_CONTRACT.md"
    )
    posthoc_sidecar = posthoc_path.with_suffix(".sha256")
    posthoc_hash = sha256_file(posthoc_path) if posthoc_path.is_file() else None
    expected_sidecar = (
        f"{POSTHOC_CONTRACT_SHA256}  {posthoc_path.name}\n"
    )
    posthoc_valid = (
        posthoc_hash == POSTHOC_CONTRACT_SHA256
        and posthoc_sidecar.is_file()
        and posthoc_sidecar.read_text(encoding="utf-8") == expected_sidecar
        and POSTHOC_CONTRACT_ID
        in posthoc_path.read_text(encoding="utf-8")
    )
    active_dependencies = read_json(
        project / "provenance" / "UPSTREAM_AUDIT_DEPENDENCIES.json"
    )
    phase1a = active_dependencies.get("phase1a", {})
    active_dependency_valid = (
        phase1a.get("archive_name")
        == "h0dn-snia-residual-deficit-localization-audit_v0.1.0.zip"
        and phase1a.get("archive_sha256")
        == "38bb6e55c66ec3442e465cfe4367c1b75e5ecb369933df6de71b75c6182e8333"
        and phase1a.get("archive_sidecar_verified") is True
    )
    chronology = (
        freeze.get("status")
        == "FROZEN_BEFORE_PHASE1C_COMPONENT_EXECUTION"
        and freeze.get(
            "contract_01_preexecution_schema_hold_observed_before_freeze"
        )
        is True
        and freeze.get("known_phase1a_baseline_observed_before_freeze") is True
        and freeze.get("phase1b_mapping_observed_before_freeze") is True
        and freeze.get(
            "stat_sys_without_velocity_result_observed_before_freeze"
        )
        is False
        and freeze.get("statonly_contrast_result_observed_before_freeze")
        is False
        and freeze.get("component_diagnostics_observed_before_freeze") is False
    )
    status = (
        "PASS"
        if chronology
        and amendments_valid
        and posthoc_valid
        and active_dependency_valid
        and all(row["status"] == "PASS" for row in checks)
        else "FAIL"
    )
    return {
        "contract_id": CONTRACT_ID,
        "contract_freeze_sha256": actual_freeze_hash,
        "freeze_timestamp_utc": freeze["freeze_timestamp_utc"],
        "chronology_status": "PASS" if chronology else "FAIL",
        "amendment_ledger_status": "PASS" if amendments_valid else "FAIL",
        "amendment_count": len(amendments),
        "posthoc_contract_id": POSTHOC_CONTRACT_ID,
        "posthoc_contract_sha256": posthoc_hash,
        "posthoc_contract_status": "PASS" if posthoc_valid else "FAIL",
        "active_upstream_dependency_status": (
            "PASS" if active_dependency_valid else "FAIL"
        ),
        "checks": checks,
        "status": status,
    }


def _run_git(root: pathlib.Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _normalize_repository(value: str) -> str:
    value = value.strip().removesuffix("/")
    return value.removesuffix(".git")


def read_source_lock(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != SOURCE_FIELDS:
            raise AuditFailure("SOURCE_LOCK.tsv schema mismatch")
        rows = list(reader)
    if len(rows) != 13:
        raise AuditFailure(f"expected 13 source-lock rows, found {len(rows)}")
    return rows


def git_blob_sha1_file(path: pathlib.Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def verify_locked_file(
    candidate: pathlib.Path, row: dict[str, str]
) -> dict[str, Any]:
    exists = candidate.is_file()
    size = candidate.stat().st_size if exists else None
    digest = sha256_file(candidate) if exists else None
    blob = git_blob_sha1_file(candidate) if exists else None
    passed = (
        exists
        and size == int(row["bytes"])
        and digest == row["sha256"]
        and blob == row["git_blob_sha1"]
    )
    return {
        "path": row["path"],
        "expected_bytes": int(row["bytes"]),
        "actual_bytes": size,
        "expected_sha256": row["sha256"],
        "actual_sha256": digest,
        "expected_git_blob_sha1": row["git_blob_sha1"],
        "actual_git_blob_sha1": blob,
        "status": "PASS" if passed else "FAIL",
    }


def verify_upstream_audit_dependencies(
    project: pathlib.Path,
    archives: dict[str, pathlib.Path],
) -> dict[str, Any]:
    dependency = read_json(
        project / "provenance" / "UPSTREAM_AUDIT_DEPENDENCIES.json"
    )
    records: dict[str, Any] = {}
    failures: list[str] = []
    for identifier in ("phase1a", "phase1b"):
        row = dependency[identifier]
        archive = archives.get(identifier)
        expected_name = row["archive_name"]
        expected_hash = row["archive_sha256"]
        exists = archive is not None and archive.is_file()
        actual_name = archive.name if archive is not None else None
        actual_hash = sha256_file(archive) if exists else None
        sidecar = (
            archive.with_name(archive.name + ".sha256")
            if archive is not None
            else None
        )
        expected_sidecar = (
            f"{expected_hash}  {expected_name}\n"
        )
        sidecar_valid = (
            sidecar is not None
            and sidecar.is_file()
            and sidecar.read_text(encoding="utf-8") == expected_sidecar
        )
        crc_valid = False
        if exists:
            try:
                with zipfile.ZipFile(archive, "r") as handle:
                    crc_valid = handle.testzip() is None
            except zipfile.BadZipFile:
                crc_valid = False
        passed = (
            exists
            and actual_name == expected_name
            and actual_hash == expected_hash
            and sidecar_valid
            and crc_valid
        )
        if not passed:
            failures.append(identifier)
        records[identifier] = {
            "expected_archive_name": expected_name,
            "actual_archive_name": actual_name,
            "expected_archive_sha256": expected_hash,
            "actual_archive_sha256": actual_hash,
            "sidecar_status": "PASS" if sidecar_valid else "FAIL",
            "zip_crc_status": "PASS" if crc_valid else "FAIL",
            "status": "PASS" if passed else "FAIL",
        }
    return {
        "dependencies": records,
        "failure_count": len(failures),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def verify_sources(
    project: pathlib.Path, roots: dict[str, pathlib.Path]
) -> dict[str, Any]:
    lock_rows = read_source_lock(project / "provenance" / "SOURCE_LOCK.tsv")
    repositories: dict[str, Any] = {}
    failures: list[str] = []
    for source_id in ("h0dn", "pantheonplus"):
        selected = [row for row in lock_rows if row["source_id"] == source_id]
        if not selected or source_id not in roots:
            failures.append(f"missing_source:{source_id}")
            continue
        expected_commit = selected[0]["commit"]
        expected_repository = selected[0]["repository"]
        root = roots[source_id]
        try:
            head = _run_git(root, "rev-parse", "HEAD")
            origin = _run_git(root, "remote", "get-url", "origin")
            worktree = _run_git(root, "status", "--short")
        except (OSError, subprocess.CalledProcessError):
            head = "UNAVAILABLE"
            origin = "UNAVAILABLE"
            worktree = "UNAVAILABLE"
        repository_match = _normalize_repository(origin) == _normalize_repository(
            expected_repository
        )
        if head != expected_commit:
            failures.append(f"commit:{source_id}")
        if not repository_match:
            failures.append(f"repository:{source_id}")
        file_records: list[dict[str, Any]] = []
        for row in selected:
            record = verify_locked_file(root / row["path"], row)
            if record["status"] != "PASS":
                failures.append(f"file:{source_id}:{row['path']}")
            file_records.append(record)
        repositories[source_id] = {
            "repository": expected_repository,
            "expected_commit": expected_commit,
            "actual_commit": head,
            "origin_match": repository_match,
            "working_tree_clean": worktree == "",
            "locked_file_count": len(selected),
            "files": file_records,
            "status": (
                "PASS"
                if head == expected_commit
                and repository_match
                and all(item["status"] == "PASS" for item in file_records)
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
        raise AuditFailure("H0DN header missing")
    header = lines[0].lstrip("#").split()
    required = {
        "name",
        "m_b",
        "err_m_b",
        "zhel",
        "zcmb",
        "vp_2mpp",
    }
    if not required.issubset(header):
        raise AuditFailure("H0DN table lacks required columns")
    rows: list[dict[str, Any]] = []
    numeric_fields = [field for field in header if field != "name"]
    for index, line in enumerate(lines[1:]):
        values = line.split()
        if len(values) != len(header):
            raise AuditFailure(f"H0DN row {index + 1} field-count mismatch")
        raw = dict(zip(header, values))
        try:
            row: dict[str, Any] = {
                "h0dn_row_0based": index,
                "h0dn_row_1based": index + 1,
                "name": raw["name"],
            }
            for field in numeric_fields:
                row[field] = float(raw[field])
        except ValueError as exc:
            raise AuditFailure(f"non-numeric H0DN row {index + 1}") from exc
        if not all(np.isfinite(row[field]) for field in numeric_fields):
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
        raise AuditFailure("official table is empty")
    header = lines[0].split()
    required = {"CID", "IDSURVEY", "USED_IN_SH0ES_HF", "m_b_corr"}
    if not required.issubset(header):
        raise AuditFailure("official table lacks required columns")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines[1:]):
        values = line.split()
        if len(values) != len(header):
            raise AuditFailure(
                f"official row {index + 1} field-count mismatch"
            )
        raw = dict(zip(header, values))
        try:
            row = {
                "official_row_0based": index,
                "official_row_1based": index + 1,
                "CID": raw["CID"],
                "IDSURVEY": int(float(raw["IDSURVEY"])),
                "USED_IN_SH0ES_HF": float(raw["USED_IN_SH0ES_HF"]),
                "m_b_corr": float(raw["m_b_corr"]),
            }
        except ValueError as exc:
            raise AuditFailure(f"non-numeric official row {index + 1}") from exc
        if not np.isfinite(row["USED_IN_SH0ES_HF"]) or not np.isfinite(
            row["m_b_corr"]
        ):
            raise AuditFailure(f"non-finite official row {index + 1}")
        rows.append(row)
    return rows


def parse_covariance(
    path: pathlib.Path, expected_dimension: int
) -> tuple[np.ndarray, dict[str, Any]]:
    values = np.fromstring(path.read_text(encoding="utf-8"), sep=" ")
    if values.size < 1 or not float(values[0]).is_integer():
        raise AuditFailure(f"invalid covariance header: {path.name}")
    dimension = int(values[0])
    if dimension != expected_dimension:
        raise AuditFailure(
            f"{path.name} dimension {dimension}; expected {expected_dimension}"
        )
    payload = values[1:]
    if payload.size != dimension * dimension:
        raise AuditFailure(
            f"{path.name} payload {payload.size}; expected {dimension ** 2}"
        )
    matrix = payload.reshape((dimension, dimension))
    if not np.isfinite(matrix).all():
        raise AuditFailure(f"non-finite covariance: {path.name}")
    transpose_difference = np.abs(matrix - matrix.T)
    return matrix, {
        "dimension": dimension,
        "payload_value_count": int(payload.size),
        "exactly_symmetric": bool(np.array_equal(matrix, matrix.T)),
        "asymmetric_element_count": int(np.count_nonzero(transpose_difference)),
        "maximum_absolute_transpose_difference": float(
            np.max(transpose_difference)
        ),
    }


def float64_matrix_sha256(matrix: np.ndarray) -> str:
    canonical = np.asarray(matrix, dtype="<f8", order="C")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def covariance_representations(
    matrix: np.ndarray,
) -> dict[str, np.ndarray]:
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise AuditFailure("covariance representation requires a square matrix")
    if not np.isfinite(matrix).all():
        raise AuditFailure("covariance representation contains non-finite data")
    upper = np.triu(matrix)
    lower = np.tril(matrix)
    return {
        "SYMMETRIC_AVERAGE": 0.5 * (matrix + matrix.T),
        "UPPER_TRIANGLE_MIRRORED": (
            upper + np.triu(matrix, k=1).T
        ),
        "LOWER_TRIANGLE_MIRRORED": (
            lower + np.tril(matrix, k=-1).T
        ),
    }


def selected_submatrix_asymmetry(
    matrix: np.ndarray,
    mapping: list[dict[str, Any]],
) -> dict[str, Any]:
    if matrix.shape != (len(mapping), len(mapping)):
        raise AuditFailure("selected submatrix and mapping dimensions differ")
    if not np.isfinite(matrix).all():
        raise AuditFailure("selected submatrix contains non-finite data")
    difference = np.abs(matrix - matrix.T)
    upper_difference = np.triu(difference, k=1)
    pair_count = int(np.count_nonzero(upper_difference > 0.0))
    maximum = float(np.max(upper_difference))
    location: dict[str, Any] | None = None
    if maximum > 0.0:
        candidates = np.argwhere(upper_difference == maximum)
        first_row, first_column = (int(value) for value in candidates[0])

        def endpoint(index: int) -> dict[str, Any]:
            row = mapping[index]
            return {
                "selected_index_0based": index,
                "selected_index_1based": index + 1,
                "h0dn_row_1based": int(row["h0dn_row_1based"]),
                "official_row_1based": int(row["official_row_1based"]),
                "CID": row["CID"],
                "IDSURVEY": int(row["IDSURVEY"]),
            }

        location = {
            "row_endpoint": endpoint(first_row),
            "column_endpoint": endpoint(first_column),
            "Cij": float(matrix[first_row, first_column]),
            "Cji": float(matrix[first_column, first_row]),
            "absolute_difference": maximum,
        }
    return {
        "shape": list(matrix.shape),
        "comparison_tolerance_absolute": 0.0,
        "offdiagonal_unordered_pair_count": (
            matrix.shape[0] * (matrix.shape[0] - 1) // 2
        ),
        "asymmetric_offdiagonal_pair_count": pair_count,
        "asymmetric_offdiagonal_element_count": pair_count * 2,
        "asymmetric_pair_count_above_tolerance": pair_count,
        "maximum_absolute_offdiagonal_transpose_difference": maximum,
        "maximum_location": location,
        "maximum_location_status": (
            "RECORDED"
            if location is not None
            else "NOT_APPLICABLE_EXACTLY_SYMMETRIC"
        ),
        "exactly_symmetric": pair_count == 0,
    }


def probability_reference_questions(
    marginal_phase1c_probability: float,
) -> dict[str, Any]:
    return {
        "phase1a_conditional_beta_probability": {
            "value": 9.368362232281232e-05,
            "display_value": 9.3683622e-05,
            "reference_distribution": (
                "conditional_beta_given_the_phase1a_partition_setup"
            ),
            "reference_question": (
                "Phase 1A conditional partition probability"
            ),
            "source_artifact": (
                "Phase 1A results/statistical_interpretation.json"
            ),
        },
        "phase1c_marginal_chi2_39_lower_tail_probability": {
            "value": marginal_phase1c_probability,
            "reference_distribution": "marginal_chi_square_df_39",
            "reference_question": (
                "Phase 1C marginal lower-tail probability for the fixed "
                "39-dimensional contrast vector"
            ),
        },
        "relationship": (
            "DISTINCT_REFERENCE_QUESTIONS_NOT_A_NUMERICAL_INCONSISTENCY"
        ),
    }


def load_mapping(
    path: pathlib.Path,
    h0dn_rows: list[dict[str, Any]],
    official_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != MAPPING_FIELDS:
            raise AuditFailure("Phase 1B compact mapping schema mismatch")
        raw_rows = list(reader)
    checks = {
        "row_count_277": len(raw_rows) == 277,
        "h0dn_source_order": True,
        "official_targets_unique": True,
        "identifiers_agree": True,
        "survey_codes_agree": True,
        "official_hubble_flow_flag": True,
        "dependency_classes_expected": True,
    }
    parsed: list[dict[str, Any]] = []
    for expected, raw in enumerate(raw_rows, start=1):
        try:
            h_index = int(raw["h0dn_row_1based"])
            o_index = int(raw["official_row_1based"])
            survey = int(raw["IDSURVEY"])
        except ValueError as exc:
            raise AuditFailure("non-integer compact mapping field") from exc
        if h_index != expected:
            checks["h0dn_source_order"] = False
        if not (1 <= h_index <= len(h0dn_rows)) or not (
            1 <= o_index <= len(official_rows)
        ):
            raise AuditFailure("compact mapping index out of range")
        hrow = h0dn_rows[h_index - 1]
        orow = official_rows[o_index - 1]
        if hrow["name"] != raw["CID"] or orow["CID"] != raw["CID"]:
            checks["identifiers_agree"] = False
        if orow["IDSURVEY"] != survey:
            checks["survey_codes_agree"] = False
        if orow["USED_IN_SH0ES_HF"] != 1.0:
            checks["official_hubble_flow_flag"] = False
        parsed.append(
            {
                "h0dn_row_0based": h_index - 1,
                "h0dn_row_1based": h_index,
                "official_row_0based": o_index - 1,
                "official_row_1based": o_index,
                "CID": raw["CID"],
                "IDSURVEY": survey,
                "final_dependency_classification": raw[
                    "final_dependency_classification"
                ],
            }
        )
    target_indices = [row["official_row_0based"] for row in parsed]
    checks["official_targets_unique"] = len(target_indices) == len(
        set(target_indices)
    )
    class_counts = Counter(
        row["final_dependency_classification"] for row in parsed
    )
    checks["dependency_classes_expected"] = class_counts == {
        "CATALOG_ONLY_UNIQUE": 275,
        "COVARIANCE_DIAGONAL_REQUIRED": 2,
    }
    return parsed, {
        "mapping_sha256": sha256_file(path),
        "row_count": len(parsed),
        "unique_official_target_count": len(set(target_indices)),
        "dependency_class_counts": dict(sorted(class_counts.items())),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def build_group_structure(
    names: Sequence[str], mapping: list[dict[str, Any]]
) -> dict[str, Any]:
    ordered_names: list[str] = []
    indices_by_name: dict[str, list[int]] = {}
    for index, name in enumerate(names):
        if name not in indices_by_name:
            ordered_names.append(name)
            indices_by_name[name] = []
        indices_by_name[name].append(index)
    z = np.zeros((len(names), len(ordered_names)), dtype=float)
    for column, name in enumerate(ordered_names):
        z[indices_by_name[name], column] = 1.0

    groups: list[dict[str, Any]] = []
    contrast_rows: list[np.ndarray] = []
    contrast_definition: list[dict[str, Any]] = []
    contrast_index = 0
    for name in ordered_names:
        indices = indices_by_name[name]
        if len(indices) < 2:
            continue
        surveys = [mapping[index]["IDSURVEY"] for index in indices]
        group = {
            "CID": name,
            "indices": indices,
            "h0dn_rows_1based": [index + 1 for index in indices],
            "official_rows_1based": [
                mapping[index]["official_row_1based"] for index in indices
            ],
            "IDSURVEY": surveys,
            "multiplicity": len(indices),
            "distinct_survey_count": len(set(surveys)),
        }
        groups.append(group)
        n = len(indices)
        for local_index in range(1, n):
            contrast_index += 1
            row = np.zeros(len(names), dtype=float)
            scale = math.sqrt(local_index * (local_index + 1))
            for position in range(local_index):
                row[indices[position]] = 1.0 / scale
            row[indices[local_index]] = -local_index / scale
            contrast_rows.append(row)
            for position in range(local_index + 1):
                source_index = indices[position]
                contrast_definition.append(
                    {
                        "contrast_index_1based": contrast_index,
                        "group_first_h0dn_row_1based": indices[0] + 1,
                        "CID": name,
                        "within_group_contrast_index_1based": local_index,
                        "h0dn_row_1based": source_index + 1,
                        "official_row_1based": mapping[source_index][
                            "official_row_1based"
                        ],
                        "IDSURVEY": mapping[source_index]["IDSURVEY"],
                        "weight": float(row[source_index]),
                    }
                )
    a = np.vstack(contrast_rows)
    multiplicities = Counter(len(value) for value in indices_by_name.values())
    orthogonality_error = float(
        np.max(np.abs(a @ a.T - np.eye(a.shape[0])))
    )
    annihilation_error = float(np.max(np.abs(a @ z)))
    multirow_surveys_cross = all(
        group["distinct_survey_count"] > 1 for group in groups
    )
    return {
        "A": a,
        "Z": z,
        "groups": groups,
        "contrast_definition": contrast_definition,
        "row_count": len(names),
        "unique_exact_name_count": len(ordered_names),
        "multirow_exact_name_group_count": len(groups),
        "rows_in_multirow_groups": sum(item["multiplicity"] for item in groups),
        "contrast_degrees_of_freedom": a.shape[0],
        "contrast_rank": int(np.linalg.matrix_rank(a)),
        "multiplicity_histogram": {
            str(size): count for size, count in sorted(multiplicities.items())
        },
        "all_multirow_groups_cross_survey": multirow_surveys_cross,
        "contrast_orthogonality_max_absolute_error": orthogonality_error,
        "group_annihilation_max_absolute_error": annihilation_error,
    }


def _velocity_to_redshift(
    velocity: np.ndarray, speed_of_light: float
) -> np.ndarray:
    return np.sqrt(
        (1.0 + velocity / speed_of_light)
        / (1.0 - velocity / speed_of_light)
    ) - 1.0


def _redshift_to_velocity(
    redshift: np.ndarray, speed_of_light: float
) -> np.ndarray:
    ratio = 1.0 + redshift
    return speed_of_light * (ratio**2 - 1.0) / (ratio**2 + 1.0)


def _cosmographic_k(
    redshift: np.ndarray, q0: float, j0: float
) -> np.ndarray:
    return (
        1.0
        + 0.5 * (1.0 - q0) * redshift
        - (1.0 / 6.0)
        * (1.0 - q0 - 3.0 * q0**2 + j0)
        * redshift**2
    )


def build_alpha_data(
    rows: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, np.ndarray]:
    model = config["fixed_model"]
    speed_of_light = C_METRES_PER_SECOND / 1000.0
    zhel = np.asarray([row["zhel"] for row in rows], dtype=float)
    zcmb = np.asarray([row["zcmb"] for row in rows], dtype=float)
    mb = np.asarray([row["m_b"] for row in rows], dtype=float)
    vpec = np.asarray([row["vp_2mpp"] for row in rows], dtype=float)
    zpec = _velocity_to_redshift(vpec, speed_of_light)
    zcorrected = (1.0 + zcmb) / (1.0 + zpec) - 1.0
    vcorrected = _redshift_to_velocity(zcorrected, speed_of_light)
    factor = (
        (1.0 + zhel)
        / (1.0 + zcorrected)
        * speed_of_light
        * zcorrected
        * _cosmographic_k(
            zcorrected, float(model["q0"]), float(model["j0"])
        )
    )
    if np.any(factor <= 0) or np.any(vcorrected <= 0):
        raise AuditFailure("non-positive cosmographic factor or velocity")
    model_term = 0.2 * 5.0 * np.log10(factor)
    data_alpha = model_term - 0.2 * mb
    dispersion = float(model["velocity_dispersion_km_s"])
    velocity_variance = (
        np.log10(vcorrected + dispersion) - np.log10(vcorrected)
    ) ** 2
    return {
        "data_alpha": data_alpha,
        "model_term_alpha": model_term,
        "velocity_variance_alpha": velocity_variance,
        "zcorrected": zcorrected,
        "vcorrected": vcorrected,
    }


def matrix_diagnostics(matrix: np.ndarray) -> dict[str, Any]:
    eigenvalues = scipy.linalg.eigvalsh(matrix, check_finite=True)
    sign, logdet = np.linalg.slogdet(matrix)
    try:
        scipy.linalg.cholesky(matrix, lower=True, check_finite=True)
        cholesky = True
    except scipy.linalg.LinAlgError:
        cholesky = False
    return {
        "shape": list(matrix.shape),
        "all_finite": bool(np.isfinite(matrix).all()),
        "symmetry_max_absolute_error": float(
            np.max(np.abs(matrix - matrix.T))
        ),
        "diagonal_minimum": float(np.min(np.diag(matrix))),
        "diagonal_maximum": float(np.max(np.diag(matrix))),
        "eigenvalue_minimum": float(eigenvalues[0]),
        "eigenvalue_maximum": float(eigenvalues[-1]),
        "condition_number": float(eigenvalues[-1] / eigenvalues[0]),
        "trace": float(np.trace(matrix)),
        "log_determinant": float(logdet),
        "log_determinant_sign": float(sign),
        "numerical_rank": int(np.linalg.matrix_rank(matrix)),
        "cholesky_success": cholesky,
    }


def component_diagnostics(matrix: np.ndarray) -> dict[str, Any]:
    eigenvalues = scipy.linalg.eigvalsh(
        0.5 * (matrix + matrix.T), check_finite=True
    )
    return {
        "shape": list(matrix.shape),
        "symmetry_max_absolute_error": float(
            np.max(np.abs(matrix - matrix.T))
        ),
        "eigenvalue_minimum": float(eigenvalues[0]),
        "eigenvalue_maximum": float(eigenvalues[-1]),
        "negative_eigenvalue_count": int(np.count_nonzero(eigenvalues < 0)),
        "trace": float(np.trace(matrix)),
    }


def primary_quadratic_form(
    vector: np.ndarray, covariance: np.ndarray
) -> float:
    lower = scipy.linalg.cholesky(
        covariance, lower=True, check_finite=True
    )
    whitened = scipy.linalg.solve_triangular(
        lower, vector, lower=True, check_finite=True
    )
    return float(whitened @ whitened)


def reference_quadratic_form(
    vector: np.ndarray, covariance: np.ndarray
) -> float:
    eigenvalues, eigenvectors = scipy.linalg.eigh(
        covariance, check_finite=True
    )
    if eigenvalues[0] <= 0:
        raise AuditFailure("reference eigensolver found non-positive covariance")
    coordinates = eigenvectors.T @ vector
    return float(np.sum(coordinates**2 / eigenvalues))


def dispersion_label(
    lower_tail_probability: float, config: dict[str, Any]
) -> str:
    strong = float(config["classification"]["strong_low_tail_alpha"])
    low = float(config["classification"]["low_tail_alpha"])
    if lower_tail_probability < strong:
        return "STRONG_LOW_DISPERSION_RELATIVE_TO_BASELINE"
    if lower_tail_probability < low:
        return "LOW_DISPERSION_RELATIVE_TO_BASELINE"
    return "NO_LOW_DISPERSION_FLAG_RELATIVE_TO_BASELINE"


def ordered_sensitivity_classification(
    flags: Sequence[bool],
) -> str:
    if len(flags) != 3:
        raise AuditFailure("ordered classification requires exactly three flags")
    phase1a, stat_sys, stat_only = flags
    if not phase1a:
        return "NO_PHASE1A_BASELINE_LOW_FLAG"
    if phase1a and not stat_sys and not stat_only:
        return "LOW_FLAG_REMOVED_WITHOUT_ROWWISE_VELOCITY_TERM"
    if phase1a and stat_sys and not stat_only:
        return (
            "LOW_FLAG_PERSISTS_WITHOUT_ROWWISE_VELOCITY_"
            "BUT_NOT_WITH_STATONLY"
        )
    if phase1a and stat_sys and stat_only:
        return "LOW_FLAG_PERSISTS_THROUGH_STATONLY"
    return "NONMONOTONIC_COMPONENT_SENSITIVITY"


def baseline_result(
    name: str,
    vector: np.ndarray,
    covariance: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    degrees = int(config["expected"]["contrast_degrees_of_freedom"])
    q_primary = primary_quadratic_form(vector, covariance)
    q_reference = reference_quadratic_form(vector, covariance)
    probability = float(scipy.stats.chi2.cdf(q_primary, degrees))
    probability_reference = float(
        scipy.special.gammainc(degrees / 2.0, q_primary / 2.0)
    )
    lower_quantile = float(scipy.stats.chi2.ppf(0.025, degrees))
    upper_quantile = float(scipy.stats.chi2.ppf(0.975, degrees))
    return {
        "baseline": name,
        "chi2": q_primary,
        "degrees_of_freedom": degrees,
        "lower_tail_probability": probability,
        "dispersion_label": dispersion_label(probability, config),
        "low_flag_at_alpha_0_01": (
            probability < float(config["classification"]["low_tail_alpha"])
        ),
        "scalar_scale_estimate_q_over_df": q_primary / degrees,
        "scalar_scale_95_percent_interval_lower": q_primary / upper_quantile,
        "scalar_scale_95_percent_interval_upper": q_primary / lower_quantile,
        "reference_eigendecomposition_chi2": q_reference,
        "reference_chi2_absolute_difference": abs(q_primary - q_reference),
        "cdf_gammainc_absolute_difference": abs(
            probability - probability_reference
        ),
        "covariance": matrix_diagnostics(covariance),
    }


def generalized_comparison(
    numerator: np.ndarray, denominator: np.ndarray
) -> dict[str, Any]:
    eigenvalues = scipy.linalg.eigvalsh(
        numerator, denominator, check_finite=True
    )
    numerator_sign, numerator_logdet = np.linalg.slogdet(numerator)
    denominator_sign, denominator_logdet = np.linalg.slogdet(denominator)
    if numerator_sign <= 0 or denominator_sign <= 0:
        raise AuditFailure("non-positive determinant in covariance comparison")
    return {
        "generalized_eigenvalue_minimum": float(eigenvalues[0]),
        "generalized_eigenvalue_median": float(np.median(eigenvalues)),
        "generalized_eigenvalue_maximum": float(eigenvalues[-1]),
        "trace_ratio": float(
            np.trace(numerator) / np.trace(denominator)
        ),
        "log_determinant_ratio": float(
            numerator_logdet - denominator_logdet
        ),
        "geometric_mean_generalized_eigenvalue": float(
            np.exp((numerator_logdet - denominator_logdet) / len(eigenvalues))
        ),
    }


def alternative_basis_checks(
    data: np.ndarray,
    covariance_by_name: dict[str, np.ndarray],
    z: np.ndarray,
    primary_by_name: dict[str, float],
) -> dict[str, Any]:
    null_columns = scipy.linalg.null_space(
        z.T, rcond=None, overwrite_a=False, check_finite=True
    )
    b = null_columns.T
    vector = b @ data
    rows: list[dict[str, Any]] = []
    for name, covariance in covariance_by_name.items():
        projected = b @ covariance @ b.T
        q = reference_quadratic_form(vector, projected)
        rows.append(
            {
                "baseline": name,
                "alternative_basis_chi2": q,
                "primary_chi2": primary_by_name[name],
                "absolute_difference": abs(q - primary_by_name[name]),
            }
        )
    return {
        "basis_shape": list(b.shape),
        "basis_rank": int(np.linalg.matrix_rank(b)),
        "basis_orthogonality_max_absolute_error": float(
            np.max(np.abs(b @ b.T - np.eye(b.shape[0])))
        ),
        "group_annihilation_max_absolute_error": float(
            np.max(np.abs(b @ z))
        ),
        "rows": rows,
    }


def orthogonal_invariance_checks(
    vector: np.ndarray,
    projected_by_name: dict[str, np.ndarray],
    primary_by_name: dict[str, float],
    config: dict[str, Any],
) -> dict[str, Any]:
    generator = np.random.default_rng(int(config["invariance"]["seed"]))
    trials = int(config["invariance"]["orthogonal_trials"])
    rows: list[dict[str, Any]] = []
    for trial in range(trials):
        random_matrix = generator.standard_normal((len(vector), len(vector)))
        q_matrix, r_matrix = np.linalg.qr(random_matrix)
        signs = np.sign(np.diag(r_matrix))
        signs[signs == 0] = 1.0
        orthogonal = q_matrix * signs
        transformed_vector = orthogonal @ vector
        for name, covariance in projected_by_name.items():
            transformed_covariance = orthogonal @ covariance @ orthogonal.T
            q_value = primary_quadratic_form(
                transformed_vector, transformed_covariance
            )
            rows.append(
                {
                    "trial_1based": trial + 1,
                    "baseline": name,
                    "chi2": q_value,
                    "reference_chi2": primary_by_name[name],
                    "absolute_difference": abs(
                        q_value - primary_by_name[name]
                    ),
                }
            )
    return {
        "seed": int(config["invariance"]["seed"]),
        "trial_count": trials,
        "comparison_count": len(rows),
        "maximum_absolute_difference": max(
            row["absolute_difference"] for row in rows
        ),
        "rows": rows,
    }


def assemble_analysis(
    h0dn_rows: list[dict[str, Any]],
    official_rows: list[dict[str, Any]],
    mapping: list[dict[str, Any]],
    h0dn_covariance: np.ndarray,
    official_stat_sys: np.ndarray,
    official_stat_only: np.ndarray,
    group: dict[str, Any],
    alpha: dict[str, np.ndarray],
    config: dict[str, Any],
) -> dict[str, Any]:
    indices = np.asarray(
        [row["official_row_0based"] for row in mapping], dtype=int
    )
    official_stat_sys_mapped_raw = official_stat_sys[np.ix_(indices, indices)]
    exact_equal = official_stat_sys_mapped_raw == h0dn_covariance
    differences = np.abs(official_stat_sys_mapped_raw - h0dn_covariance)
    lineage = {
        "mapped_shape": list(official_stat_sys_mapped_raw.shape),
        "compared_element_count": int(exact_equal.size),
        "exact_equal_element_count": int(np.count_nonzero(exact_equal)),
        "unequal_element_count": int(np.count_nonzero(~exact_equal)),
        "maximum_absolute_difference": float(np.max(differences)),
        "elementwise_float64_exact": bool(np.all(exact_equal)),
        "status": "PASS" if np.all(exact_equal) else "FAIL",
    }

    stat_sys_symmetric = 0.5 * (
        official_stat_sys + official_stat_sys.T
    )
    stat_only_symmetric = 0.5 * (
        official_stat_only + official_stat_only.T
    )
    stat_sys_mapped = stat_sys_symmetric[np.ix_(indices, indices)]
    stat_only_mapped = stat_only_symmetric[np.ix_(indices, indices)]
    a = group["A"]
    vector = a @ alpha["data_alpha"]
    full_row_covariance = (
        h0dn_covariance / 25.0
        + np.diag(alpha["velocity_variance_alpha"])
    )
    stat_sys_row_covariance = stat_sys_mapped / 25.0
    stat_only_row_covariance = stat_only_mapped / 25.0
    stat_sys_diagonal_row_covariance = np.diag(
        np.diag(stat_sys_mapped)
    ) / 25.0
    stat_only_diagonal_row_covariance = np.diag(
        np.diag(stat_only_mapped)
    ) / 25.0
    row_covariances = {
        "PHASE1A_FULL": full_row_covariance,
        "STAT_SYS_NO_ROWWISE_VELOCITY": stat_sys_row_covariance,
        "STAT_ONLY": stat_only_row_covariance,
        "STAT_SYS_DIAGONAL_ONLY": stat_sys_diagonal_row_covariance,
        "STAT_ONLY_DIAGONAL_ONLY": stat_only_diagonal_row_covariance,
    }
    projected = {
        name: a @ covariance @ a.T
        for name, covariance in row_covariances.items()
    }
    baseline_results = {
        name: baseline_result(name, vector, projected[name], config)
        for name in (*BASELINE_ORDER, *DIAGNOSTIC_ORDER)
    }
    phase1a_known = float(config["expected"]["known_phase1a_contrast_chi2"])
    known_reproduction = {
        "expected": phase1a_known,
        "actual": baseline_results["PHASE1A_FULL"]["chi2"],
        "absolute_difference": abs(
            baseline_results["PHASE1A_FULL"]["chi2"] - phase1a_known
        ),
        "tolerance": float(
            config["tolerances"]["known_phase1a_chi2_absolute"]
        ),
    }
    known_reproduction["status"] = (
        "PASS"
        if known_reproduction["absolute_difference"]
        <= known_reproduction["tolerance"]
        else "FAIL"
    )
    flags = [
        bool(baseline_results[name]["low_flag_at_alpha_0_01"])
        for name in BASELINE_ORDER
    ]
    classification = ordered_sensitivity_classification(flags)
    component = {
        "ROWWISE_VELOCITY_PROJECTED": component_diagnostics(
            projected["PHASE1A_FULL"]
            - projected["STAT_SYS_NO_ROWWISE_VELOCITY"]
        ),
        "SYSTEMATIC_PROJECTED_STAT_SYS_MINUS_STAT_ONLY": (
            component_diagnostics(
                projected["STAT_SYS_NO_ROWWISE_VELOCITY"]
                - projected["STAT_ONLY"]
            )
        ),
        "PHASE1A_FULL_VS_STAT_SYS_NO_ROWWISE_VELOCITY": (
            generalized_comparison(
                projected["PHASE1A_FULL"],
                projected["STAT_SYS_NO_ROWWISE_VELOCITY"],
            )
        ),
        "STAT_SYS_VS_STAT_ONLY": generalized_comparison(
            projected["STAT_SYS_NO_ROWWISE_VELOCITY"],
            projected["STAT_ONLY"],
        ),
    }
    primary_by_name = {
        name: baseline_results[name]["chi2"] for name in projected
    }
    alternative = alternative_basis_checks(
        alpha["data_alpha"],
        row_covariances,
        group["Z"],
        primary_by_name,
    )
    invariance = orthogonal_invariance_checks(
        vector, projected, primary_by_name, config
    )
    model_contrast = a @ alpha["model_term_alpha"]
    return {
        "contrast_vector": vector,
        "lineage": lineage,
        "row_covariances": row_covariances,
        "projected_covariances": projected,
        "baseline_results": baseline_results,
        "known_reproduction": known_reproduction,
        "ordered_flags": dict(zip(BASELINE_ORDER, flags)),
        "sensitivity_classification": classification,
        "component_diagnostics": component,
        "alternative_basis": alternative,
        "orthogonal_invariance": invariance,
        "model_term_contrast": {
            "maximum_absolute_value": float(
                np.max(np.abs(model_contrast))
            ),
            "euclidean_norm": float(np.linalg.norm(model_contrast)),
        },
    }


def numerical_gate_summary(
    analysis: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    tolerances = config["tolerances"]
    checks: list[dict[str, Any]] = []
    for name, result in analysis["baseline_results"].items():
        checks.extend(
            [
                {
                    "check": f"{name}:projected_minimum_eigenvalue",
                    "actual": result["covariance"]["eigenvalue_minimum"],
                    "requirement": (
                        f"> {tolerances['projected_covariance_minimum_eigenvalue']}"
                    ),
                    "status": (
                        "PASS"
                        if result["covariance"]["eigenvalue_minimum"]
                        > float(
                            tolerances[
                                "projected_covariance_minimum_eigenvalue"
                            ]
                        )
                        else "FAIL"
                    ),
                },
                {
                    "check": f"{name}:cholesky",
                    "actual": result["covariance"]["cholesky_success"],
                    "requirement": "True",
                    "status": (
                        "PASS"
                        if result["covariance"]["cholesky_success"]
                        else "FAIL"
                    ),
                },
                {
                    "check": f"{name}:reference_chi2",
                    "actual": result["reference_chi2_absolute_difference"],
                    "requirement": (
                        f"<= {tolerances['reference_chi2_absolute']}"
                    ),
                    "status": (
                        "PASS"
                        if result["reference_chi2_absolute_difference"]
                        <= float(tolerances["reference_chi2_absolute"])
                        else "FAIL"
                    ),
                },
                {
                    "check": f"{name}:probability_implementation",
                    "actual": result["cdf_gammainc_absolute_difference"],
                    "requirement": (
                        f"<= {tolerances['probability_absolute']}"
                    ),
                    "status": (
                        "PASS"
                        if result["cdf_gammainc_absolute_difference"]
                        <= float(tolerances["probability_absolute"])
                        else "FAIL"
                    ),
                },
            ]
        )
    for row in analysis["alternative_basis"]["rows"]:
        checks.append(
            {
                "check": f"{row['baseline']}:alternative_basis",
                "actual": row["absolute_difference"],
                "requirement": (
                    f"<= {tolerances['alternative_basis_chi2_absolute']}"
                ),
                "status": (
                    "PASS"
                    if row["absolute_difference"]
                    <= float(tolerances["alternative_basis_chi2_absolute"])
                    else "FAIL"
                ),
            }
        )
    checks.extend(
        [
            {
                "check": "known_phase1a_reproduction",
                "actual": analysis["known_reproduction"][
                    "absolute_difference"
                ],
                "requirement": (
                    f"<= {tolerances['known_phase1a_chi2_absolute']}"
                ),
                "status": analysis["known_reproduction"]["status"],
            },
            {
                "check": "orthogonal_invariance",
                "actual": analysis["orthogonal_invariance"][
                    "maximum_absolute_difference"
                ],
                "requirement": (
                    "<= "
                    + str(
                        tolerances[
                            "orthogonal_invariance_chi2_absolute"
                        ]
                    )
                ),
                "status": (
                    "PASS"
                    if analysis["orthogonal_invariance"][
                        "maximum_absolute_difference"
                    ]
                    <= float(
                        tolerances[
                            "orthogonal_invariance_chi2_absolute"
                        ]
                    )
                    else "FAIL"
                ),
            },
        ]
    )
    return {
        "check_count": len(checks),
        "pass_count": sum(row["status"] == "PASS" for row in checks),
        "checks": checks,
        "status": (
            "PASS"
            if all(row["status"] == "PASS" for row in checks)
            else "FAIL"
        ),
    }
