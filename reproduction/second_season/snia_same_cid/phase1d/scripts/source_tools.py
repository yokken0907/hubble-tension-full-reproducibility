#!/usr/bin/env python3
"""Acquire or verify the two frozen upstream Git repositories."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

from auditlib import normalize_repository, verify_sources


def run(*args: str) -> None:
    subprocess.run(list(args), check=True)


def acquire_one(repository: str, commit: str, destination: pathlib.Path) -> None:
    if destination.exists():
        if not (destination / "HEAD").is_file():
            raise RuntimeError(f"destination already exists: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(
        "git",
        "clone",
        "--bare",
        "--filter=blob:none",
        repository,
        str(destination),
    )
    run("git", "-C", str(destination), "fetch", "origin", commit)
    run(
        "git",
        "-C",
        str(destination),
        "symbolic-ref",
        "HEAD",
        "refs/heads/audit-frozen",
    )
    run(
        "git",
        "-C",
        str(destination),
        "update-ref",
        "refs/heads/audit-frozen",
        commit,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    acquire = subparsers.add_parser("acquire")
    acquire.add_argument("--destination", type=pathlib.Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--h0dn", type=pathlib.Path, required=True)
    verify.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    config = json.loads(
        (project / "provenance" / "DECISION_CONFIG.json").read_text()
    )
    if args.command == "acquire":
        root = args.destination.resolve()
        h0dn = root / "H0DN.git"
        pantheonplus = root / "PantheonPlusSH0ES-DataRelease.git"
        acquire_one(
            config["h0dn"]["repository"], config["h0dn"]["commit"], h0dn
        )
        acquire_one(
            config["pantheonplus"]["repository"],
            config["pantheonplus"]["commit"],
            pantheonplus,
        )
    else:
        h0dn = args.h0dn.resolve()
        pantheonplus = args.pantheonplus.resolve()
    result = verify_sources(
        project, {"h0dn": h0dn, "pantheonplus": pantheonplus}
    )
    result["roots"] = {
        "h0dn": h0dn.name,
        "pantheonplus": pantheonplus.name,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
