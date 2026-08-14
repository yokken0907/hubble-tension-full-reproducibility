#!/usr/bin/env python3
"""Separate-implementation cross-check of the Phase 1D result ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import pathlib
import subprocess
import sys
from collections import Counter


CONTRACT_ID = (
    "H0DN-SNIA-SAME-CID-MEASUREMENT-LINEAGE-"
    "PHASE1D-20260730-01"
)
FREEZE_SHA = (
    "9220e68d70c72324289a090634a541368aa7f28a84aaa70aae6a8e25c250f893"
)
SUCCESS = "AUDIT_COMPLETE_SHARED_DEPENDENCY_AND_LINEAGE_CLASSIFIED"
INPUT_LEVEL = "FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE"
DIRECT_ANCESTRY = "NOT_ESTABLISHED"
CONFIG_LEVEL = "CONFIGURATION_LEVEL"
ROW_INTERPRETATIONS = {
    "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE": (
        "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE"
    ),
    "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE": (
        "NO_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE"
    ),
    "AMBIGUOUS_ACTIVE_PUBLIC_PHOTOMETRY_FILES": (
        "MULTIPLE_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATES"
    ),
    "PHOTOMETRY_PARSE_FAILURE": (
        "FROZEN_CROSSWALK_CANDIDATE_EVALUATION_BLOCKED_BY_PARSE_FAILURE"
    ),
}
GROUP_INTERPRETATIONS = {
    "ALL_ROWS_UNIQUE_DISTINCT_PUBLIC_PHOTOMETRY_FILES": (
        "ALL_ROWS_HAVE_DISTINCT_UNIQUE_FROZEN_CROSSWALK_"
        "COMPATIBLE_INPUT_CANDIDATES"
    ),
    "PUBLIC_PHOTOMETRY_LINEAGE_UNRESOLVED": (
        "ONE_OR_MORE_ROWS_LACK_A_UNIQUE_FROZEN_CROSSWALK_"
        "COMPATIBLE_INPUT_CANDIDATE"
    ),
    "PUBLIC_PHOTOMETRY_FILE_REUSE_PRESENT": (
        "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE_"
        "FILE_REUSE_PRESENT"
    ),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(root: pathlib.Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    ).stdout


def git_text(root: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def tree(root: pathlib.Path, commit: str) -> dict[str, str]:
    output = git_bytes(root, "ls-tree", "-r", "-z", commit)
    result = {}
    for item in output.split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        _mode, kind, oid = metadata.decode("ascii").split()
        if kind == "blob":
            result[raw_path.decode("utf-8")] = oid
    return result


def entries(data: bytes) -> tuple[list[str], Counter[str]]:
    values = [
        line.strip()
        for line in data.decode("utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return values, Counter(values)


def parse(data: bytes) -> dict[str, object]:
    lines = data.splitlines()
    header = list(itertools.takewhile(
        lambda line: not line.startswith(b"OBS:"), lines
    ))

    def extract(prefix: bytes) -> list[bytes]:
        return [
            line[len(prefix):]
            for line in header
            if line.startswith(prefix)
        ]

    snids = extract(b"SNID:")
    surveys = extract(b"SURVEY:")
    nobs_values = extract(b"NOBS:")
    errors = []
    if len(snids) != 1:
        errors.append("SNID")
    if len(surveys) != 1:
        errors.append("SURVEY")
    if len(nobs_values) > 1:
        errors.append("NOBS_COUNT")
    try:
        snid = snids[0].decode("utf-8").strip(" \t")
        survey = " ".join(surveys[0].decode("utf-8").strip().split())
    except (IndexError, UnicodeDecodeError):
        snid = None
        survey = None
        errors.append("DECODE")
    observations = [
        line for line in lines if line.startswith(b"OBS:")
    ]
    nobs = None
    if len(nobs_values) == 1:
        try:
            nobs = int(nobs_values[0].decode("ascii").strip().split()[0])
            if nobs < 0 or nobs != len(observations):
                errors.append("NOBS_VALUE")
        except (ValueError, UnicodeDecodeError, IndexError):
            errors.append("NOBS_PARSE")
    obs_bytes = (
        b"\n".join(observations) + (b"\n" if observations else b"")
    )
    return {
        "SNID": snid,
        "SURVEY": survey,
        "NOBS": nobs,
        "observations": observations,
        "obs_count": len(observations),
        "obs_sha": sha(obs_bytes),
        "ok": not errors,
    }


def stringify(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    return [
        {
            key: (
                str(value).lower()
                if isinstance(value, bool)
                else str(value)
            )
            for key, value in row.items()
        }
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    results = project / "results"
    config = json.loads(
        (project / "provenance" / "DECISION_CONFIG.json").read_text()
    )
    commit = config["pantheonplus"]["commit"]
    pantheonplus = args.pantheonplus.resolve()
    h0dn = args.h0dn.resolve()
    checks: dict[str, bool] = {}
    checks["contract_freeze"] = (
        sha(
            (
                project / "provenance" / "CONTRACT_FREEZE.json"
            ).read_bytes()
        )
        == FREEZE_SHA
    )
    checks["repository_commits"] = (
        git_text(pantheonplus, "rev-parse", "HEAD") == commit
        and git_text(h0dn, "rev-parse", "HEAD")
        == config["h0dn"]["commit"]
    )
    checks["photometry_tree"] = (
        git_text(
            pantheonplus,
            "rev-parse",
            f"{commit}:{config['pantheonplus']['photometry_root']}",
        )
        == config["pantheonplus"]["photometry_tree_oid"]
    )
    map_path = project / config["phase1b_row_map"]["path"]
    checks["phase1b_map_hash"] = (
        sha(map_path.read_bytes())
        == config["phase1b_row_map"]["sha256"]
    )
    mapped = read_tsv(map_path)
    cid_counts = Counter(row["CID"] for row in mapped)
    population = [
        {
            "h0dn": int(row["h0dn_row_1based"]),
            "official": int(row["official_row_1based"]),
            "CID": row["CID"],
            "IDSURVEY": int(row["IDSURVEY"]),
        }
        for row in mapped
        if cid_counts[row["CID"]] > 1
    ]
    group_sizes = Counter(
        cid_counts[cid] for cid in cid_counts if cid_counts[cid] > 1
    )
    checks["population"] = (
        len(mapped) == 277
        and len(population) == 69
        and sum(group_sizes.values()) == 30
        and group_sizes == Counter({2: 21, 3: 9})
    )
    all_tree = tree(pantheonplus, commit)
    phot_root = config["pantheonplus"]["photometry_root"]
    dir_configs = {}
    for survey in config["source_vocabulary"].values():
        for directory in survey["directories"]:
            dir_configs[directory["directory"]] = directory
    parsed: dict[str, dict[str, object]] = {}
    by_directory: dict[str, dict[str, object]] = {}
    for dirname, directory in sorted(dir_configs.items()):
        base = f"{phot_root}/{dirname}"
        list_path = f"{base}/{directory['list_file']}"
        ignore_path = f"{base}/{directory['ignore_file']}"
        listed, list_count = entries(
            git_bytes(pantheonplus, "show", f"{commit}:{list_path}")
        )
        ignored, ignore_count = entries(
            git_bytes(pantheonplus, "show", f"{commit}:{ignore_path}")
        )
        if any(value != 1 for value in list_count.values()):
            raise RuntimeError(f"duplicate list entry in {list_path}")
        active_paths = []
        failures = []
        for filename in listed:
            if ignore_count[filename]:
                continue
            path = f"{base}/{filename}"
            if path not in all_tree:
                raise RuntimeError(f"missing list blob {path}")
            data = git_bytes(
                pantheonplus, "show", f"{commit}:{path}"
            )
            item = parse(data)
            item.update(
                {
                    "dir": dirname,
                    "path": path,
                    "blob": all_tree[path],
                    "bytes": len(data),
                    "sha": sha(data),
                    "list_count": list_count[filename],
                    "ignore_count": ignore_count[filename],
                }
            )
            parsed[path] = item
            active_paths.append(path)
            if not item["ok"]:
                failures.append(path)
        by_directory[dirname] = {
            "active": active_paths,
            "failures": failures,
            "listed": len(listed),
            "ignored": sum(
                1 for filename in listed if ignore_count[filename]
            ),
        }
    scan = json.loads(
        (results / "photometry_scan_summary.json").read_text()
    )
    checks["scan_summary"] = (
        scan["configured_directory_count"] == len(by_directory)
        and scan["active_file_count"]
        == sum(len(item["active"]) for item in by_directory.values())
        and scan["parse_failure_count"]
        == sum(len(item["failures"]) for item in by_directory.values())
    )
    row_rows: list[dict[str, object]] = []
    file_rows: list[dict[str, object]] = []
    selected: dict[int, dict[str, object]] = {}
    for row in population:
        vocab = config["source_vocabulary"][str(row["IDSURVEY"])]
        dirs = [item["directory"] for item in vocab["directories"]]
        accepted = set(vocab["survey_headers"])
        failures = sorted(
            path
            for dirname in dirs
            for path in by_directory[dirname]["failures"]
        )
        candidates = sorted(
            [
                parsed[path]
                for dirname in dirs
                for path in by_directory[dirname]["active"]
                if parsed[path]["ok"]
                and parsed[path]["SNID"] == row["CID"]
                and parsed[path]["SURVEY"] in accepted
            ],
            key=lambda item: item["path"],
        )
        if failures:
            status = "PHOTOMETRY_PARSE_FAILURE"
        elif len(candidates) == 1:
            status = "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
        elif len(candidates) == 0:
            status = "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
        else:
            status = "AMBIGUOUS_ACTIVE_PUBLIC_PHOTOMETRY_FILES"
        one = candidates[0] if len(candidates) == 1 else None
        if one:
            selected[row["h0dn"]] = one
        row_rows.append(
            {
                "h0dn_row_1based": row["h0dn"],
                "official_row_1based": row["official"],
                "CID": row["CID"],
                "IDSURVEY": row["IDSURVEY"],
                "survey_label": vocab["label"],
                "allowed_directories": ";".join(dirs),
                "active_candidate_count": len(candidates),
                "active_candidate_paths": ";".join(
                    item["path"] for item in candidates
                ),
                "unparseable_active_files_in_allowed_directories": len(
                    failures
                ),
                "lineage_status": status,
                "lineage_status_legacy": status,
                "lineage_status_interpretation": ROW_INTERPRETATIONS[status],
                "evidence_level": INPUT_LEVEL,
                "direct_final_measurement_ancestry": DIRECT_ANCESTRY,
                "unique_file_sha256": one["sha"] if one else "",
                "unique_file_git_blob_sha1": one["blob"] if one else "",
                "unique_file_nobs": (
                    one["NOBS"]
                    if one and one["NOBS"] is not None
                    else ""
                ),
                "unique_file_observation_line_count": (
                    one["obs_count"] if one else ""
                ),
            }
        )
        for item in candidates:
            file_rows.append(
                {
                    "h0dn_row_1based": row["h0dn"],
                    "official_row_1based": row["official"],
                    "CID": row["CID"],
                    "IDSURVEY": row["IDSURVEY"],
                    "survey_label": vocab["label"],
                    "source_directory": item["dir"],
                    "path": item["path"],
                    "git_blob_sha1": item["blob"],
                    "bytes": item["bytes"],
                    "sha256": item["sha"],
                    "SNID": item["SNID"],
                    "SURVEY": item["SURVEY"],
                    "NOBS": (
                        item["NOBS"]
                        if item["NOBS"] is not None
                        else ""
                    ),
                    "observation_line_count": item["obs_count"],
                    "observation_lines_sha256": item["obs_sha"],
                    "active_list_occurrences": item["list_count"],
                    "ignore_list_occurrences": item["ignore_count"],
                    "evidence_level": INPUT_LEVEL,
                    "direct_final_measurement_ancestry": DIRECT_ANCESTRY,
                }
            )
    row_rows.sort(key=lambda row: int(row["h0dn_row_1based"]))
    file_rows.sort(
        key=lambda row: (int(row["h0dn_row_1based"]), row["path"])
    )
    checks["row_ledger"] = (
        stringify(row_rows) == read_tsv(results / "row_lineage.tsv")
    )
    checks["candidate_file_ledger"] = (
        stringify(file_rows)
        == read_tsv(results / "candidate_file_evidence.tsv")
    )
    groups = {}
    for row in row_rows:
        groups.setdefault(row["CID"], []).append(row)
    group_rows = []
    pair_rows = []
    for cid, group in sorted(
        groups.items(), key=lambda item: int(item[1][0]["h0dn_row_1based"])
    ):
        resolved_pairs = overlaps = maximum = 0
        for left, right in itertools.combinations(group, 2):
            a = selected.get(int(left["h0dn_row_1based"]))
            b = selected.get(int(right["h0dn_row_1based"]))
            if a and b:
                shared = len(set(a["observations"]) & set(b["observations"]))
                resolved_pairs += 1
                overlaps += int(shared > 0)
                maximum = max(maximum, shared)
                pair_status = (
                    "BYTE_IDENTICAL_OBSERVATION_LINES_PRESENT"
                    if shared
                    else "NO_BYTE_IDENTICAL_OBSERVATION_LINES"
                )
                shared_value: object = shared
            else:
                pair_status = "UNRESOLVED_FILE_PAIR"
                shared_value = ""
            pair_rows.append(
                {
                    "CID": cid,
                    "h0dn_row_a_1based": left["h0dn_row_1based"],
                    "h0dn_row_b_1based": right["h0dn_row_1based"],
                    "path_a": a["path"] if a else "",
                    "path_b": b["path"] if b else "",
                    "file_a_observation_line_count": (
                        a["obs_count"] if a else ""
                    ),
                    "file_b_observation_line_count": (
                        b["obs_count"] if b else ""
                    ),
                    "shared_exact_observation_line_count": shared_value,
                    "observation_line_overlap_classification": pair_status,
                    "evidence_level": INPUT_LEVEL,
                    "direct_final_measurement_ancestry": DIRECT_ANCESTRY,
                }
            )
        unique_count = sum(
            row["lineage_status"]
            == "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
            for row in group
        )
        hashes = [
            row["unique_file_sha256"]
            for row in group
            if row["unique_file_sha256"]
        ]
        if unique_count != len(group):
            group_status = "PUBLIC_PHOTOMETRY_LINEAGE_UNRESOLVED"
        elif len(set(hashes)) == len(group):
            group_status = (
                "ALL_ROWS_UNIQUE_DISTINCT_PUBLIC_PHOTOMETRY_FILES"
            )
        else:
            group_status = "PUBLIC_PHOTOMETRY_FILE_REUSE_PRESENT"
        group_rows.append(
            {
                "CID": cid,
                "row_count": len(group),
                "h0dn_rows_1based": ";".join(
                    str(row["h0dn_row_1based"]) for row in group
                ),
                "IDSURVEY_codes": ";".join(
                    str(row["IDSURVEY"]) for row in group
                ),
                "survey_labels": ";".join(
                    str(row["survey_label"]) for row in group
                ),
                "row_lineage_statuses": ";".join(
                    str(row["lineage_status"]) for row in group
                ),
                "row_lineage_status_interpretations": ";".join(
                    str(row["lineage_status_interpretation"])
                    for row in group
                ),
                "unique_resolved_row_count": unique_count,
                "unique_compatible_candidate_row_count": unique_count,
                "distinct_resolved_file_sha256_count": len(set(hashes)),
                "distinct_compatible_candidate_sha256_count": len(
                    set(hashes)
                ),
                "pair_count": len(group) * (len(group) - 1) // 2,
                "resolved_pair_count": resolved_pairs,
                "compatible_candidate_pair_count": resolved_pairs,
                "pairs_with_byte_identical_observation_lines": overlaps,
                "maximum_shared_exact_observation_line_count": (
                    maximum if resolved_pairs else ""
                ),
                "group_lineage_classification": group_status,
                "group_lineage_classification_legacy": group_status,
                "group_lineage_interpretation": GROUP_INTERPRETATIONS[
                    group_status
                ],
                "evidence_level": INPUT_LEVEL,
                "direct_final_measurement_ancestry": DIRECT_ANCESTRY,
            }
        )
    checks["group_ledger"] = (
        stringify(group_rows) == read_tsv(results / "group_lineage.tsv")
    )
    checks["pair_ledger"] = (
        stringify(pair_rows)
        == read_tsv(results / "pair_observation_overlap.tsv")
    )
    pipeline_text = git_bytes(
        pantheonplus,
        "show",
        f"{commit}:{config['pantheonplus']['pipeline_config_path']}",
    ).decode("utf-8")
    active = [
        line.strip()
        for line in pipeline_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    anchor_rows = [
        {
            "anchor_id": anchor["anchor_id"],
            "expected_count": anchor["expected_count"],
            "actual_active_noncomment_exact_line_count": active.count(
                anchor["exact_text"]
            ),
            "exact_text_sha256": sha(
                anchor["exact_text"].encode("utf-8")
            ),
            "status": (
                "PASS"
                if active.count(anchor["exact_text"])
                == anchor["expected_count"]
                else "FAIL"
            ),
            "evidence_level": CONFIG_LEVEL,
            "executed_run_to_final_catalog_lineage": DIRECT_ANCESTRY,
        }
        for anchor in config["pipeline_anchors"]
    ]
    checks["pipeline_anchor_ledger"] = (
        stringify(anchor_rows)
        == read_tsv(results / "pipeline_anchor_evidence.tsv")
    )
    paths = sorted(all_tree)
    asset_rows = []
    for asset in config["referenced_assets"]:
        matches = [
            path
            for path in paths
            if pathlib.PurePosixPath(path).name == asset["basename"]
        ]
        asset_rows.append(
            {
                "asset_id": asset["asset_id"],
                "basename": asset["basename"],
                "required_for_full_lineage": asset[
                    "required_for_full_lineage"
                ],
                "tracked_match_count": len(matches),
                "tracked_paths": ";".join(matches),
                "availability_status": (
                    "TRACKED_IN_FROZEN_RELEASE"
                    if matches
                    else "REFERENCED_NOT_TRACKED_IN_FROZEN_RELEASE"
                ),
                "evidence_level": "REPOSITORY_TRACKING_CHECK",
                "original_analysis_asset_existence": "NOT_DETERMINED",
            }
        )
    checks["asset_ledger"] = (
        stringify(asset_rows)
        == read_tsv(results / "referenced_asset_availability.tsv")
    )
    correction = json.loads(
        (project / "provenance" / "CORRECTION_CONFIG.json").read_text()
    )
    readme_path = "Pantheon+_Data/4_DISTANCES_AND_COVAR/README"
    pplus_path = config["pantheonplus"]["pipeline_config_path"]
    legend = [
        line.strip()
        for line in git_bytes(
            pantheonplus, "show", f"{commit}:{readme_path}"
        ).decode("utf-8").splitlines()
        if "IDSURVEY - {" in line
    ]
    crosswalk_expected = []
    for code in config["expected_population"]["survey_codes"]:
        vocab = config["source_vocabulary"][str(code)]
        directories = [item["directory"] for item in vocab["directories"]]
        headers = list(vocab["survey_headers"])
        raw_lines = []
        for directory in directories:
            matches = [
                line
                for line in active
                if line.startswith("RAW_DIR:")
                and line.rstrip().endswith("/" + directory)
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"non-unique PPLUS RAW_DIR evidence for {directory}"
                )
            raw_lines.extend(matches)
        observations = sorted(
            {
                (str(row["path"]), str(row["git_blob_sha1"]), str(row["SURVEY"]))
                for row in file_rows
                if int(row["IDSURVEY"]) == code
            }
        )
        payload = {
            "IDSURVEY": code,
            "official_IDSURVEY_legend_line": legend[0],
            "frozen_crosswalk": {
                "published_label": vocab["label"],
                "allowed_directories": directories,
                "accepted_SURVEY_headers": headers,
            },
            "pplus_raw_dir_anchor_lines": raw_lines,
            "main_candidate_observations": [
                {"path": path, "git_blob_sha1": blob, "SURVEY": survey}
                for path, blob, survey in observations
            ],
        }
        excerpt_hash = sha(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )
        crosswalk_expected.append(
            {
                "IDSURVEY": code,
                "published_label": vocab["label"],
                "allowed_directory": ";".join(directories),
                "accepted_SURVEY_header": ";".join(headers),
                "evidence_source": (
                    "official IDSURVEY legend; frozen decision config; "
                    "PPLUS RAW_DIR anchors; main-audit active-file headers"
                ),
                "evidence_path_or_reference": ";".join(
                    [
                        readme_path,
                        pplus_path,
                        "provenance/DECISION_CONFIG.json",
                        "results/candidate_file_evidence.tsv",
                    ]
                ),
                "evidence_git_blob_or_version": ";".join(
                    [
                        f"commit={commit}",
                        f"IDSURVEY_README_blob={all_tree[readme_path]}",
                        f"PPLUS_blob={all_tree[pplus_path]}",
                        "photometry_tree="
                        + config["pantheonplus"]["photometry_tree_oid"],
                    ]
                ),
                "evidence_excerpt_sha256": excerpt_hash,
                "evidence_classification": correction[
                    "crosswalk_evidence_classification_by_IDSURVEY"
                ][str(code)],
                "posthoc_candidate_promoted": "NO",
                "evidence_excerpt_spec": correction[
                    "crosswalk_evidence_excerpt_spec"
                ],
            }
        )
    checks["crosswalk_evidence_ledger"] = (
        len(legend) == 1
        and stringify(crosswalk_expected)
        == read_tsv(
            project / "provenance" / "SURVEY_CROSSWALK_EVIDENCE.tsv"
        )
    )
    amendments = read_tsv(
        project / "provenance" / "CONTRACT_AMENDMENTS.tsv"
    )
    checks["amendment_register"] = (
        len(amendments) == 1
        and amendments[0]["amendment_id"] == "AMEND-001"
        and amendments[0]["new_results_observed"] == "YES"
        and amendments[0]["interpretation_affected"] == "YES"
    )
    summary = json.loads((results / "audit_summary.json").read_text())
    unique_rows = sum(
        row["lineage_status"]
        == "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
        for row in row_rows
    )
    all_assets = all(
        (not asset["required_for_full_lineage"])
        or row["availability_status"] == "TRACKED_IN_FROZEN_RELEASE"
        for asset, row in zip(config["referenced_assets"], asset_rows)
    )
    anchors_pass = all(row["status"] == "PASS" for row in anchor_rows)
    if unique_rows == 69 and anchors_pass and all_assets:
        classification = "PUBLIC_RELEASE_FULL_MEASUREMENT_LINEAGE"
    elif unique_rows == 0 and not any(
        row["status"] == "PASS" for row in anchor_rows
    ):
        classification = "PUBLIC_RELEASE_IDENTIFIER_ONLY_LINEAGE"
    else:
        classification = "PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE"
    checks["summary"] = (
        summary["audit_id"] == CONTRACT_ID
        and summary["status"] == SUCCESS
        and summary["release_sufficiency_classification"]
        == classification
        and summary["row_lineage"][
            "unique_active_public_photometry_file_count"
        ]
        == unique_rows
        and summary["group_lineage"]["group_count"] == len(group_rows)
        and summary["shared_pipeline"]["anchor_pass_count"]
        == sum(row["status"] == "PASS" for row in anchor_rows)
        and summary["interpretation"][
            "direct_final_measurement_ancestry"
        ]
        == DIRECT_ANCESTRY
        and summary["survey_crosswalk_evidence"]["row_count"] == 8
        and summary["survey_crosswalk_evidence"][
            "posthoc_candidate_promoted_count"
        ]
        == 0
    )
    result = {
        "audit_id": CONTRACT_ID,
        "check_count": len(checks),
        "pass_count": sum(checks.values()),
        "checks": checks,
        "recomputed_release_sufficiency_classification": classification,
        "recomputed_unique_row_count": unique_rows,
        "recomputed_group_count": len(group_rows),
        "verification_type": "SECOND_IMPLEMENTATION_CROSS_CHECK",
        "independent_external_replication": "NO",
        "peer_review_or_expert_endorsement": "NO",
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    (results / "independent_verification.json").write_text(
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
