#!/usr/bin/env python3
"""Build the pre-execution source and repository locks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import subprocess


H0DN_PATHS = (
    "data/sn1a_hf_pp.dat",
    "data/sn1a_covar_pp.dat",
    "h0_constrainer/configs/config.ini",
    "h0_constrainer/h0_constrainer/data_loader.py",
    "h0_constrainer/h0_constrainer/intercept.py",
    "h0_constrainer/h0_constrainer/main.py",
)
PANTHEON_KEY_PATHS = (
    "Pantheon+_Data/1_DATA/README",
    "Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat",
    "Pantheon+_Data/4_DISTANCES_AND_COVAR/README",
    "Pantheon+_Data/7_PIPPIN/PPLUS.yml",
)
FIELDS = (
    "source_id",
    "repository",
    "commit",
    "path",
    "git_blob_sha1",
    "bytes",
    "sha256",
)


def git(root: pathlib.Path, *args: str, binary: bool = False):
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return completed.stdout if binary else completed.stdout.strip()


def normalize_repository(value: str) -> str:
    value = value.strip().removesuffix("/")
    return value.removesuffix(".git")


def blob_row(
    source_id: str,
    root: pathlib.Path,
    repository: str,
    commit: str,
    path: str,
) -> dict[str, str | int]:
    data = git(root, "show", f"{commit}:{path}", binary=True)
    blob = git(root, "rev-parse", f"{commit}:{path}")
    return {
        "source_id": source_id,
        "repository": repository,
        "commit": commit,
        "path": path,
        "git_blob_sha1": blob,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    config = json.loads(
        (project / "provenance" / "DECISION_CONFIG.json").read_text(
            encoding="utf-8"
        )
    )
    roots = {
        "h0dn": args.h0dn.resolve(),
        "pantheonplus": args.pantheonplus.resolve(),
    }
    rows: list[dict[str, str | int]] = []
    source_paths: dict[str, set[str]] = {
        "h0dn": set(H0DN_PATHS),
        "pantheonplus": set(PANTHEON_KEY_PATHS),
    }
    photometry_root = config["pantheonplus"]["photometry_root"]
    for survey in config["source_vocabulary"].values():
        for directory in survey["directories"]:
            base = f"{photometry_root}/{directory['directory']}"
            for key in ("list_file", "ignore_file", "readme_file"):
                source_paths["pantheonplus"].add(
                    f"{base}/{directory[key]}"
                )
    repository_lock: dict[str, object] = {
        "contract_id": config["contract_id"],
        "repositories": {},
    }
    for source_id in ("h0dn", "pantheonplus"):
        root = roots[source_id]
        expected = config[source_id]
        commit = git(root, "rev-parse", "HEAD")
        repository = normalize_repository(
            git(root, "remote", "get-url", "origin")
        )
        if commit != expected["commit"]:
            raise RuntimeError(
                f"{source_id} commit mismatch: {commit}"
            )
        if repository != normalize_repository(expected["repository"]):
            raise RuntimeError(
                f"{source_id} repository mismatch: {repository}"
            )
        for path in sorted(source_paths[source_id]):
            rows.append(
                blob_row(
                    source_id,
                    root,
                    expected["repository"],
                    commit,
                    path,
                )
            )
        entry: dict[str, object] = {
            "repository": expected["repository"],
            "commit": commit,
            "commit_object_sha1": git(root, "rev-parse", f"{commit}^{{commit}}"),
            "locked_file_count": len(source_paths[source_id]),
        }
        if source_id == "pantheonplus":
            tree_path = expected["photometry_root"]
            entry["photometry_tree_path"] = tree_path
            entry["photometry_tree_oid"] = git(
                root, "rev-parse", f"{commit}:{tree_path}"
            )
        repository_lock["repositories"][source_id] = entry
    lock_path = project / "provenance" / "SOURCE_LOCK.tsv"
    with lock_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    repository_path = project / "provenance" / "REPOSITORY_LOCK.json"
    repository_path.write_text(
        json.dumps(repository_lock, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "repository_lock": str(repository_path),
                "source_lock": str(lock_path),
                "source_lock_rows": len(rows),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
