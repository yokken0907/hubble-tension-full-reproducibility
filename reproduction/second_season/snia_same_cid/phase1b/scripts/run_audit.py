#!/usr/bin/env python3
"""Execute the prospectively frozen Phase 1B provenance audit."""

from __future__ import annotations

import argparse
import json
import pathlib
import platform
import sys
from collections import Counter
from typing import Any

import numpy as np

from auditlib import (
    BOUNDARY_MARKER,
    CANDIDATE_FIELDS,
    DEPENDENCY_FIELDS,
    ERROR_DISCREPANCY_FIELDS,
    GROUP_FIELDS,
    MAPPING_FIELDS,
    SUCCESS_STATUS,
    AuditFailure,
    attach_covariance_diagonal_fingerprints,
    build_error_field_discrepancy,
    build_mapping_dependency_rows,
    build_mapping_rows,
    classify_multirow_groups,
    compare_covariance_lineage,
    covariance_symmetry_diagnostics,
    find_catalog_only_candidates,
    load_config,
    parse_covariance,
    parse_h0dn_table,
    parse_official_table,
    resolve_catalog_candidates_with_covariance,
    verify_contract_freeze,
    verify_sources,
    write_json,
    write_tsv,
)


def choose_status(
    *,
    source_ok: bool,
    schema_ok: bool,
    mapping_counts: dict[str, Any],
    unresolved_survey_count: int,
    covariance: dict[str, Any],
) -> str:
    if not source_ok:
        return "HOLD_SOURCE_MISMATCH"
    if not schema_ok:
        return "HOLD_INPUT_SCHEMA_MISMATCH"
    if mapping_counts["no_match_count"]:
        return "HOLD_CATALOG_MAPPING_INCOMPLETE"
    if (
        mapping_counts["ambiguous_match_count"]
        or mapping_counts["reused_official_row_count"]
        or mapping_counts["rows_assigned_to_reused_official_rows"]
    ):
        return "HOLD_AMBIGUOUS_MAPPING"
    if unresolved_survey_count:
        return "HOLD_SURVEY_CODE_UNRESOLVED"
    if covariance["status"] != "PASS":
        return "HOLD_COVARIANCE_LINEAGE_MISMATCH"
    return SUCCESS_STATUS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    results = project / "results"
    results.mkdir(exist_ok=True)
    config = load_config(project)
    try:
        contract = verify_contract_freeze(project)
        if contract["status"] != "PASS":
            raise AuditFailure("frozen contract verification failed")
        source = verify_sources(
            project,
            {
                "h0dn": args.h0dn.resolve(),
                "pantheonplus": args.pantheonplus.resolve(),
            },
        )
        write_json(results / "contract_verification.json", contract)
        write_json(results / "source_verification.json", source)
        if source["status"] != "PASS":
            raise AuditFailure("source verification failed")

        h0dn_root = args.h0dn.resolve()
        official_root = args.pantheonplus.resolve()
        h0dn_rows = parse_h0dn_table(h0dn_root / "data/sn1a_hf_pp.dat")
        official_rows = parse_official_table(
            official_root
            / "Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat"
        )
        h0dn_covariance = parse_covariance(
            h0dn_root / "data/sn1a_covar_pp.dat",
            config["covariance"]["expected_h0dn_dimension"],
            require_exact_symmetry=config["covariance"].get(
                "require_h0dn_symmetric_exact",
                config["covariance"]["require_symmetric_exact"],
            ),
        )
        official_covariance = parse_covariance(
            official_root
            / (
                "Pantheon+_Data/4_DISTANCES_AND_COVAR/"
                "Pantheon+SH0ES_STAT+SYS.cov"
            ),
            config["covariance"]["expected_official_dimension"],
            require_exact_symmetry=config["covariance"].get(
                "require_official_symmetric_exact",
                config["covariance"]["require_symmetric_exact"],
            ),
        )
        name_counts = Counter(row["name"] for row in h0dn_rows)
        multirow_names = {name for name, count in name_counts.items() if count > 1}
        inventory = {
            "h0dn_row_count": len(h0dn_rows),
            "h0dn_unique_exact_name_count": len(name_counts),
            "h0dn_multirow_exact_name_group_count": len(multirow_names),
            "h0dn_rows_in_multirow_exact_name_groups": sum(
                name_counts[name] for name in multirow_names
            ),
            "official_catalog_row_count": len(official_rows),
            "official_hubble_flow_candidate_pool_count": sum(
                row["USED_IN_SH0ES_HF"]
                == config["matching"]["candidate_filter"]["numeric_value"]
                for row in official_rows
            ),
            "h0dn_covariance_shape": list(h0dn_covariance.shape),
            "official_covariance_shape": list(official_covariance.shape),
            "h0dn_covariance_symmetry": covariance_symmetry_diagnostics(
                h0dn_covariance
            ),
            "official_covariance_symmetry": covariance_symmetry_diagnostics(
                official_covariance
            ),
            "applied_decision_amendments": config.get(
                "applied_decision_amendments", []
            ),
        }
        expected = config["expected_prior_known_counts"]
        schema_ok = (
            inventory["h0dn_row_count"] == expected["h0dn_rows"]
            and inventory["h0dn_unique_exact_name_count"]
            == expected["unique_exact_names"]
            and inventory["h0dn_multirow_exact_name_group_count"]
            == expected["multirow_exact_name_groups"]
            and inventory["h0dn_rows_in_multirow_exact_name_groups"]
            == expected["rows_in_multirow_exact_name_groups"]
            and inventory["official_catalog_row_count"]
            == config["covariance"]["expected_official_dimension"]
            and h0dn_covariance.shape
            == (
                config["covariance"]["expected_h0dn_dimension"],
                config["covariance"]["expected_h0dn_dimension"],
            )
            and official_covariance.shape
            == (
                config["covariance"]["expected_official_dimension"],
                config["covariance"]["expected_official_dimension"],
            )
        )
        inventory["schema_status"] = "PASS" if schema_ok else "FAIL"
        write_json(results / "input_inventory.json", inventory)

        attach_covariance_diagonal_fingerprints(
            official_rows, official_covariance
        )
        catalog_candidate_sets = find_catalog_only_candidates(
            h0dn_rows, official_rows, config
        )
        candidate_sets, candidate_evidence = (
            resolve_catalog_candidates_with_covariance(
                catalog_candidate_sets, config
            )
        )
        mapping_rows, mapping_counts = build_mapping_rows(
            candidate_sets, config["survey_labels"]
        )
        write_tsv(results / "row_mapping.tsv", mapping_rows, MAPPING_FIELDS)
        write_tsv(
            results / "candidate_evidence.tsv",
            candidate_evidence,
            CANDIDATE_FIELDS,
        )
        dependency_rows = build_mapping_dependency_rows(candidate_sets)
        write_tsv(
            results / "row_mapping_dependency.tsv",
            dependency_rows,
            DEPENDENCY_FIELDS,
        )
        covariance_required_rows = [
            row
            for row in dependency_rows
            if row["final_dependency_classification"]
            == "COVARIANCE_DIAGONAL_REQUIRED"
        ]
        write_tsv(
            results / "covariance_diagonal_required_rows.tsv",
            covariance_required_rows,
            DEPENDENCY_FIELDS,
        )
        catalog_class_counts = Counter(
            row["catalog_only_classification"]
            for row in dependency_rows
        )
        final_dependency_counts = Counter(
            row["final_dependency_classification"]
            for row in dependency_rows
        )
        dependency_summary = {
            "h0dn_row_count": len(dependency_rows),
            "catalog_only_unique_row_count": catalog_class_counts[
                "CATALOG_ONLY_UNIQUE"
            ],
            "catalog_only_ambiguous_row_count": catalog_class_counts[
                "CATALOG_ONLY_AMBIGUOUS"
            ],
            "catalog_only_unmatched_row_count": catalog_class_counts[
                "CATALOG_ONLY_UNMATCHED"
            ],
            "covariance_diagonal_assisted_row_count": sum(
                row["covariance_diagonal_used"] == "YES"
                for row in dependency_rows
            ),
            "covariance_diagonal_required_row_count": final_dependency_counts[
                "COVARIANCE_DIAGONAL_REQUIRED"
            ],
            "ambiguous_after_all_rules_row_count": final_dependency_counts[
                "AMBIGUOUS_AFTER_ALL_RULES"
            ],
            "unmatched_after_all_rules_row_count": final_dependency_counts[
                "UNMATCHED_AFTER_ALL_RULES"
            ],
            "final_single_candidate_count": sum(
                int(row["final_candidate_count"]) == 1
                for row in dependency_rows
            ),
            "final_one_to_one_match_count": mapping_counts[
                "unique_match_count"
            ],
            "official_row_reuse_count": mapping_counts[
                "reused_official_row_count"
            ],
            "official_candidate_coverage_complete": (
                {
                    int(row["final_official_row_1based"]) - 1
                    for row in dependency_rows
                    if row["final_official_row_1based"] != ""
                }
                == {
                    row["official_row_0based"]
                    for row in official_rows
                    if row["USED_IN_SH0ES_HF"]
                    == config["matching"]["candidate_filter"][
                        "numeric_value"
                    ]
                }
            ),
            "lineage_classification": (
                "JOINT_CATALOG_AND_COVARIANCE_LINEAGE"
            ),
            "status": (
                "PASS"
                if len(dependency_rows) == 277
                and not final_dependency_counts[
                    "AMBIGUOUS_AFTER_ALL_RULES"
                ]
                and not final_dependency_counts[
                    "UNMATCHED_AFTER_ALL_RULES"
                ]
                and mapping_counts["unique_match_count"] == 277
                else "FAIL"
            ),
        }
        write_json(
            results / "row_mapping_dependency_summary.json",
            dependency_summary,
        )
        discrepancy_rows, discrepancy_summary = (
            build_error_field_discrepancy(candidate_sets, config)
        )
        write_tsv(
            results / "error_field_discrepancy_rows.tsv",
            discrepancy_rows,
            ERROR_DISCREPANCY_FIELDS,
        )
        write_json(
            results / "error_field_discrepancy_summary.json",
            discrepancy_summary,
        )
        group_rows, class_counts = classify_multirow_groups(
            h0dn_rows, mapping_rows
        )
        write_tsv(
            results / "multirow_group_summary.tsv",
            group_rows,
            GROUP_FIELDS,
        )
        multirow_mapping_rows = [
            row for row in mapping_rows if row["name"] in multirow_names
        ]
        write_tsv(
            results / "multirow_row_evidence.tsv",
            multirow_mapping_rows,
            MAPPING_FIELDS,
        )
        unresolved_survey_count = sum(
            row["match_status"] == "UNIQUE_MATCH"
            and row["survey_label"] == "UNRESOLVED"
            for row in mapping_rows
        )
        matched_official_indices = [
            int(row["official_row_1based"]) - 1
            for row in mapping_rows
            if row["match_status"] == "UNIQUE_MATCH"
        ]
        eligible_official_indices = [
            row["official_row_0based"]
            for row in official_rows
            if row["USED_IN_SH0ES_HF"]
            == config["matching"]["candidate_filter"]["numeric_value"]
        ]
        maximum_mapping_deltas = {
            field: max(
                (
                    float(row[field])
                    for row in mapping_rows
                    if row[field] != ""
                ),
                default=None,
            )
            for field in (
                "delta_m_b",
                "delta_err_m_b",
                "delta_zhel",
                "delta_zcmb",
            )
        }
        group_size_counts = Counter(
            int(row["h0dn_row_count"]) for row in group_rows
        )
        multirow_survey_counts = Counter(
            (str(row["IDSURVEY"]), str(row["survey_label"]))
            for row in multirow_mapping_rows
        )
        covariance = compare_covariance_lineage(
            official_covariance, h0dn_covariance, mapping_rows
        )
        write_json(results / "covariance_lineage.json", covariance)

        status = choose_status(
            source_ok=source["status"] == "PASS",
            schema_ok=schema_ok,
            mapping_counts=mapping_counts,
            unresolved_survey_count=unresolved_survey_count,
            covariance=covariance,
        )
        summary = {
            "audit_id": config["contract_id"],
            "boundary_marker": BOUNDARY_MARKER,
            "classification_scope": (
                "catalog-row and survey-code provenance; two-stage mapping "
                "dependency; exact covariance submatrix comparison only"
            ),
            "covariance_lineage": covariance,
            "error_field_discrepancy": discrepancy_summary,
            "input_inventory": inventory,
            "mapping": {
                **mapping_counts,
                "unresolved_survey_code_count": unresolved_survey_count,
                "active_rule": (
                    "exact CID plus catalog m_b/z fields; covariance "
                    "diagonal used only to resolve catalog-only ambiguities"
                ),
                "official_candidate_pool_fully_covered": (
                    set(matched_official_indices)
                    == set(eligible_official_indices)
                ),
                "official_row_order_preserved": (
                    matched_official_indices == eligible_official_indices
                ),
                "maximum_absolute_deltas": maximum_mapping_deltas,
            },
            "multirow_focus": {
                "group_count": len(group_rows),
                "row_count": len(multirow_mapping_rows),
                "group_size_counts": {
                    str(key): value
                    for key, value in sorted(group_size_counts.items())
                },
                "survey_row_counts": {
                    f"{code}:{label}": count
                    for (code, label), count in sorted(
                        multirow_survey_counts.items(),
                        key=lambda item: int(item[0][0]),
                    )
                },
                "survey_multiplicity_class_counts": class_counts,
            },
            "row_mapping_dependency": dependency_summary,
            "nonclaims": [
                "mapping and covariance comparison share covariance-diagonal "
                "lineage where ambiguity resolution was required; no full "
                "statistical-independence claim",
                "no row modification",
                "no covariance correction",
                "no corrected a_B, M_B, H0, or tension significance",
                "no causal attribution",
            ],
            "protocol_amendment_disclosure": {
                "applied_amendments": config.get(
                    "applied_decision_amendments", []
                ),
                "interpretation_affecting_amendment": "AMEND-003",
                "reader_explanation_correction": "AMEND-004",
                "prospective_integrity": (
                    "CORRECTED_RULE_FROZEN_AFTER_ORIGINAL_RULE_FAILED_ALL_"
                    "277_ROWS_BUT_BEFORE_ANY_CORRECTED_MAPPING_GROUP_OR_"
                    "LINEAGE_RESULT"
                ),
                "amend_004_effect": (
                    "RESULTS_OBSERVED_YES_INTERPRETATION_AFFECTED_NO"
                ),
            },
            "status": status,
        }
        write_json(results / "audit_summary.json", summary)
        execution = {
            "contract_id": config["contract_id"],
            "formal_status": status,
            "required_gate_status": (
                "PASS" if status == SUCCESS_STATUS else "HOLD"
            ),
            "scientific_interpretation_permitted": status == SUCCESS_STATUS,
            "boundary_marker": BOUNDARY_MARKER,
        }
        write_json(results / "EXECUTION_STATUS.json", execution)
        write_json(
            results / "run_environment.json",
            {
                "numpy_version": np.__version__,
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "serialization": "JSON sort_keys=True; TSV LF",
            },
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    except (AuditFailure, OSError, ValueError, KeyError) as exc:
        failure = {
            "audit_id": config.get("contract_id", "UNKNOWN"),
            "boundary_marker": BOUNDARY_MARKER,
            "error": f"{type(exc).__name__}: {exc}",
            "status": "HOLD_SOURCE_MISMATCH",
        }
        write_json(results / "EXECUTION_STATUS.json", failure)
        print(f"FAIL: {failure['error']}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
