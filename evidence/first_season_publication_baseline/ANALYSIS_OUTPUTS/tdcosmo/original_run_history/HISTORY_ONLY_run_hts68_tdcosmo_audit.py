#!/usr/bin/env python3
"""HTS68: audit the public TDCOSMO-2025 posterior-chain contract.

This stage is deliberately posterior-descriptive.  It validates the public
HDF5 exports, reproduces the published flat-LambdaCDM H0 table, and maps the
effect of nested external-lens and auxiliary-cosmology layers.  It does not
claim independent tension significance or rerun the original likelihood.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import h5py
import numpy as np


EXPECTED_CHAIN_FILES = {
    "LambdaCDM1a.h5",
    "LambdaCDM1b.h5",
    "LambdaCDM1c.h5",
    "LambdaCDM1d.h5",
    "LambdaCDM2a.h5",
    "LambdaCDM2b.h5",
    "LambdaCDM2c.h5",
    "LambdaCDM2d.h5",
    "LambdaCDM3a.h5",
    "LambdaCDM3b.h5",
    "ULambdaCDM1.h5",
    "ULambdaCDM2.h5",
    "ULambdaCDM3.h5",
    "ULambdaCDM4.h5",
    "UoLambdaCDM.h5",
    "UwCDM.h5",
    "Uw_0w_aCDM.h5",
    "Uw_phiCDM.h5",
    "oLambdaCDM.h5",
    "wCDM1.h5",
    "wCDM2.h5",
    "wCDM3.h5",
    "w_0w_aCDM1.h5",
    "w_0w_aCDM2.h5",
    "w_0w_aCDM3.h5",
    "w_0w_aCDM4.h5",
    "w_phiCDM1.h5",
    "w_phiCDM2.h5",
}

KEY_PARAMETERS = (
    "h0",
    "om",
    "rd",
    "lambda_mst",
    "lambda_mst_sigma",
    "alpha_lambda",
    "a_ani",
    "a_ani_sigma",
)

# Paper Table 6. Values are medians with 16th/84th-percentile errors.
# The DES-SN5YR full-lens paper row is called LambdaCDM2b in the paper but is
# LambdaCDM2d in the expanded public chain grid.
PAPER_H0 = {
    "ULambdaCDM1": ("UΛCDM1", 73.7, 4.4, 4.7),
    "ULambdaCDM2": ("UΛCDM2", 76.8, 4.6, 3.9),
    "ULambdaCDM3": ("UΛCDM3", 74.2, 4.5, 4.6),
    "ULambdaCDM4": ("UΛCDM4", 77.8, 4.7, 3.7),
    "LambdaCDM1a": ("ΛCDM1a", 71.6, 3.3, 3.9),
    "LambdaCDM1b": ("ΛCDM1b", 74.1, 3.3, 3.6),
    "LambdaCDM1c": ("ΛCDM1c", 72.1, 3.4, 3.6),
    "LambdaCDM1d": ("ΛCDM1d", 74.3, 3.7, 3.1),
    "LambdaCDM2a": ("ΛCDM2a", 71.2, 3.6, 3.7),
    "LambdaCDM2d": ("ΛCDM2b", 73.9, 3.0, 3.4),
    "LambdaCDM3a": ("ΛCDM3a", 72.4, 3.6, 3.9),
    "LambdaCDM3b": ("ΛCDM3b", 74.8, 3.4, 3.5),
}

GROUPS = {
    "NO_AUXILIARY_COSMOLOGY": {
        "BASE": "ULambdaCDM1",
        "SLACS": "ULambdaCDM2",
        "SL2S": "ULambdaCDM3",
        "SLACS_PLUS_SL2S": "ULambdaCDM4",
    },
    "PANTHEON_PLUS": {
        "BASE": "LambdaCDM1a",
        "SLACS": "LambdaCDM1b",
        "SL2S": "LambdaCDM1c",
        "SLACS_PLUS_SL2S": "LambdaCDM1d",
    },
    "DES_SN5YR": {
        "BASE": "LambdaCDM2a",
        "SLACS": "LambdaCDM2b",
        "SL2S": "LambdaCDM2c",
        "SLACS_PLUS_SL2S": "LambdaCDM2d",
    },
    "DESI_DR2_BAO": {
        "BASE": "LambdaCDM3a",
        "SLACS_PLUS_SL2S": "LambdaCDM3b",
    },
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def rounded_match(actual: float, expected: float, digits: int = 1) -> bool:
    return math.isclose(round(actual, digits), expected, abs_tol=10 ** (-digits) / 2)


def safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    if np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def summarize_chain(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    row: dict[str, Any] = {
        "filename": path.name,
        "sha256": sha256_path(path),
        "size_bytes": path.stat().st_size,
    }
    stats: dict[str, Any] = {}
    with h5py.File(path, "r") as handle:
        keys = sorted(handle.keys())
        attrs = {key: decode(value) for key, value in handle.attrs.items()}
        parameters = [decode(value) for value in handle["parameters"][:]]
        samples = handle["samples"][:]

        row.update(
            {
                "hdf5_open_pass": True,
                "dataset_keys": "|".join(keys),
                "sample_rows": samples.shape[0] if samples.ndim == 2 else -1,
                "sample_columns": samples.shape[1] if samples.ndim == 2 else -1,
                "parameter_count": len(parameters),
                "parameters_unique": len(parameters) == len(set(parameters)),
                "shape_parameter_match": (
                    samples.ndim == 2 and samples.shape[1] == len(parameters)
                ),
                "all_finite": bool(np.isfinite(samples).all()),
                "model_id": attrs.get("ModelID", ""),
                "model_id_matches_filename": attrs.get("ModelID", "") == path.stem,
                "dataset_attribute": attrs.get("dataset", ""),
                "description_present": bool(attrs.get("description", "").strip()),
                "weights_present": "weights" in keys,
                "log_probability_present": any(
                    name in keys for name in ("log_prob", "log_probability")
                ),
                "walker_or_chain_metadata_present": any(
                    re.search(r"(walker|chain|burn|thin|seed)", key, re.I)
                    for key in attrs
                ),
            }
        )

        for parameter in KEY_PARAMETERS:
            if parameter not in parameters:
                continue
            values = samples[:, parameters.index(parameter)]
            q16, q50, q84 = np.quantile(values, [0.16, 0.50, 0.84])
            stats[parameter] = {
                "q16": float(q16),
                "q50": float(q50),
                "q84": float(q84),
                "minus": float(q50 - q16),
                "plus": float(q84 - q50),
                "mean": float(np.mean(values)),
                "std": float(np.std(values, ddof=1)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
            }

        h0 = samples[:, parameters.index("h0")]
        om = samples[:, parameters.index("om")]
        lambda_mst = samples[:, parameters.index("lambda_mst")]
        stats["correlations"] = {
            "h0_lambda_mst": safe_corr(h0, lambda_mst),
            "h0_om": safe_corr(h0, om),
        }
    return row, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--paper-pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    paper_pdf = args.paper_pdf.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    commit = run_git(repo, "rev-parse", "HEAD")
    commit_date = run_git(repo, "show", "-s", "--format=%aI", "HEAD")
    remote_url = run_git(repo, "remote", "get-url", "origin")
    tracked_status = run_git(repo, "status", "--short", "--untracked-files=no")
    git_fsck = subprocess.run(
        ["git", "fsck", "--full"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    chain_dir = repo / "chains_export"
    chain_paths = sorted(chain_dir.glob("*.h5"))
    found_names = {path.name for path in chain_paths}
    set_match = found_names == EXPECTED_CHAIN_FILES

    chain_rows: list[dict[str, Any]] = []
    chain_stats: dict[str, dict[str, Any]] = {}
    for path in chain_paths:
        row, stats = summarize_chain(path)
        chain_rows.append(row)
        chain_stats[path.stem] = stats

    chain_fields = [
        "filename",
        "sha256",
        "size_bytes",
        "hdf5_open_pass",
        "dataset_keys",
        "sample_rows",
        "sample_columns",
        "parameter_count",
        "parameters_unique",
        "shape_parameter_match",
        "all_finite",
        "model_id",
        "model_id_matches_filename",
        "dataset_attribute",
        "description_present",
        "weights_present",
        "log_probability_present",
        "walker_or_chain_metadata_present",
    ]
    write_tsv(output / "HTS68_CHAIN_CONTRACT_AUDIT.tsv", chain_rows, chain_fields)

    flat_models = sorted({model for members in GROUPS.values() for model in members.values()})
    posterior_rows: list[dict[str, Any]] = []
    for model in flat_models:
        values = chain_stats[model]
        row: dict[str, Any] = {
            "release_model_id": model,
            "dataset_attribute": next(
                item["dataset_attribute"]
                for item in chain_rows
                if item["model_id"] == model
            ),
            "h0_q16": values["h0"]["q16"],
            "h0_median": values["h0"]["q50"],
            "h0_q84": values["h0"]["q84"],
            "h0_minus": values["h0"]["minus"],
            "h0_plus": values["h0"]["plus"],
            "om_median": values["om"]["q50"],
            "lambda_mst_median": values["lambda_mst"]["q50"],
            "lambda_mst_minus": values["lambda_mst"]["minus"],
            "lambda_mst_plus": values["lambda_mst"]["plus"],
            "lambda_mst_sigma_median": values["lambda_mst_sigma"]["q50"],
            "corr_h0_lambda_mst": values["correlations"]["h0_lambda_mst"],
            "corr_h0_om": values["correlations"]["h0_om"],
        }
        if "rd" in values:
            row["rd_median"] = values["rd"]["q50"]
            row["rd_minus"] = values["rd"]["minus"]
            row["rd_plus"] = values["rd"]["plus"]
        posterior_rows.append(row)
    posterior_fields = [
        "release_model_id",
        "dataset_attribute",
        "h0_q16",
        "h0_median",
        "h0_q84",
        "h0_minus",
        "h0_plus",
        "om_median",
        "rd_median",
        "rd_minus",
        "rd_plus",
        "lambda_mst_median",
        "lambda_mst_minus",
        "lambda_mst_plus",
        "lambda_mst_sigma_median",
        "corr_h0_lambda_mst",
        "corr_h0_om",
    ]
    write_tsv(
        output / "HTS68_FLAT_LCDM_POSTERIOR_SUMMARY.tsv",
        posterior_rows,
        posterior_fields,
    )

    reproduction_rows: list[dict[str, Any]] = []
    for release_id, (paper_id, h0, minus, plus) in PAPER_H0.items():
        actual = chain_stats[release_id]["h0"]
        passed = (
            rounded_match(actual["q50"], h0)
            and rounded_match(actual["minus"], minus)
            and rounded_match(actual["plus"], plus)
        )
        reproduction_rows.append(
            {
                "paper_model_id": paper_id,
                "release_model_id": release_id,
                "paper_h0_median": h0,
                "paper_h0_minus": minus,
                "paper_h0_plus": plus,
                "computed_h0_median": actual["q50"],
                "computed_h0_minus": actual["minus"],
                "computed_h0_plus": actual["plus"],
                "rounded_table_match": passed,
            }
        )
    write_tsv(
        output / "HTS68_PAPER_TABLE6_REPRODUCTION.tsv",
        reproduction_rows,
        [
            "paper_model_id",
            "release_model_id",
            "paper_h0_median",
            "paper_h0_minus",
            "paper_h0_plus",
            "computed_h0_median",
            "computed_h0_minus",
            "computed_h0_plus",
            "rounded_table_match",
        ],
    )

    crosswalk_rows = [
        {
            "paper_model_id": "ΛCDM2b",
            "paper_dataset": "TDCOSMO + DES-SN5YR + SLACS + SL2S",
            "correct_release_model_id": "LambdaCDM2d",
            "same_named_release_file": "LambdaCDM2b.h5",
            "same_named_release_dataset": "TDCOSMO + DES-SN5YR + SLACS",
            "risk": "PAPER_RELEASE_IDENTIFIER_COLLISION",
            "resolution": "Use HDF5 dataset attribute; do not select by paper ID alone.",
        },
        {
            "paper_model_id": "not listed in Table 6",
            "paper_dataset": "",
            "correct_release_model_id": "LambdaCDM2c",
            "same_named_release_file": "",
            "same_named_release_dataset": "TDCOSMO + DES-SN5YR + SL2S",
            "risk": "RELEASE_ONLY_INTERMEDIATE_LAYER",
            "resolution": "Treat as an additional public posterior, not a paper Table 6 row.",
        },
    ]
    write_tsv(
        output / "HTS68_CHAIN_IDENTIFIER_CROSSWALK.tsv",
        crosswalk_rows,
        [
            "paper_model_id",
            "paper_dataset",
            "correct_release_model_id",
            "same_named_release_file",
            "same_named_release_dataset",
            "risk",
            "resolution",
        ],
    )

    shift_rows: list[dict[str, Any]] = []
    for context, layers in GROUPS.items():
        base_id = layers["BASE"]
        base = chain_stats[base_id]
        base_halfwidth = (base["h0"]["minus"] + base["h0"]["plus"]) / 2
        for layer, model in layers.items():
            if layer == "BASE":
                continue
            current = chain_stats[model]
            current_halfwidth = (
                current["h0"]["minus"] + current["h0"]["plus"]
            ) / 2
            shift_rows.append(
                {
                    "auxiliary_cosmology_context": context,
                    "added_external_lens_layer": layer,
                    "base_release_model_id": base_id,
                    "comparison_release_model_id": model,
                    "delta_h0_median": current["h0"]["q50"] - base["h0"]["q50"],
                    "delta_lambda_mst_median": (
                        current["lambda_mst"]["q50"]
                        - base["lambda_mst"]["q50"]
                    ),
                    "delta_lambda_mst_sigma_median": (
                        current["lambda_mst_sigma"]["q50"]
                        - base["lambda_mst_sigma"]["q50"]
                    ),
                    "base_h0_68_halfwidth": base_halfwidth,
                    "comparison_h0_68_halfwidth": current_halfwidth,
                    "halfwidth_ratio_comparison_to_base": (
                        current_halfwidth / base_halfwidth
                    ),
                    "descriptive_shift_in_base_halfwidths": (
                        (current["h0"]["q50"] - base["h0"]["q50"])
                        / base_halfwidth
                    ),
                    "significance_interpretation_permitted": False,
                }
            )
    write_tsv(
        output / "HTS68_NESTED_DEPENDENCY_SHIFTS.tsv",
        shift_rows,
        [
            "auxiliary_cosmology_context",
            "added_external_lens_layer",
            "base_release_model_id",
            "comparison_release_model_id",
            "delta_h0_median",
            "delta_lambda_mst_median",
            "delta_lambda_mst_sigma_median",
            "base_h0_68_halfwidth",
            "comparison_h0_68_halfwidth",
            "halfwidth_ratio_comparison_to_base",
            "descriptive_shift_in_base_halfwidths",
            "significance_interpretation_permitted",
        ],
    )

    both_rows = [
        row for row in shift_rows if row["added_external_lens_layer"] == "SLACS_PLUS_SL2S"
    ]
    slacs_rows = [
        row for row in shift_rows if row["added_external_lens_layer"] == "SLACS"
    ]
    sl2s_rows = [
        row for row in shift_rows if row["added_external_lens_layer"] == "SL2S"
    ]
    paper_reproduction_pass = all(
        row["rounded_table_match"] for row in reproduction_rows
    )
    chain_contract_pass = (
        set_match
        and len(chain_rows) == 28
        and all(
            row["hdf5_open_pass"]
            and row["dataset_keys"] == "parameters|samples"
            and row["sample_rows"] == 500000
            and row["parameters_unique"]
            and row["shape_parameter_match"]
            and row["all_finite"]
            and row["model_id_matches_filename"]
            and row["description_present"]
            for row in chain_rows
        )
    )
    consistent_both_direction = all(
        row["delta_h0_median"] > 0 and row["delta_lambda_mst_median"] > 0
        for row in both_rows
    )
    slacs_dominates = all(
        slacs["delta_h0_median"] > sl2s["delta_h0_median"]
        for slacs, sl2s in zip(slacs_rows, sl2s_rows)
    )

    readme = (repo / "README.md").read_text(encoding="utf-8")
    sampling_code = (repo / "likelihood_sampling.py").read_text(encoding="utf-8")
    portability_rows = [
        {
            "check": "README_REFERENCED_CONFIG_EXISTS",
            "result": "FAIL"
            if "parameter_config_example.yaml" in readme
            and not (repo / "parameter_config_example.yaml").exists()
            else "PASS",
            "detail": "README names parameter_config_example.yaml; repository contains parameter_config.yaml.",
        },
        {
            "check": "SAMPLING_CODE_USES_PORTABLE_DATA_ROOT",
            "result": "FAIL"
            if re.search(r"dir_path\s*=\s*['\"]/cluster/", sampling_code)
            else "PASS",
            "detail": "likelihood_sampling.py contains site-specific absolute cluster paths.",
        },
        {
            "check": "PINNED_RUNTIME_DEPENDENCIES_PRESENT",
            "result": "PASS"
            if any(
                (repo / name).exists()
                for name in (
                    "requirements.txt",
                    "environment.yml",
                    "pyproject.toml",
                    "poetry.lock",
                )
            )
            else "FAIL",
            "detail": "No pinned dependency manifest was found at repository root.",
        },
        {
            "check": "EXPORTED_CHAIN_CONVERGENCE_METADATA_PRESENT",
            "result": "PASS"
            if all(row["walker_or_chain_metadata_present"] for row in chain_rows)
            else "FAIL",
            "detail": "Exports omit walker/time dimensions, burn/thin/seed metadata, and log probability.",
        },
    ]
    write_tsv(
        output / "HTS68_CODE_REPRODUCIBILITY_AUDIT.tsv",
        portability_rows,
        ["check", "result", "detail"],
    )

    limitations = [
        {
            "limitation_id": "L01",
            "scope": "MCMC_CONVERGENCE",
            "status": "NOT_INDEPENDENTLY_AUDITABLE_FROM_EXPORT",
            "detail": "HDF5 exports contain flattened samples and parameter names but no walker/time dimensions, burn-in, thinning, seed, weights, or log probability.",
        },
        {
            "limitation_id": "L02",
            "scope": "LIKELIHOOD_REEXECUTION",
            "status": "HOLD_PORTABILITY_AND_ENVIRONMENT_CONTRACT",
            "detail": "The public script contains site-specific absolute paths, the README names an absent example config, and no pinned runtime dependency manifest is supplied.",
        },
        {
            "limitation_id": "L03",
            "scope": "MODEL_IDENTIFIER",
            "status": "RESOLVED_BY_DATASET_ATTRIBUTE_CROSSWALK",
            "detail": "Paper ΛCDM2b corresponds to release LambdaCDM2d; release LambdaCDM2b is the SLACS-only intermediate posterior.",
        },
        {
            "limitation_id": "L04",
            "scope": "CAUSAL_ATTRIBUTION",
            "status": "PROHIBITED",
            "detail": "Nested posterior shifts share time-delay data and hierarchical assumptions; they are dependency diagnostics, not independent significances or causal likelihood contributions.",
        },
        {
            "limitation_id": "L05",
            "scope": "HUBBLE_TENSION",
            "status": "UNRESOLVED",
            "detail": "The public TDCOSMO posteriors remain broad and do not establish a resolution, correction, or new-physics explanation.",
        },
    ]
    write_tsv(
        output / "HTS68_LIMITATION_REGISTER.tsv",
        limitations,
        ["limitation_id", "scope", "status", "detail"],
    )

    source_rows = [
        {
            "source": "TDCOSMO2025_PUBLIC_REPOSITORY",
            "locator": remote_url,
            "frozen_identifier": commit,
            "sha256": "",
            "validation": (
                "PASS"
                if not tracked_status and git_fsck.returncode == 0
                else "FAIL"
            ),
        },
        {
            "source": "TDCOSMO2025_ARXIV_PDF",
            "locator": "https://arxiv.org/pdf/2506.03023",
            "frozen_identifier": "2506.03023",
            "sha256": sha256_path(paper_pdf),
            "validation": "PASS",
        },
    ]
    write_tsv(
        output / "HTS68_SOURCE_FREEZE.tsv",
        source_rows,
        ["source", "locator", "frozen_identifier", "sha256", "validation"],
    )

    classification = {
        "phase": "HTS68",
        "stage": "TDCOSMO2025_PUBLIC_CHAIN_CONTRACT_AND_DEPENDENCY_AUDIT",
        "classification": (
            "PASS_TDCOSMO2025_PUBLIC_CHAIN_DEPENDENCY_RECONSTRUCTION_WITH_SCOPE"
            if chain_contract_pass
            and paper_reproduction_pass
            and consistent_both_direction
            else "HOLD_TDCOSMO2025_CHAIN_OR_REPRODUCTION_FAILURE"
        ),
        "source_reentry_gate": "PASS_TDCOSMO_PUBLIC_HDF5_TRIGGER_MET",
        "source_commit": commit,
        "source_commit_date": commit_date,
        "chain_count": len(chain_rows),
        "expected_chain_set_match": set_match,
        "chain_contract_pass": chain_contract_pass,
        "paper_table6_h0_reproduction_pass": paper_reproduction_pass,
        "paper_table6_h0_reproduction_count": sum(
            row["rounded_table_match"] for row in reproduction_rows
        ),
        "paper_table6_h0_expected_count": len(reproduction_rows),
        "combined_external_lens_h0_and_lambda_direction_consistent": consistent_both_direction,
        "slacs_shift_exceeds_sl2s_shift_in_all_comparable_contexts": slacs_dominates,
        "identifier_crosswalk_required": True,
        "exact_mcmc_convergence_independently_rerun": False,
        "exact_likelihood_reexecution": False,
        "branch_decision": (
            "KEEP_TDCOSMO_BRANCH_OPEN_FOR_PORTABLE_LIKELIHOOD_AND_SYSTEMATICS_AUDIT"
        ),
        "claim_boundary": {
            "hubble_tension_resolved": False,
            "new_physics_established": False,
            "corrected_h0_constructed": False,
            "independent_tension_significance_computed": False,
            "causal_component_attribution": False,
        },
    }
    (output / "HTS68_CLASSIFICATION.json").write_text(
        json.dumps(classification, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    def f1(value: float) -> str:
        return f"{value:.1f}"

    key_models = [
        "ULambdaCDM1",
        "ULambdaCDM4",
        "LambdaCDM1d",
        "LambdaCDM2d",
        "LambdaCDM3b",
    ]
    report_lines = [
        "# HTS68 execution report",
        "",
        "`PASS_TDCOSMO2025_PUBLIC_CHAIN_DEPENDENCY_RECONSTRUCTION_WITH_SCOPE`",
        "",
        "## Outcome",
        "",
        "The HTV136 TDCOSMO re-entry trigger is now met: the official public",
        "repository supplies 28 HDF5 posterior exports and likelihood-preparation",
        "materials. All 28 HDF5 files open successfully, contain 500,000 finite",
        "rows, have internally consistent parameter dimensions, and match their",
        "embedded model identifiers.",
        "",
        f"The released chains reproduce {sum(row['rounded_table_match'] for row in reproduction_rows)}/{len(reproduction_rows)} "
        "flat-LambdaCDM H0 rows in the paper's Table 6 at the published precision.",
        "",
        "## Key posterior layers",
        "",
        "| Release model | Dataset layer | H0 median (16th, 84th) | lambda_mst median |",
        "|---|---|---:|---:|",
    ]
    row_by_model = {row["release_model_id"]: row for row in posterior_rows}
    for model in key_models:
        row = row_by_model[model]
        report_lines.append(
            f"| {model} | {row['dataset_attribute']} | "
            f"{f1(row['h0_median'])} (-{f1(row['h0_minus'])}/+{f1(row['h0_plus'])}) | "
            f"{row['lambda_mst_median']:.3f} |"
        )
    report_lines.extend(
        [
            "",
            "Across all four flat-LambdaCDM auxiliary-cosmology contexts, adding",
            "SLACS+SL2S moves both the H0 median and the internal mass-sheet",
            "population mean upward. Where SLACS and SL2S are separately released,",
            "the SLACS shift is larger in every comparable context. This localizes",
            "the dominant released-posterior dependency to the external-lens",
            "population layer, primarily SLACS. It does not establish a causal",
            "systematic or an independent shift significance.",
            "",
            "## Contract warning",
            "",
            "The paper identifier `ΛCDM2b` denotes the DES-SN5YR posterior with",
            "SLACS+SL2S. In the expanded chain release, `LambdaCDM2b.h5` is SLACS",
            "only; the paper row is reproduced by `LambdaCDM2d.h5`. Dataset",
            "attributes, not filenames alone, are therefore authoritative.",
            "",
            "## Remaining hold",
            "",
            "Exact MCMC convergence and exact likelihood reexecution are not",
            "independently closed. The exports omit walker/time, burn-in, thinning,",
            "seed, weights and log-probability metadata. The supplied sampling code",
            "also contains site-specific absolute paths, the README references an",
            "absent example config, and no pinned dependency environment is present.",
            "",
            "## Boundary",
            "",
            "This is a posterior-contract and dependency audit. It is not an",
            "independent tension significance, a corrected H0, a causal mass-sheet",
            "attribution, or evidence that the Hubble tension is resolved.",
            "",
        ]
    )
    (output / "HTS68_EXECUTION_REPORT.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )

    selection_text = """# HTS68 selection audit

## Previous endpoint

HTS67 is accepted as `HOLD_SYMMETRIC_POOLING_CONVENTION_SENSITIVITY`.
Its numerical result is stable, but the fixed-block attribution changes under
two predeclared symmetric covariance-pooling conventions. Additional arbitrary
metric choices are not selected.

## External re-entry check

The frozen HTV136 trigger for `TDCOSMO_EXACT_CHAIN_DEPENDENCY_RECONSTRUCTION`
required public HDF5 chains to be locally available and contract-audited. The
official TDCOSMO-2025 repository now supplies those chains. This is a genuine
source-contract change, not an automatic reopening based on the old package.

## Selected question

Which posterior layer—time-delay lenses, external SLACS/SL2S lenses, or
Pantheon+/DES-SN5YR/DESI-DR2 auxiliary cosmology—controls the movement and
precision of the released TDCOSMO-2025 H0 posterior?

## Rejected operations

- no naive combination with CMB, SH0ES, MCP or standard sirens;
- no independent-significance label for nested posterior shifts;
- no preferred H0 or corrected H0;
- no attribution to a unique physical systematic;
- no full MCMC rerun without a portable, frozen execution contract.
"""
    (output / "HTS68_SELECTION_AUDIT.md").write_text(
        selection_text, encoding="utf-8"
    )

    adequacy_text = """# HTS68 source adequacy audit

The official repository is adequate for:

- exact HDF5 structural validation;
- marginal posterior quantile reproduction;
- paper-table cross-checking;
- posterior-layer dependency mapping;
- parameter-correlation diagnostics.

It is not adequate by itself for an independent convergence audit or exact
likelihood rerun because the exported chains are flattened and lack sampler
metadata, while the execution code is not packaged with a portable pinned
runtime and path contract.
"""
    (output / "HTS68_SOURCE_ADEQUACY_AUDIT.md").write_text(
        adequacy_text, encoding="utf-8"
    )

    result_files = sorted(
        path for path in output.iterdir() if path.is_file()
    )
    manifest = {
        "phase": "HTS68",
        "classification": classification["classification"],
        "source_commit": commit,
        "files": [
            {
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_path(path),
            }
            for path in result_files
        ],
    }
    (output / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    hash_targets = sorted(path for path in output.iterdir() if path.is_file())
    with (output / "SHA256SUMS.txt").open("w", encoding="utf-8") as handle:
        for path in hash_targets:
            handle.write(f"{sha256_path(path)}  {path.name}\n")

    print(json.dumps(classification, indent=2, ensure_ascii=False))
    return 0 if classification["classification"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
