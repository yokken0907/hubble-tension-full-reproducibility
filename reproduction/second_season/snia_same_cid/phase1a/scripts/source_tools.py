#!/usr/bin/env python3
"""Acquire and verify the separately distributed frozen H0DN source."""

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


def read_source_lock(manifest: pathlib.Path) -> list[dict[str, str]]:
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    expected_fields = {"path", "git_blob_sha1", "bytes", "sha256"}
    if not rows or set(rows[0]) != expected_fields:
        raise SourceVerificationError("SOURCE_LOCK.tsv has an unexpected schema")
    return rows


def verify_source(repo: pathlib.Path, manifest: pathlib.Path) -> dict[str, object]:
    if not (repo / ".git").exists():
        raise SourceVerificationError(f"Not a Git checkout: {repo}")
    head = run_git(repo, "rev-parse", "HEAD")
    if head != UPSTREAM_COMMIT:
        raise SourceVerificationError(
            f"Upstream HEAD is {head}; expected {UPSTREAM_COMMIT}"
        )
    rows = read_source_lock(manifest)
    failures: list[str] = []
    for row in rows:
        path = repo / row["path"]
        if not path.is_file():
            failures.append(f"missing:{row['path']}")
            continue
        if path.stat().st_size != int(row["bytes"]):
            failures.append(f"size:{row['path']}")
            continue
        if sha256_file(path) != row["sha256"]:
            failures.append(f"sha256:{row['path']}")
            continue
        blob = run_git(repo, "hash-object", row["path"])
        if blob != row["git_blob_sha1"]:
            failures.append(f"git_blob:{row['path']}")
    locked_paths = {row["path"] for row in rows}
    current_paths = {path for path, _blob, _size in tracked_paths(repo)}
    for path in sorted(current_paths - locked_paths):
        failures.append(f"unlocked_tracked_file:{path}")
    for path in sorted(locked_paths - current_paths):
        failures.append(f"locked_file_not_in_commit:{path}")
    if failures:
        raise SourceVerificationError(
            "Frozen source verification failed: " + ", ".join(failures)
        )
    return {
        "repository": UPSTREAM_REPOSITORY,
        "commit": head,
        "locked_file_count": len(rows),
        "working_tree_status": run_git(repo, "status", "--short"),
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
    args = parser.parse_args()
    repo = args.upstream or args.destination
    if repo is None:
        parser.error("provide --upstream or --destination")
    try:
        if args.destination is not None:
            acquire(repo.resolve())
        result = verify_source(repo.resolve(), args.manifest.resolve())
    except (OSError, subprocess.CalledProcessError, SourceVerificationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(
        f"PASS: {result['locked_file_count']} files at {result['commit']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
