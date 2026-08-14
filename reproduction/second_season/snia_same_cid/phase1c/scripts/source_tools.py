#!/usr/bin/env python3
"""Acquire or verify the two frozen public source repositories."""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

from auditlib import AuditFailure, read_source_lock, verify_sources


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def acquire(
    root: pathlib.Path, source_id: str, rows: list[dict[str, str]]
) -> pathlib.Path:
    selected = [row for row in rows if row["source_id"] == source_id]
    destination = root / (
        "H0DN" if source_id == "h0dn" else "PantheonPlusSH0ES_DataRelease"
    )
    repository = selected[0]["repository"]
    commit = selected[0]["commit"]
    if not destination.exists():
        run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                repository,
                str(destination),
            ]
        )
    if source_id == "pantheonplus":
        run(
            [
                "git",
                "-C",
                str(destination),
                "sparse-checkout",
                "init",
                "--no-cone",
            ]
        )
        run(
            [
                "git",
                "-C",
                str(destination),
                "sparse-checkout",
                "set",
                "--no-cone",
                *[row["path"] for row in selected],
            ]
        )
    run(["git", "-C", str(destination), "checkout", "--detach", commit])
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path)
    parser.add_argument("--pantheonplus", type=pathlib.Path)
    parser.add_argument("--acquire-root", type=pathlib.Path)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        if args.acquire_root:
            root = args.acquire_root.resolve()
            root.mkdir(parents=True, exist_ok=True)
            rows = read_source_lock(
                project / "provenance" / "SOURCE_LOCK.tsv"
            )
            h0dn = acquire(root, "h0dn", rows)
            pantheonplus = acquire(root, "pantheonplus", rows)
        else:
            if not args.h0dn or not args.pantheonplus:
                parser.error(
                    "provide --h0dn and --pantheonplus, or --acquire-root"
                )
            h0dn = args.h0dn.resolve()
            pantheonplus = args.pantheonplus.resolve()
        result = verify_sources(
            project, {"h0dn": h0dn, "pantheonplus": pantheonplus}
        )
    except (
        AuditFailure,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(
        f"{result['status']}: "
        f"{sum(item['locked_file_count'] for item in result['repositories'].values())} "
        "locked files"
    )
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

