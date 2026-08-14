#!/usr/bin/env python3
"""Deterministic manifest and ZIP helpers."""

from __future__ import annotations

import csv
import hashlib
import pathlib
import zipfile


CHECKSUM_FILES = {"MANIFEST.tsv", "SHA256SUMS.txt"}
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
}


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
            raise RuntimeError(f"symbolic links are prohibited: {relative}")
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
    with (project / "MANIFEST.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "bytes", "sha256"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    (project / "SHA256SUMS.txt").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in rows),
        encoding="utf-8",
    )
    return rows


def verify_manifests(project: pathlib.Path) -> dict[str, int | str]:
    with (project / "MANIFEST.tsv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["path", "bytes", "sha256"]:
            raise RuntimeError("MANIFEST.tsv schema mismatch")
        recorded = [
            {
                "path": row["path"],
                "bytes": int(row["bytes"]),
                "sha256": row["sha256"],
            }
            for row in reader
        ]
    expected = manifest_rows(project)
    if recorded != expected:
        raise RuntimeError("MANIFEST.tsv differs from delivered tree")
    sums = "".join(
        f"{row['sha256']}  {row['path']}\n" for row in expected
    )
    if (project / "SHA256SUMS.txt").read_text(encoding="utf-8") != sums:
        raise RuntimeError("SHA256SUMS.txt differs from manifest")
    return {"status": "PASS", "manifested_file_count": len(expected)}


def deterministic_archive(
    project: pathlib.Path, archive: pathlib.Path
) -> dict[str, str | int]:
    verify_manifests(project)
    archive.parent.mkdir(parents=True, exist_ok=True)
    paths = sorted(
        package_files(project)
        + [project / "MANIFEST.tsv", project / "SHA256SUMS.txt"],
        key=lambda item: item.relative_to(project).as_posix(),
    )
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as handle:
        for path in paths:
            relative = path.relative_to(project).as_posix()
            info = zipfile.ZipInfo(
                f"{project.name}/{relative}",
                date_time=(2026, 7, 30, 0, 0, 0),
            )
            info.create_system = 3
            info.external_attr = (
                0o755 if path.stat().st_mode & 0o111 else 0o644
            ) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            handle.writestr(info, path.read_bytes(), compresslevel=9)
    digest = sha256_file(archive)
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return {
        "archive": str(archive),
        "archive_bytes": archive.stat().st_size,
        "archive_file_count": len(paths),
        "archive_sha256": digest,
        "sidecar": str(sidecar),
    }
