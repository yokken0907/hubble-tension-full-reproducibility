#!/usr/bin/env python3
"""Unit tests for deterministic Phase 1C core functions."""

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
    alternative_basis_checks,
    baseline_result,
    build_group_structure,
    component_diagnostics,
    dispersion_label,
    generalized_comparison,
    json_safe,
    matrix_diagnostics,
    orthogonal_invariance_checks,
    ordered_sensitivity_classification,
    parse_covariance,
    primary_quadratic_form,
    read_source_lock,
    reference_quadratic_form,
    verify_contract_freeze,
    write_json,
)


class Phase1CTests(unittest.TestCase):
    def test_helmert_basis_two_and_three_rows(self) -> None:
        names = ["a", "a", "b", "b", "b", "single"]
        mapping = [
            {
                "IDSURVEY": value,
                "official_row_1based": index + 10,
            }
            for index, value in enumerate([1, 2, 3, 4, 5, 6])
        ]
        result = build_group_structure(names, mapping)
        basis = result["A"]
        self.assertEqual(basis.shape, (3, 6))
        np.testing.assert_allclose(basis @ basis.T, np.eye(3), atol=1e-15)
        np.testing.assert_allclose(basis @ result["Z"], 0.0, atol=1e-15)
        self.assertEqual(result["multirow_exact_name_group_count"], 2)
        self.assertEqual(result["rows_in_multirow_groups"], 5)

    def test_quadratic_solvers_agree(self) -> None:
        generator = np.random.default_rng(42)
        factor = generator.normal(size=(7, 7))
        covariance = factor @ factor.T + np.eye(7)
        vector = generator.normal(size=7)
        primary = primary_quadratic_form(vector, covariance)
        reference = reference_quadratic_form(vector, covariance)
        self.assertAlmostEqual(primary, reference, places=13)

    def test_ordered_classification(self) -> None:
        self.assertEqual(
            ordered_sensitivity_classification([False, False, False]),
            "NO_PHASE1A_BASELINE_LOW_FLAG",
        )
        self.assertEqual(
            ordered_sensitivity_classification([True, False, False]),
            "LOW_FLAG_REMOVED_WITHOUT_ROWWISE_VELOCITY_TERM",
        )
        self.assertEqual(
            ordered_sensitivity_classification([True, True, False]),
            (
                "LOW_FLAG_PERSISTS_WITHOUT_ROWWISE_VELOCITY_"
                "BUT_NOT_WITH_STATONLY"
            ),
        )
        self.assertEqual(
            ordered_sensitivity_classification([True, True, True]),
            "LOW_FLAG_PERSISTS_THROUGH_STATONLY",
        )
        self.assertEqual(
            ordered_sensitivity_classification([True, False, True]),
            "NONMONOTONIC_COMPONENT_SENSITIVITY",
        )

    def test_contract_freeze(self) -> None:
        verification = verify_contract_freeze(PROJECT)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["amendment_count"], 3)
        self.assertEqual(verification["posthoc_contract_status"], "PASS")

    def test_group_cross_survey_gate_can_fail(self) -> None:
        mapping = [
            {"IDSURVEY": 5, "official_row_1based": 10},
            {"IDSURVEY": 5, "official_row_1based": 11},
        ]
        result = build_group_structure(["same", "same"], mapping)
        self.assertFalse(result["all_multirow_groups_cross_survey"])

    def test_parse_covariance_schema_and_asymmetry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "small.cov"
            path.write_text("2\n1\n0.1\n0.2\n2\n", encoding="utf-8")
            matrix, schema = parse_covariance(path, 2)
        self.assertEqual(matrix.shape, (2, 2))
        self.assertFalse(schema["exactly_symmetric"])
        self.assertAlmostEqual(
            schema["maximum_absolute_transpose_difference"], 0.1
        )

    def test_parse_covariance_rejects_payload_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "bad.cov"
            path.write_text("2\n1\n0\n0\n", encoding="utf-8")
            with self.assertRaises(AuditFailure):
                parse_covariance(path, 2)

    def test_dispersion_labels(self) -> None:
        config = {
            "classification": {
                "strong_low_tail_alpha": 0.001,
                "low_tail_alpha": 0.01,
            }
        }
        self.assertTrue(
            dispersion_label(0.0001, config).startswith("STRONG_")
        )
        self.assertTrue(dispersion_label(0.005, config).startswith("LOW_"))
        self.assertTrue(dispersion_label(0.01, config).startswith("NO_"))

    def test_invalid_ordered_classification_length(self) -> None:
        with self.assertRaises(AuditFailure):
            ordered_sensitivity_classification([True, False])

    def test_matrix_diagnostics_spd(self) -> None:
        matrix = np.array([[2.0, 0.25], [0.25, 1.0]])
        diagnostics = matrix_diagnostics(matrix)
        self.assertTrue(diagnostics["cholesky_success"])
        self.assertGreater(diagnostics["eigenvalue_minimum"], 0)
        self.assertEqual(diagnostics["numerical_rank"], 2)

    def test_component_diagnostics_detects_negative_direction(self) -> None:
        diagnostics = component_diagnostics(np.diag([2.0, -0.5]))
        self.assertEqual(diagnostics["negative_eigenvalue_count"], 1)
        self.assertEqual(diagnostics["eigenvalue_minimum"], -0.5)

    def test_generalized_identity_comparison(self) -> None:
        matrix = np.diag([1.0, 2.0, 4.0])
        comparison = generalized_comparison(matrix, matrix)
        self.assertAlmostEqual(
            comparison["generalized_eigenvalue_minimum"], 1.0
        )
        self.assertAlmostEqual(comparison["trace_ratio"], 1.0)
        self.assertAlmostEqual(comparison["log_determinant_ratio"], 0.0)

    def test_baseline_result_scale_interval(self) -> None:
        config = {
            "classification": {
                "strong_low_tail_alpha": 0.001,
                "low_tail_alpha": 0.01,
            },
            "expected": {"contrast_degrees_of_freedom": 2},
        }
        result = baseline_result(
            "TEST", np.array([1.0, -1.0]), np.eye(2), config
        )
        self.assertAlmostEqual(result["chi2"], 2.0)
        self.assertAlmostEqual(
            result["scalar_scale_estimate_q_over_df"], 1.0
        )
        self.assertLess(
            result["scalar_scale_95_percent_interval_lower"],
            result["scalar_scale_95_percent_interval_upper"],
        )

    def test_alternative_basis_invariance(self) -> None:
        names = ["a", "a", "b", "b"]
        mapping = [
            {"IDSURVEY": index + 1, "official_row_1based": index + 10}
            for index in range(4)
        ]
        group = build_group_structure(names, mapping)
        data = np.array([0.5, -0.2, 1.1, 0.8])
        row_covariance = np.diag([1.0, 2.0, 1.5, 0.75])
        projected = group["A"] @ row_covariance @ group["A"].T
        q_value = primary_quadratic_form(group["A"] @ data, projected)
        result = alternative_basis_checks(
            data, {"TEST": row_covariance}, group["Z"], {"TEST": q_value}
        )
        self.assertLess(result["rows"][0]["absolute_difference"], 1e-13)

    def test_orthogonal_invariance(self) -> None:
        vector = np.array([0.2, -0.3, 1.0])
        covariance = np.array(
            [[2.0, 0.1, 0.2], [0.1, 1.0, 0.05], [0.2, 0.05, 1.5]]
        )
        reference = primary_quadratic_form(vector, covariance)
        config = {"invariance": {"seed": 7, "orthogonal_trials": 4}}
        result = orthogonal_invariance_checks(
            vector, {"TEST": covariance}, {"TEST": reference}, config
        )
        self.assertEqual(result["comparison_count"], 4)
        self.assertLess(result["maximum_absolute_difference"], 1e-13)

    def test_json_safe_rejects_nonfinite(self) -> None:
        with self.assertRaises(AuditFailure):
            json_safe({"bad": float("nan")})

    def test_write_json_is_sorted_and_newline_terminated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "value.json"
            write_json(path, {"z": 1, "a": 2})
            text = path.read_text(encoding="utf-8")
        self.assertLess(text.index('"a"'), text.index('"z"'))
        self.assertTrue(text.endswith("\n"))

    def test_source_lock_schema_and_count(self) -> None:
        rows = read_source_lock(PROJECT / "provenance" / "SOURCE_LOCK.tsv")
        self.assertEqual(len(rows), 13)
        self.assertEqual(
            {row["source_id"] for row in rows}, {"h0dn", "pantheonplus"}
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
