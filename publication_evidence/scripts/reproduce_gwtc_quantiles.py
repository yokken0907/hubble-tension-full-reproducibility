#!/usr/bin/env python3
"""Project-internal alternate Gate A implementation for frozen GWTC samples.

The primary percentile implementation below is a direct deterministic
Hyndman-Fan type 7 implementation. NumPy is used only as a secondary
cross-check. No official notebook computation code is imported or copied.
This implementation is not an external replication.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PERCENTILES = (15.865, 50.0, 84.135)
CROSSCHECK_TOLERANCE = 1e-10

INPUTS = (
    {
        "release": "GWTC-4",
        "record_id": "16919645",
        "doi": "10.5281/zenodo.16919645",
        "filename": "H0_dark_combined.json",
        "path": PACKAGE_ROOT / "INPUTS" / "GWTC4" / "H0_dark_combined.json",
        "source_freeze_relative_path": "SOURCES/GWTC4/H0_dark_combined.json",
        "byte_size": 66251,
        "official_md5": "00c057f15e215d909ad1b7a6760a7af2",
        "sha256": "b4b5e271d94f0ac828c840a46d72bd5e9433d706a47f352abfcdd3fbc2014fc8",
        "sample_key": "posterior",
        "sample_count": 3500,
        "headline": {
            "median": 76.6,
            "lower_error": 9.5,
            "upper_error": 13.0,
        },
    },
    {
        "release": "GWTC-5",
        "record_id": "20378418",
        "doi": "10.5281/zenodo.20378418",
        "filename": "H0_dark_combined_gw170817.json",
        "path": PACKAGE_ROOT
        / "INPUTS"
        / "GWTC5"
        / "H0_dark_combined_gw170817.json",
        "source_freeze_relative_path": (
            "SOURCES/GWTC5/H0_dark_combined_gw170817.json"
        ),
        "byte_size": 66225,
        "official_md5": "532f9c59374dede625e08987985e4df5",
        "sha256": "00aaee9573ae940ac156c1b4af441e075a462a4c54152ac20d03511b877ce0d5",
        "sample_key": "posterior",
        "sample_count": 3500,
        "headline": {
            "median": 71.0,
            "lower_error": 7.1,
            "upper_error": 9.0,
        },
    },
)


class GateHold(RuntimeError):
    """Raised when the frozen input cannot be interpreted as contracted."""


def digest(data: bytes, algorithm: str) -> str:
    return hashlib.new(algorithm, data).hexdigest()


def float_text(value: float) -> str:
    return format(float(value), ".17g")


def rounded_one_decimal(value: float) -> float:
    return float(f"{float(value):.1f}")


def type7_percentile(sorted_values: list[float], percentile: float) -> float:
    """Return the Hyndman-Fan type 7 percentile of pre-sorted values."""

    if not sorted_values:
        raise GateHold("posterior sample is empty")
    if not 0.0 <= percentile <= 100.0:
        raise ValueError("percentile must be in [0, 100]")

    probability = percentile / 100.0
    index = (len(sorted_values) - 1) * probability
    lower_index = math.floor(index)
    fraction = index - lower_index

    if lower_index >= len(sorted_values) - 1:
        return sorted_values[-1]

    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[lower_index + 1]
    return lower_value + fraction * (upper_value - lower_value)


def load_and_validate(spec: dict[str, Any]) -> tuple[list[float], dict[str, Any]]:
    raw = Path(spec["path"]).read_bytes()
    local_md5 = digest(raw, "md5")
    local_sha256 = digest(raw, "sha256")

    identity_checks = {
        "byte_size_match": len(raw) == spec["byte_size"],
        "official_md5_match": local_md5 == spec["official_md5"],
        "source_freeze_sha256_match": local_sha256 == spec["sha256"],
    }
    if not all(identity_checks.values()):
        raise GateHold(
            f"{spec['release']} input identity mismatch: {identity_checks}"
        )

    payload = json.loads(raw)
    if not isinstance(payload, dict) or set(payload) != {spec["sample_key"]}:
        raise GateHold(
            f"{spec['release']} JSON root is not the contracted single-key object"
        )

    values = payload[spec["sample_key"]]
    if not isinstance(values, list):
        raise GateHold(f"{spec['release']} sample value is not a JSON array")
    if len(values) != spec["sample_count"]:
        raise GateHold(
            f"{spec['release']} sample count {len(values)} != "
            f"{spec['sample_count']}"
        )

    numeric_values: list[float] = []
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise GateHold(
                f"{spec['release']} non-numeric sample at index {index}"
            )
        numeric = float(value)
        if not math.isfinite(numeric):
            raise GateHold(f"{spec['release']} non-finite sample at index {index}")
        numeric_values.append(numeric)

    identity = {
        "byte_size": len(raw),
        "local_md5": local_md5,
        "local_sha256": local_sha256,
        "json_keys": sorted(payload),
        "sample_count": len(numeric_values),
        "identity_status": "PASS",
    }
    return numeric_values, identity


def write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    input_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    crosscheck_rows: list[dict[str, Any]] = []
    machine_results: dict[str, Any] = {}

    print("GATE_A_PRECONTRACT = FIXED")
    print("PRIMARY_IMPLEMENTATION = CUSTOM_HYNDMAN_FAN_TYPE_7_LINEAR")
    print("SECONDARY_IMPLEMENTATION = NUMPY_PERCENTILE_METHOD_LINEAR")
    print(f"CROSSCHECK_TOLERANCE = {CROSSCHECK_TOLERANCE:.1e}")
    print("RANDOM_OR_RESAMPLING = NO")

    for spec in INPUTS:
        samples, identity = load_and_validate(spec)
        sorted_samples = sorted(samples)
        custom = {
            percentile: type7_percentile(sorted_samples, percentile)
            for percentile in PERCENTILES
        }
        numpy_values = np.percentile(
            np.asarray(samples, dtype=np.float64),
            np.asarray(PERCENTILES, dtype=np.float64),
            method="linear",
        )
        numpy_result = {
            percentile: float(value)
            for percentile, value in zip(PERCENTILES, numpy_values, strict=True)
        }

        q_low = custom[15.865]
        q_median = custom[50.0]
        q_high = custom[84.135]
        lower_error = q_median - q_low
        upper_error = q_high - q_median
        average_uncertainty = (lower_error + upper_error) / 2.0

        derived = {
            "q15_865": q_low,
            "q50": q_median,
            "q84_135": q_high,
            "lower_error": lower_error,
            "upper_error": upper_error,
            "average_uncertainty_68_27": average_uncertainty,
        }
        rounded = {
            "median": rounded_one_decimal(q_median),
            "lower_error": rounded_one_decimal(lower_error),
            "upper_error": rounded_one_decimal(upper_error),
        }

        crosscheck_pass = True
        for percentile in PERCENTILES:
            absolute_difference = abs(custom[percentile] - numpy_result[percentile])
            item_pass = absolute_difference <= CROSSCHECK_TOLERANCE
            crosscheck_pass = crosscheck_pass and item_pass
            crosscheck_rows.append(
                {
                    "release": spec["release"],
                    "percentile": float_text(percentile),
                    "custom_type7": float_text(custom[percentile]),
                    "numpy_linear": float_text(numpy_result[percentile]),
                    "absolute_difference": float_text(absolute_difference),
                    "tolerance": float_text(CROSSCHECK_TOLERANCE),
                    "match": "YES" if item_pass else "NO",
                }
            )

        headline_pass = True
        for metric in ("median", "lower_error", "upper_error"):
            item_pass = rounded[metric] == spec["headline"][metric]
            headline_pass = headline_pass and item_pass
            raw_metric = (
                q_median
                if metric == "median"
                else lower_error
                if metric == "lower_error"
                else upper_error
            )
            comparison_rows.append(
                {
                    "release": spec["release"],
                    "metric": metric,
                    "computed_raw": float_text(raw_metric),
                    "computed_rounded_1dp": f"{rounded[metric]:.1f}",
                    "official_headline_1dp": f"{spec['headline'][metric]:.1f}",
                    "match": "YES" if item_pass else "NO",
                }
            )

        input_rows.append(
            {
                "release": spec["release"],
                "official_record_id": spec["record_id"],
                "doi": spec["doi"],
                "filename": spec["filename"],
                "packaged_relative_path": str(
                    Path(spec["path"]).relative_to(PACKAGE_ROOT)
                ),
                "source_freeze_relative_path": spec["source_freeze_relative_path"],
                "role": "frozen_headline_posterior_gate_a",
                "byte_size": identity["byte_size"],
                "official_md5": spec["official_md5"],
                "local_md5": identity["local_md5"],
                "local_sha256": identity["local_sha256"],
                "sample_key": spec["sample_key"],
                "sample_count": identity["sample_count"],
                "used_in_gate": "YES",
                "identity_status": identity["identity_status"],
            }
        )
        raw_rows.append(
            {
                "release": spec["release"],
                "official_record_id": spec["record_id"],
                "filename": spec["filename"],
                "sample_key": spec["sample_key"],
                "sample_count": identity["sample_count"],
                "q15_865": float_text(q_low),
                "q50": float_text(q_median),
                "q84_135": float_text(q_high),
                "lower_error": float_text(lower_error),
                "upper_error": float_text(upper_error),
                "average_uncertainty_68_27": float_text(average_uncertainty),
                "primary_algorithm": "custom_hyndman_fan_type_7_linear",
            }
        )

        release_pass = crosscheck_pass and headline_pass
        machine_results[spec["release"]] = {
            "identity": identity,
            "custom_quantiles": {str(key): value for key, value in custom.items()},
            "numpy_quantiles": {
                str(key): value for key, value in numpy_result.items()
            },
            "derived": derived,
            "rounded": rounded,
            "official_headline": spec["headline"],
            "implementation_crosscheck": "PASS" if crosscheck_pass else "FAIL",
            "headline_comparison": "PASS" if headline_pass else "FAIL",
            "release_gate": "PASS" if release_pass else "FAIL",
        }

        print(
            f"{spec['release']} INPUT_IDENTITY = PASS; "
            f"N = {identity['sample_count']}"
        )
        print(
            f"{spec['release']} RAW = "
            f"q15.865 {q_low:.15g}; q50 {q_median:.15g}; "
            f"q84.135 {q_high:.15g}; "
            f"-{lower_error:.15g}; +{upper_error:.15g}"
        )
        print(
            f"{spec['release']} ROUNDED = "
            f"{rounded['median']:.1f} "
            f"+{rounded['upper_error']:.1f} "
            f"/ -{rounded['lower_error']:.1f}; "
            f"HEADLINE_MATCH = {'PASS' if headline_pass else 'FAIL'}"
        )
        print(
            f"{spec['release']} IMPLEMENTATION_CROSSCHECK = "
            f"{'PASS' if crosscheck_pass else 'FAIL'}"
        )

    old_average = machine_results["GWTC-4"]["derived"][
        "average_uncertainty_68_27"
    ]
    new_average = machine_results["GWTC-5"]["derived"][
        "average_uncertainty_68_27"
    ]
    diagnostic_reduction = (old_average - new_average) / old_average * 100.0
    published_metric = 25.7
    diagnostic_rows = [
        {
            "metric_id": "HEADLINE_POSTERIOR_PAIR_RAW_68P27",
            "old_release": "GWTC-4",
            "new_release": "GWTC-5",
            "old_average_uncertainty_raw": float_text(old_average),
            "new_average_uncertainty_raw": float_text(new_average),
            "relative_reduction_percent_raw": float_text(diagnostic_reduction),
            "published_metric_percent": f"{published_metric:.1f}",
            "difference_percentage_points": float_text(
                diagnostic_reduction - published_metric
            ),
            "used_for_gate_a": "NO",
            "used_to_reproduce_published_25p7": "NO",
            "interpretation": "DIAGNOSTIC_ONLY_DISTINCT_FROM_PUBLISHED_25P7",
        }
    ]

    gate_a_pass = all(
        value["release_gate"] == "PASS" for value in machine_results.values()
    )
    gate_a_decision = "PASS" if gate_a_pass else "FAIL"

    write_tsv(
        PACKAGE_ROOT / "INPUT_SOURCE_REGISTER.tsv",
        [
            "release",
            "official_record_id",
            "doi",
            "filename",
            "packaged_relative_path",
            "source_freeze_relative_path",
            "role",
            "byte_size",
            "official_md5",
            "local_md5",
            "local_sha256",
            "sample_key",
            "sample_count",
            "used_in_gate",
            "identity_status",
        ],
        input_rows,
    )
    write_tsv(
        PACKAGE_ROOT / "RAW_QUANTILES.tsv",
        [
            "release",
            "official_record_id",
            "filename",
            "sample_key",
            "sample_count",
            "q15_865",
            "q50",
            "q84_135",
            "lower_error",
            "upper_error",
            "average_uncertainty_68_27",
            "primary_algorithm",
        ],
        raw_rows,
    )
    write_tsv(
        PACKAGE_ROOT / "ROUNDED_HEADLINE_COMPARISON.tsv",
        [
            "release",
            "metric",
            "computed_raw",
            "computed_rounded_1dp",
            "official_headline_1dp",
            "match",
        ],
        comparison_rows,
    )
    write_tsv(
        PACKAGE_ROOT / "IMPLEMENTATION_CROSSCHECK.tsv",
        [
            "release",
            "percentile",
            "custom_type7",
            "numpy_linear",
            "absolute_difference",
            "tolerance",
            "match",
        ],
        crosscheck_rows,
    )
    write_tsv(
        PACKAGE_ROOT / "HEADLINE_PAIR_DIAGNOSTIC_METRIC.tsv",
        [
            "metric_id",
            "old_release",
            "new_release",
            "old_average_uncertainty_raw",
            "new_average_uncertainty_raw",
            "relative_reduction_percent_raw",
            "published_metric_percent",
            "difference_percentage_points",
            "used_for_gate_a",
            "used_to_reproduce_published_25p7",
            "interpretation",
        ],
        diagnostic_rows,
    )

    machine_payload = {
        "gate_a_decision": gate_a_decision,
        "definitions": {
            "percentiles": list(PERCENTILES),
            "primary_algorithm": "custom_hyndman_fan_type_7_linear",
            "secondary_algorithm": "numpy.percentile(method='linear')",
            "crosscheck_tolerance": CROSSCHECK_TOLERANCE,
            "rounding": "each median/lower_error/upper_error independently to 1 dp",
        },
        "results": machine_results,
        "headline_pair_diagnostic": {
            "old_average_uncertainty_raw": old_average,
            "new_average_uncertainty_raw": new_average,
            "relative_reduction_percent_raw": diagnostic_reduction,
            "published_metric_percent": published_metric,
            "used_for_gate_a": False,
            "used_to_reproduce_published_25p7": False,
        },
        "gate_b_carry_forward": {
            "metric_code_path": "PASS",
            "metric_arithmetic_trace": "PASS",
            "metric_posterior_pair_provenance": "HOLD_NOT_UNIQUE",
        },
        "stop_after_gate_a": True,
        "no_automatic_expansion": True,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }
    (PACKAGE_ROOT / "RESULTS_MACHINE_READABLE.json").write_text(
        json.dumps(machine_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        "HEADLINE_PAIR_DIAGNOSTIC_RELATIVE_REDUCTION_PERCENT = "
        f"{diagnostic_reduction:.15g}"
    )
    print("HEADLINE_PAIR_DIAGNOSTIC_USED_FOR_25P7 = NO")
    print(f"GATE_A_DECISION = {gate_a_decision}")
    print("GATE_B_METRIC_POSTERIOR_PAIR_PROVENANCE = HOLD_NOT_UNIQUE")
    print("STOP_AFTER_GATE_A = YES")
    print("NO_AUTOMATIC_EXPANSION = YES")

    return 0 if gate_a_pass else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateHold as exc:
        print(f"GATE_A_DECISION = HOLD: {exc}", file=sys.stderr)
        raise SystemExit(3)
