#!/usr/bin/env python3
"""Core routines for the frozen H0DN SN Ia Phase 1F input-dependency audit."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Sequence


CONTRACT_ID = "H0DN-SNIA-CROSS-SERIES-INPUT-DEPENDENCY-PHASE1F-20260809-01"
CONTRACT_FREEZE_SHA256 = "3b1e1508d366151a0204f52d1d94e1e81e90454b1fb75fa085df3a17b44acd91"
SUCCESS_STATUS = "AUDIT_COMPLETE_PUBLIC_INPUT_DEPENDENCY_CLASSIFIED"
BOUNDARY_MARKER = (
    "PUBLIC_INPUT_AND_CONFIGURATION_EVIDENCE_ONLY_NO_FINAL_MEASUREMENT_ANCESTRY_"
    "NO_EXPOSURE_IDENTITY_NO_STATISTICAL_INDEPENDENCE_NO_REFIT_NO_COVARIANCE_CHANGE_"
    "NO_CORRECTED_H0_NO_TENSION_RESOLUTION"
)

SOURCE_FIELDS = (
    "source_id", "repository", "commit", "path", "git_blob_sha1", "bytes", "sha256"
)
CANDIDATE_FIELDS = (
    "h0dn_row_1based", "official_row_1based", "CID", "IDSURVEY", "survey_label",
    "candidate_path", "source_directory", "candidate_source_phase",
    "candidate_evidence_label", "direct_final_measurement_ancestry"
)
PROFILE_FIELDS = (
    "h0dn_row_1based", "official_row_1based", "CID", "IDSURVEY", "survey_label",
    "candidate_path", "source_directory", "git_blob_sha1", "bytes", "sha256",
    "raw_SURVEY", "PHOTOMETRY_VERSION", "FILTERS_header", "VARLIST", "NOBS",
    "observation_count", "used_filter_tokens", "used_filter_token_count",
    "active_list_status", "parse_status", "evidence_level",
    "direct_final_measurement_ancestry"
)
PAIR_FIELDS = (
    "CID", "h0dn_row_a_1based", "h0dn_row_b_1based", "IDSURVEY_a", "IDSURVEY_b",
    "source_directory_a", "source_directory_b", "candidate_path_a", "candidate_path_b",
    "distinct_file_blob", "observation_count_a", "observation_count_b",
    "byte_exact_observation_row_match_count", "rounding_compatible_edge_count",
    "mutual_unique_rounding_compatible_match_count", "ambiguous_rounding_compatible_edge_count",
    "near_payload_edge_count", "mutual_unique_near_payload_match_count",
    "primary_pair_classification", "evidence_level", "physical_exposure_identity",
    "statistical_independence", "direct_final_measurement_ancestry"
)
MATCH_FIELDS = (
    "CID", "h0dn_row_a_1based", "h0dn_row_b_1based", "observation_index_a_1based",
    "observation_index_b_1based", "filter_token_a", "filter_token_b",
    "payload_a_sha256", "payload_b_sha256", "absolute_mjd_delta_days",
    "mjd_rounding_intervals_overlap", "absolute_mjd_delta_le_0p11_day",
    "exact_filter_token_equal", "same_public_transmission_blob",
    "same_kcor_filter_definition", "match_classification", "evidence_boundary"
)
FILTER_FIELDS = (
    "h0dn_row_1based", "CID", "IDSURVEY", "source_directory", "raw_SURVEY",
    "used_filter_token", "observation_count_for_token", "kcor_input_path",
    "kcor_output_path", "kcor_output_git_blob_sha1", "definition_count",
    "kcor_declared_SURVEY", "kcor_filter_name", "kcor_MAGSYSTEM", "kcor_FILTSYSTEM",
    "kcor_FILTPATH", "transmission_basename", "public_transmission_path",
    "public_transmission_git_blob_sha1", "public_transmission_sha256",
    "mapping_classification", "evidence_level", "executed_run_lineage"
)
SERIES_FIELDS = (
    "source_directory", "candidate_row_count", "data_prep_task", "data_prep_block_found",
    "raw_dir_basename_match", "datawithsys_task", "datawithsys_block_found", "configured_MASK",
    "base_nml_reference", "base_nml_basename_match", "fitopts_reference",
    "kcor_alias", "kcor_alias_present", "salt2excal_present", "fitinplambda_present",
    "header_override_nom_present", "appendgaltype_present", "opt_sncid_list_present",
    "realdata_aggregation_token", "realdata_aggregation_membership",
    "configuration_anchor_status", "evidence_level", "executed_run_to_final_catalog_lineage"
)
ASSET_FIELDS = (
    "asset_role", "series", "referenced_value", "lookup_basename", "tracked_match_count",
    "tracked_candidate_paths", "availability_classification", "execution_identity"
)
DEPENDENCY_FIELDS = (
    "layer", "public_evidence", "availability", "evidence_level",
    "executed_run_to_final_catalog_lineage", "interpretive_boundary"
)


class AuditFailure(RuntimeError):
    """A frozen source, schema, or operational gate failed."""


@dataclass(frozen=True)
class PrintedDecimal:
    token: str
    value: Decimal
    half_ulp: Decimal

    @property
    def low(self) -> Decimal:
        return self.value - self.half_ulp

    @property
    def high(self) -> Decimal:
        return self.value + self.half_ulp


@dataclass
class Observation:
    index_1based: int
    raw_after_prefix: bytes
    tokens: dict[str, str]
    decimals: dict[str, PrintedDecimal]


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
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_tsv(path: pathlib.Path, rows: Iterable[dict[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), delimiter="\t", lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_tsv(path: pathlib.Path, expected_fields: Sequence[str] | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if expected_fields is not None and tuple(reader.fieldnames or ()) != tuple(expected_fields):
            raise AuditFailure(f"schema mismatch: {path.name}")
        return list(reader)


def git_bytes(root: pathlib.Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def git_text(root: pathlib.Path, *args: str) -> str:
    return git_bytes(root, *args).decode("utf-8").strip()


def normalize_repository(value: str) -> str:
    return value.strip().removesuffix("/").removesuffix(".git").lower()


def load_config(project: pathlib.Path) -> dict[str, Any]:
    value = read_json(project / "provenance/DECISION_CONFIG.json")
    if value.get("contract_id") != CONTRACT_ID:
        raise AuditFailure("decision-config contract identifier mismatch")
    return value


def verify_contract(project: pathlib.Path) -> dict[str, Any]:
    freeze_path = project / "provenance/CONTRACT_FREEZE.json"
    freeze = read_json(freeze_path)
    actual = sha256_file(freeze_path)
    checks = []
    for relative, expected in sorted(freeze["files"].items()):
        path = project / relative
        size = path.stat().st_size if path.is_file() else None
        digest = sha256_file(path) if path.is_file() else None
        passed = size == expected["bytes"] and digest == expected["sha256"]
        checks.append({"path": relative, "expected_bytes": expected["bytes"], "actual_bytes": size, "expected_sha256": expected["sha256"], "actual_sha256": digest, "status": "PASS" if passed else "FAIL"})
    chronology = (
        freeze.get("contract_id") == CONTRACT_ID
        and freeze.get("status") == "PROJECT_INTERNAL_PROSPECTIVE_HASH_FREEZE_BEFORE_COMPLETE_PHASE1F_SCAN"
        and freeze.get("complete_69_candidate_profile_observed_before_freeze") is False
        and freeze.get("complete_48_pair_scan_observed_before_freeze") is False
        and freeze.get("complete_filter_mapping_observed_before_freeze") is False
        and freeze.get("independent_verification_observed_before_freeze") is False
        and freeze.get("limited_examples_and_upstream_results_disclosed") is True
    )
    sidecar = freeze_path.with_suffix(".sha256")
    sidecar_ok = sidecar.is_file() and sidecar.read_text(encoding="utf-8") == f"{CONTRACT_FREEZE_SHA256}  {freeze_path.name}\n"
    passed = actual == CONTRACT_FREEZE_SHA256 and chronology and sidecar_ok and all(row["status"] == "PASS" for row in checks)
    return {
        "contract_id": CONTRACT_ID,
        "contract_freeze_sha256": actual,
        "chronology_status": "PASS" if chronology else "FAIL",
        "result_blindness": "PARTIALLY_RESULT_BLIND_LIMITED_EXAMPLES_AND_UPSTREAM_RESULTS_DISCLOSED",
        "checks": checks,
        "status": "PASS" if passed else "FAIL",
    }


def verify_sources(project: pathlib.Path, repo: pathlib.Path) -> dict[str, Any]:
    config = load_config(project)
    commit = config["pantheonplus"]["commit"]
    lock = read_json(project / "provenance/REPOSITORY_LOCK.json")
    head = git_text(repo, "rev-parse", "HEAD")
    origin = git_text(repo, "remote", "get-url", "origin")
    repository_checks = {
        "commit": head == commit == lock["expected_commit"],
        "origin": normalize_repository(origin) == normalize_repository(config["pantheonplus"]["repository"]),
        "photometry_tree": git_text(repo, "rev-parse", f"{commit}:{config['pantheonplus']['photometry_root']}") == config["pantheonplus"]["photometry_tree_oid"],
        "calibration_tree": git_text(repo, "rev-parse", f"{commit}:{config['pantheonplus']['calibration_root']}") == config["pantheonplus"]["calibration_tree_oid"],
        "salt2_tree": git_text(repo, "rev-parse", f"{commit}:{config['pantheonplus']['salt2_root']}") == config["pantheonplus"]["salt2_tree_oid"],
    }
    file_checks = []
    for row in read_tsv(project / "provenance/SOURCE_LOCK.tsv", SOURCE_FIELDS):
        data = git_bytes(repo, "show", f"{row['commit']}:{row['path']}")
        oid = git_text(repo, "rev-parse", f"{row['commit']}:{row['path']}")
        passed = oid == row["git_blob_sha1"] and len(data) == int(row["bytes"]) and sha256_bytes(data) == row["sha256"]
        file_checks.append({"path": row["path"], "expected_git_blob_sha1": row["git_blob_sha1"], "actual_git_blob_sha1": oid, "expected_bytes": int(row["bytes"]), "actual_bytes": len(data), "expected_sha256": row["sha256"], "actual_sha256": sha256_bytes(data), "status": "PASS" if passed else "FAIL"})
    tree_checks = []
    for row in read_tsv(project / "provenance/TREE_LOCK.tsv", ("path", "git_tree_sha1")):
        actual = git_text(repo, "rev-parse", f"{commit}:{row['path']}")
        tree_checks.append({"path": row["path"], "expected_git_tree_sha1": row["git_tree_sha1"], "actual_git_tree_sha1": actual, "status": "PASS" if actual == row["git_tree_sha1"] else "FAIL"})
    upstream_checks = []
    for path_key, hash_key in (
        ("phase1b_row_map_path", "phase1b_row_map_sha256"),
        ("phase1d_row_lineage_path", "phase1d_row_lineage_sha256"),
        ("phase1d_summary_path", "phase1d_summary_sha256"),
        ("phase1e_target_path", "phase1e_target_sha256"),
        ("phase1e_candidate_evidence_path", "phase1e_candidate_evidence_sha256"),
        ("phase1e_summary_path", "phase1e_summary_sha256"),
    ):
        path = project / config["upstream"][path_key]
        actual = sha256_file(path)
        expected = config["upstream"][hash_key]
        upstream_checks.append({"path": config["upstream"][path_key], "expected_sha256": expected, "actual_sha256": actual, "status": "PASS" if actual == expected else "FAIL"})
    dependency = read_json(project / "provenance/UPSTREAM_AUDIT_DEPENDENCIES.json")
    dependency_ok = (
        dependency["phase1d"]["actual_sha256"] == dependency["phase1d"]["expected_sha256"] == config["upstream"]["phase1d_archive_sha256"]
        and dependency["phase1d"]["sidecar_status"] == "PASS"
        and dependency["phase1e"]["actual_sha256"] == dependency["phase1e"]["expected_sha256"] == config["upstream"]["phase1e_archive_sha256"]
        and dependency["phase1e"]["sidecar_status"] == "PASS"
    )
    passed = all(repository_checks.values()) and dependency_ok and all(row["status"] == "PASS" for row in file_checks + tree_checks + upstream_checks)
    return {
        "repository_checks": repository_checks,
        "upstream_archive_dependency_status": "PASS" if dependency_ok else "FAIL",
        "source_lock_row_count": len(file_checks),
        "tree_lock_row_count": len(tree_checks),
        "file_checks": file_checks,
        "tree_checks": tree_checks,
        "upstream_compact_ledger_checks": upstream_checks,
        "status": "PASS" if passed else "FAIL",
    }


def parse_printed_decimal(token: str) -> PrintedDecimal:
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise AuditFailure(f"invalid decimal token: {token!r}") from exc
    if not value.is_finite():
        raise AuditFailure(f"non-finite decimal token: {token!r}")
    lowered = token.lower()
    if "e" in lowered:
        mantissa, exponent_text = lowered.split("e", 1)
        exponent = int(exponent_text)
    else:
        mantissa = lowered
        exponent = 0
    fraction_digits = len(mantissa.split(".", 1)[1]) if "." in mantissa else 0
    quantum = Decimal(1).scaleb(exponent - fraction_digits)
    return PrintedDecimal(token=token, value=value, half_ulp=abs(quantum) / 2)


def intervals_overlap(a: PrintedDecimal, b: PrintedDecimal) -> bool:
    return max(a.low, b.low) <= min(a.high, b.high)


def relative_difference(a: Decimal, b: Decimal) -> Decimal:
    return abs(a - b) / max(abs(a), abs(b), Decimal(1))


def payload_rounding_compatible(a: Observation, b: Observation, fields: Sequence[str]) -> bool:
    return all(intervals_overlap(a.decimals[field], b.decimals[field]) for field in fields)


def payload_near(a: Observation, b: Observation, config: dict[str, Any]) -> bool:
    flux_tolerance = Decimal(config["matching"]["near_flux_relative_tolerance"])
    mag_tolerance = Decimal(config["matching"]["near_mag_absolute_tolerance"])
    magerr_tolerance = Decimal(config["matching"]["near_magerr_absolute_tolerance"])
    return (
        relative_difference(a.decimals["FLUXCAL"].value, b.decimals["FLUXCAL"].value) <= flux_tolerance
        and relative_difference(a.decimals["FLUXCALERR"].value, b.decimals["FLUXCALERR"].value) <= flux_tolerance
        and abs(a.decimals["MAG"].value - b.decimals["MAG"].value) <= mag_tolerance
        and abs(a.decimals["MAGERR"].value - b.decimals["MAGERR"].value) <= magerr_tolerance
    )


def mutual_unique_edges(edges: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    degree_a = Counter(a for a, _ in edges)
    degree_b = Counter(b for _, b in edges)
    return sorted((a, b) for a, b in edges if degree_a[a] == 1 and degree_b[b] == 1)


def active_entries(data: bytes) -> tuple[list[str], Counter[str]]:
    values = []
    for raw in data.decode("utf-8").splitlines():
        value = raw.strip()
        if value and not value.startswith("#"):
            values.append(value)
    return values, Counter(values)


def build_candidate_map(project: pathlib.Path, config: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    phase1d = read_tsv(project / config["upstream"]["phase1d_row_lineage_path"])
    phase1e = read_tsv(project / config["upstream"]["phase1e_target_path"])
    phase1e_evidence = read_tsv(project / config["upstream"]["phase1e_candidate_evidence_path"])
    target_by_row = {row["h0dn_row_1based"]: row for row in phase1e}
    evidence_by_row = {row["h0dn_row_1based"]: row for row in phase1e_evidence}
    rows = []
    counts = Counter()
    for row in sorted(phase1d, key=lambda item: int(item["h0dn_row_1based"])):
        legacy = row["lineage_status"]
        if legacy == "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE":
            if row["active_candidate_count"] != "1" or not row["active_candidate_paths"] or ";" in row["active_candidate_paths"]:
                raise AuditFailure("Phase 1D unique-candidate schema mismatch")
            path = row["active_candidate_paths"]
            source_phase = "PHASE1D_ACCEPTED_CORRECTED"
            counts["phase1d"] += 1
        elif legacy == "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE":
            target = target_by_row.get(row["h0dn_row_1based"])
            evidence = evidence_by_row.get(row["h0dn_row_1based"])
            if target is None or evidence is None:
                raise AuditFailure("Phase 1E target missing for a Phase 1D unresolved row")
            identity_fields = ("official_row_1based", "CID", "IDSURVEY")
            if any(target[field] != row[field] or evidence[field] != row[field] for field in identity_fields):
                raise AuditFailure("Phase 1D/1E target identity mismatch")
            if target["candidate_count"] != "1" or not target["candidate_paths"] or ";" in target["candidate_paths"]:
                raise AuditFailure("Phase 1E candidate-count mismatch")
            if evidence["path"] != target["candidate_paths"]:
                raise AuditFailure("Phase 1E candidate evidence/path mismatch")
            path = target["candidate_paths"]
            source_phase = "PHASE1E_ACCEPTED_CORRECTED"
            counts["phase1e"] += 1
        else:
            raise AuditFailure(f"unexpected Phase 1D lineage status: {legacy}")
        parts = pathlib.PurePosixPath(path).parts
        try:
            source_directory = parts[parts.index("photometry") + 1]
        except (ValueError, IndexError) as exc:
            raise AuditFailure("candidate path is outside the frozen photometry layout") from exc
        rows.append({
            "h0dn_row_1based": row["h0dn_row_1based"],
            "official_row_1based": row["official_row_1based"],
            "CID": row["CID"],
            "IDSURVEY": row["IDSURVEY"],
            "survey_label": row["survey_label"],
            "candidate_path": path,
            "source_directory": source_directory,
            "candidate_source_phase": source_phase,
            "candidate_evidence_label": "FROZEN_PUBLIC_INPUT_CANDIDATE_NOT_FINAL_MEASUREMENT_ANCESTRY",
            "direct_final_measurement_ancestry": "NOT_ESTABLISHED",
        })
    cid_counts = Counter(row["CID"] for row in rows)
    pair_count = sum(count * (count - 1) // 2 for count in cid_counts.values())
    expected = config["expected_population"]
    passed = (
        len(rows) == expected["candidate_row_count"]
        and sum(count > 1 for count in cid_counts.values()) == expected["group_count"]
        and pair_count == expected["pair_count"]
        and counts["phase1d"] == expected["phase1d_candidate_count"]
        and counts["phase1e"] == expected["phase1e_candidate_count"]
        and set(row["source_directory"] for row in rows).issubset(
            set(item["directory"] for item in config["series"])
        )
    )
    inventory = {
        "candidate_row_count": len(rows),
        "same_CID_group_count": sum(count > 1 for count in cid_counts.values()),
        "within_group_pair_count": pair_count,
        "phase1d_candidate_count": counts["phase1d"],
        "phase1e_candidate_count": counts["phase1e"],
        "distinct_candidate_path_count": len({row["candidate_path"] for row in rows}),
        "status": "PASS" if passed else "FAIL",
    }
    return rows, inventory


def parse_photometry_blob(data: bytes, required_fields: Sequence[str]) -> dict[str, Any]:
    raw_lines = data.splitlines()
    header_lines = [line for line in raw_lines if not line.startswith(b"OBS:")]
    headers: dict[str, list[str]] = defaultdict(list)
    for line in header_lines:
        if b":" not in line or line.lstrip().startswith(b"#"):
            continue
        key, value = line.split(b":", 1)
        try:
            headers[key.decode("utf-8").strip()].append(value.decode("utf-8").strip())
        except UnicodeDecodeError as exc:
            raise AuditFailure("photometry header UTF-8 decode failure") from exc
    for key in ("SNID", "SURVEY", "VARLIST", "NOBS"):
        if len(headers.get(key, [])) != 1:
            raise AuditFailure(f"photometry header count mismatch for {key}")
    snid = headers["SNID"][0].split()[0]
    survey = " ".join(headers["SURVEY"][0].split())
    varlist = headers["VARLIST"][0].split()
    if len(varlist) != len(set(varlist)) or not all(field in varlist for field in required_fields):
        raise AuditFailure("photometry VARLIST missing or duplicating required fields")
    try:
        nobs = int(headers["NOBS"][0].split()[0])
    except (ValueError, IndexError) as exc:
        raise AuditFailure("photometry NOBS parse failure") from exc
    observations = []
    for index, raw in enumerate((line for line in raw_lines if line.startswith(b"OBS:")), 1):
        try:
            values = raw[len(b"OBS:"):].decode("utf-8").split()
        except UnicodeDecodeError as exc:
            raise AuditFailure("photometry OBS UTF-8 decode failure") from exc
        if len(values) != len(varlist):
            raise AuditFailure("photometry OBS/VARLIST field-count mismatch")
        tokens = dict(zip(varlist, values, strict=True))
        decimals = {field: parse_printed_decimal(tokens[field]) for field in required_fields if field != "FLT"}
        observations.append(Observation(index, raw[len(b"OBS:"):], tokens, decimals))
    if nobs != len(observations):
        raise AuditFailure("photometry NOBS/OBS count mismatch")
    return {
        "SNID": snid,
        "SURVEY": survey,
        "PHOTOMETRY_VERSION": headers.get("PHOTOMETRY_VERSION", [""])[0].split()[0] if headers.get("PHOTOMETRY_VERSION") else "",
        "FILTERS": headers.get("FILTERS", [""])[0].split()[0] if headers.get("FILTERS") else "",
        "VARLIST": varlist,
        "NOBS": nobs,
        "observations": observations,
    }


def profile_candidates(repo: pathlib.Path, candidates: list[dict[str, str]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    commit = config["pantheonplus"]["commit"]
    required = config["matching"]["required_observation_fields"]
    series_by_directory = {item["directory"]: item for item in config["series"]}
    list_cache: dict[str, tuple[Counter[str], Counter[str]]] = {}
    rows = []
    parsed_by_row: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        item = series_by_directory[candidate["source_directory"]]
        base = f"{config['pantheonplus']['photometry_root']}/{item['directory']}"
        if item["directory"] not in list_cache:
            _, listed = active_entries(git_bytes(repo, "show", f"{commit}:{base}/{item['list_file']}"))
            _, ignored = active_entries(git_bytes(repo, "show", f"{commit}:{base}/{item['ignore_file']}"))
            list_cache[item["directory"]] = listed, ignored
        listed, ignored = list_cache[item["directory"]]
        filename = pathlib.PurePosixPath(candidate["candidate_path"]).name
        active_ok = listed[filename] == 1 and ignored[filename] == 0
        if not active_ok:
            raise AuditFailure("candidate is not active under frozen LIST/IGNORE rules")
        data = git_bytes(repo, "show", f"{commit}:{candidate['candidate_path']}")
        oid = git_text(repo, "rev-parse", f"{commit}:{candidate['candidate_path']}")
        parsed = parse_photometry_blob(data, required)
        if parsed["SNID"] != candidate["CID"]:
            raise AuditFailure("candidate SNID/CID mismatch")
        token_counts = Counter(obs.tokens["FLT"] for obs in parsed["observations"])
        row = {
            **candidate,
            "git_blob_sha1": oid,
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "raw_SURVEY": parsed["SURVEY"],
            "PHOTOMETRY_VERSION": parsed["PHOTOMETRY_VERSION"],
            "FILTERS_header": parsed["FILTERS"],
            "VARLIST": ";".join(parsed["VARLIST"]),
            "NOBS": parsed["NOBS"],
            "observation_count": len(parsed["observations"]),
            "used_filter_tokens": ";".join(sorted(token_counts)),
            "used_filter_token_count": len(token_counts),
            "active_list_status": "PASS",
            "parse_status": "PASS",
            "evidence_level": "FROZEN_PUBLIC_INPUT_CANDIDATE_FILE_CONTENT",
        }
        rows.append(row)
        parsed_by_row[candidate["h0dn_row_1based"]] = {**parsed, "profile": row, "filter_counts": token_counts}
    rows.sort(key=lambda row: int(row["h0dn_row_1based"]))
    return rows, parsed_by_row


def parse_kcor_input(data: bytes) -> list[dict[str, str]]:
    state = {"SURVEY": "", "FILTPATH": "", "MAGSYSTEM": "", "FILTSYSTEM": ""}
    definitions = []
    for raw in data.decode("utf-8").splitlines():
        active = raw.split("#", 1)[0].strip()
        if not active or ":" not in active:
            continue
        key, value = active.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in state:
            state[key] = value.split()[0] if value else ""
        elif key == "FILTER":
            parts = value.split()
            if len(parts) < 3:
                raise AuditFailure("KCOR FILTER definition is too short")
            name, transmission = parts[0], parts[1]
            token = name.rsplit("/", 1)[1] if "/" in name else name.rsplit("-", 1)[1]
            definitions.append({
                "token": token,
                "filter_name": name,
                "transmission_basename": transmission,
                "calibration_expression": " ".join(parts[2:]),
                **state,
            })
    if not definitions:
        raise AuditFailure("KCOR input yielded no FILTER definitions")
    return definitions


def git_object_if_present(repo: pathlib.Path, commit: str, path: str) -> tuple[str, bytes] | None:
    try:
        oid = git_text(repo, "rev-parse", f"{commit}:{path}")
        data = git_bytes(repo, "show", f"{commit}:{path}")
    except subprocess.CalledProcessError:
        return None
    return oid, data


def map_filters(repo: pathlib.Path, profiles: list[dict[str, Any]], parsed_by_row: dict[str, dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    commit = config["pantheonplus"]["commit"]
    series_by_directory = {item["directory"]: item for item in config["series"]}
    definition_cache: dict[str, list[dict[str, str]]] = {}
    output_oid_cache: dict[str, str] = {}
    transmission_cache: dict[str, tuple[str, str] | None] = {}
    rows = []
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for profile in profiles:
        item = series_by_directory[profile["source_directory"]]
        kcor_input = item["kcor_input"]
        if kcor_input not in definition_cache:
            definition_cache[kcor_input] = parse_kcor_input(git_bytes(repo, "show", f"{commit}:{kcor_input}"))
        if item["kcor_output"] not in output_oid_cache:
            output_oid_cache[item["kcor_output"]] = git_text(repo, "rev-parse", f"{commit}:{item['kcor_output']}")
        for token, observation_count in sorted(parsed_by_row[profile["h0dn_row_1based"]]["filter_counts"].items()):
            matches = [definition for definition in definition_cache[kcor_input] if definition["token"] == token]
            definition = matches[0] if len(matches) == 1 else None
            public_path = ""
            transmission_oid = ""
            transmission_sha = ""
            if definition is not None:
                path_dir = pathlib.PurePosixPath(definition["FILTPATH"]).name
                public_path = f"{config['pantheonplus']['filters_root']}/{path_dir}/{definition['transmission_basename']}"
                if public_path not in transmission_cache:
                    found = git_object_if_present(repo, commit, public_path)
                    transmission_cache[public_path] = (found[0], sha256_bytes(found[1])) if found else None
                found_record = transmission_cache[public_path]
                if found_record:
                    transmission_oid, transmission_sha = found_record
            if len(matches) != 1:
                classification = "KCOR_FILTER_TOKEN_UNRESOLVED_OR_AMBIGUOUS"
            elif not transmission_oid:
                classification = "KCOR_FILTER_DEFINITION_WITHOUT_TRACKED_PUBLIC_TRANSMISSION_AT_IMPLIED_PATH"
            else:
                classification = "PUBLIC_KCOR_TEXT_AND_TRANSMISSION_ASSET_MAPPED"
            row = {
                "h0dn_row_1based": profile["h0dn_row_1based"],
                "CID": profile["CID"],
                "IDSURVEY": profile["IDSURVEY"],
                "source_directory": profile["source_directory"],
                "raw_SURVEY": profile["raw_SURVEY"],
                "used_filter_token": token,
                "observation_count_for_token": observation_count,
                "kcor_input_path": kcor_input,
                "kcor_output_path": item["kcor_output"],
                "kcor_output_git_blob_sha1": output_oid_cache[item["kcor_output"]],
                "definition_count": len(matches),
                "kcor_declared_SURVEY": definition["SURVEY"] if definition else "",
                "kcor_filter_name": definition["filter_name"] if definition else "",
                "kcor_MAGSYSTEM": definition["MAGSYSTEM"] if definition else "",
                "kcor_FILTSYSTEM": definition["FILTSYSTEM"] if definition else "",
                "kcor_FILTPATH": definition["FILTPATH"] if definition else "",
                "transmission_basename": definition["transmission_basename"] if definition else "",
                "public_transmission_path": public_path,
                "public_transmission_git_blob_sha1": transmission_oid,
                "public_transmission_sha256": transmission_sha,
                "mapping_classification": classification,
                "evidence_level": "PUBLIC_KCOR_TEXT_AND_TRACKED_ASSET_METADATA",
                "executed_run_lineage": "NOT_ESTABLISHED",
            }
            rows.append(row)
            lookup[(profile["h0dn_row_1based"], token)] = row
    rows.sort(key=lambda row: (int(row["h0dn_row_1based"]), row["used_filter_token"]))
    return rows, lookup


def exact_row_match_count(a: Sequence[Observation], b: Sequence[Observation]) -> int:
    left = Counter(obs.raw_after_prefix for obs in a)
    right = Counter(obs.raw_after_prefix for obs in b)
    return sum(min(count, right[value]) for value, count in left.items())


def payload_digest(obs: Observation, fields: Sequence[str]) -> str:
    value = "\x1f".join(obs.tokens[field] for field in fields).encode("utf-8")
    return sha256_bytes(value)


def compare_pairs(candidates: list[dict[str, str]], parsed_by_row: dict[str, dict[str, Any]], filter_lookup: dict[tuple[str, str], dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_cid: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidates:
        by_cid[row["CID"]].append(row)
    payload_fields = config["matching"]["payload_fields"]
    time_threshold = Decimal(config["matching"]["near_mjd_descriptor_days"])
    pair_rows = []
    match_rows = []
    for cid in sorted(by_cid):
        group = sorted(by_cid[cid], key=lambda row: int(row["h0dn_row_1based"]))
        for left_index in range(len(group)):
            for right_index in range(left_index + 1, len(group)):
                a_row, b_row = group[left_index], group[right_index]
                a = parsed_by_row[a_row["h0dn_row_1based"]]["observations"]
                b = parsed_by_row[b_row["h0dn_row_1based"]]["observations"]
                rounding_edges = [(i, j) for i, obs_a in enumerate(a) for j, obs_b in enumerate(b) if payload_rounding_compatible(obs_a, obs_b, payload_fields)]
                near_edges = [(i, j) for i, obs_a in enumerate(a) for j, obs_b in enumerate(b) if payload_near(obs_a, obs_b, config)]
                mutual = mutual_unique_edges(rounding_edges)
                mutual_near = mutual_unique_edges(near_edges)
                if len(mutual) >= 2:
                    classification = "REPEATED_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD"
                elif len(mutual) == 1:
                    classification = "SINGLE_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD"
                else:
                    classification = "NO_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD"
                pair_rows.append({
                    "CID": cid,
                    "h0dn_row_a_1based": a_row["h0dn_row_1based"],
                    "h0dn_row_b_1based": b_row["h0dn_row_1based"],
                    "IDSURVEY_a": a_row["IDSURVEY"],
                    "IDSURVEY_b": b_row["IDSURVEY"],
                    "source_directory_a": a_row["source_directory"],
                    "source_directory_b": b_row["source_directory"],
                    "candidate_path_a": a_row["candidate_path"],
                    "candidate_path_b": b_row["candidate_path"],
                    "distinct_file_blob": "YES" if a_row["candidate_path"] != b_row["candidate_path"] else "NO",
                    "observation_count_a": len(a),
                    "observation_count_b": len(b),
                    "byte_exact_observation_row_match_count": exact_row_match_count(a, b),
                    "rounding_compatible_edge_count": len(rounding_edges),
                    "mutual_unique_rounding_compatible_match_count": len(mutual),
                    "ambiguous_rounding_compatible_edge_count": len(rounding_edges) - len(mutual),
                    "near_payload_edge_count": len(near_edges),
                    "mutual_unique_near_payload_match_count": len(mutual_near),
                    "primary_pair_classification": classification,
                    "evidence_level": "PUBLISHED_PHOTOMETRY_PAYLOAD_COMPARISON",
                    "physical_exposure_identity": "NOT_ESTABLISHED",
                    "statistical_independence": "NOT_ESTABLISHED",
                    "direct_final_measurement_ancestry": "NOT_ESTABLISHED",
                })
                for i, j in mutual:
                    obs_a, obs_b = a[i], b[j]
                    map_a = filter_lookup.get((a_row["h0dn_row_1based"], obs_a.tokens["FLT"]), {})
                    map_b = filter_lookup.get((b_row["h0dn_row_1based"], obs_b.tokens["FLT"]), {})
                    delta = abs(obs_a.decimals["MJD"].value - obs_b.decimals["MJD"].value)
                    same_blob = bool(map_a.get("public_transmission_git_blob_sha1")) and map_a.get("public_transmission_git_blob_sha1") == map_b.get("public_transmission_git_blob_sha1")
                    same_definition = bool(map_a.get("kcor_filter_name")) and (map_a.get("kcor_input_path"), map_a.get("kcor_filter_name")) == (map_b.get("kcor_input_path"), map_b.get("kcor_filter_name"))
                    match_rows.append({
                        "CID": cid,
                        "h0dn_row_a_1based": a_row["h0dn_row_1based"],
                        "h0dn_row_b_1based": b_row["h0dn_row_1based"],
                        "observation_index_a_1based": obs_a.index_1based,
                        "observation_index_b_1based": obs_b.index_1based,
                        "filter_token_a": obs_a.tokens["FLT"],
                        "filter_token_b": obs_b.tokens["FLT"],
                        "payload_a_sha256": payload_digest(obs_a, payload_fields),
                        "payload_b_sha256": payload_digest(obs_b, payload_fields),
                        "absolute_mjd_delta_days": format(delta, "f"),
                        "mjd_rounding_intervals_overlap": "YES" if intervals_overlap(obs_a.decimals["MJD"], obs_b.decimals["MJD"]) else "NO",
                        "absolute_mjd_delta_le_0p11_day": "YES" if delta <= time_threshold else "NO",
                        "exact_filter_token_equal": "YES" if obs_a.tokens["FLT"] == obs_b.tokens["FLT"] else "NO",
                        "same_public_transmission_blob": "YES" if same_blob else "NO",
                        "same_kcor_filter_definition": "YES" if same_definition else "NO",
                        "match_classification": "MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD_MATCH",
                        "evidence_boundary": "PUBLISHED_NUMERIC_PAYLOAD_REUSE_OR_AGREEMENT_NOT_PHYSICAL_EXPOSURE_IDENTITY",
                    })
    pair_rows.sort(key=lambda row: (row["CID"], int(row["h0dn_row_a_1based"]), int(row["h0dn_row_b_1based"])))
    match_rows.sort(key=lambda row: (row["CID"], int(row["h0dn_row_a_1based"]), int(row["h0dn_row_b_1based"]), int(row["observation_index_a_1based"]), int(row["observation_index_b_1based"])))
    return pair_rows, match_rows


def top_level_section(text: str, name: str) -> str:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line == f"{name}:"), None)
    if start is None:
        raise AuditFailure(f"PPLUS top-level section missing: {name}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i] and not lines[i][0].isspace() and re.match(r"^[A-Z][A-Z0-9_]*:$", lines[i])), len(lines))
    return "\n".join(lines[start + 1:end])


def task_block(section: str, task: str) -> str:
    lines = section.splitlines()
    pattern = re.compile(rf"^  {re.escape(task)}:\s*(?:#.*)?$")
    start = next((i for i, line in enumerate(lines) if pattern.match(line)), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^  [A-Za-z0-9_+.-]+:\s*(?:#.*)?$", lines[i])), len(lines))
    return "\n".join(lines[start:end])


def capture_first(block: str, key: str) -> str:
    match = re.search(rf"^\s+{re.escape(key)}:\s*(.+?)\s*$", block, flags=re.MULTILINE)
    return match.group(1).split("#", 1)[0].strip() if match else ""


def audit_series_configuration(repo: pathlib.Path, profiles: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    commit = config["pantheonplus"]["commit"]
    text = git_bytes(repo, "show", f"{commit}:{config['pantheonplus']['pipeline_config_path']}").decode("utf-8")
    dataprep = top_level_section(text, "DATAPREP")
    lcfit = top_level_section(text, "LCFIT")
    biascor = top_level_section(text, "BIASCOR")
    realdata = task_block(biascor, "REALDATABS20NOM")
    counts = Counter(row["source_directory"] for row in profiles)
    rows = []
    for item in config["series"]:
        prep_block = task_block(dataprep, item["data_prep_task"])
        fit_block = task_block(lcfit, item["datawithsys_task"])
        raw_dir = capture_first(prep_block, "RAW_DIR")
        base = capture_first(fit_block, "BASE")
        fitopts_match = re.search(r"^\s+-\s+([^\n]*ALL\.fitopts)\s*$", fit_block, flags=re.MULTILINE)
        fitopts = fitopts_match.group(1).strip() if fitopts_match else ""
        aggregate_token = f"{item['datawithsys_task']}_{item['data_prep_task']}"
        checks = {
            "prep": bool(prep_block),
            "raw": pathlib.PurePosixPath(raw_dir).name == item["directory"],
            "fit": bool(fit_block),
            "base": pathlib.PurePosixPath(base).name == item["lcfitting_base_basename"],
            "fitopts": bool(fitopts),
            "kcor": f"<<: *{item['kcor_alias']}" in fit_block,
            "salt2": "<<: *salt2excal" in fit_block,
            "lambda": "<<: *fitinplambda" in fit_block,
            "override": "<<: *header_override_nom" in fit_block,
            "appendgaltype": "<<: *appendgaltype" in fit_block,
            "sncid": "<<: *opt_sncid_list" in fit_block,
            "aggregation": aggregate_token in realdata,
        }
        rows.append({
            "source_directory": item["directory"],
            "candidate_row_count": counts[item["directory"]],
            "data_prep_task": item["data_prep_task"],
            "data_prep_block_found": "YES" if checks["prep"] else "NO",
            "raw_dir_basename_match": "YES" if checks["raw"] else "NO",
            "datawithsys_task": item["datawithsys_task"],
            "datawithsys_block_found": "YES" if checks["fit"] else "NO",
            "configured_MASK": capture_first(fit_block, "MASK"),
            "base_nml_reference": base,
            "base_nml_basename_match": "YES" if checks["base"] else "NO",
            "fitopts_reference": fitopts,
            "kcor_alias": item["kcor_alias"],
            "kcor_alias_present": "YES" if checks["kcor"] else "NO",
            "salt2excal_present": "YES" if checks["salt2"] else "NO",
            "fitinplambda_present": "YES" if checks["lambda"] else "NO",
            "header_override_nom_present": "YES" if checks["override"] else "NO",
            "appendgaltype_present": "YES" if checks["appendgaltype"] else "NO",
            "opt_sncid_list_present": "YES" if checks["sncid"] else "NO",
            "realdata_aggregation_token": aggregate_token,
            "realdata_aggregation_membership": "YES" if checks["aggregation"] else "NO",
            "configuration_anchor_status": "PASS" if all(checks.values()) else "FAIL",
            "evidence_level": "PPLUS_YML_CONFIGURATION_LEVEL",
            "executed_run_to_final_catalog_lineage": "NOT_ESTABLISHED",
        })
    return rows


def public_asset_availability(repo: pathlib.Path, series_rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, str]]:
    commit = config["pantheonplus"]["commit"]
    all_paths = git_text(repo, "ls-tree", "-r", "--name-only", commit).splitlines()
    records: list[tuple[str, str, str, str]] = []
    for row in series_rows:
        records.append(("LCFIT_BASE_NML", row["source_directory"], row["base_nml_reference"], pathlib.PurePosixPath(row["base_nml_reference"]).name))
    records.extend([
        ("COMMON_FITOPTS", "ALL_SERIES", "$PS1_USERS/dscolnic/PANTHEON+/kcor/fitopt_v6_1/ALL.fitopts", "ALL.fitopts"),
        ("COMMON_SALT2_MODEL_INFO", "ALL_SERIES", "$PANTHEONPLUS/submit_trainSALT2/out_train_v7_1_bd17fix/SALT2.MODEL000", "SALT2.INFO"),
        ("DOWNSTREAM_SALT2MU_BASE", "ALL_SERIES", "/project2/rkessler/SURVEYS/PS1MD/USERS/dscolnic/PANTHEON+/salt2muinputs/SALT2muH0_data_foranthony.input", "SALT2muH0_data_foranthony.input"),
    ])
    for name in ("HOSTGAL_LOGMASS", "HOSTGAL_sSFR", "VPEC", "VPEC_ERR", "REDSHIFT_CMB", "REDSHIFT_CMB_ERR"):
        records.append(("COMMON_HEADER_OVERRIDE", "ALL_SERIES", f"$overrides/nominal/{name}.txt", f"{name}.txt"))
    rows = []
    for role, series, reference, basename in records:
        matches = sorted(path for path in all_paths if pathlib.PurePosixPath(path).name == basename)
        if matches:
            classification = "TRACKED_PUBLIC_BASENAME_CANDIDATE_NO_EXECUTION_IDENTITY"
        else:
            classification = "NOT_TRACKED_IN_FIXED_RELEASE_BY_BASENAME"
        rows.append({
            "asset_role": role,
            "series": series,
            "referenced_value": reference,
            "lookup_basename": basename,
            "tracked_match_count": len(matches),
            "tracked_candidate_paths": ";".join(matches),
            "availability_classification": classification,
            "execution_identity": "NOT_ESTABLISHED",
        })
    rows.sort(key=lambda row: (row["asset_role"], row["series"], row["lookup_basename"]))
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
    contract = verify_contract(project)
    sources = verify_sources(project, pantheonplus)
    if contract["status"] != "PASS":
        raise AuditFailure("contract verification failed")
    if sources["status"] != "PASS":
        raise AuditFailure("source verification failed")
    candidates, inventory = build_candidate_map(project, config)
    if inventory["status"] != "PASS":
        raise AuditFailure("candidate population mismatch")
    profiles, parsed = profile_candidates(pantheonplus, candidates, config)
    filter_rows, filter_lookup = map_filters(pantheonplus, profiles, parsed, config)
    pair_rows, match_rows = compare_pairs(candidates, parsed, filter_lookup, config)
    series_rows = audit_series_configuration(pantheonplus, profiles, config)
    asset_rows = public_asset_availability(pantheonplus, series_rows, config)
    if len(pair_rows) != config["expected_population"]["pair_count"]:
        raise AuditFailure("pair universe mismatch")

    pair_classes = Counter(row["primary_pair_classification"] for row in pair_rows)
    filter_classes = Counter(row["mapping_classification"] for row in filter_rows)
    exact_pair_count = sum(int(row["byte_exact_observation_row_match_count"]) > 0 for row in pair_rows)
    repeated_pair_count = pair_classes["REPEATED_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD"]
    single_pair_count = pair_classes["SINGLE_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD"]
    config_pass_count = sum(row["configuration_anchor_status"] == "PASS" for row in series_rows)
    mapped_filter_record_count = filter_classes["PUBLIC_KCOR_TEXT_AND_TRANSMISSION_ASSET_MAPPED"]
    unique_filter_record_count = len(filter_rows)
    mapped_observation_count = sum(int(row["observation_count_for_token"]) for row in filter_rows if row["mapping_classification"] == "PUBLIC_KCOR_TEXT_AND_TRANSMISSION_ASSET_MAPPED")
    total_observation_count = sum(row["observation_count"] for row in profiles)

    release_classification = (
        "PUBLIC_RELEASE_SUPPORTS_BOUNDED_INPUT_DEPENDENCY_CLASSIFICATION_"
        "EXECUTED_RUN_TO_FINAL_CATALOG_LINEAGE_NOT_ESTABLISHED"
    )
    scientific_classification = (
        f"PUBLIC_INPUT_DEPENDENCIES_CLASSIFIED_"
        f"REPEATED_PAYLOAD_PAIRS_{repeated_pair_count}_OF_{len(pair_rows)}_"
        f"SINGLE_PAYLOAD_PAIRS_{single_pair_count}_OF_{len(pair_rows)}_"
        f"FILTER_RECORDS_MAPPED_{mapped_filter_record_count}_OF_{unique_filter_record_count}_"
        f"CONFIG_SERIES_PASS_{config_pass_count}_OF_{len(series_rows)}"
    )
    dependency_rows = [
        {
            "layer": "ASTROPHYSICAL_EVENT_IDENTITY",
            "public_evidence": f"{inventory['same_CID_group_count']} exact-CID groups and {inventory['candidate_row_count']} fixed rows",
            "availability": "COMPLETE_FOR_FROZEN_AUDIT_POPULATION",
            "evidence_level": "UPSTREAM_IDENTIFIER_LEVEL",
            "executed_run_to_final_catalog_lineage": "NOT_ESTABLISHED",
            "interpretive_boundary": "same CID identifies the same event but does not imply independent or shared measurements",
        },
        {
            "layer": "PUBLIC_INPUT_CANDIDATE_FILES",
            "public_evidence": f"{len(profiles)} parsed candidates; {inventory['distinct_candidate_path_count']} distinct paths",
            "availability": "COMPLETE_FOR_FROZEN_CANDIDATE_MAP",
            "evidence_level": "PUBLIC_FILE_CONTENT",
            "executed_run_to_final_catalog_lineage": "NOT_ESTABLISHED",
            "interpretive_boundary": "candidate compatibility is not final m_b_corr or FITRES ancestry",
        },
        {
            "layer": "PUBLISHED_PHOTOMETRIC_PAYLOAD_REUSE",
            "public_evidence": json.dumps(dict(sorted(pair_classes.items())), sort_keys=True, separators=(",", ":")),
            "availability": f"{len(pair_rows)} of {config['expected_population']['pair_count']} pairs classified; exact-row-positive pairs={exact_pair_count}",
            "evidence_level": "PUBLISHED_NUMERIC_PAYLOAD_COMPARISON",
            "executed_run_to_final_catalog_lineage": "NOT_ESTABLISHED",
            "interpretive_boundary": "payload equality or compatibility is not physical exposure identity or causal covariance",
        },
        {
            "layer": "FILTER_AND_CALIBRATION_DEFINITION",
            "public_evidence": json.dumps(dict(sorted(filter_classes.items())), sort_keys=True, separators=(",", ":")),
            "availability": f"mapped observations={mapped_observation_count}/{total_observation_count}",
            "evidence_level": "PUBLIC_KCOR_TEXT_AND_TRACKED_ASSET_METADATA",
            "executed_run_to_final_catalog_lineage": "NOT_ESTABLISHED",
            "interpretive_boundary": "text-to-asset mapping does not prove KCOR FITS generation or use in the final run",
        },
        {
            "layer": "SERIES_SPECIFIC_KCOR_CONFIGURATION",
            "public_evidence": f"7 series reference {len({item['kcor_input'] for item in config['series']})} distinct KCOR inputs",
            "availability": "DOCUMENTED_IN_ACTIVE_PPLUS_YML_AND_TRACKED_PUBLIC_ASSETS",
            "evidence_level": "CONFIGURATION_LEVEL",
            "executed_run_to_final_catalog_lineage": "NOT_ESTABLISHED",
            "interpretive_boundary": "configured differences do not establish measurement differences or effects",
        },
        {
            "layer": "COMMON_LIGHT_CURVE_FIT_CONFIGURATION",
            "public_evidence": f"{config_pass_count}/{len(series_rows)} active series blocks pass frozen anchors",
            "availability": "DOCUMENTED_IN_PUBLIC_PPLUS_YML",
            "evidence_level": "CONFIGURATION_LEVEL",
            "executed_run_to_final_catalog_lineage": "NOT_ESTABLISHED",
            "interpretive_boundary": "common SALT2/configuration references are not a run manifest or a causal explanation",
        },
        {
            "layer": "COMMON_REALDATA_BIASCOR_AGGREGATION",
            "public_evidence": f"{sum(row['realdata_aggregation_membership'] == 'YES' for row in series_rows)}/{len(series_rows)} series tokens in REALDATABS20NOM DATA",
            "availability": "DOCUMENTED_IN_PUBLIC_PPLUS_YML",
            "evidence_level": "CONFIGURATION_LEVEL",
            "executed_run_to_final_catalog_lineage": "NOT_ESTABLISHED",
            "interpretive_boundary": "configured convergence does not identify the executed bias-correction run or final-row ancestry",
        },
        {
            "layer": "EXECUTION_ASSET_CLOSURE",
            "public_evidence": json.dumps(dict(sorted(Counter(row["availability_classification"] for row in asset_rows).items())), sort_keys=True, separators=(",", ":")),
            "availability": "PARTIAL_PUBLIC_ANALOGUES_AND_MISSING_REFERENCED_BASENAMES",
            "evidence_level": "RELEASE_SUFFICIENCY_LEVEL",
            "executed_run_to_final_catalog_lineage": "NOT_ESTABLISHED",
            "interpretive_boundary": "a missing or differently located public asset is not evidence that the original collaboration lacked it or that the analysis was wrong",
        },
    ]
    summary = {
        "audit_id": CONTRACT_ID,
        "boundary_marker": BOUNDARY_MARKER,
        "status": SUCCESS_STATUS,
        "scientific_classification": scientific_classification,
        "public_release_classification": release_classification,
        "result_blindness": "PARTIALLY_RESULT_BLIND_LIMITED_EXAMPLES_AND_UPSTREAM_RESULTS_DISCLOSED",
        "population": inventory,
        "row_profiles": {
            "row_count": len(profiles),
            "total_observation_count": total_observation_count,
            "distinct_file_blob_count": len({row["git_blob_sha1"] for row in profiles}),
            "source_directory_counts": dict(sorted(Counter(row["source_directory"] for row in profiles).items())),
        },
        "pair_comparison": {
            "pair_count": len(pair_rows),
            "class_counts": dict(sorted(pair_classes.items())),
            "byte_exact_positive_pair_count": exact_pair_count,
            "mutual_unique_rounding_match_record_count": len(match_rows),
            "physical_exposure_identity_proven": False,
            "statistical_independence_proven": False,
        },
        "filter_calibration": {
            "row_filter_record_count": len(filter_rows),
            "class_counts": dict(sorted(filter_classes.items())),
            "mapped_observation_count": mapped_observation_count,
            "total_observation_count": total_observation_count,
            "kcor_input_count": len({row["kcor_input_path"] for row in filter_rows}),
            "transmission_blob_count": len({row["public_transmission_git_blob_sha1"] for row in filter_rows if row["public_transmission_git_blob_sha1"]}),
            "kcor_fits_generation_proven": False,
        },
        "configuration_lineage": {
            "series_count": len(series_rows),
            "passing_series_count": config_pass_count,
            "all_series_aggregate_membership_count": sum(row["realdata_aggregation_membership"] == "YES" for row in series_rows),
            "executed_run_to_final_catalog_lineage_proven": False,
        },
        "asset_availability": {
            "record_count": len(asset_rows),
            "class_counts": dict(sorted(Counter(row["availability_classification"] for row in asset_rows).items())),
            "execution_identity_proven": False,
        },
        "upstream_preservation": {
            "phase1d_main_result_changed": False,
            "phase1e_main_result_changed": False,
            "relationship": "SUPPLEMENTARY_PHASE1F_RESULT_NO_RETROACTIVE_PHASE1D_OR_PHASE1E_REWRITE",
        },
        "nonclaims": [
            "no direct final-m_b_corr, FITRES, bias-correction-run, or executed-run ancestry claim",
            "no physical exposure identity or statistical-independence claim",
            "no light-curve re-fit or SALT2 parameter recomputation",
            "no row deletion, merge, averaging, reweighting, relabelling, or correction",
            "no survey, object, residual, or influence ranking",
            "no covariance modification or correction recommendation",
            "no corrected a_B, M_B, H0, or tension significance",
            "no causal explanation of the Phase 1A or Phase 1C low-dispersion flag",
            "no new physics or Hubble-tension resolution claim",
        ],
    }
    semantics = {
        "FROZEN_PUBLIC_INPUT_CANDIDATE_NOT_FINAL_MEASUREMENT_ANCESTRY": "A public file selected by the separately frozen Phase 1D/1E metadata rules; it is not a proven final-row ancestor.",
        "MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD_MATCH": "A one-to-one published numeric-payload compatibility under displayed precision; not physical exposure identity.",
        "PUBLIC_KCOR_TEXT_AND_TRANSMISSION_ASSET_MAPPED": "One text FILTER definition and its tracked transmission basename were found; no KCOR-grid generation or final-run use is proven.",
        "CONFIGURATION_LEVEL": "Active public configuration text only; no executed-run hash chain.",
    }
    write_json(results / "contract_verification.json", contract)
    write_json(results / "source_verification.json", sources)
    write_json(results / "input_inventory.json", inventory)
    write_tsv(results / "input_candidate_map.tsv", candidates, CANDIDATE_FIELDS)
    write_tsv(results / "row_input_profile.tsv", profiles, PROFILE_FIELDS)
    write_tsv(results / "pair_dependency_classification.tsv", pair_rows, PAIR_FIELDS)
    write_tsv(results / "observation_match_evidence.tsv", match_rows, MATCH_FIELDS)
    write_tsv(results / "filter_calibration_mapping.tsv", filter_rows, FILTER_FIELDS)
    write_tsv(results / "series_configuration_lineage.tsv", series_rows, SERIES_FIELDS)
    write_tsv(results / "public_asset_availability.tsv", asset_rows, ASSET_FIELDS)
    write_tsv(results / "shared_dependency_ledger.tsv", dependency_rows, DEPENDENCY_FIELDS)
    write_json(results / "evidence_semantics.json", semantics)
    write_json(results / "audit_summary.json", summary)
    write_json(results / "run_environment.json", environment_summary())
    write_json(results / "EXECUTION_STATUS.json", {"audit_id": CONTRACT_ID, "status": SUCCESS_STATUS, "scientific_classification": scientific_classification, "public_release_classification": release_classification})
    return summary
