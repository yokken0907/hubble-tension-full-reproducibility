#!/usr/bin/env python3
"""Core routines for the frozen H0DN SN Ia Phase 1E crosswalk audit."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import pathlib
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence


CONTRACT_ID = "H0DN-SNIA-SURVEY-CODE-CROSSWALK-PHASE1E-20260802-01"
CONTRACT_FREEZE_SHA256 = "b514495dd64beec5a3963bebb9bff8b8321957d55dba7812027c251c23d7753d"
SUCCESS_STATUS = "AUDIT_COMPLETE_TARGET_EXCLUDED_PUBLIC_INTERNAL_CROSSWALK_CLASSIFIED"
BOUNDARY_MARKER = (
    "PUBLIC_METADATA_CROSSWALK_ONLY_NO_UPSTREAM_RELABELING_"
    "NO_SURVEY_RANKING_NO_COVARIANCE_CHANGE_NO_CORRECTED_H0_"
    "NO_TENSION_RESOLUTION"
)
FROZEN_CROSSWALK_DIRECTORIES = (
    "CSPDR3_anthony",
    "CSP_data2",
    "SWIFT",
    "LOSS",
    "KAIT_DS15",
    "CfA3_DJ20",
    "PS1_LOWZ_COMBINED_TEXT_DS17",
)
TARGET_STATUS_SEMANTICS = {
    "UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK": {
        "preferred_label": "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_PUBLIC_INPUT_CANDIDATE",
        "meaning": (
            "Exactly one active public photometry input candidate matched the exact CID, "
            "inferred source directory, and accepted raw SURVEY vocabulary within the "
            "frozen seven-directory universe."
        ),
        "does_not_establish": [
            "direct ancestry to the final m_b_corr row",
            "identity of the exact light-curve fit output or FITRES row",
            "identity of the bias-correction run",
            "executed-run-to-final-catalog lineage",
            "statistical independence",
        ],
    },
    "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE": {
        "preferred_label": "NO_COMPATIBLE_CANDIDATE_UNDER_PHASE1D_FROZEN_CROSSWALK",
        "meaning": (
            "Legacy Phase 1D status under its frozen vocabulary; it does not mean that "
            "no public photometry file exists."
        ),
    },
}
INTERPRETIVE_SCOPE = {
    "target_application_preferred_label": (
        "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_PUBLIC_INPUT_CANDIDATE"
    ),
    "direct_final_measurement_ancestry_proven": False,
    "fit_output_lineage_proven": False,
    "bias_correction_run_lineage_proven": False,
    "executed_run_to_final_catalog_lineage_proven": False,
    "statistical_independence_proven": False,
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
PHASE1B_FIELDS = (
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "final_dependency_classification",
)
HOLDOUT_FIELDS = (
    "catalog_row_1based",
    "CID",
    "IDSURVEY",
    "USED_IN_SH0ES_HF",
    "all_directory_candidate_count",
    "candidate_directories",
    "candidate_SURVEY_headers",
    "candidate_paths",
    "anchor_status",
)
ANCHOR_FIELDS = (
    "catalog_row_1based",
    "CID",
    "IDSURVEY",
    "USED_IN_SH0ES_HF",
    "source_directory",
    "SURVEY",
    "path",
    "git_blob_sha1",
    "bytes",
    "sha256",
)
CROSSWALK_FIELDS = (
    "IDSURVEY",
    "official_label",
    "eligible_row_count",
    "anchor_row_count",
    "hubble_flow_anchor_row_count",
    "anchor_fraction",
    "distinct_source_directory_count",
    "inferred_source_directory",
    "inferred_SURVEY_headers",
    "support_status",
)
TARGET_FIELDS = (
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "phase1d_lineage_status",
    "inferred_source_directory",
    "inferred_SURVEY_headers",
    "candidate_count",
    "candidate_paths",
    "target_application_status",
)
TARGET_FILE_FIELDS = (
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "source_directory",
    "SURVEY",
    "path",
    "git_blob_sha1",
    "bytes",
    "sha256",
    "NOBS",
    "observation_line_count",
)
LABEL_FIELDS = (
    "IDSURVEY",
    "official_label",
    "official_CFA_token",
    "inferred_SURVEY_headers",
    "inferred_CFA_tokens",
    "diagnostic_classification",
    "interpretive_boundary",
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
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def write_tsv(path: pathlib.Path, rows: Iterable[dict[str, Any]], fields: Sequence[str]) -> None:
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


def read_tsv(path: pathlib.Path, expected_fields: Sequence[str] | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if expected_fields is not None and tuple(reader.fieldnames or ()) != tuple(expected_fields):
            raise AuditFailure(f"{path.name} schema mismatch")
        return list(reader)


def git_bytes(root: pathlib.Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    ).stdout


def git_text(root: pathlib.Path, *args: str) -> str:
    return git_bytes(root, *args).decode("utf-8").strip()


def normalize_repository(value: str) -> str:
    value = value.strip().removesuffix("/").removesuffix(".git")
    return value.lower()


def load_config(project: pathlib.Path) -> dict[str, Any]:
    value = read_json(project / "provenance/DECISION_CONFIG.json")
    if value.get("contract_id") != CONTRACT_ID:
        raise AuditFailure("decision-config contract identifier mismatch")
    return value


def verify_contract(project: pathlib.Path) -> dict[str, Any]:
    freeze_path = project / "provenance/CONTRACT_FREEZE.json"
    actual = sha256_file(freeze_path)
    freeze = read_json(freeze_path)
    sidecar = freeze_path.with_suffix(".sha256")
    checks = []
    for relative, record in sorted(freeze["files"].items()):
        path = project / relative
        size = path.stat().st_size if path.is_file() else None
        digest = sha256_file(path) if path.is_file() else None
        checks.append(
            {
                "path": relative,
                "expected_bytes": record["bytes"],
                "actual_bytes": size,
                "expected_sha256": record["sha256"],
                "actual_sha256": digest,
                "status": "PASS" if size == record["bytes"] and digest == record["sha256"] else "FAIL",
            }
        )
    chronology = (
        freeze.get("contract_id") == CONTRACT_ID
        and freeze.get("status")
        == "PROJECT_INTERNAL_PROSPECTIVE_HASH_FREEZE_BEFORE_COMPLETE_PHASE1E_SCAN"
        and freeze.get("complete_target_excluded_anchor_scan_observed_before_freeze") is False
        and freeze.get("complete_target_application_observed_before_freeze") is False
        and freeze.get("independent_verification_observed_before_freeze") is False
        and freeze.get("known_posthoc_hypotheses_disclosed") is True
    )
    expected_sidecar = f"{CONTRACT_FREEZE_SHA256}  {freeze_path.name}\n"
    passed = (
        actual == CONTRACT_FREEZE_SHA256
        and sidecar.is_file()
        and sidecar.read_text(encoding="utf-8") == expected_sidecar
        and chronology
        and all(item["status"] == "PASS" for item in checks)
    )
    return {
        "contract_id": CONTRACT_ID,
        "contract_freeze_sha256": actual,
        "chronology_status": "PASS" if chronology else "FAIL",
        "result_blindness": "NOT_BLIND_POSTHOC_HYPOTHESES_FULLY_DISCLOSED",
        "checks": checks,
        "status": "PASS" if passed else "FAIL",
    }


def verify_sources(project: pathlib.Path, repo: pathlib.Path) -> dict[str, Any]:
    config = load_config(project)
    expected = config["pantheonplus"]
    rows = read_tsv(project / "provenance/SOURCE_LOCK.tsv", SOURCE_FIELDS)
    repository_lock = read_json(project / "provenance/REPOSITORY_LOCK.json")
    head = git_text(repo, "rev-parse", "HEAD")
    origin = git_text(repo, "remote", "get-url", "origin")
    tree = git_text(repo, "rev-parse", f"{head}:{expected['photometry_root']}")
    file_checks = []
    for row in rows:
        data = git_bytes(repo, "show", f"{row['commit']}:{row['path']}")
        oid = git_text(repo, "rev-parse", f"{row['commit']}:{row['path']}")
        passed = (
            oid == row["git_blob_sha1"]
            and len(data) == int(row["bytes"])
            and sha256_bytes(data) == row["sha256"]
        )
        file_checks.append(
            {
                "path": row["path"],
                "expected_git_blob_sha1": row["git_blob_sha1"],
                "actual_git_blob_sha1": oid,
                "expected_bytes": int(row["bytes"]),
                "actual_bytes": len(data),
                "expected_sha256": row["sha256"],
                "actual_sha256": sha256_bytes(data),
                "status": "PASS" if passed else "FAIL",
            }
        )
    upstream_checks = []
    for key in (
        "phase1b_row_map_path",
        "phase1d_row_lineage_path",
        "phase1d_audit_summary_path",
    ):
        path = project / config["upstream"][key]
        expected_hash = config["upstream"][key.replace("_path", "_sha256")]
        actual_hash = sha256_file(path)
        upstream_checks.append(
            {
                "path": config["upstream"][key],
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "status": "PASS" if actual_hash == expected_hash else "FAIL",
            }
        )
    repository_pass = (
        head == expected["commit"] == repository_lock["expected_commit"]
        and normalize_repository(origin) == normalize_repository(expected["repository"])
        and tree == expected["photometry_tree_oid"] == repository_lock["photometry_tree_oid"]
        and len(rows) == repository_lock["locked_file_count"]
    )
    passed = (
        repository_pass
        and all(item["status"] == "PASS" for item in file_checks)
        and all(item["status"] == "PASS" for item in upstream_checks)
    )
    return {
        "repository": {
            "expected_commit": expected["commit"],
            "actual_commit": head,
            "expected_repository": normalize_repository(expected["repository"]),
            "actual_repository": normalize_repository(origin),
            "expected_photometry_tree_oid": expected["photometry_tree_oid"],
            "actual_photometry_tree_oid": tree,
            "status": "PASS" if repository_pass else "FAIL",
        },
        "source_lock_row_count": len(rows),
        "file_checks": file_checks,
        "upstream_compact_ledger_checks": upstream_checks,
        "status": "PASS" if passed else "FAIL",
    }


def git_tree_entries(root: pathlib.Path, commit: str, prefix: str) -> dict[str, dict[str, str]]:
    data = git_bytes(root, "ls-tree", "-r", "-z", commit, "--", prefix)
    entries: dict[str, dict[str, str]] = {}
    for item in data.split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split(" ")
        entries[raw_path.decode("utf-8")] = {"mode": mode, "type": object_type, "oid": oid}
    return entries


def active_list_entries(data: bytes) -> tuple[list[str], Counter[str]]:
    entries = []
    for raw in data.decode("utf-8").splitlines():
        value = raw.strip(" \t\r\n")
        if not value or value.startswith("#"):
            continue
        entries.append(value)
    return entries, Counter(entries)


def normalize_survey(value: str) -> str:
    return " ".join(value.strip(" \t\r\n").split())


def parse_photometry_blob(data: bytes) -> dict[str, Any]:
    lines = data.splitlines()
    headers = []
    for line in lines:
        if line.startswith(b"OBS:"):
            break
        headers.append(line)
    errors: list[str] = []

    def values(key: bytes) -> list[bytes]:
        return [line[len(key) :] for line in headers if line.startswith(key)]

    snids = values(b"SNID:")
    surveys = values(b"SURVEY:")
    nobs_values = values(b"NOBS:")
    if len(snids) != 1:
        errors.append(f"SNID_HEADER_COUNT_{len(snids)}")
    if len(surveys) != 1:
        errors.append(f"SURVEY_HEADER_COUNT_{len(surveys)}")
    if len(nobs_values) > 1:
        errors.append(f"NOBS_HEADER_COUNT_{len(nobs_values)}")
    try:
        snid = snids[0].decode("utf-8").strip(" \t") if len(snids) == 1 else None
        survey = normalize_survey(surveys[0].decode("utf-8")) if len(surveys) == 1 else None
    except UnicodeDecodeError:
        snid = None
        survey = None
        errors.append("HEADER_UTF8_DECODE_FAILURE")
    observations = [line for line in lines if line.startswith(b"OBS:")]
    nobs: int | None = None
    if len(nobs_values) == 1:
        try:
            nobs = int(nobs_values[0].decode("ascii").strip().split()[0])
            if nobs < 0:
                errors.append("NEGATIVE_NOBS")
            if nobs != len(observations):
                errors.append("NOBS_OBSERVATION_LINE_COUNT_MISMATCH")
        except (UnicodeDecodeError, ValueError, IndexError):
            errors.append("NOBS_PARSE_FAILURE")
    return {
        "SNID": snid,
        "SURVEY": survey,
        "NOBS": nobs,
        "observation_line_count": len(observations),
        "parse_errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }


def scan_photometry(repo: pathlib.Path, config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    commit = config["pantheonplus"]["commit"]
    root = config["pantheonplus"]["photometry_root"]
    tree = git_tree_entries(repo, commit, root)
    parsed_files: list[dict[str, Any]] = []
    directory_summaries = []
    for item in config["directory_inventory"]:
        directory = item["directory"]
        base = f"{root}/{directory}"
        list_path = f"{base}/{item['list_file']}"
        ignore_path = f"{base}/{item['ignore_file']}"
        listed, list_counts = active_list_entries(git_bytes(repo, "show", f"{commit}:{list_path}"))
        ignored, ignore_counts = active_list_entries(git_bytes(repo, "show", f"{commit}:{ignore_path}"))
        if any(count != 1 for count in list_counts.values()):
            raise AuditFailure(f"duplicate filename in {list_path}")
        active_count = 0
        ignored_count = 0
        parse_failures = []
        for filename in listed:
            if ignore_counts[filename]:
                ignored_count += 1
                continue
            path = f"{base}/{filename}"
            entry = tree.get(path)
            if entry is None or entry["type"] != "blob":
                raise AuditFailure(f"listed photometry blob missing: {path}")
            data = git_bytes(repo, "show", f"{commit}:{path}")
            parsed = parse_photometry_blob(data)
            parsed.update(
                {
                    "source_directory": directory,
                    "path": path,
                    "git_blob_sha1": entry["oid"],
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
            parsed_files.append(parsed)
            active_count += 1
            if parsed["status"] != "PASS":
                parse_failures.append(path)
        directory_summaries.append(
            {
                "directory": directory,
                "listed_filename_count": len(listed),
                "active_file_count": active_count,
                "ignored_filename_count": ignored_count,
                "parse_failure_count": len(parse_failures),
                "parse_failure_paths": parse_failures,
            }
        )
    summary = {
        "configured_directory_count": len(directory_summaries),
        "active_file_count": len(parsed_files),
        "parse_failure_count": sum(item["parse_failure_count"] for item in directory_summaries),
        "directories": directory_summaries,
        "status": "PASS" if not any(item["parse_failure_count"] for item in directory_summaries) else "FAIL",
    }
    return parsed_files, summary


def parse_catalog(data: bytes, config: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    text = data.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text), delimiter=" ", skipinitialspace=True)
    fields = tuple(reader.fieldnames or ())
    required = config["catalog_schema"]["required_columns"]
    if not all(name in fields for name in required):
        raise AuditFailure("catalog schema missing required fields")
    rows = list(reader)
    if len(rows) != config["catalog_schema"]["expected_row_count"]:
        raise AuditFailure("catalog row count mismatch")
    for index, row in enumerate(rows, 1):
        row["catalog_row_1based"] = str(index)
    return rows, {"row_count": len(rows), "column_count": len(fields), "required_columns": required, "status": "PASS"}


def parse_official_labels(readme: bytes, expected: dict[str, str]) -> tuple[dict[str, str], dict[str, Any]]:
    text = readme.decode("utf-8").replace("’", "'").replace("‘", "'")
    found: dict[str, str] = {}
    for code, label in expected.items():
        pattern = re.compile(rf"(?<!\d){re.escape(code)}\s*:\s*'([^']+)'", re.IGNORECASE)
        matches = pattern.findall(text)
        if len(matches) == 1:
            found[code] = matches[0]
        else:
            found[code] = ""
    passed = found == expected
    return found, {"expected": expected, "observed": found, "status": "PASS" if passed else "FAIL"}


def phase_populations(project: pathlib.Path, config: dict[str, Any]) -> tuple[set[str], list[dict[str, str]], dict[str, Any]]:
    phase1b = read_tsv(project / config["upstream"]["phase1b_row_map_path"], PHASE1B_FIELDS)
    cid_counts = Counter(row["CID"] for row in phase1b)
    excluded = {cid for cid, count in cid_counts.items() if count > 1}
    phase1d = read_tsv(project / config["upstream"]["phase1d_row_lineage_path"])
    codes = {str(code) for code in config["target"]["IDSURVEY_codes"]}
    targets = [
        row
        for row in phase1d
        if row["IDSURVEY"] in codes
        and row["lineage_status"] == config["target"]["required_phase1d_status"]
    ]
    by_code = Counter(row["IDSURVEY"] for row in targets)
    passed = (
        len(phase1b) == 277
        and len(excluded) == 30
        and len(phase1d) == 69
        and len(targets) == config["target"]["expected_row_count"]
        and dict(sorted(by_code.items())) == config["target"]["expected_rows_by_IDSURVEY"]
    )
    inventory = {
        "phase1b_row_count": len(phase1b),
        "excluded_multirow_CID_count": len(excluded),
        "phase1d_row_count": len(phase1d),
        "target_row_count": len(targets),
        "target_rows_by_IDSURVEY": dict(sorted(by_code.items())),
        "status": "PASS" if passed else "FAIL",
    }
    targets.sort(key=lambda row: int(row["h0dn_row_1based"]))
    return excluded, targets, inventory


def infer_crosswalks(
    catalog: list[dict[str, str]],
    excluded_cids: set[str],
    files: list[dict[str, Any]],
    labels: dict[str, str],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    codes = {str(code) for code in config["target"]["IDSURVEY_codes"]}
    catalog_counts = Counter(row["CID"] for row in catalog)
    by_snid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in files:
        if item["status"] == "PASS" and item["SNID"] is not None:
            by_snid[item["SNID"]].append(item)
    eligible = [
        row
        for row in catalog
        if row["IDSURVEY"] in codes
        and catalog_counts[row["CID"]] == 1
        and row["CID"] not in excluded_cids
    ]
    holdout_rows = []
    anchors = []
    for row in eligible:
        candidates = sorted(by_snid.get(row["CID"], []), key=lambda item: item["path"])
        status = "TARGET_EXCLUDED_UNIQUE_FILE_ANCHOR" if len(candidates) == 1 else (
            "NO_ACTIVE_FILE_ACROSS_DIRECTORY_UNIVERSE" if not candidates else "AMBIGUOUS_ACTIVE_FILES_ACROSS_DIRECTORY_UNIVERSE"
        )
        holdout_rows.append(
            {
                "catalog_row_1based": row["catalog_row_1based"],
                "CID": row["CID"],
                "IDSURVEY": row["IDSURVEY"],
                "USED_IN_SH0ES_HF": row["USED_IN_SH0ES_HF"],
                "all_directory_candidate_count": len(candidates),
                "candidate_directories": ";".join(item["source_directory"] for item in candidates),
                "candidate_SURVEY_headers": ";".join(item["SURVEY"] for item in candidates),
                "candidate_paths": ";".join(item["path"] for item in candidates),
                "anchor_status": status,
            }
        )
        if len(candidates) == 1:
            item = candidates[0]
            anchors.append(
                {
                    "catalog_row_1based": row["catalog_row_1based"],
                    "CID": row["CID"],
                    "IDSURVEY": row["IDSURVEY"],
                    "USED_IN_SH0ES_HF": row["USED_IN_SH0ES_HF"],
                    "source_directory": item["source_directory"],
                    "SURVEY": item["SURVEY"],
                    "path": item["path"],
                    "git_blob_sha1": item["git_blob_sha1"],
                    "bytes": item["bytes"],
                    "sha256": item["sha256"],
                }
            )
    holdout_rows.sort(key=lambda row: int(row["catalog_row_1based"]))
    anchors.sort(key=lambda row: int(row["catalog_row_1based"]))
    crosswalks = []
    rule = config["inference_rule"]
    for code in sorted(codes, key=int):
        eligible_code = [row for row in holdout_rows if row["IDSURVEY"] == code]
        selected = [row for row in anchors if row["IDSURVEY"] == code]
        directories = sorted({row["source_directory"] for row in selected})
        headers = sorted({row["SURVEY"] for row in selected})
        hf_count = sum(row["USED_IN_SH0ES_HF"] == "1" for row in selected)
        if len(directories) > rule["required_distinct_source_directory_count_per_code"]:
            status = config["classification"]["conflicting"]
        elif (
            len(selected) < rule["minimum_anchor_rows_per_code"]
            or hf_count < rule["minimum_hubble_flow_anchor_rows_per_code"]
            or len(directories) != rule["required_distinct_source_directory_count_per_code"]
        ):
            status = config["classification"]["insufficient"]
        else:
            status = config["classification"]["supported"]
        crosswalks.append(
            {
                "IDSURVEY": code,
                "official_label": labels[code],
                "eligible_row_count": len(eligible_code),
                "anchor_row_count": len(selected),
                "hubble_flow_anchor_row_count": hf_count,
                "anchor_fraction": f"{len(selected)}/{len(eligible_code)}",
                "distinct_source_directory_count": len(directories),
                "inferred_source_directory": directories[0] if len(directories) == 1 else "",
                "inferred_SURVEY_headers": ";".join(headers),
                "support_status": status,
            }
        )
    return holdout_rows, anchors, crosswalks


def apply_crosswalks(
    targets: list[dict[str, str]],
    files: list[dict[str, Any]],
    crosswalks: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mapping = {row["IDSURVEY"]: row for row in crosswalks}
    by_snid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in files:
        if item["status"] == "PASS" and item["SNID"] is not None:
            by_snid[item["SNID"]].append(item)
    target_rows = []
    evidence_rows = []
    for target in targets:
        rule = mapping[target["IDSURVEY"]]
        allowed_headers = set(filter(None, rule["inferred_SURVEY_headers"].split(";")))
        candidates = []
        if rule["support_status"] == config["classification"]["supported"]:
            candidates = sorted(
                [
                    item
                    for item in by_snid.get(target["CID"], [])
                    if item["source_directory"] == rule["inferred_source_directory"]
                    and item["SURVEY"] in allowed_headers
                ],
                key=lambda item: item["path"],
            )
        status = (
            config["classification"]["target_unique"]
            if len(candidates) == 1
            else config["classification"]["target_unresolved"]
        )
        target_rows.append(
            {
                "h0dn_row_1based": target["h0dn_row_1based"],
                "official_row_1based": target["official_row_1based"],
                "CID": target["CID"],
                "IDSURVEY": target["IDSURVEY"],
                "phase1d_lineage_status": target["lineage_status"],
                "inferred_source_directory": rule["inferred_source_directory"],
                "inferred_SURVEY_headers": rule["inferred_SURVEY_headers"],
                "candidate_count": len(candidates),
                "candidate_paths": ";".join(item["path"] for item in candidates),
                "target_application_status": status,
            }
        )
        for item in candidates:
            evidence_rows.append(
                {
                    "h0dn_row_1based": target["h0dn_row_1based"],
                    "official_row_1based": target["official_row_1based"],
                    "CID": target["CID"],
                    "IDSURVEY": target["IDSURVEY"],
                    "source_directory": item["source_directory"],
                    "SURVEY": item["SURVEY"],
                    "path": item["path"],
                    "git_blob_sha1": item["git_blob_sha1"],
                    "bytes": item["bytes"],
                    "sha256": item["sha256"],
                    "NOBS": item["NOBS"] if item["NOBS"] is not None else "",
                    "observation_line_count": item["observation_line_count"],
                }
            )
    target_rows.sort(key=lambda row: int(row["h0dn_row_1based"]))
    evidence_rows.sort(key=lambda row: (int(row["h0dn_row_1based"]), row["path"]))
    return target_rows, evidence_rows


def label_header_diagnostic(crosswalks: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, str]]:
    pattern = re.compile(config["label_header_diagnostic"]["CFA_token_regex"], re.IGNORECASE)
    rows = []
    selected_codes = {str(code) for code in config["label_header_diagnostic"]["comparison_codes"]}
    for crosswalk in crosswalks:
        if crosswalk["IDSURVEY"] not in selected_codes:
            continue
        official_tokens = sorted(set(pattern.findall(crosswalk["official_label"])))
        headers = list(filter(None, crosswalk["inferred_SURVEY_headers"].split(";")))
        inferred_tokens = sorted({token for header in headers for token in pattern.findall(header)})
        if not official_tokens or not inferred_tokens:
            classification = "CFA_TOKEN_NOT_COMPARABLE"
        elif {token.lower() for token in official_tokens} == {token.lower() for token in inferred_tokens}:
            classification = "PUBLIC_LABEL_RAW_HEADER_CFA_TOKEN_CONSISTENT"
        else:
            classification = "PUBLIC_LABEL_RAW_HEADER_CFA_TOKEN_MISMATCH"
        rows.append(
            {
                "IDSURVEY": crosswalk["IDSURVEY"],
                "official_label": crosswalk["official_label"],
                "official_CFA_token": ";".join(official_tokens),
                "inferred_SURVEY_headers": crosswalk["inferred_SURVEY_headers"],
                "inferred_CFA_tokens": ";".join(inferred_tokens),
                "diagnostic_classification": classification,
                "interpretive_boundary": "DESCRIPTIVE_METADATA_TENSION_ONLY_NO_SOURCE_RELABELING",
            }
        )
    return rows


def environment_summary() -> dict[str, str]:
    return {
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
    }


def run_audit(project: pathlib.Path, pantheonplus: pathlib.Path) -> dict[str, Any]:
    results = project / "results"
    results.mkdir(exist_ok=True)
    config = load_config(project)
    configured_directories = tuple(item["directory"] for item in config["directory_inventory"])
    if configured_directories != FROZEN_CROSSWALK_DIRECTORIES:
        raise AuditFailure("frozen seven-directory audit universe mismatch")
    contract = verify_contract(project)
    sources = verify_sources(project, pantheonplus)
    excluded_cids, targets, population = phase_populations(project, config)
    if contract["status"] != "PASS":
        raise AuditFailure("contract verification failed")
    if sources["status"] != "PASS":
        raise AuditFailure("source verification failed")
    if population["status"] != "PASS":
        raise AuditFailure("upstream target population mismatch")
    commit = config["pantheonplus"]["commit"]
    catalog, catalog_inventory = parse_catalog(
        git_bytes(pantheonplus, "show", f"{commit}:{config['pantheonplus']['catalog_path']}"),
        config,
    )
    labels, label_source = parse_official_labels(
        git_bytes(pantheonplus, "show", f"{commit}:{config['pantheonplus']['distance_readme_path']}"),
        config["official_labels"],
    )
    if label_source["status"] != "PASS":
        raise AuditFailure("official label source mismatch")
    files, scan = scan_photometry(pantheonplus, config)
    if scan["status"] != "PASS":
        raise AuditFailure("photometry parse failure")
    holdout, anchors, crosswalks = infer_crosswalks(catalog, excluded_cids, files, labels, config)
    target_rows, target_files = apply_crosswalks(targets, files, crosswalks, config)
    label_rows = label_header_diagnostic(crosswalks, config)
    support_counts = Counter(row["support_status"] for row in crosswalks)
    unique_count = sum(
        row["target_application_status"] == config["classification"]["target_unique"]
        for row in target_rows
    )
    if support_counts[config["classification"]["conflicting"]]:
        formal_status = config["classification"]["conflicting"]
    elif support_counts[config["classification"]["insufficient"]]:
        formal_status = config["classification"]["insufficient"]
    else:
        formal_status = SUCCESS_STATUS
    scientific_classification = (
        f"PUBLIC_INTERNAL_CROSSWALK_SUPPORTED_{support_counts[config['classification']['supported']]}_OF_3_"
        f"TARGET_ROWS_UNIQUE_{unique_count}_OF_{len(target_rows)}"
    )
    summary = {
        "audit_id": CONTRACT_ID,
        "boundary_marker": BOUNDARY_MARKER,
        "status": formal_status,
        "scientific_classification": scientific_classification,
        "result_blindness": "NOT_BLIND_POSTHOC_HYPOTHESES_FULLY_DISCLOSED",
        "catalog": catalog_inventory,
        "population": population,
        "photometry_scan": {
            "configured_directory_count": scan["configured_directory_count"],
            "active_file_count": scan["active_file_count"],
            "parse_failure_count": scan["parse_failure_count"],
        },
        "crosswalk_universe": {
            "classification": "PROSPECTIVELY_FROZEN_SEVEN_PUBLIC_PHOTOMETRY_DIRECTORIES",
            "configured_directory_count": len(FROZEN_CROSSWALK_DIRECTORIES),
            "directories": list(FROZEN_CROSSWALK_DIRECTORIES),
            "uniqueness_scope": "WITHIN_FROZEN_SEVEN_DIRECTORY_UNIVERSE_ONLY",
            "full_public_photometry_tree_uniqueness_claim": False,
            "external_archive_uniqueness_claim": False,
        },
        "target_excluded_inference": {
            "eligible_row_count": len(holdout),
            "anchor_row_count": len(anchors),
            "crosswalk_count": len(crosswalks),
            "support_status_counts": dict(sorted(support_counts.items())),
        },
        "target_application": {
            "target_row_count": len(target_rows),
            "unique_target_row_count": unique_count,
            "unresolved_target_row_count": len(target_rows) - unique_count,
            "candidate_evidence_row_count": len(target_files),
            "by_IDSURVEY": {
                code: {
                    "row_count": sum(row["IDSURVEY"] == code for row in target_rows),
                    "unique_count": sum(
                        row["IDSURVEY"] == code
                        and row["target_application_status"] == config["classification"]["target_unique"]
                        for row in target_rows
                    ),
                }
                for code in sorted({row["IDSURVEY"] for row in target_rows}, key=int)
            },
        },
        "official_label_source": label_source,
        "label_header_diagnostic_counts": dict(
            sorted(Counter(row["diagnostic_classification"] for row in label_rows).items())
        ),
        "interpretive_scope": INTERPRETIVE_SCOPE,
        "phase1d_preservation": {
            "phase1d_row_lineage_sha256": sha256_file(project / config["upstream"]["phase1d_row_lineage_path"]),
            "phase1d_main_result_changed": False,
            "relationship": "SUPPLEMENTARY_PHASE1E_RESULT_NO_RETROACTIVE_PHASE1D_REWRITE",
        },
        "nonclaims": [
            "no official SURVEY.DEF mapping claim",
            "no upstream row or label modification",
            "no direct ancestry from a compatible public input candidate to a final m_b_corr row",
            "no exact light-curve fit output or FITRES-row identity claim",
            "no bias-correction-run or executed-run-to-final-catalog lineage claim",
            "no statistical-independence claim",
            "no survey or object ranking",
            "no residual or influence analysis",
            "no covariance modification",
            "no corrected a_B, M_B, H0, or tension significance",
            "no causal explanation of the Phase 1A or Phase 1C result",
            "no new physics or Hubble-tension resolution claim"
        ],
    }
    write_json(results / "contract_verification.json", contract)
    write_json(results / "source_verification.json", sources)
    write_json(results / "catalog_and_target_inventory.json", {"catalog": catalog_inventory, "population": population})
    write_json(results / "photometry_scan_summary.json", scan)
    write_tsv(results / "holdout_candidate_rows.tsv", holdout, HOLDOUT_FIELDS)
    write_tsv(results / "holdout_anchor_evidence.tsv", anchors, ANCHOR_FIELDS)
    write_tsv(results / "inferred_crosswalk.tsv", crosswalks, CROSSWALK_FIELDS)
    write_tsv(results / "target_row_application.tsv", target_rows, TARGET_FIELDS)
    write_tsv(results / "target_candidate_file_evidence.tsv", target_files, TARGET_FILE_FIELDS)
    write_tsv(results / "label_header_diagnostic.tsv", label_rows, LABEL_FIELDS)
    write_json(results / "status_semantics.json", TARGET_STATUS_SEMANTICS)
    write_json(results / "audit_summary.json", summary)
    write_json(results / "run_environment.json", environment_summary())
    write_json(
        results / "EXECUTION_STATUS.json",
        {"audit_id": CONTRACT_ID, "status": formal_status, "scientific_classification": scientific_classification},
    )
    return summary
