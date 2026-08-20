from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

import numpy as np


PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from auditlib import (  # noqa: E402
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
)


class AuditLibraryTests(unittest.TestCase):
    @staticmethod
    def h0dn_row(
        *,
        name: str = "SN-A",
        err: float = 0.2,
    ) -> dict[str, object]:
        return {
            "name": name,
            "m_b": 15.0,
            "err_m_b": err,
            "zhel": 0.02,
            "zcmb": 0.021,
            "h0dn_row_0based": 0,
            "h0dn_row_1based": 1,
        }

    @staticmethod
    def official_row(
        index: int,
        *,
        name: str = "SN-A",
        survey: int = 5,
        catalog_error: float = 0.9,
        m_b: float = 15.0,
    ) -> dict[str, object]:
        return {
            "CID": name,
            "IDSURVEY": survey,
            "m_b_corr": m_b,
            "m_b_corr_err_DIAG": catalog_error,
            "zHEL": 0.02,
            "zCMB": 0.021,
            "USED_IN_SH0ES_HF": 1.0,
            "official_row_0based": index,
            "official_row_1based": index + 1,
        }

    @staticmethod
    def resolve(
        h0dn: list[dict[str, object]],
        official: list[dict[str, object]],
        covariance: np.ndarray,
    ) -> list[dict[str, object]]:
        config = load_config(PROJECT)
        attach_covariance_diagonal_fingerprints(official, covariance)
        catalog = find_catalog_only_candidates(h0dn, official, config)
        resolved, _ = resolve_catalog_candidates_with_covariance(
            catalog, config
        )
        return resolved

    def test_frozen_contract_integrity(self) -> None:
        self.assertEqual(verify_contract_freeze(PROJECT)["status"], "PASS")

    def test_parse_h0dn_table(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = pathlib.Path(raw) / "h0dn.dat"
            path.write_text(
                "#name m_b err_m_b zhel zcmb extra\n"
                "SN-A 15.0 0.2 0.02 0.021 9\n",
                encoding="utf-8",
            )
            rows = parse_h0dn_table(path)
        self.assertEqual(rows[0]["name"], "SN-A")
        self.assertEqual(rows[0]["h0dn_row_1based"], 1)

    def test_parse_official_table(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = pathlib.Path(raw) / "official.dat"
            path.write_text(
                "CID IDSURVEY zCMB zHEL m_b_corr "
                "m_b_corr_err_DIAG USED_IN_SH0ES_HF\n"
                "SN-A 5 0.021 0.02 15.0 0.3 1\n",
                encoding="utf-8",
            )
            rows = parse_official_table(path)
        self.assertEqual(rows[0]["IDSURVEY"], 5)
        self.assertEqual(rows[0]["official_row_1based"], 1)

    def test_covariance_parser_and_symmetry(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = pathlib.Path(raw) / "cov.dat"
            path.write_text("2\n1\n0.2\n0.2\n2\n", encoding="utf-8")
            matrix = parse_covariance(path, 2)
        self.assertTrue(np.array_equal(matrix, np.array([[1, 0.2], [0.2, 2]])))
        self.assertTrue(
            covariance_symmetry_diagnostics(matrix)["exactly_symmetric"]
        )

    def test_asymmetric_covariance_requires_explicit_permission(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = pathlib.Path(raw) / "cov.dat"
            path.write_text("2\n1\n0.1\n0.2\n2\n", encoding="utf-8")
            with self.assertRaises(AuditFailure):
                parse_covariance(path, 2)
            matrix = parse_covariance(
                path, 2, require_exact_symmetry=False
            )
        self.assertEqual(
            covariance_symmetry_diagnostics(matrix)[
                "asymmetric_element_count"
            ],
            2,
        )

    def test_active_matching_config_records_amend_004(self) -> None:
        config = load_config(PROJECT)
        self.assertEqual(
            config["applied_decision_amendments"],
            ["AMEND-002", "AMEND-003", "AMEND-004"],
        )
        self.assertFalse(
            config["active_matching"]["interpretation_affected"]
        )
        self.assertTrue(config["active_matching"]["results_observed"])

    def test_catalog_only_unique_ignores_error_fields(self) -> None:
        h0dn = [self.h0dn_row()]
        official = [self.official_row(0, catalog_error=99.0)]
        config = load_config(PROJECT)
        attach_covariance_diagonal_fingerprints(
            official, np.array([[0.81]])
        )
        catalog = find_catalog_only_candidates(h0dn, official, config)
        self.assertEqual(
            catalog[0]["catalog_only_classification"],
            "CATALOG_ONLY_UNIQUE",
        )
        resolved, _ = resolve_catalog_candidates_with_covariance(
            catalog, config
        )
        self.assertFalse(resolved[0]["covariance_diagonal_used"])
        self.assertEqual(
            resolved[0]["final_dependency_classification"],
            "CATALOG_ONLY_UNIQUE",
        )

    def test_catalog_only_ambiguity_is_explicit(self) -> None:
        h0dn = [self.h0dn_row()]
        official = [
            self.official_row(0),
            self.official_row(1, survey=56),
        ]
        catalog = find_catalog_only_candidates(
            h0dn, official, load_config(PROJECT)
        )
        self.assertEqual(
            catalog[0]["catalog_only_classification"],
            "CATALOG_ONLY_AMBIGUOUS",
        )
        self.assertEqual(len(catalog[0]["catalog_candidates"]), 2)

    def test_covariance_diagonal_resolves_only_ambiguous_rows(self) -> None:
        h0dn = [self.h0dn_row()]
        official = [
            self.official_row(0),
            self.official_row(1, survey=56),
        ]
        resolved = self.resolve(
            h0dn, official, np.diag([0.04, 0.09])
        )
        self.assertTrue(resolved[0]["covariance_diagonal_used"])
        self.assertEqual(
            resolved[0]["final_dependency_classification"],
            "COVARIANCE_DIAGONAL_REQUIRED",
        )
        rows, counts = build_mapping_rows(resolved, {"5": "CSP"})
        self.assertEqual(counts["unique_match_count"], 1)
        self.assertEqual(rows[0]["official_row_1based"], 1)

    def test_ambiguity_after_all_rules_remains_a_hold(self) -> None:
        h0dn = [self.h0dn_row()]
        official = [
            self.official_row(0),
            self.official_row(1, survey=56),
        ]
        resolved = self.resolve(
            h0dn, official, np.diag([0.04, 0.04])
        )
        self.assertEqual(
            resolved[0]["final_dependency_classification"],
            "AMBIGUOUS_AFTER_ALL_RULES",
        )
        rows, counts = build_mapping_rows(resolved, {})
        self.assertEqual(rows[0]["match_status"], "AMBIGUOUS_MATCH")
        self.assertEqual(counts["ambiguous_match_count"], 1)

    def test_unmatched_classes_are_explicit(self) -> None:
        config = load_config(PROJECT)
        h0dn = [self.h0dn_row()]
        no_catalog = find_catalog_only_candidates(
            h0dn, [self.official_row(0, name="SN-B")], config
        )
        self.assertEqual(
            no_catalog[0]["catalog_only_classification"],
            "CATALOG_ONLY_UNMATCHED",
        )
        official = [
            self.official_row(0),
            self.official_row(1, survey=56),
        ]
        no_assisted = self.resolve(
            h0dn, official, np.diag([0.09, 0.16])
        )
        self.assertEqual(
            no_assisted[0]["final_dependency_classification"],
            "UNMATCHED_AFTER_ALL_RULES",
        )

    def test_candidate_permutation_does_not_change_resolution(self) -> None:
        h0dn = [self.h0dn_row()]
        rows_a = [
            self.official_row(0),
            self.official_row(1, survey=56),
        ]
        rows_b = [dict(rows_a[1]), dict(rows_a[0])]
        covariance = np.diag([0.04, 0.09])
        result_a = self.resolve(h0dn, rows_a, covariance)
        result_b = self.resolve(h0dn, rows_b, covariance)
        dependency_a = build_mapping_dependency_rows(result_a)
        dependency_b = build_mapping_dependency_rows(result_b)
        self.assertEqual(dependency_a, dependency_b)

    def test_covariance_diagonal_perturbation_changes_resolution(self) -> None:
        h0dn = [self.h0dn_row()]
        official = [
            self.official_row(0),
            self.official_row(1, survey=56),
        ]
        baseline = self.resolve(
            h0dn, [dict(row) for row in official], np.diag([0.04, 0.09])
        )
        perturbed = self.resolve(
            h0dn, [dict(row) for row in official], np.diag([0.0625, 0.09])
        )
        self.assertEqual(
            baseline[0]["final_dependency_classification"],
            "COVARIANCE_DIAGONAL_REQUIRED",
        )
        self.assertEqual(
            perturbed[0]["final_dependency_classification"],
            "UNMATCHED_AFTER_ALL_RULES",
        )

    def test_error_field_discrepancy_is_recomputable(self) -> None:
        h0dn = [self.h0dn_row()]
        official = [self.official_row(0, catalog_error=0.3)]
        resolved = self.resolve(h0dn, official, np.array([[0.04]]))
        rows, summary = build_error_field_discrepancy(
            resolved, load_config(PROJECT)
        )
        self.assertAlmostEqual(
            float(rows[0]["catalog_vs_matrix_absolute_difference"]),
            0.1,
        )
        self.assertEqual(
            summary["catalog_vs_matrix_outside_tolerance_count"], 1
        )
        self.assertEqual(
            summary[
                "h0dn_vs_matrix_within_h0dn_print_tolerance_count"
            ],
            1,
        )
        self.assertEqual(summary["status"], "PASS_DIAGNOSTIC_RECORDED")

    def test_dependency_ledger_records_both_stages(self) -> None:
        h0dn = [self.h0dn_row()]
        official = [
            self.official_row(0),
            self.official_row(1, survey=56),
        ]
        resolved = self.resolve(
            h0dn, official, np.diag([0.04, 0.09])
        )
        ledger = build_mapping_dependency_rows(resolved)
        self.assertEqual(ledger[0]["catalog_candidate_count"], 2)
        self.assertEqual(ledger[0]["covariance_diagonal_used"], "YES")
        self.assertEqual(
            ledger[0]["final_dependency_classification"],
            "COVARIANCE_DIAGONAL_REQUIRED",
        )

    def test_all_three_group_classifications(self) -> None:
        names = ["A", "A", "B", "B", "C", "C", "C"]
        h0dn = [
            {
                "name": name,
                "h0dn_row_0based": index,
            }
            for index, name in enumerate(names)
        ]
        codes = [5, 56, 5, 5, 5, 56, 56]
        mapping = [
            {
                "match_status": "UNIQUE_MATCH",
                "IDSURVEY": code,
                "official_row_1based": index + 10,
                "survey_label": str(code),
            }
            for index, code in enumerate(codes)
        ]
        groups, counts = classify_multirow_groups(h0dn, mapping)
        self.assertEqual(
            [row["survey_multiplicity_class"] for row in groups],
            [
                "MULTI_SURVEY_ONLY",
                "SAME_SURVEY_REPEATED",
                "MIXED_SURVEY_MULTIPLICITY",
            ],
        )
        self.assertEqual(sum(counts.values()), 3)

    def test_exact_covariance_lineage_pass_and_fail(self) -> None:
        official = np.arange(16, dtype=float).reshape(4, 4)
        mapping = [
            {
                "match_status": "UNIQUE_MATCH",
                "official_row_1based": 2,
            },
            {
                "match_status": "UNIQUE_MATCH",
                "official_row_1based": 4,
            },
        ]
        expected = official[np.ix_([1, 3], [1, 3])]
        passed = compare_covariance_lineage(official, expected, mapping)
        self.assertEqual(passed["status"], "PASS")
        changed = expected.copy()
        changed[0, 1] += 1e-12
        failed = compare_covariance_lineage(official, changed, mapping)
        self.assertEqual(failed["mismatch_count"], 1)
        self.assertEqual(failed["status"], "FAIL")

    def test_covariance_lineage_stops_on_mapping_hold(self) -> None:
        result = compare_covariance_lineage(
            np.eye(2),
            np.eye(1),
            [{"match_status": "NO_MATCH"}],
        )
        self.assertFalse(result["comparison_performed"])
        self.assertEqual(result["status"], "NOT_RUN_MAPPING_HOLD")


if __name__ == "__main__":
    unittest.main()
