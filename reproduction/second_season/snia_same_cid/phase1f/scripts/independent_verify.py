#!/usr/bin/env python3
"""Second implementation of the Phase 1F main scan and post-hoc control."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import subprocess
from collections import Counter, defaultdict
from decimal import Decimal


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def git(repo: pathlib.Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def git_text(repo: pathlib.Path, *args: str) -> str:
    return git(repo, *args).decode("utf-8").strip()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def active_values(value: bytes) -> Counter[str]:
    return Counter(line.strip() for line in value.decode().splitlines() if line.strip() and not line.strip().startswith("#"))


def printed(value: str) -> tuple[Decimal, Decimal, Decimal]:
    number = Decimal(value)
    half = Decimal(1).scaleb(number.as_tuple().exponent) / 2
    return number, number - abs(half), number + abs(half)


def parse_lightcurve(data: bytes) -> dict[str, object]:
    lines = data.splitlines()
    header: dict[str, list[str]] = defaultdict(list)
    for raw in lines:
        if raw.startswith(b"OBS:") or b":" not in raw or raw.lstrip().startswith(b"#"):
            continue
        key, value = raw.split(b":", 1)
        header[key.decode().strip()].append(value.decode().strip())
    for name in ("SNID", "SURVEY", "VARLIST", "NOBS"):
        if len(header[name]) != 1:
            raise RuntimeError(f"header failure {name}")
    fields = header["VARLIST"][0].split()
    required = ("MJD", "FLT", "FLUXCAL", "FLUXCALERR", "MAG", "MAGERR")
    if not all(name in fields for name in required):
        raise RuntimeError("missing observation field")
    observations = []
    for index, raw in enumerate((line for line in lines if line.startswith(b"OBS:")), 1):
        values = raw[4:].decode().split()
        if len(values) != len(fields):
            raise RuntimeError("observation field count")
        tokens = dict(zip(fields, values, strict=True))
        numeric = {name: printed(tokens[name]) for name in required if name != "FLT"}
        observations.append({"index": index, "raw": raw[4:], "tokens": tokens, "numeric": numeric})
    if int(header["NOBS"][0].split()[0]) != len(observations):
        raise RuntimeError("NOBS mismatch")
    return {
        "SNID": header["SNID"][0].split()[0],
        "SURVEY": " ".join(header["SURVEY"][0].split()),
        "PHOTOMETRY_VERSION": header.get("PHOTOMETRY_VERSION", [""])[0].split()[0] if header.get("PHOTOMETRY_VERSION") else "",
        "FILTERS": header.get("FILTERS", [""])[0].split()[0] if header.get("FILTERS") else "",
        "VARLIST": fields,
        "observations": observations,
    }


def overlap(a: tuple[Decimal, Decimal, Decimal], b: tuple[Decimal, Decimal, Decimal]) -> bool:
    return max(a[1], b[1]) <= min(a[2], b[2])


def compatible(a: dict[str, object], b: dict[str, object]) -> bool:
    return all(overlap(a["numeric"][name], b["numeric"][name]) for name in ("FLUXCAL", "FLUXCALERR", "MAG", "MAGERR"))


def near(a: dict[str, object], b: dict[str, object]) -> bool:
    av, bv = a["numeric"], b["numeric"]
    rel = lambda x, y: abs(x - y) / max(abs(x), abs(y), Decimal(1))
    return (
        rel(av["FLUXCAL"][0], bv["FLUXCAL"][0]) <= Decimal("0.0001")
        and rel(av["FLUXCALERR"][0], bv["FLUXCALERR"][0]) <= Decimal("0.0001")
        and abs(av["MAG"][0] - bv["MAG"][0]) <= Decimal("0.0005")
        and abs(av["MAGERR"][0] - bv["MAGERR"][0]) <= Decimal("0.0005")
    )


def mutual(edges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    da, db = Counter(a for a, _ in edges), Counter(b for _, b in edges)
    return sorted((a, b) for a, b in edges if da[a] == db[b] == 1)


def compare_observations(a: list[dict[str, object]], b: list[dict[str, object]]) -> dict[str, int | str]:
    edges = [(i, j) for i, x in enumerate(a) for j, y in enumerate(b) if compatible(x, y)]
    near_edges = [(i, j) for i, x in enumerate(a) for j, y in enumerate(b) if near(x, y)]
    selected = mutual(edges)
    if len(selected) >= 2:
        classification = "REPEATED_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD"
    elif len(selected) == 1:
        classification = "SINGLE_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD"
    else:
        classification = "NO_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD"
    ca, cb = Counter(x["raw"] for x in a), Counter(x["raw"] for x in b)
    exact = sum(min(count, cb[value]) for value, count in ca.items())
    return {
        "exact": exact,
        "edges": len(edges),
        "mutual": len(selected),
        "ambiguous": len(edges) - len(selected),
        "near_edges": len(near_edges),
        "mutual_near": len(mutual(near_edges)),
        "classification": classification,
    }


def parse_kcor(data: bytes) -> list[dict[str, str]]:
    state = {name: "" for name in ("SURVEY", "FILTPATH", "MAGSYSTEM", "FILTSYSTEM")}
    definitions = []
    for original in data.decode().splitlines():
        line = original.split("#", 1)[0].strip()
        match = re.match(r"^([A-Z_0-9]+):\s*(.*)$", line)
        if not match:
            continue
        key, rest = match.groups()
        if key in state:
            state[key] = rest.split()[0] if rest else ""
        elif key == "FILTER":
            values = rest.split()
            label = values[0]
            token = label.split("/")[-1] if "/" in label else label.rsplit("-", 1)[-1]
            definitions.append({"token": token, "name": label, "file": values[1], **state})
    return definitions


def directory_pair(a: str, b: str) -> str:
    return ";".join(sorted((a, b)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    repo = args.pantheonplus.resolve()
    config = json.loads((project / "provenance/DECISION_CONFIG.json").read_text())
    commit = config["pantheonplus"]["commit"]
    checks: list[dict[str, object]] = []

    def check(name: str, actual: object, expected: object) -> None:
        checks.append({"name": name, "actual": actual, "expected": expected, "status": "PASS" if actual == expected else "FAIL"})

    phase1d = read_tsv(project / config["upstream"]["phase1d_row_lineage_path"])
    phase1e = {row["h0dn_row_1based"]: row for row in read_tsv(project / config["upstream"]["phase1e_target_path"])}
    candidates = []
    origins = Counter()
    for row in sorted(phase1d, key=lambda x: int(x["h0dn_row_1based"])):
        if row["lineage_status"] == "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE":
            path, origin = row["active_candidate_paths"], "PHASE1D_ACCEPTED_CORRECTED"
            origins["phase1d"] += 1
        else:
            target = phase1e[row["h0dn_row_1based"]]
            path, origin = target["candidate_paths"], "PHASE1E_ACCEPTED_CORRECTED"
            origins["phase1e"] += 1
        directory = pathlib.PurePosixPath(path).parts[pathlib.PurePosixPath(path).parts.index("photometry") + 1]
        candidates.append({**{key: row[key] for key in ("h0dn_row_1based", "official_row_1based", "CID", "IDSURVEY", "survey_label")}, "candidate_path": path, "source_directory": directory, "candidate_source_phase": origin})
    expected_candidates = read_tsv(project / "results/input_candidate_map.tsv")
    check("candidate_row_count", len(candidates), 69)
    check("candidate_origins", dict(sorted(origins.items())), {"phase1d": 38, "phase1e": 31})
    check("candidate_identity_and_paths", [(r["h0dn_row_1based"], r["CID"], r["IDSURVEY"], r["candidate_path"], r["candidate_source_phase"]) for r in candidates], [(r["h0dn_row_1based"], r["CID"], r["IDSURVEY"], r["candidate_path"], r["candidate_source_phase"]) for r in expected_candidates])
    cid_counts = Counter(row["CID"] for row in candidates)
    check("same_CID_group_count", sum(value > 1 for value in cid_counts.values()), 30)
    check("within_group_pair_count", sum(value * (value - 1) // 2 for value in cid_counts.values()), 48)
    check("distinct_candidate_paths", len({row["candidate_path"] for row in candidates}), 69)

    series = {item["directory"]: item for item in config["series"]}
    parsed: dict[str, dict[str, object]] = {}
    profiles = []
    for row in candidates:
        item = series[row["source_directory"]]
        base = f"{config['pantheonplus']['photometry_root']}/{row['source_directory']}"
        listed = active_values(git(repo, "show", f"{commit}:{base}/{item['list_file']}"))
        ignored = active_values(git(repo, "show", f"{commit}:{base}/{item['ignore_file']}"))
        filename = pathlib.PurePosixPath(row["candidate_path"]).name
        if listed[filename] != 1 or ignored[filename] != 0:
            raise RuntimeError("inactive candidate")
        data = git(repo, "show", f"{commit}:{row['candidate_path']}")
        lc = parse_lightcurve(data)
        if lc["SNID"] != row["CID"]:
            raise RuntimeError("SNID mismatch")
        lc["sha256"] = sha(data)
        lc["oid"] = git_text(repo, "rev-parse", f"{commit}:{row['candidate_path']}")
        lc["bytes"] = len(data)
        parsed[row["h0dn_row_1based"]] = lc
        tokens = Counter(obs["tokens"]["FLT"] for obs in lc["observations"])
        profiles.append((row["h0dn_row_1based"], len(lc["observations"]), ";".join(sorted(tokens)), lc["SURVEY"], lc["sha256"], lc["oid"]))
    expected_profiles = read_tsv(project / "results/row_input_profile.tsv")
    check("profile_row_count", len(profiles), 69)
    check("total_observation_count", sum(item[1] for item in profiles), 6744)
    check("distinct_blob_count", len({item[5] for item in profiles}), 69)
    check("profile_scientific_fields", profiles, [(row["h0dn_row_1based"], int(row["observation_count"]), row["used_filter_tokens"], row["raw_SURVEY"], row["sha256"], row["git_blob_sha1"]) for row in expected_profiles])
    check("source_directory_counts", dict(sorted(Counter(row["source_directory"] for row in candidates).items())), {"CSPDR3_anthony": 16, "CfA3_DJ20": 18, "KAIT_DS15": 16, "LOSS": 7, "PS1_LOWZ_COMBINED_TEXT_DS17": 9, "SWIFT": 3})

    by_cid: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidates:
        by_cid[row["CID"]].append(row)
    reconstructed_pairs = []
    for cid in sorted(by_cid):
        group = sorted(by_cid[cid], key=lambda row: int(row["h0dn_row_1based"]))
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                values = compare_observations(parsed[a["h0dn_row_1based"]]["observations"], parsed[b["h0dn_row_1based"]]["observations"])
                reconstructed_pairs.append((cid, a["h0dn_row_1based"], b["h0dn_row_1based"], values["exact"], values["edges"], values["mutual"], values["ambiguous"], values["near_edges"], values["mutual_near"], values["classification"]))
    expected_pairs = read_tsv(project / "results/pair_dependency_classification.tsv")
    check("pair_ledger_full_scientific_fields", reconstructed_pairs, [(r["CID"], r["h0dn_row_a_1based"], r["h0dn_row_b_1based"], int(r["byte_exact_observation_row_match_count"]), int(r["rounding_compatible_edge_count"]), int(r["mutual_unique_rounding_compatible_match_count"]), int(r["ambiguous_rounding_compatible_edge_count"]), int(r["near_payload_edge_count"]), int(r["mutual_unique_near_payload_match_count"]), r["primary_pair_classification"]) for r in expected_pairs])
    check("byte_exact_positive_pairs", sum(item[3] > 0 for item in reconstructed_pairs), 0)
    check("single_primary_pairs", sum(item[-1] == "SINGLE_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD" for item in reconstructed_pairs), 4)
    check("repeated_primary_pairs", sum(item[-1] == "REPEATED_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD" for item in reconstructed_pairs), 0)
    check("primary_mutual_match_count", sum(item[5] for item in reconstructed_pairs), 4)

    definition_cache: dict[str, list[dict[str, str]]] = {}
    filter_reconstructed = []
    for row in candidates:
        item = series[row["source_directory"]]
        if item["kcor_input"] not in definition_cache:
            definition_cache[item["kcor_input"]] = parse_kcor(git(repo, "show", f"{commit}:{item['kcor_input']}"))
        counts = Counter(obs["tokens"]["FLT"] for obs in parsed[row["h0dn_row_1based"]]["observations"])
        for token, count in sorted(counts.items()):
            matches = [definition for definition in definition_cache[item["kcor_input"]] if definition["token"] == token]
            definition = matches[0] if len(matches) == 1 else None
            oid = ""
            if definition:
                path = f"{config['pantheonplus']['filters_root']}/{pathlib.PurePosixPath(definition['FILTPATH']).name}/{definition['file']}"
                try:
                    oid = git_text(repo, "rev-parse", f"{commit}:{path}")
                except subprocess.CalledProcessError:
                    pass
            classification = "PUBLIC_KCOR_TEXT_AND_TRANSMISSION_ASSET_MAPPED" if len(matches) == 1 and oid else ("KCOR_FILTER_TOKEN_UNRESOLVED_OR_AMBIGUOUS" if len(matches) != 1 else "KCOR_FILTER_DEFINITION_WITHOUT_TRACKED_PUBLIC_TRANSMISSION_AT_IMPLIED_PATH")
            filter_reconstructed.append((row["h0dn_row_1based"], token, count, item["kcor_input"], len(matches), oid, classification))
    expected_filter = read_tsv(project / "results/filter_calibration_mapping.tsv")
    check("filter_mapping_full_core_fields", filter_reconstructed, [(r["h0dn_row_1based"], r["used_filter_token"], int(r["observation_count_for_token"]), r["kcor_input_path"], int(r["definition_count"]), r["public_transmission_git_blob_sha1"], r["mapping_classification"]) for r in expected_filter])
    check("row_filter_record_count", len(filter_reconstructed), 434)
    check("mapped_row_filter_records", sum(item[-1] == "PUBLIC_KCOR_TEXT_AND_TRANSMISSION_ASSET_MAPPED" for item in filter_reconstructed), 434)
    check("mapped_observations", sum(item[2] for item in filter_reconstructed if item[-1] == "PUBLIC_KCOR_TEXT_AND_TRANSMISSION_ASSET_MAPPED"), 6744)
    check("distinct_kcor_inputs", len({item[3] for item in filter_reconstructed}), 5)
    check("distinct_transmission_blobs", len({item[5] for item in filter_reconstructed if item[5]}), 50)

    pplus = git(repo, "show", f"{commit}:{config['pantheonplus']['pipeline_config_path']}").decode()
    series_output = read_tsv(project / "results/series_configuration_lineage.tsv")
    independent_series_pass = 0
    for item in config["series"]:
        aggregate = f"{item['datawithsys_task']}_{item['data_prep_task']}"
        anchors = (item["data_prep_task"] in pplus, item["directory"] in pplus, item["datawithsys_task"] in pplus, item["lcfitting_base_basename"] in pplus, f"*{item['kcor_alias']}" in pplus, aggregate in pplus)
        independent_series_pass += all(anchors)
    check("configuration_series_count", len(series_output), 7)
    check("configuration_series_pass_count", independent_series_pass, 7)
    check("recorded_configuration_pass_count", sum(row["configuration_anchor_status"] == "PASS" for row in series_output), 7)
    check("realdata_aggregation_membership_count", sum(row["realdata_aggregation_membership"] == "YES" for row in series_output), 7)

    allowed = {directory_pair(row["source_directory_a"], row["source_directory_b"]) for row in expected_pairs}
    control_rows = []
    for i, a in enumerate(candidates):
        for b in candidates[i + 1:]:
            if a["CID"] == b["CID"] or directory_pair(a["source_directory"], b["source_directory"]) not in allowed:
                continue
            ao = parsed[a["h0dn_row_1based"]]["observations"]
            bo = parsed[b["h0dn_row_1based"]]["observations"]
            edges = [(x, y) for x, left in enumerate(ao) for y, right in enumerate(bo) if compatible(left, right)]
            selected = mutual(edges)
            control_rows.append((directory_pair(a["source_directory"], b["source_directory"]), len(ao) * len(bo), len(selected)))
    control_summary = json.loads((project / "results/posthoc_cross_cid_negative_control_summary.json").read_text())
    check("negative_control_file_pair_count", len(control_rows), control_summary["cross_CID_candidate_file_pair_count"])
    check("negative_control_observation_opportunities", sum(row[1] for row in control_rows), control_summary["cross_CID_observation_pair_opportunity_count"])
    check("negative_control_positive_pair_count", sum(row[2] > 0 for row in control_rows), control_summary["cross_CID_positive_candidate_file_pair_count"])
    check("negative_control_mutual_match_count", sum(row[2] for row in control_rows), control_summary["cross_CID_mutual_unique_rounding_match_count"])
    strata = defaultdict(lambda: [0, 0, 0, 0])
    for key, opportunities, count in control_rows:
        strata[key][0] += 1
        strata[key][1] += opportunities
        strata[key][2] += count > 0
        strata[key][3] += count
    expected_strata = read_tsv(project / "results/posthoc_cross_cid_negative_control_by_directory_pair.tsv")
    check("negative_control_strata", [(key, *values) for key, values in sorted(strata.items())], [(row["source_directory_pair"], int(row["candidate_file_pair_count"]), int(row["observation_pair_opportunity_count"]), int(row["positive_candidate_file_pair_count"]), int(row["mutual_unique_rounding_compatible_match_count"])) for row in expected_strata])

    passed = sum(row["status"] == "PASS" for row in checks)
    result = {
        "verification_type": "WITHIN_PROJECT_SECOND_IMPLEMENTATION_NOT_EXTERNAL_REPLICATION",
        "check_count": len(checks),
        "pass_count": passed,
        "checks": checks,
        "status": "PASS" if passed == len(checks) else "FAIL",
    }
    output = project / "results/independent_verification.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "pass_count": passed, "check_count": len(checks)}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
