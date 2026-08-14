#!/usr/bin/env python3
"""Run the frozen cross-CID payload-collision negative control."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
from collections import Counter, defaultdict

from auditlib import (
    build_candidate_map,
    load_config,
    mutual_unique_edges,
    payload_rounding_compatible,
    profile_candidates,
    read_json,
    read_tsv,
    sha256_file,
    write_json,
    write_tsv,
)


PAIR_FIELDS = (
    "CID_a", "CID_b", "h0dn_row_a_1based", "h0dn_row_b_1based",
    "source_directory_a", "source_directory_b", "observation_count_a",
    "observation_count_b", "observation_pair_opportunity_count",
    "rounding_compatible_edge_count", "mutual_unique_rounding_compatible_match_count",
    "negative_control_pair_classification"
)
STRATUM_FIELDS = (
    "source_directory_pair", "candidate_file_pair_count", "observation_pair_opportunity_count",
    "positive_candidate_file_pair_count", "mutual_unique_rounding_compatible_match_count"
)


def directory_pair(a: str, b: str) -> str:
    return ";".join(sorted((a, b)))


def protected_status(project: pathlib.Path) -> tuple[dict[str, object], bool]:
    freeze = read_json(project / "provenance/POSTHOC_PAYLOAD_COLLISION_NEGATIVE_CONTROL_FREEZE.json")
    passed = all(
        (project / relative).is_file()
        and (project / relative).stat().st_size == expected["bytes"]
        and sha256_file(project / relative) == expected["sha256"]
        for relative, expected in freeze["protected_main_results"].items()
    )
    return freeze, passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    config = load_config(project)
    freeze, protected_before = protected_status(project)
    if not protected_before or freeze["negative_control_result_observed_before_freeze"] is not False:
        raise RuntimeError("post-hoc freeze or protected main result mismatch")
    candidates, inventory = build_candidate_map(project, config)
    if inventory["status"] != "PASS":
        raise RuntimeError("candidate inventory mismatch")
    profiles, parsed = profile_candidates(args.pantheonplus.resolve(), candidates, config)
    main_pairs = read_tsv(project / "results/pair_dependency_classification.tsv")
    allowed_directory_pairs = {directory_pair(row["source_directory_a"], row["source_directory_b"]) for row in main_pairs}
    payload_fields = config["matching"]["payload_fields"]
    rows = []
    for index, a_row in enumerate(candidates):
        for b_row in candidates[index + 1:]:
            if a_row["CID"] == b_row["CID"]:
                continue
            stratum = directory_pair(a_row["source_directory"], b_row["source_directory"])
            if stratum not in allowed_directory_pairs:
                continue
            a = parsed[a_row["h0dn_row_1based"]]["observations"]
            b = parsed[b_row["h0dn_row_1based"]]["observations"]
            edges = [(i, j) for i, obs_a in enumerate(a) for j, obs_b in enumerate(b) if payload_rounding_compatible(obs_a, obs_b, payload_fields)]
            mutual = mutual_unique_edges(edges)
            rows.append({
                "CID_a": a_row["CID"],
                "CID_b": b_row["CID"],
                "h0dn_row_a_1based": a_row["h0dn_row_1based"],
                "h0dn_row_b_1based": b_row["h0dn_row_1based"],
                "source_directory_a": a_row["source_directory"],
                "source_directory_b": b_row["source_directory"],
                "observation_count_a": len(a),
                "observation_count_b": len(b),
                "observation_pair_opportunity_count": len(a) * len(b),
                "rounding_compatible_edge_count": len(edges),
                "mutual_unique_rounding_compatible_match_count": len(mutual),
                "negative_control_pair_classification": "CROSS_CID_POSITIVE" if mutual else "CROSS_CID_ZERO",
            })
    rows.sort(key=lambda row: (row["CID_a"], row["CID_b"], int(row["h0dn_row_a_1based"]), int(row["h0dn_row_b_1based"])))
    strata: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        key = directory_pair(row["source_directory_a"], row["source_directory_b"])
        strata[key]["candidate_file_pair_count"] += 1
        strata[key]["observation_pair_opportunity_count"] += int(row["observation_pair_opportunity_count"])
        strata[key]["positive_candidate_file_pair_count"] += row["negative_control_pair_classification"] == "CROSS_CID_POSITIVE"
        strata[key]["mutual_unique_rounding_compatible_match_count"] += int(row["mutual_unique_rounding_compatible_match_count"])
    stratum_rows = [{"source_directory_pair": key, **value} for key, value in sorted(strata.items())]
    positive = sum(row["negative_control_pair_classification"] == "CROSS_CID_POSITIVE" for row in rows)
    matches = sum(int(row["mutual_unique_rounding_compatible_match_count"]) for row in rows)
    opportunities = sum(int(row["observation_pair_opportunity_count"]) for row in rows)
    main_positive = sum(int(row["mutual_unique_rounding_compatible_match_count"]) > 0 for row in main_pairs)
    summary = {
        "status": "POSTHOC_NEGATIVE_CONTROL_COMPLETE",
        "chronology": "DESIGNED_AND_FROZEN_AFTER_MAIN_RESULT",
        "cross_CID_candidate_file_pair_count": len(rows),
        "cross_CID_observation_pair_opportunity_count": opportunities,
        "cross_CID_positive_candidate_file_pair_count": positive,
        "cross_CID_mutual_unique_rounding_match_count": matches,
        "main_same_CID_candidate_file_pair_count": len(main_pairs),
        "main_same_CID_positive_candidate_file_pair_count": main_positive,
        "directory_pair_stratum_count": len(stratum_rows),
        "interpretive_boundary": "NONEXCHANGEABLE_DESCRIPTIVE_COLLISION_SCREEN_NO_P_VALUE_NO_CAUSAL_INFERENCE_NO_MAIN_RESULT_CHANGE",
        "protected_main_results_unchanged_before_diagnostic": protected_before,
    }
    write_tsv(project / "results/posthoc_cross_cid_negative_control_pairs.tsv", rows, PAIR_FIELDS)
    write_tsv(project / "results/posthoc_cross_cid_negative_control_by_directory_pair.tsv", stratum_rows, STRATUM_FIELDS)
    write_json(project / "results/posthoc_cross_cid_negative_control_summary.json", summary)
    _, protected_after = protected_status(project)
    summary["protected_main_results_unchanged_after_diagnostic"] = protected_after
    write_json(project / "results/posthoc_cross_cid_negative_control_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0 if protected_after else 2


if __name__ == "__main__":
    raise SystemExit(main())
