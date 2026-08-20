#!/usr/bin/env python3
"""Acquire, lock, and verify the separately distributed H0DN upstream source."""

from __future__ import annotations

import argparse
import csv
import hashlib
import pathlib
import subprocess
import sys
from typing import Iterable


UPSTREAM_REPOSITORY = "https://github.com/StefCas789/H0DN.git"
UPSTREAM_COMMIT = "cc0a4b9f36e65470d514f254a3c5cffa463fbd94"


class SourceVerificationError(RuntimeError):
    """Raised when the upstream checkout differs from the frozen source."""


def run_git(repo: pathlib.Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_paths(repo: pathlib.Path) -> Iterable[tuple[str, str, int]]:
    raw = run_git(repo, "ls-tree", "-r", "-l", UPSTREAM_COMMIT)
    for line in raw.splitlines():
        metadata, relpath = line.split("\t", 1)
        _mode, _kind, blob, size_text = metadata.split()
        yield relpath, blob, int(size_text)


def write_source_lock(repo: pathlib.Path, manifest: pathlib.Path) -> None:
    head = run_git(repo, "rev-parse", "HEAD")
    if head != UPSTREAM_COMMIT:
        raise SourceVerificationError(
            f"Cannot lock source at {head}; expected {UPSTREAM_COMMIT}."
        )
    rows = []
    for relpath, blob, expected_size in tracked_paths(repo):
        path = repo / relpath
        actual_size = path.stat().st_size
        if actual_size != expected_size:
            raise SourceVerificationError(
                f"Size mismatch while locking {relpath}: "
                f"{actual_size} != {expected_size}"
            )
        rows.append(
            {
                "path": relpath,
                "git_blob_sha1": blob,
                "bytes": actual_size,
                "sha256": sha256_file(path),
            }
        )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "git_blob_sha1", "bytes", "sha256"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def read_source_lock(manifest: pathlib.Path) -> list[dict[str, str]]:
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def verify_source(repo: pathlib.Path, manifest: pathlib.Path) -> dict[str, object]:
    if not (repo / ".git").exists():
        raise SourceVerificationError(f"Not a Git checkout: {repo}")
    head = run_git(repo, "rev-parse", "HEAD")
    if head != UPSTREAM_COMMIT:
        raise SourceVerificationError(
            f"Upstream HEAD is {head}; expected {UPSTREAM_COMMIT}."
        )
    rows = read_source_lock(manifest)
    failures: list[str] = []
    for row in rows:
        path = repo / row["path"]
        if not path.is_file():
            failures.append(f"missing:{row['path']}")
            continue
        actual_size = path.stat().st_size
        if actual_size != int(row["bytes"]):
            failures.append(f"size:{row['path']}")
            continue
        if sha256_file(path) != row["sha256"]:
            failures.append(f"sha256:{row['path']}")
    locked_paths = {row["path"] for row in rows}
    current_paths = {path for path, _blob, _size in tracked_paths(repo)}
    if current_paths != locked_paths:
        for path in sorted(current_paths - locked_paths):
            failures.append(f"unlocked_tracked_file:{path}")
        for path in sorted(locked_paths - current_paths):
            failures.append(f"locked_file_not_in_commit:{path}")
    if failures:
        raise SourceVerificationError(
            "Frozen upstream verification failed: " + ", ".join(failures)
        )
    return {
        "repository": UPSTREAM_REPOSITORY,
        "commit": head,
        "locked_file_count": len(rows),
        "status": "PASS",
    }


def acquire(destination: pathlib.Path) -> None:
    if destination.exists():
        if not (destination / ".git").exists():
            raise SourceVerificationError(
                f"Destination exists but is not a Git repository: {destination}"
            )
    else:
        subprocess.run(
            ["git", "clone", "--no-checkout", UPSTREAM_REPOSITORY, str(destination)],
            check=True,
        )
    subprocess.run(
        ["git", "-C", str(destination), "fetch", "origin", UPSTREAM_COMMIT],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(destination), "checkout", "--detach", UPSTREAM_COMMIT],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=pathlib.Path)
    parser.add_argument("--destination", type=pathlib.Path)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--write-lock", action="store_true")
    args = parser.parse_args()

    repo = args.upstream or args.destination
    if repo is None:
        parser.error("provide --upstream or --destination")
    repo = repo.resolve()
    manifest = args.manifest.resolve()

    try:
        if args.destination is not None:
            acquire(repo)
        if args.write_lock:
            write_source_lock(repo, manifest)
        result = verify_source(repo, manifest)
    except (OSError, subprocess.CalledProcessError, SourceVerificationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(
        f"PASS: {result['locked_file_count']} files at "
        f"{result['commit']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

