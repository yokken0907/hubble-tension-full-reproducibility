#!/usr/bin/env python3
"""Independently verify the post-hoc CID-only crosswalk diagnostic."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
from collections import Counter

import independent_verify as iv


POSTHOC_HASH = (
    "6b015a230dbf5cb8dcaf9bec516e81fdd5b4b79f1527588375f1d172b5fab603"
)
PROTECTED = (
    "audit_summary.json",
    "row_lineage.tsv",
    "group_lineage.tsv",
    "candidate_file_evidence.tsv",
    "referenced_asset_availability.tsv",
)


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    results = project / "results"
    contract = (
        project / "POSTHOC_CID_ONLY_CROSSWALK_DIAGNOSTIC_CONTRACT.md"
    )
    config = json.loads(
        (project / "provenance" / "DECISION_CONFIG.json").read_text()
    )
    pantheonplus = args.pantheonplus.resolve()
    commit = config["pantheonplus"]["commit"]
    all_tree = iv.tree(pantheonplus, commit)
    phot_root = config["pantheonplus"]["photometry_root"]
    unique_dirs = {}
    for survey in config["source_vocabulary"].values():
        for directory in survey["directories"]:
            unique_dirs[directory["directory"]] = directory
    parsed = []
    for dirname, directory in sorted(unique_dirs.items()):
        base = f"{phot_root}/{dirname}"
        listed, _ = iv.entries(
            iv.git_bytes(
                pantheonplus,
                "show",
                f"{commit}:{base}/{directory['list_file']}",
            )
        )
        ignored, ignore_counts = iv.entries(
            iv.git_bytes(
                pantheonplus,
                "show",
                f"{commit}:{base}/{directory['ignore_file']}",
            )
        )
        for filename in listed:
            if ignore_counts[filename]:
                continue
            path = f"{base}/{filename}"
            data = iv.git_bytes(
                pantheonplus, "show", f"{commit}:{path}"
            )
            item = iv.parse(data)
            if item["ok"]:
                item.update(
                    {
                        "path": path,
                        "dir": dirname,
                        "blob": all_tree[path],
                        "sha": hashlib.sha256(data).hexdigest(),
                    }
                )
                parsed.append(item)
    main_rows = read_tsv(results / "row_lineage.tsv")
    used_paths = {
        row["active_candidate_paths"]
        for row in main_rows
        if row["lineage_status"]
        == "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
    }
    rows = []
    candidates_out = []
    for row in main_rows:
        if (
            row["lineage_status"]
            == "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
        ):
            continue
        candidates = sorted(
            [item for item in parsed if item["SNID"] == row["CID"]],
            key=lambda item: item["path"],
        )
        if len(candidates) == 0:
            classification = "NO_CID_ONLY_PUBLIC_FILE"
        elif len(candidates) == 1:
            classification = (
                "ONE_CID_ONLY_PUBLIC_FILE_OUTSIDE_FROZEN_CROSSWALK"
            )
        else:
            classification = (
                "MULTIPLE_CID_ONLY_PUBLIC_FILES_OUTSIDE_FROZEN_CROSSWALK"
            )
        used = [
            item["path"] for item in candidates
            if item["path"] in used_paths
        ]
        rows.append(
            {
                "h0dn_row_1based": row["h0dn_row_1based"],
                "official_row_1based": row["official_row_1based"],
                "CID": row["CID"],
                "IDSURVEY": row["IDSURVEY"],
                "survey_label": row["survey_label"],
                "main_lineage_status": row["lineage_status"],
                "cid_only_candidate_count": str(len(candidates)),
                "cid_only_candidate_paths": ";".join(
                    item["path"] for item in candidates
                ),
                "cid_only_candidate_directories": ";".join(
                    item["dir"] for item in candidates
                ),
                "cid_only_candidate_SURVEY_headers": ";".join(
                    str(item["SURVEY"]) for item in candidates
                ),
                "candidate_paths_used_by_other_main_rows": ";".join(used),
                "cid_only_classification": classification,
            }
        )
        for item in candidates:
            candidates_out.append(
                {
                    "target_h0dn_row_1based": row["h0dn_row_1based"],
                    "target_CID": row["CID"],
                    "target_IDSURVEY": row["IDSURVEY"],
                    "target_survey_label": row["survey_label"],
                    "path": item["path"],
                    "source_directory": item["dir"],
                    "SNID": str(item["SNID"]),
                    "SURVEY": str(item["SURVEY"]),
                    "git_blob_sha1": item["blob"],
                    "sha256": item["sha"],
                    "used_by_other_main_row": str(
                        item["path"] in used_paths
                    ).lower(),
                }
            )
    rows.sort(key=lambda row: int(row["h0dn_row_1based"]))
    candidates_out.sort(
        key=lambda row: (
            int(row["target_h0dn_row_1based"]),
            row["path"],
        )
    )
    actual_rows = read_tsv(
        results / "posthoc_cid_only_crosswalk_diagnostic.tsv"
    )
    actual_candidates = read_tsv(
        results / "posthoc_cid_only_candidate_files.tsv"
    )
    summary = json.loads(
        (
            results / "posthoc_cid_only_crosswalk_summary.json"
        ).read_text()
    )
    survey_defs = sorted(
        path
        for path in all_tree
        if pathlib.PurePosixPath(path).name == "SURVEY.DEF"
    )
    checks = {
        "contract_hash": hashlib.sha256(
            contract.read_bytes()
        ).hexdigest() == POSTHOC_HASH,
        "row_ledger": rows == actual_rows,
        "candidate_ledger": candidates_out == actual_candidates,
        "summary_row_count": (
            summary["unresolved_main_row_count"] == len(rows)
        ),
        "summary_candidate_count": (
            summary["cid_only_candidate_ledger_row_count"]
            == len(candidates_out)
        ),
        "summary_classifications": (
            summary["classification_counts"]
            == dict(
                sorted(
                    Counter(
                        row["cid_only_classification"] for row in rows
                    ).items()
                )
            )
        ),
        "survey_def": (
            summary["survey_def"]["tracked_paths"] == survey_defs
        ),
        "protected_hashes": all(
            summary["protected_main_results"][name]["before_sha256"]
            == summary["protected_main_results"][name]["after_sha256"]
            == hashlib.sha256((results / name).read_bytes()).hexdigest()
            for name in PROTECTED
        ),
        "promotion_status": (
            summary["promotion_status"]
            == "POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE"
        ),
    }
    result = {
        "check_count": len(checks),
        "pass_count": sum(checks.values()),
        "checks": checks,
        "verification_type": "SECOND_IMPLEMENTATION_CROSS_CHECK",
        "independent_external_replication": "NO",
        "peer_review_or_expert_endorsement": "NO",
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    (
        results
        / "posthoc_cid_only_crosswalk_independent_verification.json"
    ).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"]}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
