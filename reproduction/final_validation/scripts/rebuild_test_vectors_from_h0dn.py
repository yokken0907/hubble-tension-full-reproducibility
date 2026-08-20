#!/usr/bin/env python3
"""Build self-contained numerical test vectors from the frozen H0DN source."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import io
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

import numpy as np


H0DN_COMMIT = "cc0a4b9f36e65470d514f254a3c5cffa463fbd94"


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(repr(value.shape).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


@contextlib.contextmanager
def pushd(path: pathlib.Path):
    previous = pathlib.Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def git_output(root: pathlib.Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def capture_h0dn(upstream: pathlib.Path) -> tuple[dict[str, Any], dict[str, Any]]:
    module_root = (upstream / "h0_constrainer").resolve()
    config_dir = module_root / "configs"
    for name in list(sys.modules):
        if name == "h0_constrainer" or name.startswith("h0_constrainer."):
            del sys.modules[name]
    sys.path.insert(0, str(module_root))
    main_module = importlib.import_module("h0_constrainer.main")
    equation_module = importlib.import_module("h0_constrainer.equations")
    solver_module = importlib.import_module("h0_constrainer.solver")
    captured: dict[str, Any] = {}
    original_build = equation_module.build_equations
    original_solve = solver_module.solve_system

    def capture_build(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original_build(*args, **kwargs)
        captured["equation_data"] = result
        return result

    def capture_solve(equation_data: dict[str, Any]) -> dict[str, Any]:
        result = original_solve(equation_data)
        captured["solution"] = result
        return result

    equation_module.build_equations = capture_build
    solver_module.solve_system = capture_solve
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with pushd(config_dir), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            main_module.main("config.ini")
    finally:
        equation_module.build_equations = original_build
        solver_module.solve_system = original_solve
        if sys.path and sys.path[0] == str(module_root):
            sys.path.pop(0)
    if {"equation_data", "solution"} - set(captured):
        raise RuntimeError("untouched H0DN matrix capture did not complete")
    captured["stdout"] = stdout.getvalue()
    captured["stderr"] = stderr.getvalue()
    return captured["equation_data"], captured["solution"]


def parse_sn_inputs(upstream: pathlib.Path) -> tuple[np.ndarray, np.ndarray]:
    table = upstream / "data" / "sn1a_hf_pp.dat"
    covariance_file = upstream / "data" / "sn1a_covar_pp.dat"
    rows: list[list[float]] = []
    for line_number, raw in enumerate(table.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 9:
            raise RuntimeError(f"unexpected SN table schema at line {line_number}")
        rows.append([float(value) for value in fields[1:]])
    values = np.asarray(rows, dtype=np.float64)
    raw_covariance = np.loadtxt(covariance_file, dtype=np.float64).reshape(-1)
    dimension = int(raw_covariance[0])
    covariance_mag = raw_covariance[1:].reshape(dimension, dimension)
    if values.shape != (277, 8) or covariance_mag.shape != (277, 277):
        raise RuntimeError("unexpected frozen SN input dimensions")

    mb = values[:, 0]
    zhel = values[:, 2]
    zcmb = values[:, 3]
    vpec = values[:, 7]
    speed_of_light = 299792.458
    q0 = -0.55
    j0 = 1.0
    velocity_dispersion = 240.0
    zpec = np.sqrt(
        (1.0 + vpec / speed_of_light) / (1.0 - vpec / speed_of_light)
    ) - 1.0
    zcorrected = (1.0 + zcmb) / (1.0 + zpec) - 1.0
    ratio = 1.0 + zcorrected
    vcorrected = speed_of_light * (ratio**2 - 1.0) / (ratio**2 + 1.0)
    kz = (
        1.0
        + 0.5 * (1.0 - q0) * zcorrected
        - (1.0 / 6.0)
        * (1.0 - q0 - 3.0 * q0**2 + j0)
        * zcorrected**2
    )
    magnitude_model = 5.0 * np.log10(
        ((1.0 + zhel) / (1.0 + zcorrected))
        * (speed_of_light * zcorrected)
        * kz
    )
    data_alpha = 0.2 * (magnitude_model - mb)
    velocity_variance = (
        np.log10(vcorrected + velocity_dispersion) - np.log10(vcorrected)
    ) ** 2
    covariance_alpha = covariance_mag / 25.0 + np.diag(velocity_variance)
    return data_alpha, covariance_alpha


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=pathlib.Path)
    parser.add_argument("--output-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    upstream = args.upstream.resolve()
    output = args.output_root.resolve()
    output.mkdir(parents=True, exist_ok=True)

    head = git_output(upstream, "rev-parse", "HEAD")
    if head != H0DN_COMMIT:
        raise RuntimeError(f"H0DN HEAD mismatch: {head}")
    equation_data, solution = capture_h0dn(upstream)
    coeffs = np.asarray(equation_data["coeffs"], dtype=np.float64)
    observations = np.asarray(equation_data["yval"], dtype=np.float64)
    covariance = np.asarray(equation_data["covar"], dtype=np.float64)
    ihub = int(equation_data["ihub"])
    iabs = int(equation_data["iabs"])

    h0dn_path = output / "h0dn_network_gls.npz"
    np.savez_compressed(
        h0dn_path,
        coeffs=coeffs,
        observations=observations,
        covariance=covariance,
        ihub=np.asarray([ihub], dtype=np.int64),
        iabs=np.asarray([iabs], dtype=np.int64),
    )

    sn_data, sn_covariance = parse_sn_inputs(upstream)
    sn_path = output / "sn_intercept_block.npz"
    np.savez_compressed(
        sn_path,
        data_alpha=sn_data,
        covariance_alpha=sn_covariance,
    )

    locked_paths = [
        "h0_constrainer/configs/config.ini",
        "h0_constrainer/h0_constrainer/equations.py",
        "h0_constrainer/h0_constrainer/solver.py",
        "data/sn1a_hf_pp.dat",
        "data/sn1a_covar_pp.dat",
    ]
    metadata = {
        "generator": "project-internal matrix capture plus independent raw SN parser",
        "h0dn_commit": head,
        "source_files": {
            path: sha256_file(upstream / path) for path in locked_paths
        },
        "h0dn_vector": {
            "archive_sha256": sha256_file(h0dn_path),
            "coeffs_shape": list(coeffs.shape),
            "coeffs_sha256": sha256_array(coeffs),
            "observations_shape": list(observations.shape),
            "observations_sha256": sha256_array(observations),
            "covariance_shape": list(covariance.shape),
            "covariance_sha256": sha256_array(covariance),
            "ihub": ihub,
            "iabs": iabs,
            "untouched_h0": float(solution["h0_value"]),
            "untouched_h0_error": float(solution["h0_error"]),
            "untouched_covariance_rank": int(solution["covar_rank"]),
        },
        "sn_vector": {
            "archive_sha256": sha256_file(sn_path),
            "data_shape": list(sn_data.shape),
            "data_sha256": sha256_array(sn_data),
            "covariance_shape": list(sn_covariance.shape),
            "covariance_sha256": sha256_array(sn_covariance),
        },
        "independence_boundary": (
            "Matrix construction uses the untouched frozen H0DN workflow. "
            "The delivered solvers are project-internal independent linear-algebra "
            "reimplementations, not external replication."
        ),
    }
    (output / "TEST_VECTOR_PROVENANCE.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
