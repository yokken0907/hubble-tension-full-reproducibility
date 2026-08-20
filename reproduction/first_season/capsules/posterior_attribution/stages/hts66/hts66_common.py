#!/usr/bin/env python3
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import os
import shutil
import zipfile
from pathlib import Path

STAGES = {
    59: {
        "filename": "HTS59_RESULTS_FOR_REVIEW.zip",
        "sha256": "1557c7f4ec5a08f1714d008f67c46a014d9c8773a444c76bdceaaee60bf129fd",
        "classification": "PASS_TN2D_SUFFICIENCY_AND_CONDITIONAL_4D_RESIDUAL_AUDIT",
    },
    60: {
        "filename": "HTS60_RESULTS_FOR_REVIEW.zip",
        "sha256": "5077137b284feffaf81fa2afc0f71bd4a84c1dfa705906d8f384e3f6cce9e847",
        "classification": "PASS_CONDITIONAL_4D_EIGENMODE_LOCALIZATION_AUDIT",
    },
    61: {
        "filename": "HTS61_RESULTS_FOR_REVIEW.zip",
        "sha256": "a3cee388510a17bcd218b9485759760ed579f1c5d9c8c02f572b2fc44c38b0e3",
        "classification": "PASS_CONDITIONAL_EIGENMODE_IDENTIFIABILITY_AND_SUBSPACE_STABILITY_AUDIT",
    },
    62: {
        "filename": "HTS62_RESULTS_FOR_REVIEW.zip",
        "sha256": "f51b60503ae20361c9fbcdff4d50b2bac74266b0a270545cb71fe60b582c7a18",
        "classification": "PASS_FIXED_BLOCK_SHAPLEY_AND_ORDER_SENSITIVITY_AUDIT",
    },
    63: {
        "filename": "HTS63_RESULTS_FOR_REVIEW.zip",
        "sha256": "6edf04ec0af66629015f08964986b508864e3430cb27ff99e078db83086a4456",
        "classification": "PASS_EXACT_VARIABLE_SHAPLEY_AND_OWEN_COALITION_AUDIT",
    },
    64: {
        "filename": "HTS64_RESULTS_FOR_REVIEW.zip",
        "sha256": "0f00f14c0a122fcb4f6dd3d522f4d01de199d279acbd0c3b8c99ebef27a35b3d",
        "classification": "PASS_WITHIN_BLOCK_REPARAMETERIZATION_INVARIANCE_AUDIT",
    },
    65: {
        "filename": "HTS65_RESULTS_FOR_REVIEW.zip",
        "sha256": "0cd4714c250806eb2153900a5e42510655c715eb150b713e76338bc08cb326ab",
        "classification": "PASS_EXHAUSTIVE_COALITION_PARTITION_SENSITIVITY_AUDIT",
    },
}

TABLES = {
    59: "HTS59_DIRECTED_6D_DECOMPOSITION.tsv",
    60: "HTS60_DIRECTED_MODE_SUMMARY.tsv",
    61: "HTS61_EDGE_CONTRIBUTION_IDENTIFIABILITY.tsv",
    62: "HTS62_DIRECTED_FIXED_BLOCK_DECOMPOSITION.tsv",
    63: "HTS63_DIRECTED_VARIABLE_ALLOCATION_SUMMARY.tsv",
    64: "HTS64_REPARAMETERIZATION_SUMMARY.tsv",
    65: "HTS65_DIRECTED_PARTITION_SUMMARY.tsv",
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def candidate_paths(downloads: Path, store: Path, filename: str):
    seen = set()
    direct = [downloads / filename, store / filename]
    for p in direct:
        if p.exists():
            q = p.resolve()
            if q not in seen:
                seen.add(q)
                yield q
    for root in (downloads, store):
        if not root.exists():
            continue
        for p in root.rglob(filename):
            try:
                q = p.resolve()
            except OSError:
                continue
            if q not in seen:
                seen.add(q)
                yield q

def locate_exact(downloads: Path, store: Path, filename: str, expected_sha: str) -> Path:
    mismatches = []
    for p in candidate_paths(downloads, store, filename):
        got = sha256_file(p)
        if got == expected_sha:
            return p
        mismatches.append(f"{p}={got}")
    detail = "; ".join(mismatches[:8]) if mismatches else "no filename candidate"
    raise FileNotFoundError(f"exact source not found: {filename} sha256={expected_sha}; {detail}")

def read_tsv_bytes(data: bytes):
    text = data.decode("utf-8")
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))

def read_tsv_zip(path: Path, member: str):
    with zipfile.ZipFile(path) as zf:
        return read_tsv_bytes(zf.read(member))

def verify_internal_manifest(path: Path):
    with zipfile.ZipFile(path) as zf:
        bad_member = zf.testzip()
        if bad_member is not None:
            raise RuntimeError(f"ZIP CRC failure: {path}: {bad_member}")
        names = set(zf.namelist())
        if "SHA256SUMS.txt" not in names:
            raise RuntimeError(f"missing internal SHA256SUMS.txt: {path}")
        lines = zf.read("SHA256SUMS.txt").decode("utf-8").splitlines()
        count = 0
        for line in lines:
            if not line.strip():
                continue
            expected, name = line.split(None, 1)
            name = name.strip()
            if name not in names:
                raise RuntimeError(f"internal manifest member missing: {path}: {name}")
            got = hashlib.sha256(zf.read(name)).hexdigest()
            if got != expected:
                raise RuntimeError(f"internal hash mismatch: {path}: {name}")
            count += 1
        return count

def stage_classification(path: Path, stage: int):
    rows = read_tsv_zip(path, f"HTS{stage}_CLASSIFICATION.tsv")
    if len(rows) != 1:
        raise RuntimeError(f"unexpected classification row count for HTS{stage}: {len(rows)}")
    return rows[0]["classification"]

def materialize_sources(downloads: Path, store: Path):
    located = {}
    freeze = []
    for stage, spec in STAGES.items():
        p = locate_exact(downloads, store, spec["filename"], spec["sha256"])
        actual = sha256_file(p)
        manifest_count = verify_internal_manifest(p)
        classification = stage_classification(p, stage)
        if classification != spec["classification"]:
            raise RuntimeError(
                f"HTS{stage} classification mismatch: {classification} != {spec['classification']}"
            )
        located[stage] = p
        freeze.append({
            "stage": f"HTS{stage}",
            "filename": spec["filename"],
            "resolved_path": str(p),
            "expected_sha256": spec["sha256"],
            "actual_sha256": actual,
            "zip_crc": "PASS",
            "internal_manifest_entries": manifest_count,
            "internal_manifest_result": "PASS",
            "expected_classification": spec["classification"],
            "actual_classification": classification,
            "source_result": "PASS",
        })
    return located, freeze

def key_of(row):
    return (row["edge"], row["direction"], float(row["burn_fraction_per_chain"]))

def index_rows(rows):
    out = {}
    for row in rows:
        k = key_of(row)
        if k in out:
            raise RuntimeError(f"duplicate directed key: {k}")
        out[k] = row
    return out

def f(row, name):
    return float(row[name])

def bool_text(v):
    return "True" if bool(v) else "False"

def write_tsv(path: Path, rows):
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    seen = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as fobj:
        w = csv.DictWriter(
            fobj, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore"
        )
        w.writeheader()
        w.writerows(rows)

def make_zip(source_dir: Path, zip_path: Path):
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for p in sorted(source_dir.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(source_dir).as_posix())
    sidecar = zip_path.with_name(zip_path.name + ".sha256")
    sidecar.write_text(f"{sha256_file(zip_path)}  {zip_path.name}\n", encoding="utf-8")

def load_analysis_tables(located):
    return {stage: index_rows(read_tsv_zip(located[stage], TABLES[stage])) for stage in TABLES}

def canonical_partition_id(located):
    rows = read_tsv_zip(located[65], "HTS65_PARTITION_CATALOG.tsv")
    matches = [r["partition_id"] for r in rows if r["is_HTS62_canonical_partition"] == "True"]
    if len(matches) != 1:
        raise RuntimeError(f"canonical partition count is {len(matches)}")
    return matches[0]

def hts65_canonical_block_index(located):
    pid = canonical_partition_id(located)
    rows = read_tsv_zip(located[65], "HTS65_DIRECTED_PARTITION_BLOCK_ALLOCATIONS.tsv")
    out = {}
    for r in rows:
        if r["partition_id"] != pid:
            continue
        k = key_of(r)
        out.setdefault(k, {})[r["block_variables"]] = float(r["block_owen_share"])
    return pid, out

def build_cross_stage(located):
    tables = load_analysis_tables(located)
    key_sets = {stage: set(rows) for stage, rows in tables.items()}
    reference = key_sets[59]
    if len(reference) != 28:
        raise RuntimeError(f"HTS59 directed key count {len(reference)} != 28")
    key_audit = []
    for stage in sorted(key_sets):
        missing = sorted(reference - key_sets[stage])
        extra = sorted(key_sets[stage] - reference)
        key_audit.append({
            "stage": f"HTS{stage}",
            "directed_key_count": len(key_sets[stage]),
            "missing_reference_key_count": len(missing),
            "extra_key_count": len(extra),
            "key_set_result": "PASS" if not missing and not extra else "FAIL",
        })
        if missing or extra:
            raise RuntimeError(f"HTS{stage} directed key mismatch")
    distance_rows = []
    max_d2_error = 0.0
    max_maha_error = 0.0
    for k in sorted(reference):
        r59 = tables[59][k]
        maha = {
            59: f(tables[59][k], "conditional4d_mahalanobis"),
            60: f(tables[60][k], "conditional4d_mahalanobis"),
            61: f(tables[61][k], "conditional4d_mahalanobis"),
            62: f(tables[62][k], "conditional4d_mahalanobis"),
            63: f(tables[63][k], "conditional4d_mahalanobis"),
            64: f(tables[64][k], "conditional4d_mahalanobis"),
            65: f(tables[65][k], "conditional4d_mahalanobis"),
        }
        d2 = {
            59: f(tables[59][k], "conditional4d_distance_squared"),
            60: f(tables[60][k], "conditional4d_distance_squared"),
            62: f(tables[62][k], "conditional4d_distance_squared"),
            63: f(tables[63][k], "conditional4d_distance_squared"),
            65: f(tables[65][k], "conditional4d_distance_squared"),
        }
        maha_err = max(abs(v - maha[59]) for v in maha.values())
        d2_err = max(abs(v - d2[59]) for v in d2.values())
        max_maha_error = max(max_maha_error, maha_err)
        max_d2_error = max(max_d2_error, d2_err)
        distance_rows.append({
            "edge": k[0],
            "direction": k[1],
            "burn_fraction_per_chain": k[2],
            "source_contract": r59["source_contract"],
            "target_contract": r59["target_contract"],
            "full6d_mahalanobis_HTS59": f(r59, "full6d_mahalanobis"),
            "tn2d_mahalanobis_HTS59": f(r59, "tn2d_mahalanobis"),
            "conditional4d_mahalanobis_HTS59": maha[59],
            "conditional4d_mahalanobis_HTS60": maha[60],
            "conditional4d_mahalanobis_HTS61": maha[61],
            "conditional4d_mahalanobis_HTS62": maha[62],
            "conditional4d_mahalanobis_HTS63": maha[63],
            "conditional4d_mahalanobis_HTS64": maha[64],
            "conditional4d_mahalanobis_HTS65": maha[65],
            "max_conditional4d_mahalanobis_cross_stage_error": maha_err,
            "max_conditional4d_distance_squared_cross_stage_error": d2_err,
            "conditional_fraction_full_distance_squared_HTS59":
                f(r59, "conditional_fraction_full_distance_squared"),
            "distance_consistency_result":
                "PASS" if maha_err <= 1e-10 and d2_err <= 1e-10 else "FAIL",
        })
    pid, b65 = hts65_canonical_block_index(located)
    block_rows = []
    max_block_error = 0.0
    for k in sorted(reference):
        b62 = f(tables[62][k], "baryon_tilt_shapley_share")
        a62 = f(tables[62][k], "tau_amplitude_shapley_share")
        b63 = f(tables[63][k], "baryon_tilt_block_shapley_share")
        a63 = f(tables[63][k], "tau_amplitude_block_shapley_share")
        b64 = f(tables[64][k], "physical_amplitude_baryon_tilt_block_share")
        a64 = f(tables[64][k], "physical_amplitude_tau_amplitude_block_share")
        if k not in b65 or "omega_b+n_s" not in b65[k] or "tau+logA" not in b65[k]:
            raise RuntimeError(f"HTS65 canonical block row missing for {k}")
        b65v = b65[k]["omega_b+n_s"]
        a65v = b65[k]["tau+logA"]
        err = max(
            abs(b63-b62), abs(a63-a62),
            abs(b64-b62), abs(a64-a62),
            abs(b65v-b62), abs(a65v-a62),
            abs((b62+a62)-1.0),
        )
        max_block_error = max(max_block_error, err)
        block_rows.append({
            "edge": k[0],
            "direction": k[1],
            "burn_fraction_per_chain": k[2],
            "HTS65_canonical_partition_id": pid,
            "baryon_tilt_share_HTS62": b62,
            "baryon_tilt_share_HTS63": b63,
            "baryon_tilt_share_HTS64_logA_minus_2tau": b64,
            "baryon_tilt_share_HTS65_canonical_partition": b65v,
            "tau_amplitude_share_HTS62": a62,
            "tau_amplitude_share_HTS63": a63,
            "tau_amplitude_share_HTS64_logA_minus_2tau": a64,
            "tau_amplitude_share_HTS65_canonical_partition": a65v,
            "max_fixed_block_cross_stage_error": err,
            "fixed_block_consistency_result": "PASS" if err <= 1e-10 else "FAIL",
        })
    return tables, key_audit, distance_rows, block_rows, max_d2_error, max_maha_error, max_block_error

def primary_summary(located, tables):
    modes = read_tsv_zip(located[61], "HTS61_ENDPOINT_MODE_IDENTIFIABILITY.tsv")
    clusters = {}
    for r in modes:
        if float(r["burn_fraction_per_chain"]) != 0.3:
            continue
        if int(r["identifiability_cluster_size"]) > 1:
            k = (r["contract"], r["identifiability_cluster_id"])
            clusters.setdefault(k, []).append(int(r["mode_index"]))
    basis = [r for r in tables[64].values() if key_of(r)[2] == 0.3]
    parts = [r for r in tables[65].values() if key_of(r)[2] == 0.3]
    basis_sensitive = sum(
        r["reparameterization_classification"] ==
        "BLOCK_ROBUST_VARIABLE_ALLOCATION_BASIS_SENSITIVE" for r in basis
    )
    partition_sensitive = sum(
        r["partition_sensitivity_classification"] ==
        "COALITION_PARTITION_SENSITIVE" for r in parts
    )
    partition_stable = len(parts) - partition_sensitive
    top_turnover = sum(int(r["partition_unique_top_variable_count"]) > 1 for r in parts)
    cluster_text = ";".join(
        f"{contract}:modes-{','.join(map(str, sorted(members)))}"
        for (contract, cid), members in sorted(clusters.items())
    )
    return [{
        "primary_directed_edge_count": len(parts),
        "near_degenerate_cluster_count": len(clusters),
        "near_degenerate_cluster_members": cluster_text,
        "HTS64_basis_sensitive_directed_edge_count": basis_sensitive,
        "HTS64_basis_stable_directed_edge_count": len(basis)-basis_sensitive,
        "HTS64_max_rotation_top_share_range":
            max(float(r["rotation_grid_top_share_range"]) for r in basis),
        "HTS64_max_rotation_effective_count_range":
            max(float(r["rotation_grid_effective_count_range"]) for r in basis),
        "HTS65_partition_sensitive_directed_edge_count": partition_sensitive,
        "HTS65_partition_stable_directed_edge_count": partition_stable,
        "HTS65_partition_top_variable_turnover_count": top_turnover,
        "HTS65_max_variable_owen_share_range":
            max(float(r["max_variable_owen_share_range_across_partitions"]) for r in parts),
        "HTS65_max_partition_effective_count_range":
            max(float(r["partition_effective_count_range"]) for r in parts),
    }]

def invariant_hierarchy(summary_row, max_d2, max_maha, max_block):
    return [
        {
            "quantity": "CONDITIONAL_4D_DISTANCE_WITHIN_FROZEN_2_PLUS_4_SPLIT",
            "status": "CROSS_STAGE_INVARIANT",
            "scope": "Exact HTS59-65 directed endpoints and frozen source-posterior metric",
            "evidence": f"max d2 discrepancy={max_d2:.17g}; max Mahalanobis discrepancy={max_maha:.17g}",
            "allowed_interpretation": "A reproducible descriptive distance within the frozen split.",
            "forbidden_interpretation": "Independent tension significance or causal likelihood contribution.",
        },
        {
            "quantity": "HTS62_FIXED_BLOCK_TOTALS",
            "status": "INVARIANT_UNDER_TESTED_WITHIN_BLOCK_REPARAMETERIZATION",
            "scope": "BARYON_TILT=(omega_b,n_s), TAU_AMPLITUDE=(tau,logA)",
            "evidence": f"max HTS62-65 block-share discrepancy={max_block:.17g}",
            "allowed_interpretation": "Stable bookkeeping under invertible transformations inside each fixed block.",
            "forbidden_interpretation": "Uniquely physical block partition or causal sector share.",
        },
        {
            "quantity": "CONDITIONAL_EIGENMODE_IDENTITIES",
            "status": "PARTIALLY_IDENTIFIABLE",
            "scope": "Individual modes only where the predeclared eigengap supports them",
            "evidence": f"near-degenerate clusters={summary_row['near_degenerate_cluster_count']} ({summary_row['near_degenerate_cluster_members']})",
            "allowed_interpretation": "Near-degenerate modes are retained only as subspaces.",
            "forbidden_interpretation": "Unique physical labels for rotations inside a near-degenerate cluster.",
        },
        {
            "quantity": "INDIVIDUAL_VARIABLE_SHAPLEY_OR_OWEN_SHARES",
            "status": "NON_INVARIANT_UNDER_COORDINATE_BASIS",
            "scope": "All 14 primary directed edges",
            "evidence": f"HTS64 basis-sensitive={summary_row['HTS64_basis_sensitive_directed_edge_count']}/14; max top-share range={summary_row['HTS64_max_rotation_top_share_range']:.17g}",
            "allowed_interpretation": "Descriptive values in the explicitly named coordinate basis.",
            "forbidden_interpretation": "Coordinate-invariant physical importance or causal attribution.",
        },
        {
            "quantity": "COALITION_PARTITION_VARIABLE_ALLOCATIONS",
            "status": "PARTITION_DEPENDENT",
            "scope": "All 15 set partitions of four conditional coordinates",
            "evidence": f"sensitive={summary_row['HTS65_partition_sensitive_directed_edge_count']}/14; stable={summary_row['HTS65_partition_stable_directed_edge_count']}/14; max share range={summary_row['HTS65_max_variable_owen_share_range']:.17g}",
            "allowed_interpretation": "Robustness description conditional on a declared coalition partition.",
            "forbidden_interpretation": "Selection of a uniquely physical alternative partition.",
        },
        {
            "quantity": "PHYSICAL_OR_CAUSAL_PARAMETER_ATTRIBUTION",
            "status": "NOT_SUPPORTED_BY_HTS59_TO_HTS65",
            "scope": "Posterior geometry and allocation series",
            "evidence": "Variable shares fail coordinate invariance; coalition allocations depend on partition; eigengap limits individual mode labels.",
            "allowed_interpretation": "Only the invariant hierarchy above is retained.",
            "forbidden_interpretation": "Claims that n_s, omega_b, tau, logA, an eigenmode, or a coalition caused an endpoint shift.",
        },
        {
            "quantity": "ATTRIBUTION_DIAGNOSTIC_BRANCH",
            "status": "CLOSE_AFTER_HTS66",
            "scope": "Further coordinate/eigenmode/coalition decomposition of the same released endpoints",
            "evidence": "Within-block rotations and all 15 coalition partitions have been exhausted.",
            "allowed_interpretation": "Reopen only with an externally justified physical parameterization, exact component posterior edge, or new independent data product.",
            "forbidden_interpretation": "Continuing decomposition solely to obtain a preferred attribution.",
        },
    ]
