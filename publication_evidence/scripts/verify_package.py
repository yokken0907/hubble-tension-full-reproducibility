#!/usr/bin/env python3
"""Verify package integrity, public-evidence coverage, and scope boundaries."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_MASTERS = {
    "FIRST_MASTER": (
        "HUBBLE_TENSION_FIRST_SEASON_MASTER_REFERENCE_PACKAGE_v1.0.0.zip",
        "3e6df9f557485de1bb21c54bb129af78943e8e5d08da036e648d251dd952663c",
    ),
    "SECOND_MASTER": (
        "HUBBLE_TENSION_SECOND_SEASON_MASTER_REFERENCE_PACKAGE_v1.0.0.zip",
        "cc15c96a45865f22fcd13c2ef03c8cccc39af8fa6dcace4a25f229d07e964940",
    ),
    "CROSS_SEASON_MASTER": (
        "HUBBLE_TENSION_CROSS_SEASON_AUDIT_PACKAGE_v0.1.0.zip",
        "9719fae4cbfefeca5ec9e8f04f7949f1a1bdb21d784523752a587ecd166e60cf",
    ),
    "FINAL_VALIDATION_MASTER": (
        "HUBBLE_TENSION_FINAL_INTERNAL_VALIDATION_AND_CLOSURE_AUDIT_PACKAGE_v0.1.0.zip",
        "db70c27daa85eb1daf907aeedd644c2d0f0cb3a262c121b28431d15c7b95fb2f",
    ),
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_member(relative: str) -> pathlib.Path:
    candidate = pathlib.PurePosixPath(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe package path: {relative}")
    return ROOT.joinpath(*candidate.parts)


def read_tsv(relative: str, expected_columns: list[str], failures: list[str]) -> list[dict[str, str]]:
    path = safe_member(relative)
    if not path.is_file():
        failures.append(f"missing TSV: {relative}")
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
        if reader.fieldnames != expected_columns:
            failures.append(
                f"schema mismatch: {relative}: {reader.fieldnames} != {expected_columns}"
            )
    return rows


def load_json(relative: str, failures: list[str]) -> dict:
    path = safe_member(relative)
    if not path.is_file():
        failures.append(f"missing JSON: {relative}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - reporting path
        failures.append(f"invalid JSON {relative}: {exc}")
        return {}


def main() -> int:
    failures: list[str] = []
    checksum_path = ROOT / "SHA256SUMS.txt"
    manifest_path = ROOT / "MANIFEST.tsv"
    if not checksum_path.is_file() or not manifest_path.is_file():
        print("status=FAIL reason=missing_manifest_or_checksums")
        return 1

    checksum_rows: dict[str, str] = {}
    for line_number, line in enumerate(
        checksum_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            expected, relative = line.split("  ", 1)
        except ValueError:
            failures.append(f"malformed checksum line {line_number}")
            continue
        if not HEX64.fullmatch(expected):
            failures.append(f"malformed checksum digest: {relative}")
            continue
        try:
            path = safe_member(relative)
        except ValueError as exc:
            failures.append(str(exc))
            continue
        observed = sha256(path) if path.is_file() else "MISSING"
        if observed != expected:
            failures.append(f"checksum mismatch: {relative}")
        if relative in checksum_rows:
            failures.append(f"duplicate checksum path: {relative}")
        checksum_rows[relative] = expected

    manifest_rows = read_tsv(
        "MANIFEST.tsv", ["path", "bytes", "sha256", "role"], failures
    )
    for row in manifest_rows:
        relative = row["path"]
        try:
            path = safe_member(relative)
        except ValueError as exc:
            failures.append(str(exc))
            continue
        if not path.is_file():
            failures.append(f"manifest member missing: {relative}")
            continue
        try:
            expected_bytes = int(row["bytes"])
        except ValueError:
            failures.append(f"manifest invalid byte count: {relative}")
            continue
        if path.stat().st_size != expected_bytes:
            failures.append(f"manifest byte count mismatch: {relative}")
        observed = sha256(path)
        if observed != row["sha256"]:
            failures.append(f"manifest digest mismatch: {relative}")
        if checksum_rows.get(relative) != row["sha256"]:
            failures.append(f"checksum/manifest disagreement: {relative}")

    actual_members = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.name not in {"MANIFEST.tsv", "SHA256SUMS.txt"}
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }
    if actual_members != set(checksum_rows):
        failures.append(
            "unmanifested_or_missing_members: "
            + ",".join(sorted(actual_members.symmetric_difference(checksum_rows)))
        )

    required = {
        "AI_ASSISTANCE_DISCLOSURE.md",
        "README.md",
        "REPRODUCTION.md",
        "SCOPE_AND_NONCLAIMS.md",
        "THIRD_PARTY_NOTICES.md",
        "VERSION",
        "evidence/CLAIM_EVIDENCE_CROSSWALK.tsv",
        "evidence/EXPECTED_PRINCIPAL_RESULTS.json",
        "evidence/first_season/FIRST_SEASON_COVERAGE_INDEX.tsv",
        "evidence/second_season/CANONICAL_CONTENT_AUDIT.tsv",
        "evidence/cross_season/CROSS_SEASON_CONTRADICTION_LEDGER.tsv",
        "evidence/cross_season/PROPOSITION_ALIGNMENT_REGISTER.tsv",
        "evidence/cross_season/EVIDENCE_COORDINATE_MATRIX.tsv",
        "evidence/cross_season/STATUS_SCHEMA.md",
        "evidence/final_validation/VALIDATION_GATE_REGISTER.tsv",
        "evidence/final_validation/FINAL_VALIDATION_SUMMARY.json",
        "evidence/final_validation/STOP_RECORD.md",
        "evidence/final_validation/REENTRY_CONDITIONS.tsv",
        "evidence/final_validation/exact_fixtures/H0DN_EXACT_RATIONAL_FIXTURE.json",
        "evidence/final_validation/exact_fixtures/SN_EQUAL_COMPRESSION_UNEQUAL_RESIDUAL_FIXTURE.json",
        "provenance/MASTER_IDENTITIES.tsv",
        "provenance/SOURCE_REGISTRY.tsv",
        "scripts/verify_synthetic_fixtures.py",
    }
    missing_required = required - set(checksum_rows)
    if missing_required:
        failures.append("required members absent: " + ",".join(sorted(missing_required)))

    if (ROOT / "VERSION").read_text(encoding="utf-8").strip() != "1.1":
        failures.append("version is not 1.1")

    prohibited_suffixes = {
        ".npz",
        ".npy",
        ".h5",
        ".hdf5",
        ".cov",
        ".fits",
        ".fit",
        ".pdf",
    }
    prohibited = [
        relative
        for relative in checksum_rows
        if pathlib.PurePosixPath(relative).suffix.lower() in prohibited_suffixes
    ]
    if prohibited:
        failures.append(
            "third-party/raw numerical payload type present: " + ",".join(prohibited)
        )
    if any(pathlib.PurePosixPath(relative).suffix.lower() == ".zip" for relative in checksum_rows):
        failures.append("nested ZIP present; authoritative project records must remain identity-only")

    source_rows = read_tsv(
        "provenance/SOURCE_REGISTRY.tsv",
        [
            "source_id",
            "official_url",
            "commit_or_record",
            "relative_path",
            "expected_bytes",
            "sha256",
            "redistribution",
            "retrieval_note",
        ],
        failures,
    )
    if not source_rows or any(row["redistribution"] != "NOT_INCLUDED" for row in source_rows):
        failures.append("external source redistribution boundary mismatch")

    master_rows = read_tsv(
        "provenance/MASTER_IDENTITIES.tsv",
        [
            "source_id",
            "exact_filename",
            "version",
            "sha256",
            "role",
            "scientific_scope",
            "public_redistribution_status",
            "authority",
        ],
        failures,
    )
    observed_masters = {row["source_id"]: row for row in master_rows}
    if set(observed_masters) != set(EXPECTED_MASTERS):
        failures.append("Master identity set mismatch")
    for source_id, (filename, digest) in EXPECTED_MASTERS.items():
        row = observed_masters.get(source_id, {})
        if row.get("exact_filename") != filename or row.get("sha256") != digest:
            failures.append(f"Master identity mismatch: {source_id}")
        if row and row.get("public_redistribution_status") != "IDENTITY_ONLY_NOT_REDISTRIBUTED_IN_THIS_SUPPLEMENT":
            failures.append(f"Master redistribution boundary mismatch: {source_id}")

    first_rows = read_tsv(
        "evidence/first_season/FIRST_SEASON_COVERAGE_INDEX.tsv",
        [
            "case_id",
            "title",
            "branch_ids",
            "result_summary",
            "result_row_count",
            "coverage_status",
            "scientific_state",
        ],
        failures,
    )
    expected_first_cases = {
        "local_ladder",
        "bao_bbn",
        "cmb_desi",
        "desi_influence",
        "act_robustness",
        "release_geometry",
        "tdcosmo",
        "local_flow",
        "h0dn",
        "cross_route",
    }
    if {row["case_id"] for row in first_rows} != expected_first_cases:
        failures.append("First-Season coverage set mismatch")
    for row in first_rows:
        summary = safe_member(row["result_summary"])
        directory = summary.parent
        if not summary.is_file():
            failures.append(f"First-Season result summary missing: {row['case_id']}")
        for filename in ["RESULT_SUMMARY.tsv", "SOURCE_REGISTER.tsv", "CLAIM_BOUNDARY.md", "REPRODUCTION_STATUS.tsv"]:
            if not (directory / filename).is_file():
                failures.append(f"First-Season branch member missing: {row['case_id']}/{filename}")
        if row["coverage_status"] != "PASS_CLAIM_LEVEL_COVERAGE":
            failures.append(f"First-Season coverage status mismatch: {row['case_id']}")

    canonical_rows = read_tsv(
        "evidence/second_season/CANONICAL_CONTENT_AUDIT.tsv",
        [
            "supplement_path",
            "authority_layer",
            "canonical_source_path",
            "canonical_source_sha256",
            "supplement_sha256",
            "byte_identity",
            "canonical_status",
            "action",
        ],
        failures,
    )
    if len(canonical_rows) != 24:
        failures.append(f"canonical content audit count {len(canonical_rows)} != 24")
    for row in canonical_rows:
        if row["byte_identity"] != "PASS_BYTE_IDENTICAL":
            failures.append(f"canonical byte identity failed: {row['supplement_path']}")
        if row["canonical_source_sha256"] != row["supplement_sha256"]:
            failures.append(f"canonical digest disagreement: {row['supplement_path']}")
        target = safe_member(row["supplement_path"])
        if not target.is_file() or sha256(target) != row["supplement_sha256"]:
            failures.append(f"canonical target mismatch: {row['supplement_path']}")

    contradiction_columns = [
        "proposition_id",
        "first_season_record",
        "second_season_record",
        "source_match",
        "product_match",
        "numerical_contract_match",
        "quantity_match",
        "time_or_version_match",
        "contradiction_verdict",
        "rationale",
        "evidence_locator",
    ]
    contradiction_rows = read_tsv(
        "evidence/cross_season/CROSS_SEASON_CONTRADICTION_LEDGER.tsv",
        contradiction_columns,
        failures,
    )
    summary_rows = [row for row in contradiction_rows if row["proposition_id"] == "CQ-SUMMARY"]
    if len(contradiction_rows) != 8 or len(summary_rows) != 1:
        failures.append("cross-season contradiction ledger count/summary mismatch")
    if summary_rows and summary_rows[0]["contradiction_verdict"] != "TRUE_SCIENTIFIC_CONTRADICTION_COUNT_0":
        failures.append("cross-season zero-contradiction summary mismatch")
    for row in contradiction_rows:
        if row["proposition_id"] != "CQ-SUMMARY" and row["contradiction_verdict"] != "NO_TRUE_CONTRADICTION":
            failures.append(f"unexpected contradiction verdict: {row['proposition_id']}")
        locator = row["evidence_locator"].split("#", 1)[0]
        if not safe_member(locator).is_file():
            failures.append(f"contradiction evidence locator missing: {row['proposition_id']}")

    proposition_rows = read_tsv(
        "evidence/cross_season/PROPOSITION_ALIGNMENT_REGISTER.tsv",
        [
            "crosswalk_id",
            "first_claim_id",
            "first_original_status",
            "second_claim_ids",
            "relation",
            "current_bounded_reading",
            "scientific_value_changed",
            "true_contradiction",
        ],
        failures,
    )
    if len(proposition_rows) != 20:
        failures.append(f"proposition alignment count {len(proposition_rows)} != 20")
    if any(row["scientific_value_changed"] != "NO" or row["true_contradiction"] != "NO" for row in proposition_rows):
        failures.append("proposition alignment value/contradiction boundary mismatch")

    matrix_rows = read_tsv(
        "evidence/cross_season/EVIDENCE_COORDINATE_MATRIX.tsv",
        [
            "case_id",
            "case_name",
            "F0_status",
            "F1_status",
            "F2_status",
            "F3_status",
            "F4_status",
            "F5_status",
            "F6_status",
            "rationale",
            "supporting_artifact",
            "limitation",
        ],
        failures,
    )
    allowed_statuses = {"PASS", "MIXED", "HOLD", "FAIL", "NOT_TESTED", "NOT_APPLICABLE"}
    if len(matrix_rows) != 13:
        failures.append(f"F0-F6 matrix count {len(matrix_rows)} != 13")
    for row in matrix_rows:
        for coordinate in [f"F{i}_status" for i in range(7)]:
            if row[coordinate] not in allowed_statuses:
                failures.append(f"invalid matrix status: {row['case_id']} {coordinate}")
        if not safe_member(row["supporting_artifact"]).is_file():
            failures.append(f"matrix supporting artifact missing: {row['case_id']}")

    crosswalk_rows = read_tsv(
        "evidence/CLAIM_EVIDENCE_CROSSWALK.tsv",
        [
            "claim_id",
            "manuscript_section",
            "claim_summary",
            "season",
            "branch_or_phase",
            "evidence_path",
            "source_record",
            "source_version",
            "artifact_sha256",
            "evidence_level",
            "limitation",
            "nonclaim",
        ],
        failures,
    )
    if len(crosswalk_rows) != 33:
        failures.append(f"claim-evidence crosswalk count {len(crosswalk_rows)} != 33")
    if len({row["claim_id"] for row in crosswalk_rows}) != len(crosswalk_rows):
        failures.append("duplicate claim_id in claim-evidence crosswalk")
    for row in crosswalk_rows:
        target = safe_member(row["evidence_path"])
        if not target.is_file():
            failures.append(f"claim evidence path missing: {row['claim_id']}")
        elif sha256(target) != row["artifact_sha256"]:
            failures.append(f"claim evidence digest mismatch: {row['claim_id']}")
        if row["nonclaim"] not in {"YES", "NO"}:
            failures.append(f"invalid nonclaim flag: {row['claim_id']}")

    gate_rows = read_tsv(
        "evidence/final_validation/VALIDATION_GATE_REGISTER.tsv",
        ["check_id", "description", "observed", "requirement", "status"],
        failures,
    )
    if len(gate_rows) != 24 or any(row["status"] != "PASS" for row in gate_rows):
        failures.append("Final-Validation gate result is not 24/24 PASS")
    final_summary = load_json(
        "evidence/final_validation/FINAL_VALIDATION_SUMMARY.json", failures
    )
    admitted = final_summary.get("admitted_new_validation", {})
    if (
        final_summary.get("status") != "PASS"
        or admitted.get("check_count") != 24
        or admitted.get("pass_count") != 24
        or final_summary.get("stop_current_frozen_evidence") is not True
    ):
        failures.append("Final-Validation summary/STOP mismatch")

    reentry_rows = read_tsv(
        "evidence/final_validation/REENTRY_CONDITIONS.tsv",
        [
            "gate_id",
            "item",
            "final_state",
            "why_not_internal_now",
            "reentry_requirement",
            "priority",
            "source_artifact_path",
            "source_artifact_sha256",
        ],
        failures,
    )
    if {row["gate_id"] for row in reentry_rows} != {f"RG-{i:03d}" for i in range(1, 12)}:
        failures.append("re-entry condition set mismatch")
    if any(not HEX64.fullmatch(row["source_artifact_sha256"]) for row in reentry_rows):
        failures.append("re-entry source digest malformed")

    h0_fixture = load_json(
        "evidence/final_validation/exact_fixtures/H0DN_EXACT_RATIONAL_FIXTURE.json",
        failures,
    )
    if not (
        h0_fixture.get("status") == "PASS"
        and h0_fixture.get("baseline_estimate") == "1/2"
        and h0_fixture.get("nonorthogonal_scaled_estimate") == "1/5"
        and h0_fixture.get("orthogonally_rotated_estimate") == "1/2"
    ):
        failures.append("H0DN exact fixture mismatch")
    sn_fixture = load_json(
        "evidence/final_validation/exact_fixtures/SN_EQUAL_COMPRESSION_UNEQUAL_RESIDUAL_FIXTURE.json",
        failures,
    )
    if not (
        sn_fixture.get("status") == "PASS"
        and sn_fixture.get("compressed_mean_first") == sn_fixture.get("compressed_mean_second") == "0"
        and sn_fixture.get("residual_chi2_first") == "2"
        and sn_fixture.get("residual_chi2_second") == "8"
    ):
        failures.append("SN exact fixture mismatch")

    expected_results = load_json("evidence/EXPECTED_PRINCIPAL_RESULTS.json", failures)
    scope = expected_results.get("scope", {})
    if not (
        scope.get("final_internal_validation") == "PASS"
        and scope.get("project_state") == "CLOSED_WITH_SCOPE"
        and scope.get("stop_current_frozen_evidence") is True
        and scope.get("external_replication_claimed") is False
    ):
        failures.append("expected principal-result scope mismatch")

    disclosure = (ROOT / "AI_ASSISTANCE_DISCLOSURE.md").read_text(encoding="utf-8")
    for phrase in [
        "research direction",
        "scope and claim boundaries",
        "reruns and corrections",
        "completion of the specified analyses and release",
        "managed provenance",
        "correction, withdrawal",
        "AI output is not treated as evidence",
        "External independent replication = NOT ESTABLISHED",
    ]:
        if phrase not in disclosure:
            failures.append(f"AI disclosure phrase missing: {phrase}")

    scope_text = (ROOT / "SCOPE_AND_NONCLAIMS.md").read_text(encoding="utf-8")
    for statement in [
        "Scientific values changed: NO",
        "Claim boundaries changed: NO",
        "Third-party raw data redistributed: NO",
    ]:
        if statement not in scope_text:
            failures.append(f"scope boundary statement missing: {statement}")

    status = "PASS" if not failures else "FAIL"
    true_contradictions = 0 if summary_rows and summary_rows[0]["contradiction_verdict"].endswith("_0") else -1
    print(
        f"status={status} checksums={len(checksum_rows)} manifest_rows={len(manifest_rows)} "
        f"first_cases={len(first_rows)} second_canonical={len(canonical_rows)} "
        f"true_contradictions={true_contradictions} matrix_cases={len(matrix_rows)} "
        f"claims={len(crosswalk_rows)} final_gates={len(gate_rows)} failures={len(failures)}"
    )
    for failure in failures:
        print("FAIL", failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
