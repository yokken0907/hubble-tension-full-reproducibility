#!/usr/bin/env python3
"""Shared deterministic package-manifest and archive helpers."""

from __future__ import annotations

import csv
import hashlib
import pathlib
import zipfile
from typing import Iterable


CHECKSUM_FILES = {"MANIFEST.tsv", "SHA256SUMS.txt"}
EXCLUDED_DIRECTORY_NAMES = {".git", ".venv", "__pycache__", "build", "dist"}


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_files(project: pathlib.Path) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for path in project.rglob("*"):
        relative = path.relative_to(project)
        if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative.parts):
            continue
        if path.is_symlink():
            raise RuntimeError(f"Symlinks are not permitted: {relative}")
        if not path.is_file():
            continue
        if relative.as_posix() in CHECKSUM_FILES:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(project).as_posix())


def manifest_rows(project: pathlib.Path) -> list[dict[str, str | int]]:
    return [
        {
            "path": path.relative_to(project).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in package_files(project)
    ]


def write_manifests(project: pathlib.Path) -> list[dict[str, str | int]]:
    rows = manifest_rows(project)
    manifest = project / "MANIFEST.tsv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "bytes", "sha256"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    sums = project / "SHA256SUMS.txt"
    sums.write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in rows),
        encoding="utf-8",
    )
    return rows


def read_manifest(project: pathlib.Path) -> list[dict[str, str]]:
    with (project / "MANIFEST.tsv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["path", "bytes", "sha256"]:
            raise RuntimeError("MANIFEST.tsv has an unexpected schema")
        return list(reader)


def verify_manifests(project: pathlib.Path) -> dict[str, int | str]:
    if not (project / "MANIFEST.tsv").is_file():
        raise RuntimeError("MANIFEST.tsv is missing")
    if not (project / "SHA256SUMS.txt").is_file():
        raise RuntimeError("SHA256SUMS.txt is missing")
    expected = manifest_rows(project)
    recorded = read_manifest(project)
    normalized_recorded = [
        {
            "path": row["path"],
            "bytes": int(row["bytes"]),
            "sha256": row["sha256"],
        }
        for row in recorded
    ]
    if normalized_recorded != expected:
        raise RuntimeError("MANIFEST.tsv does not match the delivered file set")
    expected_sums = "".join(
        f"{row['sha256']}  {row['path']}\n" for row in expected
    )
    actual_sums = (project / "SHA256SUMS.txt").read_text(encoding="utf-8")
    if actual_sums != expected_sums:
        raise RuntimeError("SHA256SUMS.txt does not match MANIFEST.tsv")
    return {"status": "PASS", "manifested_file_count": len(expected)}


def deterministic_archive(
    project: pathlib.Path, archive: pathlib.Path
) -> dict[str, str | int]:
    verify_manifests(project)
    archive.parent.mkdir(parents=True, exist_ok=True)
    paths = package_files(project) + [
        project / "MANIFEST.tsv",
        project / "SHA256SUMS.txt",
    ]
    paths = sorted(
        paths, key=lambda item: item.relative_to(project).as_posix()
    )
    root_name = project.name
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as handle:
        for path in paths:
            relative = path.relative_to(project).as_posix()
            info = zipfile.ZipInfo(
                f"{root_name}/{relative}",
                date_time=(2026, 7, 30, 0, 0, 0),
            )
            info.create_system = 3
            info.external_attr = (0o755 if path.stat().st_mode & 0o111 else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            handle.writestr(info, path.read_bytes(), compresslevel=9)
    archive_sha256 = sha256_file(archive)
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(
        f"{archive_sha256}  {archive.name}\n", encoding="utf-8"
    )
    return {
        "archive": str(archive),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": archive_sha256,
        "archive_file_count": len(paths),
        "sidecar": str(sidecar),
    }

