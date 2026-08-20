#!/usr/bin/env python3
"""Verify deterministic archives and execute clean extracted-package checks."""

from __future__ import annotations

import argparse
import json
import pathlib
import stat
import subprocess
import sys
import tempfile
import zipfile


def sha256(path: pathlib.Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_members(handle: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo], bool]:
    infos = handle.infolist()
    safe = all(
        not pathlib.PurePosixPath(info.filename).is_absolute()
        and ".." not in pathlib.PurePosixPath(info.filename).parts
        for info in infos
    )
    return infos, safe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--archive", type=pathlib.Path, required=True)
    parser.add_argument("--replica", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    source_repo = args.pantheonplus.resolve()
    archive = args.archive.resolve()
    replica = args.replica.resolve()
    sidecar = archive.with_name(archive.name + ".sha256")
    sys.path.insert(0, str(project / "scripts"))
    from package_tools import ARCHIVE_TIMESTAMP, verify_manifests

    manifest = verify_manifests(project)
    archive_hash = sha256(archive)
    replica_hash = sha256(replica)
    with zipfile.ZipFile(archive) as handle:
        infos, safe_paths = safe_members(handle)
        bad_member = handle.testzip()
        names = [info.filename for info in infos]
        symlinks = [
            info.filename for info in infos
            if info.create_system == 3 and stat.S_ISLNK(info.external_attr >> 16)
        ]
    with zipfile.ZipFile(replica) as handle:
        replica_bad_member = handle.testzip()

    forbidden = [
        name for name in names
        if "/Pantheon+_Data/" in name
        or name.lower().endswith((".fits", ".fitres", ".cov"))
        or name.endswith("Pantheon+SH0ES.dat")
        or name.endswith("PPLUS.yml")
    ]
    expected_archive_name = "h0dn-snia-cross-series-input-dependency-audit_v0.1.0.zip"
    expected_root = project.name + "/"

    extracted_manifest_pass = False
    extracted_verifier_pass = False
    extracted_verifier_checks = None
    extracted_finalizer_pass = False
    if safe_paths:
        with tempfile.TemporaryDirectory(prefix="phase1f-delivery-extract-") as temporary:
            destination = pathlib.Path(temporary)
            with zipfile.ZipFile(archive) as handle:
                handle.extractall(destination)
            extracted = destination / project.name
            try:
                extracted_manifest_pass = verify_manifests(extracted)["status"] == "PASS"
            except (OSError, RuntimeError, ValueError):
                extracted_manifest_pass = False
            verifier = subprocess.run(
                [sys.executable, "scripts/verify_results.py", "--pantheonplus", str(source_repo)],
                cwd=extracted,
                text=True,
                capture_output=True,
                check=False,
            )
            try:
                verifier_json = json.loads(verifier.stdout)
            except json.JSONDecodeError:
                verifier_json = {}
            extracted_verifier_checks = verifier_json.get("check_count")
            extracted_verifier_pass = (
                verifier.returncode == 0
                and verifier_json.get("status") == "PASS"
                and verifier_json.get("pass_count") == verifier_json.get("check_count") == 117
            )
            finalizer = subprocess.run(
                [sys.executable, "scripts/finalize_package.py", "--check"],
                cwd=extracted,
                text=True,
                capture_output=True,
                check=False,
            )
            extracted_finalizer_pass = finalizer.returncode == 0

    checks = {
        "manifest": manifest["status"] == "PASS",
        "archive_name": archive.name == expected_archive_name,
        "archive_crc": bad_member is None,
        "replica_crc": replica_bad_member is None,
        "sidecar": sidecar.is_file() and sidecar.read_text(encoding="utf-8") == f"{archive_hash}  {archive.name}\n",
        "replica_byte_identity": archive.stat().st_size == replica.stat().st_size and archive_hash == replica_hash and archive.read_bytes() == replica.read_bytes(),
        "archive_member_count": len(names) == manifest["manifested_file_count"] + 2,
        "single_expected_root": bool(names) and all(name.startswith(expected_root) for name in names),
        "sorted_unique_members": names == sorted(names) and len(names) == len(set(names)),
        "safe_member_paths": safe_paths,
        "no_symbolic_links": not symlinks,
        "fixed_member_timestamps": all(info.date_time == ARCHIVE_TIMESTAMP for info in infos),
        "deflated_members": all(info.compress_type == zipfile.ZIP_DEFLATED for info in infos),
        "upstream_bytes_not_redistributed": not forbidden,
        "extracted_manifest": extracted_manifest_pass,
        "extracted_strict_verifier_117_of_117": extracted_verifier_pass,
        "extracted_manifest_finalizer": extracted_finalizer_pass,
    }
    result = {
        "archive_name": archive.name,
        "archive_bytes": archive.stat().st_size,
        "archive_file_count": len(names),
        "archive_sha256": archive_hash,
        "replica_name": replica.name,
        "replica_bytes": replica.stat().st_size,
        "replica_sha256": replica_hash,
        "manifested_file_count": manifest["manifested_file_count"],
        "extracted_verifier_check_count": extracted_verifier_checks,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    args.output.resolve().write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
