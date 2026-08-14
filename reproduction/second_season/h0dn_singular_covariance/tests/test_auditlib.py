#!/usr/bin/env python3
"""Synthetic unit tests for the independent audit linear algebra."""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

import numpy as np


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from auditlib import (  # noqa: E402
    ablation_interpretation_status,
    covariance_model_status,
    match_component_ablations_to_leave_one_out,
    solve_gls,
    write_json,
)
from verify_results import VerificationFailure, read_tsv_with_header  # noqa: E402


class SolveGlsTests(unittest.TestCase):
    def test_full_rank_gls_is_invariant_to_exact_row_scaling(self) -> None:
        design = np.asarray(
            [
                [1.0, 0.0],
                [1.0, 1.0],
                [1.0, 2.0],
                [1.0, 3.0],
            ]
        )
        data = np.asarray([0.2, 0.9, 2.2, 2.8])
        mixing = np.asarray(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.2, 1.2, 0.0, 0.0],
                [0.1, -0.3, 0.8, 0.0],
                [0.0, 0.2, 0.4, 1.1],
            ]
        )
        covariance = mixing @ mixing.T
        scale = np.asarray([0.25, 3.0, 1.7, 0.6])
        baseline = solve_gls(
            design,
            data,
            covariance,
            ihub=0,
            iabs=1,
            policy="synthetic_full_rank",
        )
        transformed = solve_gls(
            scale[:, None] * design,
            scale * data,
            scale[:, None] * covariance * scale[None, :],
            ihub=0,
            iabs=1,
            policy="synthetic_full_rank_scaled",
        )
        self.assertEqual(baseline["status"], "OK")
        self.assertEqual(transformed["status"], "OK")
        np.testing.assert_allclose(
            baseline["_params"], transformed["_params"], rtol=0, atol=1e-11
        )
        self.assertAlmostEqual(
            baseline["h0_error"], transformed["h0_error"], places=10
        )

    def test_singular_mp_gls_can_depend_on_row_scaling(self) -> None:
        design = np.ones((3, 1))
        data = np.asarray([1.0, 3.0, 2.0])
        covariance = np.asarray(
            [
                [1.0, 1.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        scale = np.asarray([1.0, 2.0, 1.0])
        baseline = solve_gls(
            design,
            data,
            covariance,
            ihub=0,
            iabs=None,
            policy="synthetic_singular",
        )
        transformed = solve_gls(
            scale[:, None] * design,
            scale * data,
            scale[:, None] * covariance * scale[None, :],
            ihub=0,
            iabs=None,
            policy="synthetic_singular_scaled",
        )
        self.assertEqual(baseline["covar_rank"], 2)
        self.assertEqual(transformed["covar_rank"], 2)
        self.assertAlmostEqual(float(baseline["_params"][0]), 2.0, places=12)
        self.assertAlmostEqual(
            float(transformed["_params"][0]), 2.3, places=12
        )


class SerializationTests(unittest.TestCase):
    def test_json_writer_never_emits_nonstandard_nan_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory) / "strict.json"
            write_json(
                target,
                {
                    "nan": float("nan"),
                    "positive_infinity": float("inf"),
                    "negative_infinity": float("-inf"),
                    "finite": np.float64(1.25),
                },
            )
            text = target.read_text(encoding="utf-8")
            self.assertNotIn("NaN", text)
            self.assertNotIn("Infinity", text)
            parsed = json.loads(text)
            self.assertIsNone(parsed["nan"])
            self.assertIsNone(parsed["positive_infinity"])
            self.assertIsNone(parsed["negative_infinity"])
            self.assertEqual(parsed["finite"], 1.25)


class AblationClassificationTests(unittest.TestCase):
    def test_fixed_interpretation_vocabulary_is_applied_by_precedence(
        self,
    ) -> None:
        self.assertEqual(
            ablation_interpretation_status(
                {"status": "OK", "covar_materially_indefinite": False},
                zero_precision_row_count=1,
            ),
            "PSEUDOINVERSE_DISCARDED_CONSTRAINT",
        )
        self.assertEqual(
            ablation_interpretation_status(
                {
                    "status": "OK_INDEFINITE_COVARIANCE",
                    "covar_materially_indefinite": True,
                },
                zero_precision_row_count=0,
            ),
            "INDEFINITE_ALGEBRAIC_DIAGNOSTIC",
        )
        self.assertEqual(
            ablation_interpretation_status(
                {
                    "status": "HOLD_UNIDENTIFIED",
                    "covar_materially_indefinite": False,
                },
                zero_precision_row_count=0,
            ),
            "HOLD_UNIDENTIFIED",
        )

    def test_covariance_model_status_is_separate_from_solver_status(
        self,
    ) -> None:
        self.assertEqual(
            covariance_model_status(
                {
                    "status": "OK",
                    "nrows": 4,
                    "covar_rank": 4,
                    "covar_materially_indefinite": False,
                }
            ),
            "PSD",
        )
        self.assertEqual(
            covariance_model_status(
                {
                    "status": "OK",
                    "nrows": 4,
                    "covar_rank": 3,
                    "covar_materially_indefinite": False,
                }
            ),
            "SINGULAR_PSD",
        )

    def test_exact_discarded_row_match_checks_all_parameters(self) -> None:
        component = {
            "discarded_equation_indices": [8],
            "solver_status": "OK",
            "h0_value": 74.0,
            "h0_error": 1.5,
            "_params": np.asarray([1.0, 2.0, 3.0]),
            "matched_leave_one_block_out_id": "",
            "matched_leave_one_block_out_match_status": "NO_EXACT_ROW_BLOCK",
        }
        leave_one_out = {
            "removed_row_indices": [8],
            "block_id": "synthetic_link",
            "status": "OK",
            "h0_value": 74.0,
            "h0_error": 1.5,
            "delta_h0": 0.5,
            "_params": np.asarray([1.0, 2.0, 3.0 + 1.0e-12]),
        }
        match_component_ablations_to_leave_one_out(
            [component], [leave_one_out]
        )
        self.assertEqual(
            component["matched_leave_one_block_out_id"],
            "synthetic_link",
        )
        self.assertEqual(
            component["matched_leave_one_block_out_match_status"], "PASS"
        )
        self.assertLess(
            component[
                "matched_leave_one_block_out_parameter_max_absolute_difference"
            ],
            1.0e-9,
        )


class TsvSchemaTests(unittest.TestCase):
    def test_missing_trailing_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory) / "broken.tsv"
            target.write_text("a\tb\n1\n", encoding="utf-8")
            with self.assertRaises(VerificationFailure):
                read_tsv_with_header(target)


if __name__ == "__main__":
    unittest.main()
