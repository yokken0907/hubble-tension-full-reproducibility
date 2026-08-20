#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
import hts66_common as c

DOCS = (
    "CANONICAL_STATE_THROUGH_HTS65.md",
    "HTS65_CANONICALIZATION_AUDIT.md",
    "HTS66_EXECUTION_CONTRACT.md",
    "HTS66_SELECTION_AUDIT.md",
    "HTS66_SOURCE_ADEQUACY_AUDIT.md",
    "HTS66_PREFLIGHT_RESULT.md",
    "HTS66_PREFLIGHT_TEST_AUDIT.md",
    "README_RUN.md",
)

def main():
    pkg = Path(__file__).resolve().parent
    downloads = Path(os.environ.get("HTS66_DOWNLOADS", str(pkg.parent))).resolve()
    store = Path(os.environ.get(
        "HTS_CACHE_STORE", str(downloads / "HTS_CHAIN_CACHE_STORE")
    )).resolve()
    out = Path(os.environ.get(
        "HTS66_OUTPUT", str(downloads / "HTS66_RESULTS_FOR_REVIEW")
    )).resolve()
    zipout = Path(os.environ.get(
        "HTS66_ZIP_OUTPUT", str(downloads / "HTS66_RESULTS_FOR_REVIEW.zip")
    )).resolve()
    out_sidecar = zipout.with_name(zipout.name + ".sha256")
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    try:
        located, freeze = c.materialize_sources(downloads, store)
        c.write_tsv(out / "HTS66_SOURCE_FREEZE.tsv", freeze)
        tables, key_audit, distances, blocks, max_d2, max_maha, max_block = \
            c.build_cross_stage(located)
        c.write_tsv(out / "HTS66_CROSS_STAGE_KEY_AUDIT.tsv", key_audit)
        c.write_tsv(out / "HTS66_CONDITIONAL_DISTANCE_CONSISTENCY.tsv", distances)
        c.write_tsv(out / "HTS66_FIXED_BLOCK_CONSISTENCY.tsv", blocks)
        summary = c.primary_summary(located, tables)
        c.write_tsv(out / "HTS66_PRIMARY_SYNTHESIS.tsv", summary)
        hierarchy = c.invariant_hierarchy(summary[0], max_d2, max_maha, max_block)
        c.write_tsv(out / "HTS66_INVARIANT_HIERARCHY.tsv", hierarchy)

        for name in DOCS:
            shutil.copy2(pkg / name, out / name)

        source_map = {str(stage): str(path) for stage, path in located.items()}
        runtime = out / "HTS66_RUNTIME_SOURCES.json"
        runtime.write_text(json.dumps(source_map, indent=2) + "\n", encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable, str(pkg / "audit_hts66.py"),
                "--output-dir", str(out),
                "--source-json", str(runtime),
            ],
            capture_output=True, text=True
        )
        (out / "HTS66_AUDIT_STDOUT.txt").write_text(proc.stdout, encoding="utf-8")
        (out / "HTS66_AUDIT_STDERR.txt").write_text(proc.stderr, encoding="utf-8")
        audit_pass = proc.returncode == 0

        source_gate = all(r["source_result"] == "PASS" for r in freeze)
        key_gate = all(r["key_set_result"] == "PASS" for r in key_audit)
        distance_gate = max_d2 <= 1e-10 and max_maha <= 1e-10
        block_gate = max_block <= 1e-10
        hierarchy_gate = (
            summary[0]["primary_directed_edge_count"] == 14
            and summary[0]["HTS64_basis_sensitive_directed_edge_count"] == 14
            and summary[0]["HTS65_partition_sensitive_directed_edge_count"]
                + summary[0]["HTS65_partition_stable_directed_edge_count"] == 14
        )
        passed = all((source_gate, key_gate, distance_gate, block_gate,
                      hierarchy_gate, audit_pass))
        classification = (
            "PASS_ATTRIBUTION_INVARIANT_CORE_SYNTHESIS_AND_BRANCH_CLOSEOUT"
            if passed else
            "HOLD_CROSS_STAGE_CONSISTENCY_OR_CLOSEOUT_AUDIT_FAILURE"
        )
        c.write_tsv(out / "HTS66_CLASSIFICATION.tsv", [{
            "classification": classification,
            "frozen_source_stage_count": len(freeze),
            "directed_key_count": len(distances),
            "max_conditional4d_distance_squared_cross_stage_error": max_d2,
            "max_conditional4d_mahalanobis_cross_stage_error": max_maha,
            "max_fixed_block_cross_stage_error": max_block,
            "near_degenerate_cluster_count":
                summary[0]["near_degenerate_cluster_count"],
            "HTS64_basis_sensitive_primary_count":
                summary[0]["HTS64_basis_sensitive_directed_edge_count"],
            "HTS65_partition_sensitive_primary_count":
                summary[0]["HTS65_partition_sensitive_directed_edge_count"],
            "HTS65_partition_stable_primary_count":
                summary[0]["HTS65_partition_stable_directed_edge_count"],
            "source_freeze_gate_pass": source_gate,
            "cross_stage_key_gate_pass": key_gate,
            "conditional_distance_consistency_gate_pass": distance_gate,
            "fixed_block_consistency_gate_pass": block_gate,
            "invariant_hierarchy_completeness_gate_pass": hierarchy_gate,
            "independent_audit_pass": audit_pass,
            "branch_decision": "CLOSE_ATTRIBUTION_DIAGNOSTIC_BRANCH",
            "reopen_condition":
                "Externally justified physical parameterization, exact component posterior edge, or new independent data product.",
            "interpretation_boundary":
                "This closeout preserves invariant posterior geometry and rejects coordinate-, mode-, or coalition-dependent quantities as physical or causal attributions.",
        }])
        (out / "HTS66_EXECUTION_REPORT.md").write_text(
            "# HTS66 execution report\n\n"
            f"`{classification}`\n\n"
            "HTS66 cross-audits the exact HTS59-65 result archives. It freezes the "
            "cross-stage invariant core, separates convention-dependent quantities, and "
            "closes further attribution decomposition of the same released endpoints.\n",
            encoding="utf-8"
        )
        (out / "MANIFEST.json").write_text(json.dumps({
            "stage": "HTS66",
            "classification": classification,
            "source_stages": [f"HTS{s}" for s in sorted(c.STAGES)],
            "branch_decision": "CLOSE_ATTRIBUTION_DIAGNOSTIC_BRANCH",
            "cache_store": str(store),
            "boundary":
                "Invariant-core synthesis and closeout; no new physical attribution.",
        }, indent=2) + "\n", encoding="utf-8")
        runtime.unlink(missing_ok=True)
        c.make_zip(out, zipout)
        print(classification)
        print(zipout)
        return 0 if passed else 2
    except Exception as exc:
        (out / "HTS66_RUNTIME_FAILURE.txt").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        for name in DOCS:
            if (pkg / name).exists():
                shutil.copy2(pkg / name, out / name)
        c.write_tsv(out / "HTS66_CLASSIFICATION.tsv", [{
            "classification":
                "HOLD_SOURCE_MATERIALIZATION_OR_CLOSEOUT_EXECUTION_FAILURE",
            "error": str(exc),
        }])
        (out / "HTS66_EXECUTION_REPORT.md").write_text(
            "# HTS66 execution report\n\n"
            "`HOLD_SOURCE_MATERIALIZATION_OR_CLOSEOUT_EXECUTION_FAILURE`\n\n"
            f"```text\n{exc}\n```\n",
            encoding="utf-8"
        )
        c.make_zip(out, zipout)
        print("HOLD_SOURCE_MATERIALIZATION_OR_CLOSEOUT_EXECUTION_FAILURE")
        print(zipout)
        return 2

if __name__ == "__main__":
    sys.exit(main())
