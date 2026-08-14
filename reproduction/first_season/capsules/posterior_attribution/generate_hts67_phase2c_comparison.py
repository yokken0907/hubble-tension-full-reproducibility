#!/usr/bin/env python3
"""Generate the current HTS67 comparison from the canonical Phase2C ZIP.

This is a provenance/identity comparison only. It does not execute HTS67 or
recompute any scientific result.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "REPRODUCTION" / "posterior_attribution"
EXPECTED_ZIP_SHA256 = (
    "8254503a8a18d6ca3cfcc6dfb0104458982e19bd13bf89b9c81d3e8f34a31353"
)
EXPECTED_MEMBERS = (
    (
        "HTS67_CLASSIFICATION.tsv",
        "8d4c8ff4002d3dd9e40f61bf1c4e34020f4ceb5a43d12b556a656713e0456625",
    ),
    (
        "HTS67_BURNIN_SENSITIVITY.tsv",
        "cb68bc1b210cf2febf0a501c2981bfbc27452617d938a4838ac929c868c45a1a",
    ),
    (
        "HTS67_DIRECTED_BASELINE_COMPARISON.tsv",
        "bbde8cb893f9ab0891a574e5ac6d10c18307e0e72ba32510bae8757bb9029ef9",
    ),
    (
        "HTS67_ENDPOINT_6D_SUMMARY.tsv",
        "abf1612bd842037a9a9655ca1743b761d198619440e68246a3106b5615d0c207",
    ),
    (
        "HTS67_INDEPENDENT_AUDIT_CHECKS.tsv",
        "0141763190dbd058b32d4d0166b7acdcf1d4c5f9e004df5b68d4c1364242e3ff",
    ),
    (
        "HTS67_LOO_STABILITY.tsv",
        "0242e200c8aefe146b21d663533a315585a7ea72d1a5ef2f018053f8decc79c2",
    ),
    (
        "HTS67_SYMMETRIC_METRIC_RESULTS.tsv",
        "f7137158cbc97d8c01ec3462ef7fb3a57aca75cb19921b965fb72847b2b69b41",
    ),
    (
        "HTS67_SYMMETRIC_POOLING_SENSITIVITY.tsv",
        "3c7e6bfc17dee1a33a6a3dee60cb287eabff7aa9a10f5fb8c7e5dc4fb135dfa0",
    ),
)
FIELDNAMES = (
    "PATH",
    "REFERENCE_KIND",
    "HISTORICAL_SHA256",
    "FRESH_SHA256",
    "BYTE_IDENTICAL",
    "COMPARISON_TYPE",
    "MAX_ABS_NUMERIC_DIFFERENCE",
    "TEXT_DIFFERENCE_COUNT",
    "CLASSIFICATION_MATCH",
    "PUBLICATION_PRECISION_MATCH",
    "STATUS",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=f".{path.name}.",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        writer = csv.DictWriter(
            handle, fieldnames=FIELDNAMES, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)
    path.chmod(0o644)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zip",
        type=Path,
        default=BASE
        / "official_fetch_records"
        / "phase2c_network_execution"
        / "outputs"
        / "HTS67_RESULTS_FOR_REVIEW.zip",
    )
    parser.add_argument(
        "--historical-dir",
        type=Path,
        default=BASE / "historical_substantive_reference" / "hts67",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE / "HTS67_HISTORICAL_VS_FRESH_COMPARISON.tsv",
    )
    args = parser.parse_args()

    if sha256_file(args.zip) != EXPECTED_ZIP_SHA256:
        raise SystemExit("canonical Phase2C HTS67 ZIP SHA-256 mismatch")

    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(args.zip) as archive:
        if archive.testzip() is not None:
            raise SystemExit("canonical Phase2C HTS67 ZIP CRC failure")
        members = set(archive.namelist())
        for name, expected_digest in EXPECTED_MEMBERS:
            if name not in members:
                raise SystemExit(f"canonical Phase2C ZIP member missing: {name}")
            fresh_bytes = archive.read(name)
            historical_path = args.historical_dir / name
            historical_bytes = historical_path.read_bytes()
            fresh_digest = sha256_bytes(fresh_bytes)
            historical_digest = sha256_bytes(historical_bytes)
            if fresh_digest != expected_digest:
                raise SystemExit(f"canonical Phase2C member SHA-256 mismatch: {name}")
            if historical_digest != expected_digest:
                raise SystemExit(f"historical reference SHA-256 mismatch: {name}")
            if fresh_bytes != historical_bytes:
                raise SystemExit(f"designated substantive table is not identical: {name}")
            rows.append(
                {
                    "PATH": name,
                    "REFERENCE_KIND": "PHASE2C_OFFICIAL_EMPTY_CACHE_FRESH_OUTPUT",
                    "HISTORICAL_SHA256": historical_digest,
                    "FRESH_SHA256": fresh_digest,
                    "BYTE_IDENTICAL": "YES",
                    "COMPARISON_TYPE": "BYTE_IDENTITY_AND_NUMERIC_EQUALITY",
                    "MAX_ABS_NUMERIC_DIFFERENCE": "0.0",
                    "TEXT_DIFFERENCE_COUNT": "0",
                    "CLASSIFICATION_MATCH": "YES",
                    "PUBLICATION_PRECISION_MATCH": "YES",
                    "STATUS": "PASS_BYTE_IDENTICAL",
                }
            )

    write_rows(args.output, rows)
    print(f"PHASE2C_HTS67_ZIP_SHA256 = {EXPECTED_ZIP_SHA256}")
    print(f"HTS67_SUBSTANTIVE_TABLE_BYTE_IDENTITY = {len(rows)}/8 PASS")
    print(f"WROTE = {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
