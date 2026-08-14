#!/usr/bin/env python3
"""Core routines for the frozen H0DN SN Ia Phase 1D audit."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import pathlib
import platform
import subprocess
import sys
from collections import Counter
from typing import Any, Iterable, Sequence


CONTRACT_ID = (
    "H0DN-SNIA-SAME-CID-MEASUREMENT-LINEAGE-"
    "PHASE1D-20260730-01"
)
CONTRACT_FREEZE_SHA256 = (
    "9220e68d70c72324289a090634a541368aa7f28a84aaa70aae6a8e25c250f893"
)
SUCCESS_STATUS = (
    "AUDIT_COMPLETE_SHARED_DEPENDENCY_AND_LINEAGE_CLASSIFIED"
)
BOUNDARY_MARKER = (
    "PUBLIC_MEASUREMENT_LINEAGE_AND_SHARED_DEPENDENCY_ONLY_"
    "NO_SURVEY_RANKING_NO_COVARIANCE_MODIFICATION_"
    "NO_CORRECTED_H0_NO_TENSION_RESOLUTION"
)
INPUT_CANDIDATE_EVIDENCE_LEVEL = (
    "FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE"
)
DIRECT_FINAL_MEASUREMENT_ANCESTRY = "NOT_ESTABLISHED"
CONFIGURATION_EVIDENCE_LEVEL = "CONFIGURATION_LEVEL"
CONFIGURATION_BOUNDARY_MARKER = (
    "CONFIGURATION_LEVEL_SHARED_DEPENDENCY_EVIDENCE_ONLY"
)
EXECUTED_RUN_BOUNDARY_MARKER = (
    "NO_EXECUTED_RUN_TO_FINAL_CATALOG_LINEAGE_PROOF"
)
ROW_STATUS_INTERPRETATIONS = {
    "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE": (
        "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE"
    ),
    "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE": (
        "NO_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE"
    ),
    "AMBIGUOUS_ACTIVE_PUBLIC_PHOTOMETRY_FILES": (
        "MULTIPLE_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATES"
    ),
    "PHOTOMETRY_PARSE_FAILURE": (
        "FROZEN_CROSSWALK_CANDIDATE_EVALUATION_BLOCKED_BY_PARSE_FAILURE"
    ),
}
GROUP_STATUS_INTERPRETATIONS = {
    "ALL_ROWS_UNIQUE_DISTINCT_PUBLIC_PHOTOMETRY_FILES": (
        "ALL_ROWS_HAVE_DISTINCT_UNIQUE_FROZEN_CROSSWALK_"
        "COMPATIBLE_INPUT_CANDIDATES"
    ),
    "PUBLIC_PHOTOMETRY_LINEAGE_UNRESOLVED": (
        "ONE_OR_MORE_ROWS_LACK_A_UNIQUE_FROZEN_CROSSWALK_"
        "COMPATIBLE_INPUT_CANDIDATE"
    ),
    "PUBLIC_PHOTOMETRY_FILE_REUSE_PRESENT": (
        "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE_"
        "FILE_REUSE_PRESENT"
    ),
}
SOURCE_FIELDS = (
    "source_id",
    "repository",
    "commit",
    "path",
    "git_blob_sha1",
    "bytes",
    "sha256",
)
MAP_FIELDS = (
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "final_dependency_classification",
)
ROW_FIELDS = (
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "survey_label",
    "allowed_directories",
    "active_candidate_count",
    "active_candidate_paths",
    "unparseable_active_files_in_allowed_directories",
    "lineage_status",
    "lineage_status_legacy",
    "lineage_status_interpretation",
    "evidence_level",
    "direct_final_measurement_ancestry",
    "unique_file_sha256",
    "unique_file_git_blob_sha1",
    "unique_file_nobs",
    "unique_file_observation_line_count",
)
FILE_FIELDS = (
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "survey_label",
    "source_directory",
    "path",
    "git_blob_sha1",
    "bytes",
    "sha256",
    "SNID",
    "SURVEY",
    "NOBS",
    "observation_line_count",
    "observation_lines_sha256",
    "active_list_occurrences",
    "ignore_list_occurrences",
    "evidence_level",
    "direct_final_measurement_ancestry",
)
GROUP_FIELDS = (
    "CID",
    "row_count",
    "h0dn_rows_1based",
    "IDSURVEY_codes",
    "survey_labels",
    "row_lineage_statuses",
    "row_lineage_status_interpretations",
    "unique_resolved_row_count",
    "unique_compatible_candidate_row_count",
    "distinct_resolved_file_sha256_count",
    "distinct_compatible_candidate_sha256_count",
    "pair_count",
    "resolved_pair_count",
    "compatible_candidate_pair_count",
    "pairs_with_byte_identical_observation_lines",
    "maximum_shared_exact_observation_line_count",
    "group_lineage_classification",
    "group_lineage_classification_legacy",
    "group_lineage_interpretation",
    "evidence_level",
    "direct_final_measurement_ancestry",
)
PAIR_FIELDS = (
    "CID",
    "h0dn_row_a_1based",
    "h0dn_row_b_1based",
    "path_a",
    "path_b",
    "file_a_observation_line_count",
    "file_b_observation_line_count",
    "shared_exact_observation_line_count",
    "observation_line_overlap_classification",
    "evidence_level",
    "direct_final_measurement_ancestry",
)
ANCHOR_FIELDS = (
    "anchor_id",
    "expected_count",
    "actual_active_noncomment_exact_line_count",
    "exact_text_sha256",
    "status",
    "evidence_level",
    "executed_run_to_final_catalog_lineage",
)
ASSET_FIELDS = (
    "asset_id",
    "basename",
    "required_for_full_lineage",
    "tracked_match_count",
    "tracked_paths",
    "availability_status",
    "evidence_level",
    "original_analysis_asset_existence",
)
DEPENDENCY_FIELDS = (
    "layer",
    "evidence",
    "availability",
    "evidence_level",
    "executed_run_to_final_catalog_lineage",
    "boundary_marker",
    "interpretive_boundary",
)
CROSSWALK_EVIDENCE_FIELDS = (
    "IDSURVEY",
    "published_label",
    "allowed_directory",
    "accepted_SURVEY_header",
    "evidence_source",
    "evidence_path_or_reference",
    "evidence_git_blob_or_version",
    "evidence_excerpt_sha256",
    "evidence_classification",
    "posthoc_candidate_promoted",
    "evidence_excerpt_spec",
)


class AuditFailure(RuntimeError):
    """A frozen operational gate failed."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
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
    fields: Sequence[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fields),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_tsv(
    path: pathlib.Path, expected_fields: Sequence[str]
) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != tuple(expected_fields):
            raise AuditFailure(f"{path.name} schema mismatch")
        return list(reader)


def git_text(root: pathlib.Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def git_bytes(root: pathlib.Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def normalize_repository(value: str) -> str:
    return value.strip().removesuffix("/").removesuffix(".git")


def environment_summary() -> dict[str, str]:
    return {
        "implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "byteorder": sys.byteorder,
    }


def load_config(project: pathlib.Path) -> dict[str, Any]:
    config = read_json(project / "provenance" / "DECISION_CONFIG.json")
    if config.get("contract_id") != CONTRACT_ID:
        raise AuditFailure("decision-config contract identifier mismatch")
    return config


def load_correction_config(project: pathlib.Path) -> dict[str, Any]:
    config = read_json(project / "provenance" / "CORRECTION_CONFIG.json")
    if config.get("contract_id") != CONTRACT_ID:
        raise AuditFailure("correction-config contract identifier mismatch")
    if config.get("amendment_id") != "AMEND-001":
        raise AuditFailure("correction-config amendment identifier mismatch")
    return config


def canonical_json_sha256(value: Any) -> str:
    data = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(data)


def expected_crosswalk_evidence_rows(
    project: pathlib.Path,
    config: dict[str, Any],
    pantheonplus: pathlib.Path,
    file_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    correction = load_correction_config(project)
    commit = config["pantheonplus"]["commit"]
    readme_path = "Pantheon+_Data/4_DISTANCES_AND_COVAR/README"
    pplus_path = config["pantheonplus"]["pipeline_config_path"]
    readme_text = git_bytes(
        pantheonplus, "show", f"{commit}:{readme_path}"
    ).decode("utf-8")
    legend_lines = [
        line.strip()
        for line in readme_text.splitlines()
        if "IDSURVEY - {" in line
    ]
    if len(legend_lines) != 1:
        raise AuditFailure("official IDSURVEY legend line is not unique")
    pplus_text = git_bytes(
        pantheonplus, "show", f"{commit}:{pplus_path}"
    ).decode("utf-8")
    active_lines = [
        line.strip()
        for line in pplus_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    readme_blob = git_text(
        pantheonplus, "rev-parse", f"{commit}:{readme_path}"
    )
    pplus_blob = git_text(
        pantheonplus, "rev-parse", f"{commit}:{pplus_path}"
    )
    classification_by_code = correction[
        "crosswalk_evidence_classification_by_IDSURVEY"
    ]
    evidence_rows: list[dict[str, Any]] = []
    for code in config["expected_population"]["survey_codes"]:
        vocab = config["source_vocabulary"][str(code)]
        directories = [item["directory"] for item in vocab["directories"]]
        headers = list(vocab["survey_headers"])
        raw_dir_lines: list[str] = []
        for directory in directories:
            matches = [
                line
                for line in active_lines
                if line.startswith("RAW_DIR:")
                and line.rstrip().endswith("/" + directory)
            ]
            if len(matches) != 1:
                raise AuditFailure(
                    f"PPLUS RAW_DIR evidence is not unique for {directory}"
                )
            raw_dir_lines.extend(matches)
        candidate_observations = sorted(
            {
                (
                    str(row["path"]),
                    str(row["git_blob_sha1"]),
                    str(row["SURVEY"]),
                )
                for row in file_rows
                if int(row["IDSURVEY"]) == code
            }
        )
        payload = {
            "IDSURVEY": code,
            "official_IDSURVEY_legend_line": legend_lines[0],
            "frozen_crosswalk": {
                "published_label": vocab["label"],
                "allowed_directories": directories,
                "accepted_SURVEY_headers": headers,
            },
            "pplus_raw_dir_anchor_lines": raw_dir_lines,
            "main_candidate_observations": [
                {
                    "path": path,
                    "git_blob_sha1": blob,
                    "SURVEY": survey,
                }
                for path, blob, survey in candidate_observations
            ],
        }
        classification = classification_by_code[str(code)]
        evidence_rows.append(
            {
                "IDSURVEY": code,
                "published_label": vocab["label"],
                "allowed_directory": ";".join(directories),
                "accepted_SURVEY_header": ";".join(headers),
                "evidence_source": (
                    "official IDSURVEY legend; frozen decision config; "
                    "PPLUS RAW_DIR anchors; main-audit active-file headers"
                ),
                "evidence_path_or_reference": ";".join(
                    [
                        readme_path,
                        pplus_path,
                        "provenance/DECISION_CONFIG.json",
                        "results/candidate_file_evidence.tsv",
                    ]
                ),
                "evidence_git_blob_or_version": ";".join(
                    [
                        f"commit={commit}",
                        f"IDSURVEY_README_blob={readme_blob}",
                        f"PPLUS_blob={pplus_blob}",
                        "photometry_tree="
                        + config["pantheonplus"]["photometry_tree_oid"],
                    ]
                ),
                "evidence_excerpt_sha256": canonical_json_sha256(payload),
                "evidence_classification": classification,
                "posthoc_candidate_promoted": "NO",
                "evidence_excerpt_spec": correction[
                    "crosswalk_evidence_excerpt_spec"
                ],
            }
        )
    return evidence_rows


def verify_crosswalk_evidence(
    project: pathlib.Path,
    config: dict[str, Any],
    pantheonplus: pathlib.Path,
    file_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    path = project / "provenance" / "SURVEY_CROSSWALK_EVIDENCE.tsv"
    actual = read_tsv(path, CROSSWALK_EVIDENCE_FIELDS)
    expected = expected_crosswalk_evidence_rows(
        project, config, pantheonplus, file_rows
    )
    expected_text = [
        {field: str(row.get(field, "")) for field in CROSSWALK_EVIDENCE_FIELDS}
        for row in expected
    ]
    allowed = {"DIRECTLY_DOCUMENTED", "COMPOSITE_INFERENCE", "UNRESOLVED_BRIDGE"}
    passed = (
        actual == expected_text
        and len(actual) == 8
        and {int(row["IDSURVEY"]) for row in actual}
        == set(config["expected_population"]["survey_codes"])
        and all(row["evidence_classification"] in allowed for row in actual)
        and all(row["posthoc_candidate_promoted"] == "NO" for row in actual)
    )
    summary = {
        "row_count": len(actual),
        "classification_counts": dict(
            sorted(Counter(row["evidence_classification"] for row in actual).items())
        ),
        "posthoc_candidate_promoted_count": sum(
            row["posthoc_candidate_promoted"] != "NO" for row in actual
        ),
        "status": "PASS" if passed else "FAIL",
    }
    return actual, summary


def verify_contract_freeze(project: pathlib.Path) -> dict[str, Any]:
    path = project / "provenance" / "CONTRACT_FREEZE.json"
    actual = sha256_file(path)
    freeze = read_json(path)
    sidecar = path.with_suffix(".sha256")
    sidecar_expected = f"{CONTRACT_FREEZE_SHA256}  {path.name}\n"
    checks: list[dict[str, Any]] = []
    for relative, record in sorted(freeze["files"].items()):
        candidate = project / relative
        data = candidate.read_bytes() if candidate.is_file() else None
        digest = sha256_bytes(data) if data is not None else None
        size = len(data) if data is not None else None
        if relative == "provenance/CONTRACT_AMENDMENTS.tsv":
            frozen_prefix = (
                data[: record["bytes"]] if data is not None else None
            )
            passed = (
                data is not None
                and len(data) >= record["bytes"]
                and sha256_bytes(frozen_prefix) == record["sha256"]
            )
            verification_mode = "FROZEN_PREFIX_WITH_APPEND_ONLY_REGISTER"
            frozen_prefix_sha256 = (
                sha256_bytes(frozen_prefix)
                if frozen_prefix is not None
                else None
            )
        else:
            passed = size == record["bytes"] and digest == record["sha256"]
            verification_mode = "EXACT_FROZEN_BYTES"
            frozen_prefix_sha256 = None
        checks.append(
            {
                "path": relative,
                "expected_bytes": record["bytes"],
                "actual_bytes": size,
                "expected_sha256": record["sha256"],
                "actual_sha256": digest,
                "verification_mode": verification_mode,
                "frozen_prefix_sha256": frozen_prefix_sha256,
                "status": "PASS" if passed else "FAIL",
            }
        )
    chronology = (
        freeze.get("contract_id") == CONTRACT_ID
        and freeze.get("status") == "FROZEN_BEFORE_COMPLETE_PHASE1D_SCAN"
        and freeze.get("partial_result_blindness") is True
        and freeze.get("complete_69_row_scan_observed_before_freeze") is False
        and freeze.get(
            "complete_30_group_classification_observed_before_freeze"
        )
        is False
        and freeze.get("independent_verification_observed_before_freeze")
        is False
        and freeze.get(
            "release_sufficiency_classification_observed_before_freeze"
        )
        is False
    )
    status = (
        "PASS"
        if actual == CONTRACT_FREEZE_SHA256
        and sidecar.is_file()
        and sidecar.read_text(encoding="utf-8") == sidecar_expected
        and chronology
        and all(row["status"] == "PASS" for row in checks)
        else "FAIL"
    )
    return {
        "contract_id": CONTRACT_ID,
        "contract_freeze_sha256": actual,
        "chronology_status": "PASS" if chronology else "FAIL",
        "partial_result_blindness": True,
        "checks": checks,
        "status": status,
    }


def verify_sources(
    project: pathlib.Path,
    roots: dict[str, pathlib.Path],
) -> dict[str, Any]:
    config = load_config(project)
    rows = read_tsv(
        project / "provenance" / "SOURCE_LOCK.tsv", SOURCE_FIELDS
    )
    repository_lock = read_json(
        project / "provenance" / "REPOSITORY_LOCK.json"
    )
    repositories: dict[str, Any] = {}
    overall = True
    for source_id in ("h0dn", "pantheonplus"):
        root = roots[source_id]
        expected = config[source_id]
        head = git_text(root, "rev-parse", "HEAD")
        origin = normalize_repository(
            git_text(root, "remote", "get-url", "origin")
        )
        selected = [row for row in rows if row["source_id"] == source_id]
        file_checks = []
        for row in selected:
            try:
                data = git_bytes(
                    root, "show", f"{row['commit']}:{row['path']}"
                )
                blob = git_text(
                    root, "rev-parse", f"{row['commit']}:{row['path']}"
                )
            except subprocess.CalledProcessError:
                data = b""
                blob = None
            passed = (
                blob == row["git_blob_sha1"]
                and len(data) == int(row["bytes"])
                and sha256_bytes(data) == row["sha256"]
            )
            file_checks.append(
                {
                    "path": row["path"],
                    "expected_git_blob_sha1": row["git_blob_sha1"],
                    "actual_git_blob_sha1": blob,
                    "expected_bytes": int(row["bytes"]),
                    "actual_bytes": len(data) if blob else None,
                    "expected_sha256": row["sha256"],
                    "actual_sha256": sha256_bytes(data) if blob else None,
                    "status": "PASS" if passed else "FAIL",
                }
            )
        lock_entry = repository_lock["repositories"][source_id]
        tree_pass = True
        actual_tree = None
        if source_id == "pantheonplus":
            actual_tree = git_text(
                root,
                "rev-parse",
                f"{head}:{expected['photometry_root']}",
            )
            tree_pass = (
                actual_tree == expected["photometry_tree_oid"]
                == lock_entry["photometry_tree_oid"]
            )
        passed = (
            head == expected["commit"] == lock_entry["commit"]
            and origin == normalize_repository(expected["repository"])
            and tree_pass
            and len(selected) == lock_entry["locked_file_count"]
            and all(item["status"] == "PASS" for item in file_checks)
        )
        overall = overall and passed
        repositories[source_id] = {
            "actual_commit": head,
            "expected_commit": expected["commit"],
            "actual_repository": origin,
            "expected_repository": normalize_repository(
                expected["repository"]
            ),
            "actual_photometry_tree_oid": actual_tree,
            "locked_file_count": len(selected),
            "file_checks": file_checks,
            "status": "PASS" if passed else "FAIL",
        }
    return {
        "repositories": repositories,
        "source_lock_row_count": len(rows),
        "status": "PASS" if overall else "FAIL",
    }


def read_population(
    project: pathlib.Path, config: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = project / config["phase1b_row_map"]["path"]
    if sha256_file(path) != config["phase1b_row_map"]["sha256"]:
        raise AuditFailure("Phase 1B row-map hash mismatch")
    raw = read_tsv(path, MAP_FIELDS)
    rows: list[dict[str, Any]] = []
    seen_h0dn: set[int] = set()
    seen_official: set[int] = set()
    for record in raw:
        row = {
            "h0dn_row_1based": int(record["h0dn_row_1based"]),
            "official_row_1based": int(record["official_row_1based"]),
            "CID": record["CID"],
            "IDSURVEY": int(record["IDSURVEY"]),
            "final_dependency_classification": record[
                "final_dependency_classification"
            ],
        }
        if row["h0dn_row_1based"] in seen_h0dn:
            raise AuditFailure("reused H0DN row in Phase 1B map")
        if row["official_row_1based"] in seen_official:
            raise AuditFailure("reused official row in Phase 1B map")
        seen_h0dn.add(row["h0dn_row_1based"])
        seen_official.add(row["official_row_1based"])
        rows.append(row)
    if len(rows) != 277:
        raise AuditFailure("Phase 1B map does not contain 277 rows")
    counts = Counter(row["CID"] for row in rows)
    population = [row for row in rows if counts[row["CID"]] > 1]
    group_sizes = Counter(counts[cid] for cid in counts if counts[cid] > 1)
    survey_codes = sorted({row["IDSURVEY"] for row in population})
    expected = config["expected_population"]
    passed = (
        len(population) == expected["row_count"]
        and sum(group_sizes.values()) == expected["group_count"]
        and {str(key): value for key, value in sorted(group_sizes.items())}
        == expected["group_size_counts"]
        and survey_codes == expected["survey_codes"]
    )
    inventory = {
        "phase1b_map_row_count": len(rows),
        "same_cid_group_count": sum(group_sizes.values()),
        "same_cid_row_count": len(population),
        "group_size_counts": {
            str(key): value for key, value in sorted(group_sizes.items())
        },
        "survey_codes": survey_codes,
        "status": "PASS" if passed else "FAIL",
    }
    return population, inventory


def git_tree_entries(
    root: pathlib.Path, commit: str, prefix: str | None = None
) -> dict[str, dict[str, str]]:
    args = ["ls-tree", "-r", "-z", commit]
    if prefix:
        args.extend(["--", prefix])
    data = git_bytes(root, *args)
    entries: dict[str, dict[str, str]] = {}
    for item in data.split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split(" ")
        path = raw_path.decode("utf-8")
        entries[path] = {
            "mode": mode,
            "type": object_type,
            "oid": oid,
        }
    return entries


def active_list_entries(data: bytes) -> tuple[list[str], Counter[str]]:
    lines = []
    for raw in data.decode("utf-8").splitlines():
        value = raw.strip(" \t\r\n")
        if not value or value.startswith("#"):
            continue
        lines.append(value)
    return lines, Counter(lines)


def normalize_survey(value: str) -> str:
    return " ".join(value.strip(" \t\r\n").split())


def parse_photometry_blob(data: bytes) -> dict[str, Any]:
    lines = data.splitlines()
    header_lines = []
    for line in lines:
        if line.startswith(b"OBS:"):
            break
        header_lines.append(line)
    errors: list[str] = []

    def values(key: bytes) -> list[bytes]:
        return [
            line[len(key) :]
            for line in header_lines
            if line.startswith(key)
        ]

    snid_values = values(b"SNID:")
    survey_values = values(b"SURVEY:")
    nobs_values = values(b"NOBS:")
    if len(snid_values) != 1:
        errors.append(f"SNID_HEADER_COUNT_{len(snid_values)}")
    if len(survey_values) != 1:
        errors.append(f"SURVEY_HEADER_COUNT_{len(survey_values)}")
    if len(nobs_values) > 1:
        errors.append(f"NOBS_HEADER_COUNT_{len(nobs_values)}")
    try:
        snid = (
            snid_values[0].decode("utf-8").strip(" \t")
            if len(snid_values) == 1
            else None
        )
        survey = (
            normalize_survey(survey_values[0].decode("utf-8"))
            if len(survey_values) == 1
            else None
        )
    except UnicodeDecodeError:
        snid = None
        survey = None
        errors.append("HEADER_UTF8_DECODE_FAILURE")
    observation_lines = [
        line for line in lines if line.startswith(b"OBS:")
    ]
    nobs = None
    if len(nobs_values) == 1:
        try:
            token = nobs_values[0].decode("ascii").strip().split()[0]
            nobs = int(token)
            if nobs < 0:
                errors.append("NEGATIVE_NOBS")
            if nobs != len(observation_lines):
                errors.append("NOBS_OBSERVATION_LINE_COUNT_MISMATCH")
        except (UnicodeDecodeError, ValueError, IndexError):
            errors.append("NOBS_PARSE_FAILURE")
    observation_bytes = (
        b"\n".join(observation_lines) + (b"\n" if observation_lines else b"")
    )
    return {
        "SNID": snid,
        "SURVEY": survey,
        "NOBS": nobs,
        "observation_lines": observation_lines,
        "observation_line_count": len(observation_lines),
        "observation_lines_sha256": sha256_bytes(observation_bytes),
        "parse_errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }


def scan_photometry(
    pantheonplus: pathlib.Path,
    config: dict[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    commit = config["pantheonplus"]["commit"]
    root_path = config["pantheonplus"]["photometry_root"]
    tree = git_tree_entries(pantheonplus, commit, root_path)
    directory_configs: dict[str, dict[str, str]] = {}
    for survey in config["source_vocabulary"].values():
        for item in survey["directories"]:
            directory_configs[item["directory"]] = item
    directories: dict[str, dict[str, Any]] = {}
    parsed_by_path: dict[str, dict[str, Any]] = {}
    total_listed = 0
    total_parse_failures = 0
    for directory, item in sorted(directory_configs.items()):
        base = f"{root_path}/{directory}"
        list_path = f"{base}/{item['list_file']}"
        ignore_path = f"{base}/{item['ignore_file']}"
        listed, list_counts = active_list_entries(
            git_bytes(pantheonplus, "show", f"{commit}:{list_path}")
        )
        ignored, ignore_counts = active_list_entries(
            git_bytes(pantheonplus, "show", f"{commit}:{ignore_path}")
        )
        if any(count != 1 for count in list_counts.values()):
            raise AuditFailure(f"duplicate filename in {list_path}")
        unparseable_paths = []
        active_paths = []
        for filename in listed:
            if ignore_counts[filename]:
                continue
            path = f"{base}/{filename}"
            entry = tree.get(path)
            if entry is None or entry["type"] != "blob":
                raise AuditFailure(f"listed photometry blob missing: {path}")
            data = git_bytes(pantheonplus, "show", f"{commit}:{path}")
            parsed = parse_photometry_blob(data)
            parsed.update(
                {
                    "source_directory": directory,
                    "path": path,
                    "git_blob_sha1": entry["oid"],
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                    "active_list_occurrences": list_counts[filename],
                    "ignore_list_occurrences": ignore_counts[filename],
                }
            )
            parsed_by_path[path] = parsed
            active_paths.append(path)
            if parsed["status"] != "PASS":
                unparseable_paths.append(path)
        total_listed += len(active_paths)
        total_parse_failures += len(unparseable_paths)
        directories[directory] = {
            "active_paths": active_paths,
            "unparseable_paths": unparseable_paths,
            "listed_filename_count": len(listed),
            "active_file_count": len(active_paths),
            "ignored_filename_count": sum(
                1 for filename in listed if ignore_counts[filename]
            ),
        }
    summary = {
        "configured_directory_count": len(directories),
        "active_file_count": total_listed,
        "parse_failure_count": total_parse_failures,
        "directories": {
            key: {
                "listed_filename_count": value["listed_filename_count"],
                "active_file_count": value["active_file_count"],
                "ignored_filename_count": value[
                    "ignored_filename_count"
                ],
                "parse_failure_count": len(value["unparseable_paths"]),
                "parse_failure_paths": value["unparseable_paths"],
            }
            for key, value in sorted(directories.items())
        },
        "status": "PASS_SCAN_COMPLETE",
    }
    return directories, parsed_by_path, summary


def row_and_group_lineage(
    population: list[dict[str, Any]],
    config: dict[str, Any],
    directories: dict[str, dict[str, Any]],
    parsed_by_path: dict[str, dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    row_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    selected_by_h0dn: dict[int, dict[str, Any]] = {}
    for row in population:
        survey = config["source_vocabulary"][str(row["IDSURVEY"])]
        allowed_dirs = [
            item["directory"] for item in survey["directories"]
        ]
        accepted_surveys = set(survey["survey_headers"])
        unparseable = sorted(
            path
            for directory in allowed_dirs
            for path in directories[directory]["unparseable_paths"]
        )
        candidates = sorted(
            (
                parsed_by_path[path]
                for directory in allowed_dirs
                for path in directories[directory]["active_paths"]
                if parsed_by_path[path]["status"] == "PASS"
                and parsed_by_path[path]["SNID"] == row["CID"]
                and parsed_by_path[path]["SURVEY"] in accepted_surveys
            ),
            key=lambda item: item["path"],
        )
        if unparseable:
            status = "PHOTOMETRY_PARSE_FAILURE"
        elif len(candidates) == 1:
            status = "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
        elif not candidates:
            status = "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
        else:
            status = "AMBIGUOUS_ACTIVE_PUBLIC_PHOTOMETRY_FILES"
        unique = candidates[0] if len(candidates) == 1 else None
        if unique is not None:
            selected_by_h0dn[row["h0dn_row_1based"]] = unique
        row_rows.append(
            {
                "h0dn_row_1based": row["h0dn_row_1based"],
                "official_row_1based": row["official_row_1based"],
                "CID": row["CID"],
                "IDSURVEY": row["IDSURVEY"],
                "survey_label": survey["label"],
                "allowed_directories": ";".join(allowed_dirs),
                "active_candidate_count": len(candidates),
                "active_candidate_paths": ";".join(
                    item["path"] for item in candidates
                ),
                "unparseable_active_files_in_allowed_directories": len(
                    unparseable
                ),
                "lineage_status": status,
                "lineage_status_legacy": status,
                "lineage_status_interpretation": (
                    ROW_STATUS_INTERPRETATIONS[status]
                ),
                "evidence_level": INPUT_CANDIDATE_EVIDENCE_LEVEL,
                "direct_final_measurement_ancestry": (
                    DIRECT_FINAL_MEASUREMENT_ANCESTRY
                ),
                "unique_file_sha256": unique["sha256"] if unique else "",
                "unique_file_git_blob_sha1": (
                    unique["git_blob_sha1"] if unique else ""
                ),
                "unique_file_nobs": (
                    unique["NOBS"]
                    if unique is not None and unique["NOBS"] is not None
                    else ""
                ),
                "unique_file_observation_line_count": (
                    unique["observation_line_count"] if unique else ""
                ),
            }
        )
        for candidate in candidates:
            candidate_rows.append(
                {
                    "h0dn_row_1based": row["h0dn_row_1based"],
                    "official_row_1based": row["official_row_1based"],
                    "CID": row["CID"],
                    "IDSURVEY": row["IDSURVEY"],
                    "survey_label": survey["label"],
                    "source_directory": candidate["source_directory"],
                    "path": candidate["path"],
                    "git_blob_sha1": candidate["git_blob_sha1"],
                    "bytes": candidate["bytes"],
                    "sha256": candidate["sha256"],
                    "SNID": candidate["SNID"],
                    "SURVEY": candidate["SURVEY"],
                    "NOBS": (
                        candidate["NOBS"]
                        if candidate["NOBS"] is not None
                        else ""
                    ),
                    "observation_line_count": candidate[
                        "observation_line_count"
                    ],
                    "observation_lines_sha256": candidate[
                        "observation_lines_sha256"
                    ],
                    "active_list_occurrences": candidate[
                        "active_list_occurrences"
                    ],
                    "ignore_list_occurrences": candidate[
                        "ignore_list_occurrences"
                    ],
                    "evidence_level": INPUT_CANDIDATE_EVIDENCE_LEVEL,
                    "direct_final_measurement_ancestry": (
                        DIRECT_FINAL_MEASUREMENT_ANCESTRY
                    ),
                }
            )
    row_rows.sort(key=lambda item: item["h0dn_row_1based"])
    by_cid: dict[str, list[dict[str, Any]]] = {}
    for row in row_rows:
        by_cid.setdefault(row["CID"], []).append(row)
    pair_rows: list[dict[str, Any]] = []
    group_rows: list[dict[str, Any]] = []
    for cid, group in sorted(
        by_cid.items(), key=lambda item: item[1][0]["h0dn_row_1based"]
    ):
        resolved_pair_count = 0
        overlap_pair_count = 0
        maximum_overlap = 0
        for left, right in itertools.combinations(group, 2):
            file_left = selected_by_h0dn.get(left["h0dn_row_1based"])
            file_right = selected_by_h0dn.get(right["h0dn_row_1based"])
            if file_left is not None and file_right is not None:
                shared = len(
                    set(file_left["observation_lines"])
                    & set(file_right["observation_lines"])
                )
                resolved_pair_count += 1
                overlap_pair_count += int(shared > 0)
                maximum_overlap = max(maximum_overlap, shared)
                pair_class = (
                    "BYTE_IDENTICAL_OBSERVATION_LINES_PRESENT"
                    if shared
                    else "NO_BYTE_IDENTICAL_OBSERVATION_LINES"
                )
                pair_rows.append(
                    {
                        "CID": cid,
                        "h0dn_row_a_1based": left["h0dn_row_1based"],
                        "h0dn_row_b_1based": right["h0dn_row_1based"],
                        "path_a": file_left["path"],
                        "path_b": file_right["path"],
                        "file_a_observation_line_count": file_left[
                            "observation_line_count"
                        ],
                        "file_b_observation_line_count": file_right[
                            "observation_line_count"
                        ],
                        "shared_exact_observation_line_count": shared,
                        "observation_line_overlap_classification": pair_class,
                        "evidence_level": INPUT_CANDIDATE_EVIDENCE_LEVEL,
                        "direct_final_measurement_ancestry": (
                            DIRECT_FINAL_MEASUREMENT_ANCESTRY
                        ),
                    }
                )
            else:
                pair_rows.append(
                    {
                        "CID": cid,
                        "h0dn_row_a_1based": left["h0dn_row_1based"],
                        "h0dn_row_b_1based": right["h0dn_row_1based"],
                        "path_a": file_left["path"] if file_left else "",
                        "path_b": file_right["path"] if file_right else "",
                        "file_a_observation_line_count": (
                            file_left["observation_line_count"]
                            if file_left
                            else ""
                        ),
                        "file_b_observation_line_count": (
                            file_right["observation_line_count"]
                            if file_right
                            else ""
                        ),
                        "shared_exact_observation_line_count": "",
                        "observation_line_overlap_classification": (
                            "UNRESOLVED_FILE_PAIR"
                        ),
                        "evidence_level": INPUT_CANDIDATE_EVIDENCE_LEVEL,
                        "direct_final_measurement_ancestry": (
                            DIRECT_FINAL_MEASUREMENT_ANCESTRY
                        ),
                    }
                )
        unique_count = sum(
            row["lineage_status"]
            == "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
            for row in group
        )
        hashes = [
            row["unique_file_sha256"]
            for row in group
            if row["unique_file_sha256"]
        ]
        distinct_hash_count = len(set(hashes))
        if unique_count != len(group):
            classification = "PUBLIC_PHOTOMETRY_LINEAGE_UNRESOLVED"
        elif distinct_hash_count == len(group):
            classification = (
                "ALL_ROWS_UNIQUE_DISTINCT_PUBLIC_PHOTOMETRY_FILES"
            )
        else:
            classification = "PUBLIC_PHOTOMETRY_FILE_REUSE_PRESENT"
        group_rows.append(
            {
                "CID": cid,
                "row_count": len(group),
                "h0dn_rows_1based": ";".join(
                    str(row["h0dn_row_1based"]) for row in group
                ),
                "IDSURVEY_codes": ";".join(
                    str(row["IDSURVEY"]) for row in group
                ),
                "survey_labels": ";".join(
                    row["survey_label"] for row in group
                ),
                "row_lineage_statuses": ";".join(
                    row["lineage_status"] for row in group
                ),
                "row_lineage_status_interpretations": ";".join(
                    row["lineage_status_interpretation"] for row in group
                ),
                "unique_resolved_row_count": unique_count,
                "unique_compatible_candidate_row_count": unique_count,
                "distinct_resolved_file_sha256_count": distinct_hash_count,
                "distinct_compatible_candidate_sha256_count": (
                    distinct_hash_count
                ),
                "pair_count": len(group) * (len(group) - 1) // 2,
                "resolved_pair_count": resolved_pair_count,
                "compatible_candidate_pair_count": resolved_pair_count,
                "pairs_with_byte_identical_observation_lines": (
                    overlap_pair_count
                ),
                "maximum_shared_exact_observation_line_count": (
                    maximum_overlap if resolved_pair_count else ""
                ),
                "group_lineage_classification": classification,
                "group_lineage_classification_legacy": classification,
                "group_lineage_interpretation": (
                    GROUP_STATUS_INTERPRETATIONS[classification]
                ),
                "evidence_level": INPUT_CANDIDATE_EVIDENCE_LEVEL,
                "direct_final_measurement_ancestry": (
                    DIRECT_FINAL_MEASUREMENT_ANCESTRY
                ),
            }
        )
    candidate_rows.sort(
        key=lambda item: (item["h0dn_row_1based"], item["path"])
    )
    return row_rows, candidate_rows, group_rows, pair_rows


def pipeline_evidence(
    pantheonplus: pathlib.Path,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    commit = config["pantheonplus"]["commit"]
    path = config["pantheonplus"]["pipeline_config_path"]
    text = git_bytes(
        pantheonplus, "show", f"{commit}:{path}"
    ).decode("utf-8")
    active_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    anchor_rows = []
    for anchor in config["pipeline_anchors"]:
        actual = active_lines.count(anchor["exact_text"])
        anchor_rows.append(
            {
                "anchor_id": anchor["anchor_id"],
                "expected_count": anchor["expected_count"],
                "actual_active_noncomment_exact_line_count": actual,
                "exact_text_sha256": sha256_bytes(
                    anchor["exact_text"].encode("utf-8")
                ),
                "status": (
                    "PASS"
                    if actual == anchor["expected_count"]
                    else "FAIL"
                ),
                "evidence_level": CONFIGURATION_EVIDENCE_LEVEL,
                "executed_run_to_final_catalog_lineage": (
                    DIRECT_FINAL_MEASUREMENT_ANCESTRY
                ),
            }
        )
    tree = git_tree_entries(pantheonplus, commit)
    all_paths = sorted(tree)
    asset_rows = []
    for asset in config["referenced_assets"]:
        matches = [
            path
            for path in all_paths
            if pathlib.PurePosixPath(path).name == asset["basename"]
        ]
        asset_rows.append(
            {
                "asset_id": asset["asset_id"],
                "basename": asset["basename"],
                "required_for_full_lineage": str(
                    asset["required_for_full_lineage"]
                ).lower(),
                "tracked_match_count": len(matches),
                "tracked_paths": ";".join(matches),
                "availability_status": (
                    "TRACKED_IN_FROZEN_RELEASE"
                    if matches
                    else "REFERENCED_NOT_TRACKED_IN_FROZEN_RELEASE"
                ),
                "evidence_level": "REPOSITORY_TRACKING_CHECK",
                "original_analysis_asset_existence": "NOT_DETERMINED",
            }
        )
    summary = {
        "pipeline_config_path": path,
        "pipeline_config_sha256": sha256_bytes(text.encode("utf-8")),
        "anchor_count": len(anchor_rows),
        "anchor_pass_count": sum(
            row["status"] == "PASS" for row in anchor_rows
        ),
        "required_asset_count": sum(
            row["required_for_full_lineage"] == "true"
            for row in asset_rows
        ),
        "required_asset_present_count": sum(
            row["required_for_full_lineage"] == "true"
            and row["availability_status"] == "TRACKED_IN_FROZEN_RELEASE"
            for row in asset_rows
        ),
        "evidence_level": CONFIGURATION_EVIDENCE_LEVEL,
        "executed_run_to_final_catalog_lineage": (
            DIRECT_FINAL_MEASUREMENT_ANCESTRY
        ),
        "boundary_markers": [
            CONFIGURATION_BOUNDARY_MARKER,
            EXECUTED_RUN_BOUNDARY_MARKER,
        ],
        "status": (
            "PASS"
            if all(row["status"] == "PASS" for row in anchor_rows)
            else "FAIL"
        ),
    }
    return anchor_rows, asset_rows, summary


def make_dependency_ledger(
    row_rows: list[dict[str, Any]],
    group_rows: list[dict[str, Any]],
    pipeline_summary: dict[str, Any],
    asset_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    row_counts = Counter(row["lineage_status"] for row in row_rows)
    group_counts = Counter(
        row["group_lineage_classification"] for row in group_rows
    )
    missing_assets = [
        row["asset_id"]
        for row in asset_rows
        if row["availability_status"]
        == "REFERENCED_NOT_TRACKED_IN_FROZEN_RELEASE"
    ]
    return [
        {
            "layer": "ASTROPHYSICAL_EVENT_IDENTITY",
            "evidence": "30 exact-CID groups fixed by the Phase 1B map",
            "availability": "COMPLETE_FOR_AUDIT_POPULATION",
            "evidence_level": "PHASE1B_IDENTIFIER_LEVEL",
            "executed_run_to_final_catalog_lineage": (
                DIRECT_FINAL_MEASUREMENT_ANCESTRY
            ),
            "boundary_marker": DIRECT_FINAL_MEASUREMENT_ANCESTRY,
            "interpretive_boundary": (
                "same CID identifies the same event but does not make "
                "survey fits independent"
            ),
        },
        {
            "layer": "PUBLIC_PHOTOMETRY_FILE",
            "evidence": json.dumps(
                dict(sorted(row_counts.items())),
                sort_keys=True,
                separators=(",", ":"),
            ),
            "availability": json.dumps(
                dict(sorted(group_counts.items())),
                sort_keys=True,
                separators=(",", ":"),
            ),
            "evidence_level": INPUT_CANDIDATE_EVIDENCE_LEVEL,
            "executed_run_to_final_catalog_lineage": (
                DIRECT_FINAL_MEASUREMENT_ANCESTRY
            ),
            "boundary_marker": DIRECT_FINAL_MEASUREMENT_ANCESTRY,
            "interpretive_boundary": (
                "distinct blobs do not prove disjoint exposures, "
                "calibration, or likelihood independence"
            ),
        },
        {
            "layer": "COMMON_LIGHT_CURVE_AND_BIASCOR_PIPELINE",
            "evidence": (
                f"{pipeline_summary['anchor_pass_count']}/"
                f"{pipeline_summary['anchor_count']} frozen anchors pass"
            ),
            "availability": "DOCUMENTED_BY_PUBLIC_PPLUS_YML",
            "evidence_level": CONFIGURATION_EVIDENCE_LEVEL,
            "executed_run_to_final_catalog_lineage": (
                DIRECT_FINAL_MEASUREMENT_ANCESTRY
            ),
            "boundary_marker": (
                CONFIGURATION_BOUNDARY_MARKER
                + ";"
                + EXECUTED_RUN_BOUNDARY_MARKER
            ),
            "interpretive_boundary": (
                "configuration text describing shared processing is not "
                "proof of an executed public-catalog production run or a "
                "causal explanation "
                "for the Phase 1C result"
            ),
        },
        {
            "layer": "DUPLICATE_CID_INTRINSIC_SCATTER_COVARIANCE",
            "evidence": "DUP_SIGINT and NOSYS anchors in public PPLUS.yml",
            "availability": (
                "ALL_REFERENCED_ASSETS_TRACKED"
                if not missing_assets
                else "REFERENCED_NOT_TRACKED_IN_FROZEN_RELEASE:"
                + ";".join(missing_assets)
            ),
            "evidence_level": CONFIGURATION_EVIDENCE_LEVEL,
            "executed_run_to_final_catalog_lineage": (
                DIRECT_FINAL_MEASUREMENT_ANCESTRY
            ),
            "boundary_marker": (
                CONFIGURATION_BOUNDARY_MARKER
                + ";"
                + EXECUTED_RUN_BOUNDARY_MARKER
            ),
            "interpretive_boundary": (
                "an untracked referenced asset is a release-sufficiency "
                "limit, not evidence of an absent original asset or error"
            ),
        },
    ]


def run_audit(
    project: pathlib.Path,
    h0dn: pathlib.Path,
    pantheonplus: pathlib.Path,
) -> dict[str, Any]:
    results = project / "results"
    results.mkdir(exist_ok=True)
    config = load_config(project)
    contract = verify_contract_freeze(project)
    source = verify_sources(
        project, {"h0dn": h0dn, "pantheonplus": pantheonplus}
    )
    population, inventory = read_population(project, config)
    if contract["status"] != "PASS":
        raise AuditFailure("contract verification failed")
    if source["status"] != "PASS":
        raise AuditFailure("source verification failed")
    if inventory["status"] != "PASS":
        raise AuditFailure("upstream population verification failed")
    directories, parsed, scan = scan_photometry(pantheonplus, config)
    row_rows, file_rows, group_rows, pair_rows = row_and_group_lineage(
        population, config, directories, parsed
    )
    anchor_rows, asset_rows, pipeline = pipeline_evidence(
        pantheonplus, config
    )
    if pipeline["status"] != "PASS":
        raise AuditFailure("pipeline anchor verification failed")
    row_counts = Counter(row["lineage_status"] for row in row_rows)
    group_counts = Counter(
        row["group_lineage_classification"] for row in group_rows
    )
    unique_row_count = row_counts[
        "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
    ]
    required_assets_present = (
        pipeline["required_asset_present_count"]
        == pipeline["required_asset_count"]
    )
    if (
        unique_row_count == len(row_rows)
        and pipeline["anchor_pass_count"] == pipeline["anchor_count"]
        and required_assets_present
    ):
        classification = "PUBLIC_RELEASE_FULL_MEASUREMENT_LINEAGE"
    elif (
        unique_row_count == 0
        and pipeline["anchor_pass_count"] == 0
    ):
        classification = "PUBLIC_RELEASE_IDENTIFIER_ONLY_LINEAGE"
    else:
        classification = "PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE"
    dependency_rows = make_dependency_ledger(
        row_rows, group_rows, pipeline, asset_rows
    )
    _crosswalk_rows, crosswalk_summary = verify_crosswalk_evidence(
        project, config, pantheonplus, file_rows
    )
    if crosswalk_summary["status"] != "PASS":
        raise AuditFailure("survey-crosswalk evidence ledger failed")
    summary = {
        "audit_id": CONTRACT_ID,
        "boundary_marker": BOUNDARY_MARKER,
        "status": SUCCESS_STATUS,
        "release_sufficiency_classification": classification,
        "result_blindness": "PARTIAL_RESULT_BLINDNESS_DISCLOSED",
        "interpretation": {
            "evidence_level": INPUT_CANDIDATE_EVIDENCE_LEVEL,
            "direct_final_measurement_ancestry": (
                DIRECT_FINAL_MEASUREMENT_ANCESTRY
            ),
            "legacy_row_status_aliases": dict(
                sorted(ROW_STATUS_INTERPRETATIONS.items())
            ),
            "legacy_group_status_aliases": dict(
                sorted(GROUP_STATUS_INTERPRETATIONS.items())
            ),
        },
        "population": inventory,
        "photometry_scan": {
            "configured_directory_count": scan[
                "configured_directory_count"
            ],
            "active_file_count": scan["active_file_count"],
            "parse_failure_count": scan["parse_failure_count"],
        },
        "row_lineage": {
            "row_count": len(row_rows),
            "classification_counts": dict(sorted(row_counts.items())),
            "unique_active_public_photometry_file_count": unique_row_count,
            "unique_frozen_crosswalk_compatible_input_candidate_count": (
                unique_row_count
            ),
            "candidate_evidence_row_count": len(file_rows),
            "direct_final_measurement_ancestry": (
                DIRECT_FINAL_MEASUREMENT_ANCESTRY
            ),
        },
        "group_lineage": {
            "group_count": len(group_rows),
            "classification_counts": dict(sorted(group_counts.items())),
            "pair_count": len(pair_rows),
            "resolved_pair_count": sum(
                row["observation_line_overlap_classification"]
                != "UNRESOLVED_FILE_PAIR"
                for row in pair_rows
            ),
            "pairs_with_byte_identical_observation_lines": sum(
                row["observation_line_overlap_classification"]
                == "BYTE_IDENTICAL_OBSERVATION_LINES_PRESENT"
                for row in pair_rows
            ),
            "direct_final_measurement_ancestry": (
                DIRECT_FINAL_MEASUREMENT_ANCESTRY
            ),
        },
        "shared_pipeline": pipeline,
        "survey_crosswalk_evidence": crosswalk_summary,
        "referenced_assets": {
            "asset_count": len(asset_rows),
            "required_asset_count": pipeline["required_asset_count"],
            "required_asset_present_count": pipeline[
                "required_asset_present_count"
            ],
            "availability_counts": dict(
                sorted(
                    Counter(
                        row["availability_status"] for row in asset_rows
                    ).items()
                )
            ),
        },
        "nonclaims": [
            "no direct executed-run ancestry from public photometry inputs to final m_b_corr rows",
            "no statistical-independence claim from distinct files",
            "no executed public-catalog production-run claim from PPLUS.yml configuration anchors",
            "no causal attribution for the Phase 1A or Phase 1C result",
            "no survey or object ranking",
            "no covariance modification",
            "no corrected a_B, M_B, H0, or tension significance",
            "no claim that an untracked frozen-release asset was absent from the original analysis",
            "no promotion of post-hoc IDSURVEY 51, 57, or 65 candidates"
        ],
    }
    write_json(results / "contract_verification.json", contract)
    write_json(results / "source_verification.json", source)
    write_json(results / "input_inventory.json", inventory)
    write_json(results / "photometry_scan_summary.json", scan)
    write_tsv(results / "row_lineage.tsv", row_rows, ROW_FIELDS)
    write_tsv(
        results / "candidate_file_evidence.tsv", file_rows, FILE_FIELDS
    )
    write_tsv(results / "group_lineage.tsv", group_rows, GROUP_FIELDS)
    write_tsv(
        results / "pair_observation_overlap.tsv", pair_rows, PAIR_FIELDS
    )
    write_tsv(
        results / "pipeline_anchor_evidence.tsv",
        anchor_rows,
        ANCHOR_FIELDS,
    )
    write_tsv(
        results / "referenced_asset_availability.tsv",
        asset_rows,
        ASSET_FIELDS,
    )
    write_tsv(
        results / "shared_dependency_ledger.tsv",
        dependency_rows,
        DEPENDENCY_FIELDS,
    )
    write_json(results / "audit_summary.json", summary)
    write_json(results / "run_environment.json", environment_summary())
    write_json(
        results / "EXECUTION_STATUS.json",
        {
            "audit_id": CONTRACT_ID,
            "status": SUCCESS_STATUS,
            "release_sufficiency_classification": classification,
            "evidence_level": INPUT_CANDIDATE_EVIDENCE_LEVEL,
            "direct_final_measurement_ancestry": (
                DIRECT_FINAL_MEASUREMENT_ANCESTRY
            ),
            "configuration_level_boundary": (
                CONFIGURATION_BOUNDARY_MARKER
            ),
            "executed_run_boundary": EXECUTED_RUN_BOUNDARY_MARKER,
        },
    )
    return summary
