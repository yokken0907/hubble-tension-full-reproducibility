#!/usr/bin/env python3
"""Read-only verifier for the final internal validation and closure package."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path


CONTRACT_SHA256 = "5a54607d6004c88215e2981dce5a0a4ff1012c4505885487ef27b57db7a0b7d5"


class VerificationError(RuntimeError):
    pass


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    return list(
        csv.DictReader(
            io.StringIO(path.read_text(encoding="utf-8-sig")),
            delimiter="\t",
        )
    )


def strict_json(path: Path):
    def reject(value: str):
        raise ValueError(f"non-finite JSON constant {value}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


def manifested_hashes(root: Path, manifest_rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["path"]: digest(root / row["path"]) for row in manifest_rows}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    checks = 0
    manifest = root / "MANIFEST.tsv"
    sums = root / "SHA256SUMS.txt"
    if not manifest.is_file() or not sums.is_file():
        raise VerificationError("manifest or SHA256SUMS missing")
    checks += 1

    manifest_rows = rows(manifest)
    expected_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name not in {"MANIFEST.tsv", "SHA256SUMS.txt"}
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }
    recorded_paths = {row["path"] for row in manifest_rows}
    if expected_paths != recorded_paths or len(recorded_paths) != len(manifest_rows):
        raise VerificationError("manifest path closure failure")
    checks += 2
    for row in manifest_rows:
        path = root / row["path"]
        if path.stat().st_size != int(row["bytes"]):
            raise VerificationError(f"byte size mismatch: {row['path']}")
        if digest(path) != row["sha256"]:
            raise VerificationError(f"SHA-256 mismatch: {row['path']}")
    checks += len(manifest_rows)

    sum_rows: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        checksum, path = line.split("  ", 1)
        sum_rows[path] = checksum
    if sum_rows != {row["path"]: row["sha256"] for row in manifest_rows}:
        raise VerificationError("SHA256SUMS differs from manifest")
    checks += 1

    if digest(root / "INTERNAL_VALIDATION_CONTRACT.md") != CONTRACT_SHA256:
        raise VerificationError("frozen contract digest mismatch")
    sidecar = (root / "INTERNAL_VALIDATION_CONTRACT.md.sha256").read_text(encoding="utf-8")
    if sidecar != f"{CONTRACT_SHA256}  INTERNAL_VALIDATION_CONTRACT.md\n":
        raise VerificationError("contract sidecar mismatch")
    checks += 2

    for path in sorted(root.rglob("*.json")):
        strict_json(path)
        checks += 1

    provenance = strict_json(root / "test_vectors/TEST_VECTOR_PROVENANCE.json")
    if provenance["h0dn_vector"]["archive_sha256"] != digest(root / "test_vectors/h0dn_network_gls.npz"):
        raise VerificationError("H0DN vector digest mismatch")
    if provenance["sn_vector"]["archive_sha256"] != digest(root / "test_vectors/sn_intercept_block.npz"):
        raise VerificationError("SN vector digest mismatch")
    checks += 2

    result = strict_json(root / "results/internal_validation_results.json")
    if result["status"] != "PASS" or result["check_count"] != 24 or result["pass_count"] != 24:
        raise VerificationError("internal validation result drift")
    if any(row["status"] != "PASS" for row in result["checks"]):
        raise VerificationError("non-PASS frozen validation check")
    checks += 2

    closure = strict_json(root / "results/closure_summary.json")
    if closure["project_internal_validation_program"] != "CLOSED_WITH_SCOPE":
        raise VerificationError("internal program not closed")
    if closure["stop_current_frozen_evidence"] is not True:
        raise VerificationError("STOP marker missing")
    if closure["paper_drafting"] != "NOT_PERFORMED":
        raise VerificationError("paper-drafting boundary drift")
    checks += 3

    decisions = rows(root / "INFORMATION_GAIN_DECISION_LEDGER.tsv")
    if len(decisions) != 14 or len({row["decision_id"] for row in decisions}) != 14:
        raise VerificationError("information-gain ledger cardinality failure")
    if any(row["decision"] not in {"EXECUTE", "DO_NOT_ADD_BRANCH", "HOLD_EXTERNAL_PRODUCT", "STOP"} for row in decisions):
        raise VerificationError("unknown information-gain decision")
    checks += 2

    validation = rows(root / "VALIDATION_LEDGER.tsv")
    if len(validation) != 17 or len({row["validation_id"] for row in validation}) != 17:
        raise VerificationError("validation ledger cardinality failure")
    if any(row["status"] not in {"PASS", "PASS_WITH_HOLD", "OVERALL_PASS"} for row in validation):
        raise VerificationError("validation ledger contains unresolved FAIL")
    checks += 2

    claims = rows(root / "CLAIM_AND_NONCLAIM_LEDGER.tsv")
    required_nonclaims = {f"FV-NC{index:03d}" for index in range(1, 11)}
    if not required_nonclaims.issubset({row["claim_id"] for row in claims}):
        raise VerificationError("required nonclaim missing")
    checks += 1

    reentry = rows(root / "HOLD_REENTRY_AND_STOP.tsv")
    stop_rows = [row for row in reentry if row["gate_id"] == "STOP-001"]
    if len(stop_rows) != 1 or stop_rows[0]["final_state"] != "STOP":
        raise VerificationError("final STOP row invalid")
    checks += 1

    evidence = rows(root / "EVIDENCE_LOCATOR.tsv")
    if len(evidence) != 17 or len({row["evidence_id"] for row in evidence}) != 17:
        raise VerificationError("evidence locator failure")
    checks += 1

    forbidden_suffixes = {".docx", ".pdf", ".tex"}
    if any(path.suffix.lower() in forbidden_suffixes for path in root.rglob("*")):
        raise VerificationError("unexpected manuscript/document artifact")
    checks += 1

    hashes_before = manifested_hashes(root, manifest_rows)
    completed = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/run_internal_validations.py"),
            "--root",
            str(root),
            "--verify-recorded",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 or "fail=0" not in completed.stdout:
        raise VerificationError(
            "live numerical validation failed: "
            + completed.stdout
            + completed.stderr
        )
    hashes_after = manifested_hashes(root, manifest_rows)
    if hashes_before != hashes_after:
        raise VerificationError("verifier modified a manifested file")
    checks += 2

    print(
        f"checks={checks} pass={checks} fail=0 files={len(manifest_rows)} "
        "numerical=24/24 stop=PASS"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (VerificationError, OSError, KeyError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
