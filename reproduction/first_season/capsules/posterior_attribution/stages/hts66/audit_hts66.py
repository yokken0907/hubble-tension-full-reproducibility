#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path
import hts66_common as c

def read_tsv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--source-json", required=True)
    args = ap.parse_args()
    out = Path(args.output_dir)
    source_map = json.loads(Path(args.source_json).read_text(encoding="utf-8"))
    located = {int(stage): Path(path) for stage, path in source_map.items()}

    checks = []
    max_source_hash_error = 0
    for stage, spec in c.STAGES.items():
        p = located[stage]
        got = c.sha256_file(p)
        ok = got == spec["sha256"]
        checks.append({
            "check": f"HTS{stage}_outer_sha256",
            "observed": got,
            "required": spec["sha256"],
            "result": "PASS" if ok else "FAIL",
        })
        try:
            count = c.verify_internal_manifest(p)
            manifest_ok = count > 0
        except Exception:
            count = -1
            manifest_ok = False
        checks.append({
            "check": f"HTS{stage}_internal_manifest",
            "observed": count,
            "required": ">0 and all match",
            "result": "PASS" if manifest_ok else "FAIL",
        })
        actual_class = c.stage_classification(p, stage)
        checks.append({
            "check": f"HTS{stage}_classification",
            "observed": actual_class,
            "required": spec["classification"],
            "result": "PASS" if actual_class == spec["classification"] else "FAIL",
        })

    tables, key_audit, distances, blocks, max_d2, max_maha, max_block = \
        c.build_cross_stage(located)
    saved_dist = {
        (r["edge"], r["direction"], float(r["burn_fraction_per_chain"])): r
        for r in read_tsv(out / "HTS66_CONDITIONAL_DISTANCE_CONSISTENCY.tsv")
    }
    saved_block = {
        (r["edge"], r["direction"], float(r["burn_fraction_per_chain"])): r
        for r in read_tsv(out / "HTS66_FIXED_BLOCK_CONSISTENCY.tsv")
    }
    max_saved_error = 0.0
    for r in distances:
        k = (r["edge"], r["direction"], float(r["burn_fraction_per_chain"]))
        q = saved_dist[k]
        for name in (
            "max_conditional4d_mahalanobis_cross_stage_error",
            "max_conditional4d_distance_squared_cross_stage_error",
            "conditional_fraction_full_distance_squared_HTS59",
        ):
            max_saved_error = max(
                max_saved_error, abs(float(r[name]) - float(q[name]))
            )
    for r in blocks:
        k = (r["edge"], r["direction"], float(r["burn_fraction_per_chain"]))
        q = saved_block[k]
        for name in (
            "baryon_tilt_share_HTS62",
            "baryon_tilt_share_HTS63",
            "baryon_tilt_share_HTS64_logA_minus_2tau",
            "baryon_tilt_share_HTS65_canonical_partition",
            "tau_amplitude_share_HTS62",
            "tau_amplitude_share_HTS63",
            "tau_amplitude_share_HTS64_logA_minus_2tau",
            "tau_amplitude_share_HTS65_canonical_partition",
            "max_fixed_block_cross_stage_error",
        ):
            max_saved_error = max(
                max_saved_error, abs(float(r[name]) - float(q[name]))
            )
    checks.append({
        "check": "saved_cross_stage_table_reconstruction_max_error",
        "observed": max_saved_error,
        "required": "<=1e-12",
        "result": "PASS" if max_saved_error <= 1e-12 else "FAIL",
    })
    checks.append({
        "check": "conditional4d_distance_squared_cross_stage_max_error",
        "observed": max_d2,
        "required": "<=1e-10",
        "result": "PASS" if max_d2 <= 1e-10 else "FAIL",
    })
    checks.append({
        "check": "conditional4d_mahalanobis_cross_stage_max_error",
        "observed": max_maha,
        "required": "<=1e-10",
        "result": "PASS" if max_maha <= 1e-10 else "FAIL",
    })
    checks.append({
        "check": "fixed_block_cross_stage_max_error",
        "observed": max_block,
        "required": "<=1e-10",
        "result": "PASS" if max_block <= 1e-10 else "FAIL",
    })
    summary = c.primary_summary(located, tables)[0]
    checks.append({
        "check": "HTS64_primary_basis_sensitive_count",
        "observed": summary["HTS64_basis_sensitive_directed_edge_count"],
        "required": "14",
        "result": "PASS" if summary["HTS64_basis_sensitive_directed_edge_count"] == 14 else "FAIL",
    })
    checks.append({
        "check": "HTS65_primary_partition_classification_count",
        "observed":
            summary["HTS65_partition_sensitive_directed_edge_count"]
            + summary["HTS65_partition_stable_directed_edge_count"],
        "required": "14",
        "result": "PASS" if (
            summary["HTS65_partition_sensitive_directed_edge_count"]
            + summary["HTS65_partition_stable_directed_edge_count"] == 14
        ) else "FAIL",
    })
    c.write_tsv(out / "HTS66_INDEPENDENT_AUDIT_CHECKS.tsv", checks)
    ok = all(r["result"] == "PASS" for r in checks)
    (out / "HTS66_INDEPENDENT_AUDIT_RESULT.md").write_text(
        "# HTS66 independent audit result\n\n"
        f"`{'PASS' if ok else 'FAIL'}`\n",
        encoding="utf-8"
    )
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
