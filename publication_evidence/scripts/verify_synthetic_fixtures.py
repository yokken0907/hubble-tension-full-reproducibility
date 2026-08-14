#!/usr/bin/env python3
"""Run exact data-free fixtures and check compact recorded results."""

from __future__ import annotations

import csv
import json
import math
import pathlib
from fractions import Fraction


ROOT = pathlib.Path(__file__).resolve().parents[1]


def dot(left: list[Fraction], right: list[Fraction]) -> Fraction:
    return sum((a * b for a, b in zip(left, right)), Fraction(0))


def rank_one_quadratic(v: list[Fraction], residual: list[Fraction]) -> Fraction:
    return dot(v, residual) ** 2 / dot(v, v) ** 2


def rank_one_estimate(
    v: list[Fraction], design: list[Fraction], data: list[Fraction]
) -> Fraction:
    return dot(v, data) / dot(v, design)


def close(actual: float, expected: float, tolerance: float) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=tolerance)


def main() -> int:
    checks: list[tuple[str, bool]] = []

    # On-support singular-Gaussian quadratic: r = v*u before and after D=diag(1,2).
    v = [Fraction(1), Fraction(1)]
    residual = [Fraction(3), Fraction(3)]
    scaled_v = [Fraction(1), Fraction(2)]
    scaled_residual = [Fraction(3), Fraction(6)]
    q_original = rank_one_quadratic(v, residual)
    q_scaled = rank_one_quadratic(scaled_v, scaled_residual)
    checks.append(("on_support_invertible_coordinate_invariance", q_original == q_scaled == 9))

    # Explicitly off-support fixture. No theta makes (1-theta,-theta) parallel to (1,1).
    design = [Fraction(1), Fraction(1)]
    data = [Fraction(1), Fraction(0)]
    baseline = rank_one_estimate(v, design, data)
    scaled_design = [Fraction(1), Fraction(2)]
    scaled_data = [Fraction(1), Fraction(0)]
    transformed = rank_one_estimate(scaled_v, scaled_design, scaled_data)
    # Because both design entries are equal, the residual-entry difference is
    # fixed at data[0]-data[1] for every theta.
    support_feasible = data[0] - data[1] == 0
    checks.extend(
        [
            ("off_support_fixture_baseline_one_half", baseline == Fraction(1, 2)),
            ("off_support_fixture_scaled_one_fifth", transformed == Fraction(1, 5)),
            ("off_support_fixture_infeasible", not support_feasible),
        ]
    )

    # Equal one-intercept compression, unequal residual energy.
    first = [Fraction(-1), Fraction(0), Fraction(1)]
    second = [Fraction(-2), Fraction(0), Fraction(2)]
    mean_first = sum(first, Fraction(0)) / len(first)
    mean_second = sum(second, Fraction(0)) / len(second)
    chi2_first = sum((value - mean_first) ** 2 for value in first)
    chi2_second = sum((value - mean_second) ** 2 for value in second)
    checks.extend(
        [
            ("sn_equal_compressed_mean", mean_first == mean_second == 0),
            ("sn_first_residual_chi2_two", chi2_first == 2),
            ("sn_second_residual_chi2_eight", chi2_second == 8),
        ]
    )

    expected = json.loads(
        (ROOT / "evidence" / "EXPECTED_PRINCIPAL_RESULTS.json").read_text(
            encoding="utf-8"
        )
    )
    recorded = json.loads(
        (ROOT / "results" / "internal_validation_results_recorded.json").read_text(
            encoding="utf-8"
        )
    )
    h0_methods = recorded["h0dn"]["methods"]
    deltas = [float(item["delta_h0"]) for item in h0_methods.values()]
    h0_expected = expected["h0dn"]
    sn_expected = expected["sn_compression"]
    checks.extend(
        [
            ("recorded_internal_status", recorded["status"] == "PASS" and recorded["pass_count"] == 24),
            ("recorded_h0", close(h0_methods["eigh_evd"]["h0_original"], h0_expected["h0"], 5e-9)),
            ("recorded_delta", close(h0_methods["eigh_evd"]["delta_h0"], h0_expected["off_support_projected_loss_delta_h0"], 5e-8)),
            ("recorded_delta_spread", close(max(deltas) - min(deltas), h0_expected["four_route_delta_spread"], 1e-15)),
            ("recorded_orthogonal_control", close(recorded["h0dn"]["maximum_absolute_orthogonal_delta_h0"], h0_expected["maximum_absolute_orthogonal_delta_h0"], 1e-15)),
            ("recorded_congruence_defect", close(recorded["h0dn"]["moore_penrose_congruence_relative_frobenius_defect"], h0_expected["moore_penrose_congruence_relative_frobenius_defect"], 1e-15)),
            ("recorded_projected_design", close(recorded["h0dn"]["support"]["projected_design_frobenius_norm"], h0_expected["projected_design_frobenius_norm"], 1e-20)),
            ("recorded_projected_data", close(recorded["h0dn"]["support"]["projected_data_l2_norm"], h0_expected["projected_data_l2_norm_mag"], 1e-14)),
            ("recorded_sn_intercept", close(recorded["sn_compression"]["alpha"], sn_expected["intercept"], 5e-13)),
            ("recorded_sn_error", close(recorded["sn_compression"]["alpha_error"], sn_expected["standard_error"], 5e-13)),
            ("recorded_sn_residual", close(recorded["sn_compression"]["residual_chi2"], sn_expected["omitted_residual_chi2"], 5e-10)),
            ("recorded_completion_square", close(recorded["sn_compression"]["maximum_complete_square_residual"], sn_expected["maximum_complete_square_residual"], 1e-20)),
        ]
    )

    same_cid = json.loads((ROOT / "results" / "audit_summary.json").read_text(encoding="utf-8"))
    checks.extend(
        [
            ("same_cid_classification", same_cid["sensitivity_classification"] == expected["same_cid"]["classification"]),
            ("same_cid_statonly", close(same_cid["ordered_baseline_results"]["STAT_ONLY"]["chi2"], expected["same_cid"]["statonly_chi2"], 1e-12)),
        ]
    )

    gwtc = json.loads((ROOT / "evidence" / "gwtc" / "RESULTS_MACHINE_READABLE.json").read_text(encoding="utf-8"))
    checks.extend(
        [
            ("gwtc_gate_a", gwtc["gate_a_decision"] == "PASS"),
            ("gwtc_metric_hold", gwtc["gate_b_carry_forward"]["metric_posterior_pair_provenance"] == "HOLD_NOT_UNIQUE"),
        ]
    )

    with (ROOT / "evidence" / "tdcosmo" / "FINAL_RESULT_SUMMARY.tsv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        td_rows = {row["metric"]: row for row in csv.DictReader(handle, delimiter="\t")}
    checks.extend(
        [
            ("tdcosmo_structures", td_rows["extension_structural_comparisons"]["value"] == "13/13"),
            ("tdcosmo_quantiles", td_rows["extension_quantiles_within_preregistered_tolerance"]["value"] == "39/39"),
            ("tdcosmo_table6", td_rows["table6_rows_at_published_precision"]["value"] == "12/12"),
        ]
    )

    failed = [identifier for identifier, passed in checks if not passed]
    status = "PASS" if not failed else "FAIL"
    payload = {
        "status": status,
        "check_count": len(checks),
        "pass_count": len(checks) - len(failed),
        "failed": failed,
        "exact": {
            "on_support_quadratic_original": str(q_original),
            "on_support_quadratic_scaled": str(q_scaled),
            "off_support_estimate_original": str(baseline),
            "off_support_estimate_scaled": str(transformed),
            "sn_residual_chi2": [str(chi2_first), str(chi2_second)],
        },
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
