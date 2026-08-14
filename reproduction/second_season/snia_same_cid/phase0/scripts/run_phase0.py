#!/usr/bin/env python3
"""Execute the frozen Phase 0 SN Ia compression-sufficiency audit."""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

from phase0lib import (
    CONTRACT_ID,
    FINAL_PASS_STATUS,
    PROFILE_OFFSETS_SIGMA,
    TOLERANCES,
    AuditFailure,
    baseline_fidelity,
    build_hubble_flow_system,
    capture_upstream_baseline,
    compression_identity_grid,
    environment_record,
    input_inventory,
    load_hubble_flow_inputs,
    matrix_diagnostics,
    public_intercept_result,
    resolve_execution_status,
    run_network_embedding_audit,
    scientific_gates,
    sha256_file,
    solve_intercept_cholesky,
    solve_intercept_inverse,
    upstream_baseline_summary,
    write_json,
    write_tsv,
)
from source_tools import verify_source


BOUNDARY_MARKER = (
    "FROZEN_MODEL_ONLY_NO_CORRECTED_H0_NO_TENSION_RESOLUTION"
)


def _comparison_max(comparison: dict[str, Any]) -> float:
    return max(
        float(comparison["max_abs_parameter_difference"]),
        float(comparison["max_abs_parameter_covariance_difference"]),
        float(comparison["absolute_h0_difference"]),
        float(comparison["absolute_h0_error_difference"]),
    )


def english_report(
    status: str,
    baseline: dict[str, Any],
    alpha: dict[str, Any],
    network: dict[str, Any],
    profile_max: float,
    permutation_max: float,
) -> str:
    passing = status == FINAL_PASS_STATUS
    conclusion = (
        "The scalar intercept and variance are an exact sufficient statistic "
        "for every parameter-dependent contribution of this 277-object block "
        "to the frozen H0DN linear model."
        if passing
        else "At least one frozen gate failed, so Phase 0 makes no sufficiency claim."
    )
    return rf"""# Phase 0 report: SN Ia Hubble-flow compression sufficiency

Authoritative status: **{status}**

Boundary marker: `{BOUNDARY_MARKER}`

## Result

{conclusion}

The independent Cholesky reconstruction gives
\(a_B={alpha['independent_cholesky']['alpha']:.15f}\) and
\(\sigma(a_B)={alpha['independent_cholesky']['alpha_error']:.15f}\) from
277 Pantheon+ Hubble-flow rows. The untouched upstream values are
\(a_B={alpha['upstream']['alpha']:.15f}\) and
\(\sigma(a_B)={alpha['upstream']['alpha_error']:.15f}\).

The maximum residual on the 11-point, pre-specified full-versus-scalar
chi-square grid is `{profile_max:.6e}`. Replacing the one scalar H0DN link by
all 277 correlated equations changes no fitted parameter by more than
`{network['expanded_vs_scalar']['max_abs_parameter_difference']:.6e}` and no
parameter-covariance element by more than
`{network['expanded_vs_scalar']['max_abs_parameter_covariance_difference']:.6e}`.
The largest tested difference across 16 seeded permutations is
`{permutation_max:.6e}`.

The untouched baseline remains
\(H_0={baseline['h0_value']:.12f}\pm{baseline['h0_error']:.12f}\)
km/s/Mpc. The expanded calculation is an equivalent representation, not a new
or corrected H0 estimate.

## What the scalar compression omits

The expanded fit has a chi-square larger by
`{network['expanded_minus_scalar_chi2']:.12f}`, equal within
`{abs(network['chi2_closure_residual']):.6e}` to the parameter-independent
Hubble-flow minimum chi-square
`{network['hubble_flow_minimum_chi2']:.12f}`. The covariance rank and adjusted
degrees of freedom each increase by
`{network['covariance_rank_increase']}`.

Therefore the scalar is sufficient for the network parameters under the frozen
one-intercept model, but it is not sufficient for residual diagnostics,
goodness-of-fit assessment, or testing richer redshift-, survey-, flow-, or
population-dependent models.

## Scope boundary

No covariance was zeroed, tuned, rescaled, or fitted. No constraint was
dropped. This audit does not validate the physical adequacy of the frozen
model, infer a Hubble-tension significance, produce a corrected H0, or show
that the Hubble tension is resolved. It is an independent computational audit,
not H0DN collaboration validation or peer review.

The frozen equations, tolerances, status rules, and non-claims are in
`PHASE0_CONTRACT.md`.
"""


def japanese_report(
    status: str,
    baseline: dict[str, Any],
    alpha: dict[str, Any],
    network: dict[str, Any],
    profile_max: float,
    permutation_max: float,
) -> str:
    passing = status == FINAL_PASS_STATUS
    conclusion = (
        "凍結したH0DNの1切片・固定共分散線形モデルに限れば、切片とその分散は、"
        "277天体ブロックがネットワークの推定パラメータへ渡す情報の厳密な十分統計量である。"
        if passing
        else "凍結ゲートの少なくとも一つが不合格のため、Phase 0は十分性を主張しない。"
    )
    return rf"""# Phase 0報告：SN Iaハッブルフロー圧縮の十分性

正式ステータス：**{status}**

境界マーカー：`{BOUNDARY_MARKER}`

## 結果

{conclusion}

独立Cholesky実装により、277行のPantheon+ハッブルフローデータから
\(a_B={alpha['independent_cholesky']['alpha']:.15f}\)、
\(\sigma(a_B)={alpha['independent_cholesky']['alpha_error']:.15f}\)
を再構成した。未改変上流実装は
\(a_B={alpha['upstream']['alpha']:.15f}\)、
\(\sigma(a_B)={alpha['upstream']['alpha_error']:.15f}\) である。

事前固定した11点の完全尤度対スカラー尤度の
\(\Delta\chi^2\) 恒等式における最大残差は `{profile_max:.6e}`。
H0DNの1本のスカラー制約を277本の相関付き方程式に戻したとき、
全パラメータの最大差は
`{network['expanded_vs_scalar']['max_abs_parameter_difference']:.6e}`、
パラメータ共分散要素の最大差は
`{network['expanded_vs_scalar']['max_abs_parameter_covariance_difference']:.6e}`
だった。事前固定seedによる16置換での最大差は
`{permutation_max:.6e}` である。

未改変ベースラインは
\(H_0={baseline['h0_value']:.12f}\pm{baseline['h0_error']:.12f}\)
km/s/Mpcのままである。非圧縮計算は同じモデルの等価表現であり、新しい値でも
補正値でもない。

## 1数値への圧縮で失われるもの

非圧縮ネットワークのchi-squareはスカラー版より
`{network['expanded_minus_scalar_chi2']:.12f}` 大きく、その差は
ハッブルフロー単独の最小chi-square
`{network['hubble_flow_minimum_chi2']:.12f}` と
`{abs(network['chi2_closure_residual']):.6e}` の範囲で一致した。
共分散rankと調整自由度はいずれも
`{network['covariance_rank_increase']}` 増える。

したがって、1数値への圧縮は凍結モデルのネットワーク・パラメータ推定には十分だが、
残差診断、適合度評価、赤方偏移・サーベイ・速度場・母集団依存を持つ拡張モデルの
検定には十分ではない。

## 科学的境界

共分散のゼロ化・調整・再スケール・フィットは行っていない。制約も落としていない。
本監査は凍結モデルの物理的妥当性を検証せず、ハッブルテンションの有意度を推定せず、
補正H0を与えず、テンションが解消したとも主張しない。これは独立した計算監査であり、
H0DN共同研究の承認や査読ではない。

固定した式、許容差、停止条件、非主張事項は `PHASE0_CONTRACT.md` にある。
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=pathlib.Path)
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1] / "results",
    )
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    upstream = args.upstream.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    try:
        source = verify_source(
            upstream, project / "provenance" / "SOURCE_LOCK.tsv"
        )
        write_json(output / "source_verification.json", source)

        captured = capture_upstream_baseline(upstream)
        baseline = upstream_baseline_summary(captured)
        fidelity = baseline_fidelity(baseline)
        write_json(
            output / "upstream_baseline_reproduction.json",
            {"baseline": baseline, "fidelity_gate": fidelity},
        )
        (output / "upstream_stdout.log").write_text(
            captured["stdout"], encoding="utf-8"
        )
        (output / "upstream_stderr.log").write_text(
            captured["stderr"], encoding="utf-8"
        )

        inputs = load_hubble_flow_inputs(upstream)
        inventory = input_inventory(inputs)
        write_json(output / "input_inventory.json", inventory)
        system = build_hubble_flow_system(inputs)

        cholesky = solve_intercept_cholesky(
            system["data_alpha"], system["covariance_alpha"]
        )
        inverse = solve_intercept_inverse(
            system["data_alpha"], system["covariance_alpha"]
        )
        upstream_alpha = float(
            captured["equation_data"]["a_sn1a"]
        )
        upstream_alpha_error = float(
            captured["equation_data"]["a_sn1a_err"]
        )
        alpha_record = {
            "object_count": len(inputs.names),
            "upstream": {
                "policy": "untouched_upstream_explicit_inverse",
                "alpha": upstream_alpha,
                "alpha_error": upstream_alpha_error,
                "chi2": float(
                    captured["equation_data"]["chisq_sn1a_hf"]
                ),
                "ndof": int(
                    captured["equation_data"]["ndof_sn1a_hf"]
                ),
            },
            "independent_cholesky": public_intercept_result(cholesky),
            "explicit_inverse_crosscheck": public_intercept_result(inverse),
            "alpha_covariance": matrix_diagnostics(
                system["covariance_alpha"]
            ),
            "cholesky_succeeded": True,
            "upstream_match": {
                "alpha_absolute_difference": abs(
                    float(cholesky["alpha"]) - upstream_alpha
                ),
                "alpha_error_absolute_difference": abs(
                    float(cholesky["alpha_error"])
                    - upstream_alpha_error
                ),
                "tolerance": TOLERANCES["alpha_reconstruction"],
            },
            "solver_crosscheck": {
                "alpha_absolute_difference": abs(
                    float(cholesky["alpha"]) - float(inverse["alpha"])
                ),
                "alpha_error_absolute_difference": abs(
                    float(cholesky["alpha_error"])
                    - float(inverse["alpha_error"])
                ),
                "chi2_absolute_difference": abs(
                    float(cholesky["chi2"]) - float(inverse["chi2"])
                ),
                "tolerance": TOLERANCES["solver_crosscheck"],
            },
            "frozen_model": {
                "q0": -0.55,
                "j0": 1.0,
                "velocity_dispersion_km_s": 240.0,
                "velocity_column": "vp_2mpp",
                "redshift_cut_applied": False,
            },
        }
        write_json(output / "intercept_reconstruction.json", alpha_record)

        profile_rows = compression_identity_grid(
            system["data_alpha"],
            system["covariance_alpha"],
            cholesky,
        )
        write_tsv(
            output / "compression_identity_grid.tsv",
            profile_rows,
            [
                "offset_sigma",
                "trial_alpha",
                "full_chi2",
                "full_delta_chi2",
                "scalar_delta_chi2",
                "identity_residual",
                "absolute_identity_residual",
                "tolerance",
                "status",
            ],
        )

        network, permutation_rows = run_network_embedding_audit(
            captured,
            system["data_alpha"],
            system["covariance_alpha"],
            cholesky,
        )
        write_json(output / "network_embedding_equivalence.json", network)
        write_tsv(
            output / "permutation_invariance.tsv",
            permutation_rows,
            [
                "iteration",
                "seed",
                "permutation_sha256",
                "max_abs_parameter_difference",
                "max_abs_parameter_covariance_difference",
                "absolute_h0_difference",
                "absolute_h0_error_difference",
                "absolute_logh0_difference",
                "absolute_mzero_difference",
                "maximum_tested_difference",
                "tolerance",
                "status",
            ],
        )
        write_json(output / "run_environment.json", environment_record())

        gates = scientific_gates(
            source,
            inventory,
            alpha_record,
            profile_rows,
            network,
            permutation_rows,
            fidelity,
        )
        status = resolve_execution_status(gates)
        execution_status = {
            "authoritative": True,
            "contract_id": CONTRACT_ID,
            "contract_freeze_commit": (
                "5a5e8a3ef8bb340c11a769b32231ac0ece1026cb"
            ),
            "status": status,
            "scientific_gate_count": len(gates),
            "scientific_gate_pass_count": sum(
                gate["status"] == "PASS" for gate in gates
            ),
            "gates": gates,
            "failed_gate_ids": [
                gate["gate_id"]
                for gate in gates
                if gate["status"] != "PASS"
            ],
        }
        write_json(output / "EXECUTION_STATUS.json", execution_status)

        profile_max = max(
            float(row["absolute_identity_residual"])
            for row in profile_rows
        )
        permutation_max = max(
            float(row["maximum_tested_difference"])
            for row in permutation_rows
        )
        phase0_summary = {
            "status": status,
            "scientific_answer": (
                "Exact parameter-inference sufficiency is established for "
                "the frozen one-intercept, fixed-covariance linear model."
                if status == FINAL_PASS_STATUS
                else "No sufficiency claim because at least one frozen gate failed."
            ),
            "object_count": len(inputs.names),
            "alpha": float(cholesky["alpha"]),
            "alpha_error": float(cholesky["alpha_error"]),
            "hubble_flow_minimum_chi2": float(cholesky["chi2"]),
            "hubble_flow_ndof": int(cholesky["ndof"]),
            "baseline_h0_value": float(baseline["h0_value"]),
            "baseline_h0_error": float(baseline["h0_error"]),
            "expanded_h0_value": float(
                network["expanded_full_block"]["h0_value"]
            ),
            "expanded_h0_error": float(
                network["expanded_full_block"]["h0_error"]
            ),
            "profile_identity_max_absolute_residual": profile_max,
            "expanded_vs_scalar_max_abs_parameter_difference": float(
                network["expanded_vs_scalar"][
                    "max_abs_parameter_difference"
                ]
            ),
            "expanded_vs_scalar_max_abs_parameter_covariance_difference": float(
                network["expanded_vs_scalar"][
                    "max_abs_parameter_covariance_difference"
                ]
            ),
            "permutation_maximum_tested_difference": permutation_max,
            "chi2_constant_omitted_by_scalar_network": float(
                network["expanded_minus_scalar_chi2"]
            ),
            "diagnostic_boundary": (
                "The scalar retains parameter information but not the full "
                "residual pattern or the parameter-independent goodness-of-fit term."
            ),
            "non_claim": (
                "No corrected H0, Hubble-tension significance, physical-model "
                "validation, or tension-resolution claim is made."
            ),
            "boundary_marker": BOUNDARY_MARKER,
            "profile_offsets_sigma": list(PROFILE_OFFSETS_SIGMA),
        }
        write_json(output / "phase0_summary.json", phase0_summary)

        report = english_report(
            status,
            baseline,
            alpha_record,
            network,
            profile_max,
            permutation_max,
        )
        report_ja = japanese_report(
            status,
            baseline,
            alpha_record,
            network,
            profile_max,
            permutation_max,
        )
        report_path = project / "PHASE0_REPORT.md"
        report_ja_path = project / "PHASE0_REPORT_JA.md"
        report_path.write_text(report, encoding="utf-8")
        report_ja_path.write_text(report_ja, encoding="utf-8")
        write_json(
            output / "report_generation.json",
            {
                "generator": "scripts/run_phase0.py",
                "report_path": "PHASE0_REPORT.md",
                "report_sha256": sha256_file(report_path),
                "report_ja_path": "PHASE0_REPORT_JA.md",
                "report_ja_sha256": sha256_file(report_ja_path),
                "boundary_marker": BOUNDARY_MARKER,
                "status": "PASS",
            },
        )
    except Exception as exc:
        failure = {
            "authoritative": True,
            "contract_id": CONTRACT_ID,
            "status": (
                "HOLD_SOURCE_MISMATCH"
                if "source" in str(exc).lower()
                or "commit" in str(exc).lower()
                else "HOLD_PUBLIC_INPUT_INCOMPLETE"
            ),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        write_json(output / "EXECUTION_STATUS.json", failure)
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(
        f"{status}: {len(inputs.names)} objects; "
        f"a_B={cholesky['alpha']:.15f} ± {cholesky['alpha_error']:.15f}; "
        f"profile max={profile_max:.3e}; "
        f"expanded parameter max={network['expanded_vs_scalar']['max_abs_parameter_difference']:.3e}"
    )
    return 0 if status == FINAL_PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
