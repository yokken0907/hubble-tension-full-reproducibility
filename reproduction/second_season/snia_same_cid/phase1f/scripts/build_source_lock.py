#!/usr/bin/env python3
"""Build the Phase 1F fixed-commit source and upstream dependency locks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import subprocess


def git(root: pathlib.Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def git_text(root: pathlib.Path, *args: str) -> str:
    return git(root, *args).decode("utf-8").strip()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    parser.add_argument("--phase1d-zip", type=pathlib.Path, required=True)
    parser.add_argument("--phase1d-sidecar", type=pathlib.Path, required=True)
    parser.add_argument("--phase1e-zip", type=pathlib.Path, required=True)
    parser.add_argument("--phase1e-sidecar", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    config = json.loads((project / "provenance/DECISION_CONFIG.json").read_text(encoding="utf-8"))
    repo = args.pantheonplus.resolve()
    commit = config["pantheonplus"]["commit"]

    exact_paths = [
        "Pantheon+_Data/1_DATA/README",
        "Pantheon+_Data/2_CALIBRATION/README",
        "Pantheon+_Data/3_SALT2/README",
        "Pantheon+_Data/3_SALT2/CALIB_fitopts/ALL.fitopts",
        "Pantheon+_Data/3_SALT2/SALT2_B21trained_withsys/SALT2.MODEL000/SALT2.INFO",
        "Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat",
        "Pantheon+_Data/4_DISTANCES_AND_COVAR/README",
        config["pantheonplus"]["pipeline_config_path"],
    ]
    for name in ("HOSTGAL_LOGMASS", "HOSTGAL_sSFR", "VPEC", "VPEC_ERR", "REDSHIFT_CMB", "REDSHIFT_CMB_ERR"):
        exact_paths.append(f"Pantheon+_Data/1_DATA/header_overrides/{name}.txt")
    for item in config["series"]:
        base = f"{config['pantheonplus']['photometry_root']}/{item['directory']}"
        exact_paths.extend(f"{base}/{item[key]}" for key in ("list_file", "ignore_file", "readme_file"))
        exact_paths.extend((item["kcor_input"], item["kcor_output"]))
    exact_paths = sorted(set(exact_paths))

    rows = []
    for path in exact_paths:
        data = git(repo, "show", f"{commit}:{path}")
        oid = git_text(repo, "rev-parse", f"{commit}:{path}")
        rows.append({
            "source_id": "pantheonplus",
            "repository": config["pantheonplus"]["repository"],
            "commit": commit,
            "path": path,
            "git_blob_sha1": oid,
            "bytes": len(data),
            "sha256": sha_bytes(data),
        })
    with (project / "provenance/SOURCE_LOCK.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    tree_paths = [
        config["pantheonplus"]["photometry_root"],
        config["pantheonplus"]["calibration_root"],
        f"{config['pantheonplus']['calibration_root']}/SNANA_kcor",
        config["pantheonplus"]["filters_root"],
        config["pantheonplus"]["salt2_root"],
        "Pantheon+_Data/1_DATA/header_overrides",
    ]
    tree_paths.extend(f"{config['pantheonplus']['photometry_root']}/{item['directory']}" for item in config["series"])
    tree_paths.extend(
        f"{config['pantheonplus']['filters_root']}/{name}"
        for name in ("CFA3_native", "PS1_CFA4", "SNLS3-Landolt", "CSP_Str11", "CSP_TAMU_20180316", "KAIT_2018", "SWIFT")
    )
    tree_rows = [{"path": path, "git_tree_sha1": git_text(repo, "rev-parse", f"{commit}:{path}")} for path in sorted(set(tree_paths))]
    with (project / "provenance/TREE_LOCK.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "git_tree_sha1"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(tree_rows)

    phase1d_zip = args.phase1d_zip.resolve()
    phase1e_zip = args.phase1e_zip.resolve()
    p1d_hash = sha_file(phase1d_zip)
    p1e_hash = sha_file(phase1e_zip)
    sidecar_checks = {
        "phase1d": args.phase1d_sidecar.resolve().read_text(encoding="utf-8") == f"{p1d_hash}  {phase1d_zip.name}\n",
        "phase1e": args.phase1e_sidecar.resolve().read_text(encoding="utf-8") == f"{p1e_hash}  {phase1e_zip.name}\n",
    }
    copied = {}
    for key, expected_key in (
        ("phase1b_row_map_path", "phase1b_row_map_sha256"),
        ("phase1d_row_lineage_path", "phase1d_row_lineage_sha256"),
        ("phase1d_summary_path", "phase1d_summary_sha256"),
        ("phase1e_target_path", "phase1e_target_sha256"),
        ("phase1e_candidate_evidence_path", "phase1e_candidate_evidence_sha256"),
        ("phase1e_summary_path", "phase1e_summary_sha256"),
    ):
        rel = config["upstream"][key]
        path = project / rel
        copied[rel] = {"bytes": path.stat().st_size, "sha256": sha_file(path), "expected_sha256": config["upstream"][expected_key]}

    repository_lock = {
        "actual_commit": git_text(repo, "rev-parse", "HEAD"),
        "expected_commit": commit,
        "origin": git_text(repo, "remote", "get-url", "origin"),
        "photometry_tree_oid": git_text(repo, "rev-parse", f"{commit}:{config['pantheonplus']['photometry_root']}"),
        "calibration_tree_oid": git_text(repo, "rev-parse", f"{commit}:{config['pantheonplus']['calibration_root']}"),
        "salt2_tree_oid": git_text(repo, "rev-parse", f"{commit}:{config['pantheonplus']['salt2_root']}"),
        "source_lock_count": len(rows),
        "tree_lock_count": len(tree_rows),
    }
    write_json(project / "provenance/REPOSITORY_LOCK.json", repository_lock)
    dependency = {
        "phase1d": {"archive_name": phase1d_zip.name, "actual_sha256": p1d_hash, "expected_sha256": config["upstream"]["phase1d_archive_sha256"], "sidecar_status": "PASS" if sidecar_checks["phase1d"] else "FAIL"},
        "phase1e": {"archive_name": phase1e_zip.name, "actual_sha256": p1e_hash, "expected_sha256": config["upstream"]["phase1e_archive_sha256"], "sidecar_status": "PASS" if sidecar_checks["phase1e"] else "FAIL"},
        "copied_compact_ledgers": copied,
        "raw_upstream_bytes_redistributed": False,
    }
    write_json(project / "provenance/UPSTREAM_AUDIT_DEPENDENCIES.json", dependency)
    ok = (
        repository_lock["actual_commit"] == repository_lock["expected_commit"]
        and repository_lock["photometry_tree_oid"] == config["pantheonplus"]["photometry_tree_oid"]
        and repository_lock["calibration_tree_oid"] == config["pantheonplus"]["calibration_tree_oid"]
        and repository_lock["salt2_tree_oid"] == config["pantheonplus"]["salt2_tree_oid"]
        and p1d_hash == config["upstream"]["phase1d_archive_sha256"]
        and p1e_hash == config["upstream"]["phase1e_archive_sha256"]
        and all(sidecar_checks.values())
        and all(record["sha256"] == record["expected_sha256"] for record in copied.values())
    )
    print(json.dumps({"status": "PASS" if ok else "FAIL", "source_lock_count": len(rows), "tree_lock_count": len(tree_rows)}, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
