#!/usr/bin/env python3
"""Verify final manifests, ZIP CRC, checksum sidecar, and replica identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import zipfile


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=pathlib.Path, required=True)
    parser.add_argument("--archive", type=pathlib.Path, required=True)
    parser.add_argument("--replica", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    archive = args.archive.resolve()
    replica = args.replica.resolve()
    sidecar = archive.with_name(archive.name + ".sha256")

    from sys import path as module_path

    module_path.insert(0, str(project / "scripts"))
    from package_tools import verify_manifests

    manifest_result = verify_manifests(project)
    archive_hash = sha256(archive)
    replica_hash = sha256(replica)
    expected_sidecar = f"{archive_hash}  {archive.name}\n"
    sidecar_valid = (
        sidecar.is_file()
        and sidecar.read_text(encoding="utf-8") == expected_sidecar
    )
    with zipfile.ZipFile(archive, "r") as handle:
        bad_member = handle.testzip()
        names = handle.namelist()
    with zipfile.ZipFile(replica, "r") as handle:
        replica_bad_member = handle.testzip()
    identical = (
        archive.stat().st_size == replica.stat().st_size
        and archive_hash == replica_hash
        and archive.read_bytes() == replica.read_bytes()
    )
    root_prefix = project.name + "/"
    forbidden_source_paths = [
        name
        for name in names
        if "/sources/" in name
        or name.endswith("Pantheon+SH0ES_STAT+SYS.cov")
        or name.endswith("Pantheon+SH0ES_STATONLY.cov")
        or name.endswith("sn1a_covar_pp.dat")
    ]
    checks = {
        "manifest": manifest_result["status"] == "PASS",
        "archive_crc": bad_member is None,
        "replica_crc": replica_bad_member is None,
        "sidecar": sidecar_valid,
        "replica_byte_identity": identical,
        "single_expected_root": all(
            name.startswith(root_prefix) for name in names
        ),
        "upstream_bytes_not_redistributed": not forbidden_source_paths,
    }
    result = {
        "archive_name": archive.name,
        "archive_bytes": archive.stat().st_size,
        "archive_file_count": len(names),
        "archive_sha256": archive_hash,
        "replica_name": replica.name,
        "replica_bytes": replica.stat().st_size,
        "replica_sha256": replica_hash,
        "checks": checks,
        "manifested_file_count": manifest_result[
            "manifested_file_count"
        ],
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    args.output.resolve().write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

