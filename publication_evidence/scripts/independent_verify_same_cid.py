#!/usr/bin/env python3
"""Project-internal alternate Phase 1C parser without importing auditlib.

This separately written code path is not an external replication.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import sys

import numpy as np
import scipy.linalg
import scipy.stats
from scipy.constants import c as C_METRES_PER_SECOND


BASELINES = (
    "PHASE1A_FULL",
    "STAT_SYS_NO_ROWWISE_VELOCITY",
    "STAT_ONLY",
    "STAT_SYS_DIAGONAL_ONLY",
    "STAT_ONLY_DIAGONAL_ONLY",
)


def read_h0dn(path: pathlib.Path) -> dict[str, object]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    header = lines[0].lstrip("#").split()
    records = [dict(zip(header, line.split())) for line in lines[1:]]
    return {
        "names": [row["name"] for row in records],
        "mb": np.array([float(row["m_b"]) for row in records]),
        "zhel": np.array([float(row["zhel"]) for row in records]),
        "zcmb": np.array([float(row["zcmb"]) for row in records]),
        "vpec": np.array([float(row["vp_2mpp"]) for row in records]),
    }


def read_covariance(path: pathlib.Path) -> np.ndarray:
    values = np.fromfile(path, dtype=float, sep=" ")
    dimension = int(values[0])
    if values.size != 1 + dimension * dimension:
        raise RuntimeError(f"invalid covariance payload: {path.name}")
    return values[1:].reshape((dimension, dimension))


def read_official_identity(path: pathlib.Path) -> list[tuple[str, int]]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    header = lines[0].split()
    cid = header.index("CID")
    survey = header.index("IDSURVEY")
    return [
        (fields[cid], int(float(fields[survey])))
        for fields in (line.split() for line in lines[1:])
    ]


def read_mapping(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def alpha_data(data: dict[str, object]) -> tuple[np.ndarray, np.ndarray]:
    speed = C_METRES_PER_SECOND / 1000.0
    zhel = np.asarray(data["zhel"])
    zcmb = np.asarray(data["zcmb"])
    vpec = np.asarray(data["vpec"])
    zpec = np.sqrt((1 + vpec / speed) / (1 - vpec / speed)) - 1
    corrected = (1 + zcmb) / (1 + zpec) - 1
    ratio = 1 + corrected
    velocity = speed * (ratio**2 - 1) / (ratio**2 + 1)
    k = (
        1
        + 0.5 * (1 - (-0.55)) * corrected
        - (1 / 6)
        * (1 - (-0.55) - 3 * (-0.55) ** 2 + 1)
        * corrected**2
    )
    model = 0.2 * 5 * np.log10(
        (1 + zhel) / (1 + corrected) * speed * corrected * k
    )
    vector = model - 0.2 * np.asarray(data["mb"])
    velocity_variance = (
        np.log10(velocity + 240.0) - np.log10(velocity)
    ) ** 2
    return vector, velocity_variance


def group_incidence(names: list[str]) -> np.ndarray:
    ordered: list[str] = []
    index: dict[str, int] = {}
    for name in names:
        if name not in index:
            index[name] = len(ordered)
            ordered.append(name)
    matrix = np.zeros((len(names), len(ordered)))
    for row, name in enumerate(names):
        matrix[row, index[name]] = 1
    return matrix


def eig_quadratic(vector: np.ndarray, covariance: np.ndarray) -> float:
    eigenvalues, eigenvectors = scipy.linalg.eigh(covariance)
    if eigenvalues[0] <= 0:
        raise RuntimeError("projected covariance is not positive definite")
    coordinates = eigenvectors.T @ vector
    return float(np.sum(coordinates**2 / eigenvalues))


def classify(flags: list[bool]) -> str:
    phase1a, stat_sys, stat_only = flags
    if not phase1a:
        return "NO_PHASE1A_BASELINE_LOW_FLAG"
    if not stat_sys and not stat_only:
        return "LOW_FLAG_REMOVED_WITHOUT_ROWWISE_VELOCITY_TERM"
    if stat_sys and not stat_only:
        return (
            "LOW_FLAG_PERSISTS_WITHOUT_ROWWISE_VELOCITY_"
            "BUT_NOT_WITH_STATONLY"
        )
    if stat_sys and stat_only:
        return "LOW_FLAG_PERSISTS_THROUGH_STATONLY"
    return "NONMONOTONIC_COMPONENT_SENSITIVITY"


def execute(
    project: pathlib.Path,
    h0dn_root: pathlib.Path,
    pantheon_root: pathlib.Path,
) -> dict[str, object]:
    h0dn = read_h0dn(h0dn_root / "data" / "sn1a_hf_pp.dat")
    h0_cov = read_covariance(h0dn_root / "data" / "sn1a_covar_pp.dat")
    directory = pantheon_root / "Pantheon+_Data" / "4_DISTANCES_AND_COVAR"
    official_identity = read_official_identity(
        directory / "Pantheon+SH0ES.dat"
    )
    stat_sys = read_covariance(directory / "Pantheon+SH0ES_STAT+SYS.cov")
    stat_only = read_covariance(directory / "Pantheon+SH0ES_STATONLY.cov")
    mapping = read_mapping(project / "provenance" / "PHASE1B_ROW_MAP.tsv")

    names = list(h0dn["names"])
    if len(names) != 277 or len(mapping) != 277:
        raise RuntimeError("unexpected H0DN or mapping row count")
    target = np.array(
        [int(row["official_row_1based"]) - 1 for row in mapping]
    )
    if len(set(target.tolist())) != 277:
        raise RuntimeError("mapping targets are not unique")
    identity_checks = [
        names[index] == row["CID"]
        and official_identity[target[index]]
        == (row["CID"], int(row["IDSURVEY"]))
        for index, row in enumerate(mapping)
    ]
    if not all(identity_checks):
        raise RuntimeError("mapping identity check failed")

    z = group_incidence(names)
    basis = scipy.linalg.null_space(z.T).T
    if basis.shape != (39, 277):
        raise RuntimeError(f"unexpected null-space shape: {basis.shape}")
    data_alpha, velocity_variance = alpha_data(h0dn)
    contrast = basis @ data_alpha
    stat_sys = 0.5 * (stat_sys + stat_sys.T)
    stat_only = 0.5 * (stat_only + stat_only.T)
    stat_sys_mapped = stat_sys[np.ix_(target, target)]
    stat_only_mapped = stat_only[np.ix_(target, target)]
    if not np.array_equal(
        read_covariance(
            directory / "Pantheon+SH0ES_STAT+SYS.cov"
        )[np.ix_(target, target)],
        h0_cov,
    ):
        raise RuntimeError("STAT+SYS lineage mismatch")
    row_covariances = {
        "PHASE1A_FULL": h0_cov / 25 + np.diag(velocity_variance),
        "STAT_SYS_NO_ROWWISE_VELOCITY": stat_sys_mapped / 25,
        "STAT_ONLY": stat_only_mapped / 25,
        "STAT_SYS_DIAGONAL_ONLY": np.diag(
            np.diag(stat_sys_mapped)
        )
        / 25,
        "STAT_ONLY_DIAGONAL_ONLY": np.diag(
            np.diag(stat_only_mapped)
        )
        / 25,
    }
    recomputed: dict[str, dict[str, object]] = {}
    for name, row_covariance in row_covariances.items():
        projected = basis @ row_covariance @ basis.T
        q_value = eig_quadratic(contrast, projected)
        probability = float(scipy.stats.chi2.cdf(q_value, 39))
        recomputed[name] = {
            "chi2": q_value,
            "lower_tail_probability": probability,
            "low_flag_at_alpha_0_01": probability < 0.01,
        }

    reported = json.loads(
        (project / "results" / "covariance_baselines.json").read_text(
            encoding="utf-8"
        )
    )
    comparisons = []
    for name in BASELINES:
        difference = abs(recomputed[name]["chi2"] - reported[name]["chi2"])
        comparisons.append(
            {
                "baseline": name,
                "recomputed_chi2": recomputed[name]["chi2"],
                "reported_chi2": reported[name]["chi2"],
                "absolute_difference": difference,
                "tolerance": 2e-08,
                "status": "PASS" if difference <= 2e-08 else "FAIL",
            }
        )
    flags = [
        bool(recomputed[name]["low_flag_at_alpha_0_01"])
        for name in BASELINES[:3]
    ]
    independent_classification = classify(flags)
    audit_summary = json.loads(
        (project / "results" / "audit_summary.json").read_text(
            encoding="utf-8"
        )
    )
    classification_match = (
        independent_classification
        == audit_summary["sensitivity_classification"]
    )
    baseline_difference = abs(
        recomputed["PHASE1A_FULL"]["chi2"] - 11.209315063602752
    )
    status = (
        "PASS"
        if all(row["status"] == "PASS" for row in comparisons)
        and classification_match
        and baseline_difference <= 2e-08
        else "FAIL"
    )
    return {
        "implementation": (
            "project_internal_alternate_parser_null_space_eigendecomposition"
        ),
        "contrast_basis_shape": list(basis.shape),
        "contrast_basis_orthogonality_max_absolute_error": float(
            np.max(np.abs(basis @ basis.T - np.eye(39)))
        ),
        "group_annihilation_max_absolute_error": float(
            np.max(np.abs(basis @ z))
        ),
        "mapping_identity_check_count": len(identity_checks),
        "mapping_identity_pass_count": sum(identity_checks),
        "comparisons": comparisons,
        "known_phase1a_absolute_difference": baseline_difference,
        "independent_sensitivity_classification": independent_classification,
        "reported_sensitivity_classification": audit_summary[
            "sensitivity_classification"
        ],
        "classification_match": classification_match,
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h0dn", type=pathlib.Path, required=True)
    parser.add_argument("--pantheonplus", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = pathlib.Path(__file__).resolve().parents[1]
    try:
        result = execute(
            project, args.h0dn.resolve(), args.pantheonplus.resolve()
        )
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    target = project / "results" / "independent_verification.json"
    target.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"]}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
