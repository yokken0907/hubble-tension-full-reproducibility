#!/usr/bin/env python3
"""Run the frozen post-hoc CID-only crosswalk diagnostic."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import sys
from collections import Counter

from auditlib import git_tree_entries, load_config, scan_photometry, write_json


POSTHOC_ID = (
    "H0DN-SNIA-PHASE1D-POSTHOC-CID-ONLY-CROSSWALK-20260730-01"
)
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
ROW_FIELDS = (
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "survey_label",
    "main_lineage_status",
    "cid_only_candidate_count",
    "cid_only_candidate_paths",
    "cid_only_candidate_directories",
    "cid_only_candidate_SURVEY_headers",
    "candidate_paths_used_by_other_main_rows",
    "cid_only_classification",
)
CANDIDATE_FIELDS = (
    "target_h0dn_row_1based",
    "target_CID",
    "target_IDSURVEY",
    "target_survey_label",
    "path",
    "source_directory",
    "SNID",
    "SURVEY",
    "git_blob_sha1",
    "sha256",
    "used_by_other_main_row",
)


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(
    path: pathlib.Path,
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    results = project / "results"
    contract = (
        project / "POSTHOC_CID_ONLY_CROSSWALK_DIAGNOSTIC_CONTRACT.md"
    )
    if sha(contract) != POSTHOC_HASH:
        raise RuntimeError("post-hoc contract hash mismatch")
    sidecar = contract.with_suffix(".sha256")
    if sidecar.read_text(encoding="utf-8") != (
        f"{POSTHOC_HASH}  {contract.name}\n"
    ):
        raise RuntimeError("post-hoc contract sidecar mismatch")
    before = {name: sha(results / name) for name in PROTECTED}
    config = load_config(project)
    directories, parsed, _scan = scan_photometry(
        args.pantheonplus.resolve(), config
    )
    main_rows = read_tsv(results / "row_lineage.tsv")
    used_main_paths = {
        row["active_candidate_paths"]
        for row in main_rows
        if row["lineage_status"]
        == "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
    }
    all_active = sorted(
        path
        for directory in directories.values()
        for path in directory["active_paths"]
        if parsed[path]["status"] == "PASS"
    )
    output_rows = []
    candidate_rows = []
    for row in main_rows:
        if (
            row["lineage_status"]
            == "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
        ):
            continue
        candidates = [
            parsed[path]
            for path in all_active
            if parsed[path]["SNID"] == row["CID"]
        ]
        if not candidates:
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
            item["path"]
            for item in candidates
            if item["path"] in used_main_paths
        ]
        output_rows.append(
            {
                "h0dn_row_1based": row["h0dn_row_1based"],
                "official_row_1based": row["official_row_1based"],
                "CID": row["CID"],
                "IDSURVEY": row["IDSURVEY"],
                "survey_label": row["survey_label"],
                "main_lineage_status": row["lineage_status"],
                "cid_only_candidate_count": len(candidates),
                "cid_only_candidate_paths": ";".join(
                    item["path"] for item in candidates
                ),
                "cid_only_candidate_directories": ";".join(
                    item["source_directory"] for item in candidates
                ),
                "cid_only_candidate_SURVEY_headers": ";".join(
                    item["SURVEY"] for item in candidates
                ),
                "candidate_paths_used_by_other_main_rows": ";".join(used),
                "cid_only_classification": classification,
            }
        )
        for item in candidates:
            candidate_rows.append(
                {
                    "target_h0dn_row_1based": row["h0dn_row_1based"],
                    "target_CID": row["CID"],
                    "target_IDSURVEY": row["IDSURVEY"],
                    "target_survey_label": row["survey_label"],
                    "path": item["path"],
                    "source_directory": item["source_directory"],
                    "SNID": item["SNID"],
                    "SURVEY": item["SURVEY"],
                    "git_blob_sha1": item["git_blob_sha1"],
                    "sha256": item["sha256"],
                    "used_by_other_main_row": str(
                        item["path"] in used_main_paths
                    ).lower(),
                }
            )
    output_rows.sort(key=lambda row: int(row["h0dn_row_1based"]))
    candidate_rows.sort(
        key=lambda row: (
            int(row["target_h0dn_row_1based"]),
            row["path"],
        )
    )
    write_tsv(
        results / "posthoc_cid_only_crosswalk_diagnostic.tsv",
        output_rows,
        ROW_FIELDS,
    )
    write_tsv(
        results / "posthoc_cid_only_candidate_files.tsv",
        candidate_rows,
        CANDIDATE_FIELDS,
    )
    tree = git_tree_entries(
        args.pantheonplus.resolve(), config["pantheonplus"]["commit"]
    )
    survey_def_paths = sorted(
        path
        for path in tree
        if pathlib.PurePosixPath(path).name == "SURVEY.DEF"
    )
    classification_counts = Counter(
        row["cid_only_classification"] for row in output_rows
    )
    by_survey = {}
    for code in sorted({row["IDSURVEY"] for row in output_rows}, key=int):
        selected = [row for row in output_rows if row["IDSURVEY"] == code]
        by_survey[code] = {
            "row_count": len(selected),
            "cid_only_candidate_count": sum(
                int(row["cid_only_candidate_count"]) for row in selected
            ),
            "classification_counts": dict(
                sorted(
                    Counter(
                        row["cid_only_classification"]
                        for row in selected
                    ).items()
                )
            ),
        }
    after = {name: sha(results / name) for name in PROTECTED}
    protected = {
        name: {
            "before_sha256": before[name],
            "after_sha256": after[name],
            "byte_unchanged": before[name] == after[name],
        }
        for name in PROTECTED
    }
    summary = {
        "diagnostic_id": POSTHOC_ID,
        "status": "POSTHOC_DIAGNOSTIC_COMPLETE",
        "promotion_status": "POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE",
        "main_release_sufficiency_classification": json.loads(
            (results / "audit_summary.json").read_text()
        )["release_sufficiency_classification"],
        "unresolved_main_row_count": len(output_rows),
        "cid_only_candidate_ledger_row_count": len(candidate_rows),
        "classification_counts": dict(sorted(classification_counts.items())),
        "by_IDSURVEY": by_survey,
        "survey_def": {
            "tracked_match_count": len(survey_def_paths),
            "tracked_paths": survey_def_paths,
            "availability_status": (
                "TRACKED_IN_FROZEN_RELEASE"
                if survey_def_paths
                else "NOT_TRACKED_IN_FROZEN_RELEASE"
            ),
        },
        "protected_main_results": protected,
        "all_protected_main_results_byte_unchanged": all(
            record["byte_unchanged"] for record in protected.values()
        ),
        "nonclaims": [
            "CID-only candidates are not promoted to direct final-measurement ancestors",
            "no alternate IDSURVEY crosswalk is inferred",
            "no main result or classification is changed",
            "no covariance or H0 result is changed"
        ],
    }
    write_json(
        results / "posthoc_cid_only_crosswalk_summary.json", summary
    )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "promotion_status": summary["promotion_status"],
            },
            sort_keys=True,
        )
    )
    return (
        0
        if summary["all_protected_main_results_byte_unchanged"]
        else 2
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
