#!/usr/bin/env python3
"""Write package checksums and build a deterministic source/results archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import pathlib
import subprocess
import sys
import zipfile


EXCLUDED_FROM_MANIFEST = {"MANIFEST.tsv", "SHA256SUMS.txt"}
ARCHIVE_ROOT = "h0dn-covariance-influence-audit-0.1.0"
FIXED_ZIP_TIMESTAMP = (2026, 7, 29, 0, 0, 0)
FORBIDDEN_UPSTREAM_ROOTS = {
    "data",
    "h0_constrainer",
    "idlcode",
    "H0DN",
    "H0DN_CLEAN",
}
RUNTIME_PATH_EXCLUSIONS = {
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".DS_Store",
}


class PackageFailure(RuntimeError):
    """Raised when the package cannot be finalized reproducibly."""


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_tracked_paths(project_root: pathlib.Path) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(project_root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return sorted(
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    )


def packaged_paths(project_root: pathlib.Path) -> list[str]:
    """Resolve package paths in a Git worktree or an extracted archive."""

    if (project_root / ".git").exists():
        return git_tracked_paths(project_root)
    return sorted(
        path.relative_to(project_root).as_posix()
        for path in project_root.rglob("*")
        if path.is_file()
        and not any(
            part in RUNTIME_PATH_EXCLUSIONS
            for part in path.relative_to(project_root).parts
        )
    )


def write_manifests(project_root: pathlib.Path) -> None:
    paths = [
        path
        for path in packaged_paths(project_root)
        if path not in EXCLUDED_FROM_MANIFEST
    ]
    rows = []
    for relative in paths:
        target = project_root / relative
        if not target.is_file():
            raise PackageFailure(f"Tracked path is not a file: {relative}")
        rows.append(
            {
                "path": relative,
                "bytes": target.stat().st_size,
                "sha256": sha256_file(target),
            }
        )
    with (project_root / "MANIFEST.tsv").open(
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
    with (project_root / "SHA256SUMS.txt").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        for row in rows:
            handle.write(f"{row['sha256']}  {row['path']}\n")


def verify_no_upstream_bytes(paths: list[str]) -> None:
    bundled = [
        path
        for path in paths
        if pathlib.PurePosixPath(path).parts
        and pathlib.PurePosixPath(path).parts[0]
        in FORBIDDEN_UPSTREAM_ROOTS
    ]
    if bundled:
        raise PackageFailure(
            "Upstream source/data paths must not be packaged: "
            + ", ".join(bundled)
        )


def verify_manifests(project_root: pathlib.Path) -> list[str]:
    manifest = project_root / "MANIFEST.tsv"
    checksums = project_root / "SHA256SUMS.txt"
    if not manifest.is_file() or not checksums.is_file():
        raise PackageFailure("MANIFEST.tsv or SHA256SUMS.txt is missing")
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise PackageFailure("Package manifest is empty")
    paths = [row["path"] for row in rows]
    if len(paths) != len(set(paths)):
        raise PackageFailure("Package manifest contains duplicate paths")
    expected_paths = [
        path
        for path in packaged_paths(project_root)
        if path not in EXCLUDED_FROM_MANIFEST
    ]
    if paths != expected_paths:
        raise PackageFailure(
            "Package manifest does not exactly cover tracked package files"
        )
    verify_no_upstream_bytes(packaged_paths(project_root))
    for row in rows:
        target = project_root / row["path"]
        if not target.is_file():
            raise PackageFailure(f"Missing packaged file: {row['path']}")
        if target.stat().st_size != int(row["bytes"]):
            raise PackageFailure(f"Size mismatch: {row['path']}")
        if sha256_file(target) != row["sha256"]:
            raise PackageFailure(f"SHA-256 mismatch: {row['path']}")
    expected_lines = [
        f"{row['sha256']}  {row['path']}\n" for row in rows
    ]
    actual_lines = checksums.read_text(encoding="utf-8").splitlines(
        keepends=True
    )
    if actual_lines != expected_lines:
        raise PackageFailure("SHA256SUMS.txt does not match MANIFEST.tsv")
    return paths


def build_archive(project_root: pathlib.Path, output: pathlib.Path) -> None:
    verify_manifests(project_root)
    paths = git_tracked_paths(project_root)
    missing = [path for path in paths if not (project_root / path).is_file()]
    if missing:
        raise PackageFailure("Missing tracked files: " + ", ".join(missing))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for relative in paths:
            data = (project_root / relative).read_bytes()
            info = zipfile.ZipInfo(
                f"{ARCHIVE_ROOT}/{relative}",
                date_time=FIXED_ZIP_TIMESTAMP,
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.create_system = 3
            archive.writestr(info, data, compresslevel=9)
        commit = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        archive.comment = (
            f"Independent H0DN covariance influence audit v0.1.0; "
            f"git {commit}"
        ).encode("ascii")
    with zipfile.ZipFile(output, mode="r") as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise PackageFailure(f"ZIP CRC failure: {corrupt}")


def write_external_sha256(output: pathlib.Path) -> pathlib.Path:
    target = output.with_name(output.name + ".sha256")
    target.write_text(
        f"{sha256_file(output)}  {output.name}\n",
        encoding="utf-8",
    )
    return target


def main() -> int:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-manifests",
        action="store_true",
        help="Regenerate MANIFEST.tsv and SHA256SUMS.txt.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the existing package manifests.",
    )
    parser.add_argument(
        "--archive",
        type=pathlib.Path,
        help="Build a deterministic ZIP from all tracked files.",
    )
    args = parser.parse_args()
    if not (args.write_manifests or args.check or args.archive):
        parser.error("choose --write-manifests, --check, and/or --archive")
    try:
        if args.write_manifests:
            write_manifests(project_root)
        if args.check or args.archive:
            paths = verify_manifests(project_root)
            print(f"PASS: verified {len(paths)} manifested files")
        if args.archive:
            output = args.archive.resolve()
            build_archive(project_root, output)
            checksum = write_external_sha256(output)
            print(
                f"PASS: wrote {output} ({output.stat().st_size} bytes, "
                f"sha256={sha256_file(output)})"
            )
            print(f"PASS: wrote external checksum {checksum}")
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        PackageFailure,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
