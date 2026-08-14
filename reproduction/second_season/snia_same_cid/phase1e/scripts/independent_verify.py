#!/usr/bin/env python3
"""Second-implementation Phase 1E cross-check using a separate parsing path."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter, defaultdict


FROZEN_CROSSWALK_DIRECTORIES = (
    "CSPDR3_anthony",
    "CSP_data2",
    "SWIFT",
    "LOSS",
    "KAIT_DS15",
    "CfA3_DJ20",
    "PS1_LOWZ_COMBINED_TEXT_DS17",
)
PREFERRED_TARGET_LABEL = "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_PUBLIC_INPUT_CANDIDATE"


def git(repo: pathlib.Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def git_text(repo: pathlib.Path, *args: str) -> str:
    return git(repo, *args).decode("utf-8").strip()


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_header(value: str) -> str:
    return " ".join(value.strip().split())


def parse_blob(raw: bytes) -> dict[str, object]:
    before_obs = []
    all_lines = raw.splitlines()
    for line in all_lines:
        if line[:4] == b"OBS:":
            break
        before_obs.append(line)

    def collect(prefix: bytes) -> list[bytes]:
        return [line.partition(b":")[2] for line in before_obs if line.startswith(prefix + b":")]

    snid_raw = collect(b"SNID")
    survey_raw = collect(b"SURVEY")
    nobs_raw = collect(b"NOBS")
    observations = [line for line in all_lines if line[:4] == b"OBS:"]
    errors = []
    if len(snid_raw) != 1:
        errors.append("SNID")
    if len(survey_raw) != 1:
        errors.append("SURVEY")
    if len(nobs_raw) > 1:
        errors.append("NOBS_COUNT")
    snid = snid_raw[0].decode("utf-8").strip(" \t") if len(snid_raw) == 1 else None
    survey = normalize_header(survey_raw[0].decode("utf-8")) if len(survey_raw) == 1 else None
    nobs = None
    if len(nobs_raw) == 1:
        try:
            nobs = int(nobs_raw[0].decode("ascii").strip().split()[0])
            if nobs < 0 or nobs != len(observations):
                errors.append("NOBS_VALUE")
        except (ValueError, IndexError, UnicodeError):
            errors.append("NOBS_PARSE")
    return {
        "SNID": snid,
        "SURVEY": survey,
        "NOBS": nobs,
        "observation_line_count": len(observations),
        "status": "PASS" if not errors else "FAIL",
    }


def active_names(raw: bytes) -> tuple[list[str], Counter[str]]:
    names = []
    for line in raw.decode("utf-8").split("\n"):
        token = line.strip(" \t\r")
        if token and token[0] != "#":
            names.append(token)
    return names, Counter(names)


def tree(repo: pathlib.Path, commit: str, prefix: str) -> dict[str, tuple[str, str]]:
    raw = git(repo, "ls-tree", "-r", "-z", commit, "--", prefix)
    output = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        left, right = record.split(b"\t", 1)
        _mode, kind, oid = left.decode("ascii").split()
        output[right.decode("utf-8")] = (kind, oid)
    return output


def scan(repo: pathlib.Path, config: dict[str, object]) -> list[dict[str, object]]:
    pp = config["pantheonplus"]
    commit = pp["commit"]
    root = pp["photometry_root"]
    objects = tree(repo, commit, root)
    output = []
    for source in config["directory_inventory"]:
        directory = source["directory"]
        base = f"{root}/{directory}"
        names, counts = active_names(git(repo, "show", f"{commit}:{base}/{source['list_file']}"))
        ignored, ignore_counts = active_names(git(repo, "show", f"{commit}:{base}/{source['ignore_file']}"))
        if any(value != 1 for value in counts.values()):
            raise RuntimeError("duplicate LIST entry")
        for name in names:
            if ignore_counts[name]:
                continue
            path = f"{base}/{name}"
            if path not in objects or objects[path][0] != "blob":
                raise RuntimeError("listed blob missing")
            raw = git(repo, "show", f"{commit}:{path}")
            parsed = parse_blob(raw)
            parsed.update(
                {
                    "source_directory": directory,
                    "path": path,
                    "git_blob_sha1": objects[path][1],
                    "bytes": len(raw),
                    "sha256": digest(raw),
                }
            )
            output.append(parsed)
    return output


def parse_catalog(raw: bytes) -> list[dict[str, str]]:
    lines = [line for line in raw.decode("utf-8").splitlines() if line.strip()]
    names = lines[0].split()
    rows = []
    for number, line in enumerate(lines[1:], 1):
        values = line.split()
        if len(values) != len(names):
            raise RuntimeError("catalog width mismatch")
        row = dict(zip(names, values, strict=True))
        row["catalog_row_1based"] = str(number)
        rows.append(row)
    return rows


def compare_rows(actual: list[dict[str, object]], recorded: list[dict[str, str]], fields: list[str]) -> bool:
    normalized = [{field: str(row.get(field, "")) for field in fields} for row in actual]
    selected = [{field: row[field] for field in fields} for row in recorded]
    return normalized == selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    results = project / "results"
    config = json.loads((project / "provenance/DECISION_CONFIG.json").read_text(encoding="utf-8"))
    repo = args.pantheonplus.resolve()
    commit = config["pantheonplus"]["commit"]

    phase1b = read_tsv(project / config["upstream"]["phase1b_row_map_path"])
    phase1b_counts = Counter(row["CID"] for row in phase1b)
    excluded = {cid for cid, count in phase1b_counts.items() if count > 1}
    phase1d = read_tsv(project / config["upstream"]["phase1d_row_lineage_path"])
    code_set = {str(code) for code in config["target"]["IDSURVEY_codes"]}
    targets = sorted(
        [
            row
            for row in phase1d
            if row["IDSURVEY"] in code_set
            and row["lineage_status"] == config["target"]["required_phase1d_status"]
        ],
        key=lambda row: int(row["h0dn_row_1based"]),
    )
    catalog = parse_catalog(git(repo, "show", f"{commit}:{config['pantheonplus']['catalog_path']}"))
    catalog_counts = Counter(row["CID"] for row in catalog)
    parsed_files = scan(repo, config)
    by_snid = defaultdict(list)
    for item in parsed_files:
        if item["status"] == "PASS":
            by_snid[item["SNID"]].append(item)
    eligible = [
        row
        for row in catalog
        if row["IDSURVEY"] in code_set
        and catalog_counts[row["CID"]] == 1
        and row["CID"] not in excluded
    ]
    holdout = []
    anchors = []
    for row in eligible:
        candidates = sorted(by_snid.get(row["CID"], []), key=lambda item: item["path"])
        if len(candidates) == 1:
            anchor_status = "TARGET_EXCLUDED_UNIQUE_FILE_ANCHOR"
        elif not candidates:
            anchor_status = "NO_ACTIVE_FILE_ACROSS_DIRECTORY_UNIVERSE"
        else:
            anchor_status = "AMBIGUOUS_ACTIVE_FILES_ACROSS_DIRECTORY_UNIVERSE"
        holdout.append(
            {
                "catalog_row_1based": row["catalog_row_1based"],
                "CID": row["CID"],
                "IDSURVEY": row["IDSURVEY"],
                "USED_IN_SH0ES_HF": row["USED_IN_SH0ES_HF"],
                "all_directory_candidate_count": len(candidates),
                "candidate_directories": ";".join(item["source_directory"] for item in candidates),
                "candidate_SURVEY_headers": ";".join(item["SURVEY"] for item in candidates),
                "candidate_paths": ";".join(item["path"] for item in candidates),
                "anchor_status": anchor_status,
            }
        )
        if len(candidates) == 1:
            item = candidates[0]
            anchors.append(
                {
                    "catalog_row_1based": row["catalog_row_1based"],
                    "CID": row["CID"],
                    "IDSURVEY": row["IDSURVEY"],
                    "USED_IN_SH0ES_HF": row["USED_IN_SH0ES_HF"],
                    "source_directory": item["source_directory"],
                    "SURVEY": item["SURVEY"],
                    "path": item["path"],
                    "git_blob_sha1": item["git_blob_sha1"],
                    "bytes": item["bytes"],
                    "sha256": item["sha256"],
                }
            )
    holdout.sort(key=lambda row: int(row["catalog_row_1based"]))
    anchors.sort(key=lambda row: int(row["catalog_row_1based"]))

    readme = git(repo, "show", f"{commit}:{config['pantheonplus']['distance_readme_path']}").decode("utf-8")
    readme = readme.replace("’", "'").replace("‘", "'")
    labels = {}
    for code in sorted(code_set, key=int):
        found = re.findall(rf"(?<!\d){code}\s*:\s*'([^']+)'", readme, flags=re.IGNORECASE)
        if len(found) != 1:
            raise RuntimeError("official label parse failure")
        labels[code] = found[0]
    inferred = []
    supported = config["classification"]["supported"]
    for code in sorted(code_set, key=int):
        e = [row for row in holdout if row["IDSURVEY"] == code]
        a = [row for row in anchors if row["IDSURVEY"] == code]
        directories = sorted({row["source_directory"] for row in a})
        headers = sorted({row["SURVEY"] for row in a})
        hf = sum(row["USED_IN_SH0ES_HF"] == "1" for row in a)
        if len(directories) > 1:
            status = config["classification"]["conflicting"]
        elif len(a) < 5 or hf < 3 or len(directories) != 1:
            status = config["classification"]["insufficient"]
        else:
            status = supported
        inferred.append(
            {
                "IDSURVEY": code,
                "official_label": labels[code],
                "eligible_row_count": len(e),
                "anchor_row_count": len(a),
                "hubble_flow_anchor_row_count": hf,
                "anchor_fraction": f"{len(a)}/{len(e)}",
                "distinct_source_directory_count": len(directories),
                "inferred_source_directory": directories[0] if len(directories) == 1 else "",
                "inferred_SURVEY_headers": ";".join(headers),
                "support_status": status,
            }
        )
    mapping = {row["IDSURVEY"]: row for row in inferred}
    target_rows = []
    target_files = []
    for target in targets:
        rule = mapping[target["IDSURVEY"]]
        headers = set(filter(None, rule["inferred_SURVEY_headers"].split(";")))
        candidates = []
        if rule["support_status"] == supported:
            candidates = sorted(
                [
                    item
                    for item in by_snid.get(target["CID"], [])
                    if item["source_directory"] == rule["inferred_source_directory"]
                    and item["SURVEY"] in headers
                ],
                key=lambda item: item["path"],
            )
        target_rows.append(
            {
                "h0dn_row_1based": target["h0dn_row_1based"],
                "official_row_1based": target["official_row_1based"],
                "CID": target["CID"],
                "IDSURVEY": target["IDSURVEY"],
                "phase1d_lineage_status": target["lineage_status"],
                "inferred_source_directory": rule["inferred_source_directory"],
                "inferred_SURVEY_headers": rule["inferred_SURVEY_headers"],
                "candidate_count": len(candidates),
                "candidate_paths": ";".join(item["path"] for item in candidates),
                "target_application_status": config["classification"]["target_unique"] if len(candidates) == 1 else config["classification"]["target_unresolved"],
            }
        )
        for item in candidates:
            target_files.append(
                {
                    "h0dn_row_1based": target["h0dn_row_1based"],
                    "official_row_1based": target["official_row_1based"],
                    "CID": target["CID"],
                    "IDSURVEY": target["IDSURVEY"],
                    "source_directory": item["source_directory"],
                    "SURVEY": item["SURVEY"],
                    "path": item["path"],
                    "git_blob_sha1": item["git_blob_sha1"],
                    "bytes": item["bytes"],
                    "sha256": item["sha256"],
                    "NOBS": item["NOBS"] if item["NOBS"] is not None else "",
                    "observation_line_count": item["observation_line_count"],
                }
            )
    target_rows.sort(key=lambda row: int(row["h0dn_row_1based"]))
    target_files.sort(key=lambda row: (int(row["h0dn_row_1based"]), row["path"]))

    comparisons = {
        "catalog_row_count_1701": len(catalog) == 1701,
        "phase1b_multirow_CID_count_30": len(excluded) == 30,
        "phase1d_target_row_count_31": len(targets) == 31,
        "active_file_count_847": len(parsed_files) == 847,
        "photometry_parse_failures_zero": all(item["status"] == "PASS" for item in parsed_files),
        "eligible_row_count_74": len(eligible) == 74,
        "anchor_row_count_62": len(anchors) == 62,
        "anchors_exclude_all_target_CIDs": not ({row["CID"] for row in anchors} & excluded),
        "holdout_ledger_exact": compare_rows(holdout, read_tsv(results / "holdout_candidate_rows.tsv"), list(holdout[0])),
        "anchor_ledger_exact": compare_rows(anchors, read_tsv(results / "holdout_anchor_evidence.tsv"), list(anchors[0])),
        "crosswalk_ledger_exact": compare_rows(inferred, read_tsv(results / "inferred_crosswalk.tsv"), list(inferred[0])),
        "three_crosswalks_supported": sum(row["support_status"] == supported for row in inferred) == 3,
        "target_ledger_exact": compare_rows(target_rows, read_tsv(results / "target_row_application.tsv"), list(target_rows[0])),
        "target_file_ledger_exact": compare_rows(target_files, read_tsv(results / "target_candidate_file_evidence.tsv"), list(target_files[0])),
        "target_rows_unique_31_of_31": sum(row["target_application_status"] == config["classification"]["target_unique"] for row in target_rows) == 31,
        "code65_label_header_token_mismatch": mapping["65"]["official_label"] == "CFA4p2" and "CFA4p1" in mapping["65"]["inferred_SURVEY_headers"],
    }
    summary = json.loads((results / "audit_summary.json").read_text(encoding="utf-8"))
    semantics = json.loads((results / "status_semantics.json").read_text(encoding="utf-8"))
    comparisons["summary_status_exact"] = summary["status"] == "AUDIT_COMPLETE_TARGET_EXCLUDED_PUBLIC_INTERNAL_CROSSWALK_CLASSIFIED"
    comparisons["summary_classification_exact"] = summary["scientific_classification"] == "PUBLIC_INTERNAL_CROSSWALK_SUPPORTED_3_OF_3_TARGET_ROWS_UNIQUE_31_OF_31"
    configured_directories = tuple(item["directory"] for item in config["directory_inventory"])
    universe = summary["crosswalk_universe"]
    comparisons["configured_directory_universe_exact"] = configured_directories == FROZEN_CROSSWALK_DIRECTORIES
    comparisons["summary_crosswalk_universe_exact"] = (
        universe["classification"] == "PROSPECTIVELY_FROZEN_SEVEN_PUBLIC_PHOTOMETRY_DIRECTORIES"
        and universe["configured_directory_count"] == 7
        and tuple(universe["directories"]) == FROZEN_CROSSWALK_DIRECTORIES
        and universe["uniqueness_scope"] == "WITHIN_FROZEN_SEVEN_DIRECTORY_UNIVERSE_ONLY"
    )
    comparisons["summary_broader_uniqueness_claims_false"] = (
        universe["full_public_photometry_tree_uniqueness_claim"] is False
        and universe["external_archive_uniqueness_claim"] is False
    )
    legacy_semantics = semantics["UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK"]
    comparisons["candidate_semantics_preferred_label"] = legacy_semantics["preferred_label"] == PREFERRED_TARGET_LABEL
    comparisons["candidate_semantics_denies_direct_ancestry"] = (
        "direct ancestry to the final m_b_corr row" in legacy_semantics["does_not_establish"]
        and "executed-run-to-final-catalog lineage" in legacy_semantics["does_not_establish"]
        and "statistical independence" in legacy_semantics["does_not_establish"]
    )
    interpretive_scope = summary["interpretive_scope"]
    comparisons["interpretive_scope_no_ancestry_or_independence"] = (
        interpretive_scope["target_application_preferred_label"] == PREFERRED_TARGET_LABEL
        and interpretive_scope["direct_final_measurement_ancestry_proven"] is False
        and interpretive_scope["fit_output_lineage_proven"] is False
        and interpretive_scope["bias_correction_run_lineage_proven"] is False
        and interpretive_scope["executed_run_to_final_catalog_lineage_proven"] is False
        and interpretive_scope["statistical_independence_proven"] is False
    )
    result = {
        "implementation": "second_implementation_manual_split_and_header_parser",
        "verification_scope": "SECOND_IMPLEMENTATION_INTERNAL_CROSSCHECK",
        "external_independent_replication": False,
        "expert_review_or_endorsement": False,
        "direct_final_measurement_ancestry_conclusion": False,
        "check_count": len(comparisons),
        "pass_count": sum(comparisons.values()),
        "checks": comparisons,
        "status": "PASS" if all(comparisons.values()) else "FAIL",
    }
    (results / "independent_verification.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"], "pass_count": result["pass_count"], "check_count": result["check_count"]}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError, UnicodeError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
