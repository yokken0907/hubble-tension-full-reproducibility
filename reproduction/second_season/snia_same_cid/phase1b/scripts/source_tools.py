#!/usr/bin/env python3
"""Acquire or verify the two separately distributed frozen sources."""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

from auditlib import AuditFailure, read_source_lock, verify_sources


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def acquire_one(
    source_id: str,
    destination: pathlib.Path,
    rows: list[dict[str, str]],
) -> None:
    selected = [row for row in rows if row["source_id"] == source_id]
    repository = selected[0]["repository"]
    commit = selected[0]["commit"]
    paths = [row["path"] for row in selected]
    if destination.exists():
        if not (destination / ".git").exists():
            raise AuditFailure(
                f"destination exists but is not a Git repository: {destination}"
            )
    else:
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
    run(["git", "-C", str(destination), "fetch", "origin", commit])
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
                *paths,
            ]
        )
    run(["git", "-C", str(destination), "checkout", "--detach", commit])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--h0dn", type=pathlib.Path)
    parser.add_argument("--pantheonplus", type=pathlib.Path)
    parser.add_argument("--acquire-root", type=pathlib.Path)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    manifest = args.manifest.resolve()
    try:
        if args.acquire_root:
            root = args.acquire_root.resolve()
            root.mkdir(parents=True, exist_ok=True)
            rows = read_source_lock(manifest)
            h0dn = root / "H0DN"
            pantheonplus = root / "PantheonPlusSH0ES_DataRelease"
            acquire_one("h0dn", h0dn, rows)
            acquire_one("pantheonplus", pantheonplus, rows)
        else:
            if args.h0dn is None or args.pantheonplus is None:
                parser.error(
                    "provide both --h0dn and --pantheonplus, or --acquire-root"
                )
            h0dn = args.h0dn.resolve()
            pantheonplus = args.pantheonplus.resolve()
        result = verify_sources(
            project,
            {"h0dn": h0dn, "pantheonplus": pantheonplus},
        )
    except (
        AuditFailure,
        OSError,
        subprocess.CalledProcessError,
        KeyError,
    ) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if result["status"] != "PASS":
        print(
            "FAIL: " + ", ".join(result["failures"]),
            file=sys.stderr,
        )
        return 2
    total = sum(
        record["locked_file_count"]
        for record in result["repositories"].values()
    )
    print(f"PASS: {total} locked files across 2 repositories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
