#!/usr/bin/env python3
"""Build the pre-execution source lock for Phase 1E."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import subprocess


def run_bytes(root: pathlib.Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    ).stdout


def run_text(root: pathlib.Path, *args: str) -> str:
    return run_bytes(root, *args).decode("utf-8").strip()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: pathlib.Path) -> str:
    return sha(path.read_bytes())


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--phase1d-zip", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    config = json.loads(
        (project / "provenance/DECISION_CONFIG.json").read_text(encoding="utf-8")
    )
    repo = args.pantheonplus.resolve()
    commit = config["pantheonplus"]["commit"]
    key_paths = [
        config["pantheonplus"]["catalog_path"],
        config["pantheonplus"]["distance_readme_path"],
        config["pantheonplus"]["pipeline_config_path"],
    ]
    root = config["pantheonplus"]["photometry_root"]
    for item in config["directory_inventory"]:
        base = f"{root}/{item['directory']}"
        key_paths.extend(
            f"{base}/{item[name]}"
            for name in ("list_file", "ignore_file", "readme_file")
        )
    rows = []
    for path in key_paths:
        data = run_bytes(repo, "show", f"{commit}:{path}")
        oid = run_text(repo, "rev-parse", f"{commit}:{path}")
        rows.append(
            {
                "source_id": "pantheonplus",
                "repository": config["pantheonplus"]["repository"],
                "commit": commit,
                "path": path,
                "git_blob_sha1": oid,
                "bytes": len(data),
                "sha256": sha(data),
            }
        )
    fields = list(rows[0])
    with (project / "provenance/SOURCE_LOCK.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    actual_tree = run_text(repo, "rev-parse", f"{commit}:{root}")
    phase1d_sha = file_sha(args.phase1d_zip.resolve())
    upstream_files = {}
    for key in (
        "phase1b_row_map_path",
        "phase1d_row_lineage_path",
        "phase1d_audit_summary_path",
    ):
        rel = config["upstream"][key]
        p = project / rel
        upstream_files[rel] = {"bytes": p.stat().st_size, "sha256": file_sha(p)}
    write_json(
        project / "provenance/REPOSITORY_LOCK.json",
        {
            "commit": run_text(repo, "rev-parse", "HEAD"),
            "expected_commit": commit,
            "origin": run_text(repo, "remote", "get-url", "origin"),
            "photometry_tree_oid": actual_tree,
            "expected_photometry_tree_oid": config["pantheonplus"]["photometry_tree_oid"],
            "locked_file_count": len(rows),
        },
    )
    write_json(
        project / "provenance/UPSTREAM_AUDIT_DEPENDENCIES.json",
        {
            "phase1d_archive_name": args.phase1d_zip.name,
            "phase1d_archive_expected_sha256": config["upstream"]["phase1d_archive_sha256"],
            "phase1d_archive_actual_sha256": phase1d_sha,
            "phase1d_archive_status": "PASS" if phase1d_sha == config["upstream"]["phase1d_archive_sha256"] else "FAIL",
            "copied_files": upstream_files,
            "upstream_bytes_redistributed": False,
        },
    )
    ok = (
        run_text(repo, "rev-parse", "HEAD") == commit
        and actual_tree == config["pantheonplus"]["photometry_tree_oid"]
        and phase1d_sha == config["upstream"]["phase1d_archive_sha256"]
        and all(
            upstream_files[config["upstream"][key]]["sha256"]
            == config["upstream"][key.replace("_path", "_sha256")]
            for key in (
                "phase1b_row_map_path",
                "phase1d_row_lineage_path",
                "phase1d_audit_summary_path",
            )
        )
    )
    print(json.dumps({"status": "PASS" if ok else "FAIL", "source_lock_rows": len(rows)}, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
