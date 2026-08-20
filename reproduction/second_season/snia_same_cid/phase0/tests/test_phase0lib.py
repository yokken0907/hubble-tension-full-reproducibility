from __future__ import annotations

import pathlib
import sys
import unittest

import numpy as np


PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from phase0lib import (  # noqa: E402
    FINAL_PASS_STATUS,
    PROFILE_OFFSETS_SIGMA,
    build_expanded_network,
    build_recompressed_network,
    compare_network_results,
    compression_identity_grid,
    resolve_execution_status,
    solve_expanded_blockwise,
    solve_intercept_cholesky,
    solve_intercept_inverse,
    solve_network,
)


class InterceptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = np.array([0.70, 0.73, 0.71, 0.72], dtype=float)
        self.covariance = np.array(
            [
                [0.010, 0.002, 0.000, 0.001],
                [0.002, 0.020, 0.001, 0.000],
                [0.000, 0.001, 0.015, 0.003],
                [0.001, 0.000, 0.003, 0.018],
            ],
            dtype=float,
        )

    def test_cholesky_and_inverse_crosscheck(self) -> None:
        cholesky = solve_intercept_cholesky(self.data, self.covariance)
        inverse = solve_intercept_inverse(self.data, self.covariance)
        self.assertAlmostEqual(cholesky["alpha"], inverse["alpha"], places=14)
        self.assertAlmostEqual(
            cholesky["alpha_error"], inverse["alpha_error"], places=14
        )
        self.assertAlmostEqual(cholesky["chi2"], inverse["chi2"], places=13)

    def test_full_profile_equals_scalar_profile(self) -> None:
        fit = solve_intercept_cholesky(self.data, self.covariance)
        rows = compression_identity_grid(self.data, self.covariance, fit)
        self.assertEqual(
            [row["offset_sigma"] for row in rows],
            list(PROFILE_OFFSETS_SIGMA),
        )
        self.assertLess(
            max(row["absolute_identity_residual"] for row in rows), 1.0e-11
        )

    def test_correlations_change_the_fit_but_not_identity(self) -> None:
        correlated = solve_intercept_cholesky(self.data, self.covariance)
        diagonal = solve_intercept_cholesky(
            self.data, np.diag(np.diag(self.covariance))
        )
        self.assertNotEqual(correlated["alpha"], diagonal["alpha"])
        rows = compression_identity_grid(
            self.data, self.covariance, correlated
        )
        self.assertTrue(all(row["status"] == "PASS" for row in rows))


class NetworkEmbeddingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = np.array([0.70, 0.74, 0.72], dtype=float)
        self.hf_covariance = np.array(
            [
                [0.020, 0.003, 0.001],
                [0.003, 0.025, 0.002],
                [0.001, 0.002, 0.018],
            ],
            dtype=float,
        )
        self.fit = solve_intercept_cholesky(
            self.data, self.hf_covariance
        )
        coefficients = np.array(
            [
                [0.0, 1.0],
                [1.0, 0.0],
                [1.0, -0.2],
            ],
            dtype=float,
        )
        observations = np.array(
            [-19.2, 1.87, self.fit["alpha"] + 5.0], dtype=float
        )
        covariance = np.diag(
            [0.02, 0.01, self.fit["alpha_variance"]]
        )
        self.captured = {
            "equation_data": {
                "coeffs": coefficients,
                "yval": observations,
                "covar": covariance,
                "ieq_h0_m1a": 2,
                "ihub": 0,
                "iabs": 1,
            }
        }

    def test_full_block_and_scalar_have_same_normal_equations(self) -> None:
        (
            scalar_a,
            scalar_y,
            scalar_c,
            ihub,
            iabs,
            _link,
        ) = build_recompressed_network(self.captured, self.fit)
        scalar = solve_network(
            scalar_a,
            scalar_y,
            scalar_c,
            ihub=ihub,
            iabs=iabs,
            policy="test_scalar",
        )
        expanded_system = build_expanded_network(
            self.captured, self.data, self.hf_covariance
        )
        expanded = solve_network(
            expanded_system["coefficients"],
            expanded_system["observations"],
            expanded_system["covariance"],
            ihub=ihub,
            iabs=iabs,
            policy="test_expanded",
        )
        comparison = compare_network_results(scalar, expanded)
        self.assertLess(
            comparison["max_abs_parameter_difference"], 1.0e-12
        )
        self.assertLess(
            comparison["max_abs_parameter_covariance_difference"], 1.0e-12
        )
        self.assertLess(
            np.max(np.abs(scalar["_normal"] - expanded["_normal"])),
            1.0e-11,
        )
        self.assertAlmostEqual(
            expanded["chi2"] - scalar["chi2"],
            self.fit["chi2"],
            places=12,
        )

    def test_blockwise_solver_matches_full_solver(self) -> None:
        expanded_system = build_expanded_network(
            self.captured, self.data, self.hf_covariance
        )
        full = solve_network(
            expanded_system["coefficients"],
            expanded_system["observations"],
            expanded_system["covariance"],
            ihub=0,
            iabs=1,
            policy="test_full",
        )
        blockwise = solve_expanded_blockwise(expanded_system)
        comparison = compare_network_results(full, blockwise)
        self.assertLess(
            comparison["max_abs_parameter_difference"], 1.0e-12
        )
        self.assertLess(
            comparison["max_abs_parameter_covariance_difference"], 1.0e-12
        )

    def test_nonzero_link_cross_covariance_is_rejected(self) -> None:
        self.captured["equation_data"]["covar"][2, 0] = 1.0e-4
        self.captured["equation_data"]["covar"][0, 2] = 1.0e-4
        with self.assertRaisesRegex(
            RuntimeError, "nonzero cross-covariance"
        ):
            build_expanded_network(
                self.captured, self.data, self.hf_covariance
            )


class StatusTests(unittest.TestCase):
    def test_all_pass_resolves_to_frozen_pass_status(self) -> None:
        gates = [
            {"gate_id": "source_lock", "status": "PASS"},
            {"gate_id": "profile_identity", "status": "PASS"},
        ]
        self.assertEqual(resolve_execution_status(gates), FINAL_PASS_STATUS)

    def test_profile_failure_resolves_to_hold(self) -> None:
        gates = [
            {"gate_id": "source_lock", "status": "PASS"},
            {"gate_id": "profile_identity", "status": "FAIL"},
        ]
        self.assertEqual(
            resolve_execution_status(gates),
            "HOLD_COMPRESSION_IDENTITY_FAILURE",
        )


if __name__ == "__main__":
    unittest.main()

