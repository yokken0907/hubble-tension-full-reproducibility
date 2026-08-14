#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shlex
import shutil
import sys
import traceback
import zipfile

import h5py
import numpy as np


RESULT_BASENAME = "TDCOSMO_BLIND_SENTINEL_RESULTS_FOR_REVIEW"
AUDIT_COLUMNS = [
    "filename",
    "sha256",
    "source_hash_gate",
    "top_level_objects",
    "file_attributes_json",
    "samples_shape",
    "samples_dtype",
    "parameters_shape",
    "parameters_dtype",
    "n_samples",
    "n_parameters",
    "parameter_names_unique",
    "sample_column_count_matches_parameters",
    "h0_match_count",
    "h0_column_index",
    "h0_all_finite",
    "structural_status",
]
QUANTILE_COLUMNS = [
    "filename",
    "parameter_name",
    "n_values",
    "weighting",
    "quantile_method",
    "q16",
    "q50",
    "q84",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def shape_text(shape: tuple[int, ...]) -> str:
    return ",".join(str(int(dimension)) for dimension in shape)


def decode_utf8(value: object) -> str:
    if isinstance(value, (bytes, np.bytes_)):
        return bytes(value).decode("utf-8")
    if isinstance(value, str):
        return value
    raise TypeError(f"Expected a byte string or string, got {type(value).__name__}")


def json_compatible(value: object) -> object:
    if isinstance(value, (bytes, np.bytes_)):
        return bytes(value).decode("utf-8")
    if isinstance(value, np.ndarray):
        return [json_compatible(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return json_compatible(value.item())
    if isinstance(value, tuple):
        return [json_compatible(item) for item in value]
    if isinstance(value, list):
        return [json_compatible(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_compatible(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported HDF5 attribute type for JSON: {type(value).__name__}")


def object_type_name(obj: object) -> str:
    if isinstance(obj, h5py.Dataset):
        return "dataset"
    if isinstance(obj, h5py.Group):
        return "group"
    if isinstance(obj, h5py.Datatype):
        return "datatype"
    return type(obj).__name__


def type7_quantile(sorted_values: np.ndarray, probability: float) -> float:
    count = int(sorted_values.size)
    if count == 0:
        raise ValueError("Cannot calculate a quantile from an empty array")
    h = (count - 1) * probability
    lower = math.floor(h)
    upper = math.ceil(h)
    return float(
        sorted_values[lower]
        + (h - lower) * (sorted_values[upper] - sorted_values[lower])
    )


def bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def write_tsv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=columns,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def read_source_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"filename", "sha256"}
    if not rows or not required.issubset(rows[0].keys()):
        raise ValueError("SOURCE_MANIFEST.tsv is missing required columns")
    return rows


def empty_audit_row(filename: str, digest: str, gate: str) -> dict[str, object]:
    return {
        "filename": filename,
        "sha256": digest,
        "source_hash_gate": gate,
        "top_level_objects": "",
        "file_attributes_json": "",
        "samples_shape": "",
        "samples_dtype": "",
        "parameters_shape": "",
        "parameters_dtype": "",
        "n_samples": "",
        "n_parameters": "",
        "parameter_names_unique": "",
        "sample_column_count_matches_parameters": "",
        "h0_match_count": "",
        "h0_column_index": "",
        "h0_all_finite": "",
        "structural_status": "NOT_RUN",
    }


def audit_file(
    input_path: Path, filename: str, digest: str
) -> tuple[dict[str, object], list[dict[str, object]], dict[str, object] | None]:
    parameter_rows: list[dict[str, object]] = []
    quantile_row: dict[str, object] | None = None

    with h5py.File(input_path, "r") as handle:
        top_level = [
            {"name": name, "type": object_type_name(handle[name])}
            for name in sorted(handle.keys())
        ]
        attributes = {
            str(key): json_compatible(handle.attrs[key])
            for key in sorted(handle.attrs.keys())
        }

        samples_obj = handle.get("samples")
        parameters_obj = handle.get("parameters")
        samples_is_dataset = isinstance(samples_obj, h5py.Dataset)
        parameters_is_dataset = isinstance(parameters_obj, h5py.Dataset)

        samples_shape = tuple(samples_obj.shape) if samples_is_dataset else ()
        parameters_shape = tuple(parameters_obj.shape) if parameters_is_dataset else ()
        samples_dtype = str(samples_obj.dtype) if samples_is_dataset else ""
        parameters_dtype = str(parameters_obj.dtype) if parameters_is_dataset else ""

        parameter_names: list[str] = []
        parameter_decode_ok = False
        if parameters_is_dataset:
            raw_parameters = parameters_obj[...]
            try:
                parameter_names = [
                    decode_utf8(item) for item in np.asarray(raw_parameters).reshape(-1)
                ]
                parameter_decode_ok = parameters_obj.ndim == 1
            except (TypeError, UnicodeDecodeError):
                parameter_names = []
                parameter_decode_ok = False

        for index, name in enumerate(parameter_names):
            parameter_rows.append(
                {
                    "filename": filename,
                    "column_index": index,
                    "parameter_name": name,
                }
            )

        samples_two_dimensional = samples_is_dataset and samples_obj.ndim == 2
        n_samples = int(samples_shape[0]) if samples_two_dimensional else ""
        n_parameters = len(parameter_names) if parameter_decode_ok else ""
        names_unique = (
            len(set(parameter_names)) == len(parameter_names)
            if parameter_decode_ok
            else False
        )
        columns_match = (
            samples_two_dimensional
            and parameter_decode_ok
            and int(samples_shape[1]) == len(parameter_names)
        )
        h0_indices = [
            index for index, name in enumerate(parameter_names) if name == "h0"
        ]
        h0_match_count = len(h0_indices)
        h0_index: int | str = h0_indices[0] if h0_match_count == 1 else ""

        h0_all_finite = False
        h0_values: np.ndarray | None = None
        if samples_two_dimensional and columns_match and h0_match_count == 1:
            h0_values = np.asarray(samples_obj[:, int(h0_index)], dtype=np.float64)
            h0_all_finite = bool(np.isfinite(h0_values).all())

        structural_pass = all(
            [
                samples_is_dataset,
                parameters_is_dataset,
                samples_two_dimensional,
                parameter_decode_ok,
                names_unique,
                columns_match,
                h0_match_count == 1,
                h0_all_finite,
            ]
        )

        audit_row = {
            "filename": filename,
            "sha256": digest,
            "source_hash_gate": "PASS",
            "top_level_objects": json.dumps(
                top_level, ensure_ascii=False, separators=(",", ":")
            ),
            "file_attributes_json": json.dumps(
                attributes,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
            "samples_shape": shape_text(samples_shape) if samples_is_dataset else "",
            "samples_dtype": samples_dtype,
            "parameters_shape": (
                shape_text(parameters_shape) if parameters_is_dataset else ""
            ),
            "parameters_dtype": parameters_dtype,
            "n_samples": n_samples,
            "n_parameters": n_parameters,
            "parameter_names_unique": bool_text(names_unique),
            "sample_column_count_matches_parameters": bool_text(columns_match),
            "h0_match_count": h0_match_count,
            "h0_column_index": h0_index,
            "h0_all_finite": bool_text(h0_all_finite),
            "structural_status": "PASS" if structural_pass else "FAIL",
        }

        if structural_pass and h0_values is not None:
            sorted_h0 = np.sort(h0_values, kind="quicksort")
            q16 = type7_quantile(sorted_h0, 0.16)
            q50 = type7_quantile(sorted_h0, 0.50)
            q84 = type7_quantile(sorted_h0, 0.84)
            quantile_row = {
                "filename": filename,
                "parameter_name": "h0",
                "n_values": int(sorted_h0.size),
                "weighting": "equal",
                "quantile_method": "type7_linear_n_minus_1",
                "q16": format(q16, ".17e"),
                "q50": format(q50, ".17e"),
                "q84": format(q84, ".17e"),
            }

    return audit_row, parameter_rows, quantile_row


def write_method_note(path: Path) -> None:
    text = f"""# Method Note

- Implementation language: Python {platform.python_version()}.
- Libraries: NumPy {np.__version__}; h5py {h5py.__version__}.
- Byte-string decoding: every element of the `parameters` dataset was decoded exactly with UTF-8; byte-valued file attributes, if present, were also decoded with UTF-8 for valid JSON representation.
- H0 location: the zero-based column index was obtained only by finding the unique decoded parameter name exactly equal to `h0`; no numeric column index was hard-coded.
- Quantile algorithm: all H0 rows were used with equal weight. Values were sorted ascending. For each p in {{0.16, 0.50, 0.84}}, h = (n - 1) * p, i = floor(h), j = ceil(h), and q(p) = x[i] + (h - i) * (x[j] - x[i]).
- Serialization: `top_level_objects` is compact JSON listing each sorted top-level name and its HDF5 object type. `file_attributes_json` is compact valid JSON containing every file-level attribute; JSON escaping preserves embedded newlines and other characters.
- Blindness confirmation: no external source, paper, repository, prior implementation, prior numerical result, expected value, correction patch, or identifier crosswalk was consulted.
- Weighting confirmation: no thinning, resampling, reweighting, or weighted posterior calculation was performed.
- Warning or deviation: none.
"""
    path.write_text(text, encoding="utf-8", newline="\n")


def write_environment(path: Path) -> None:
    uname = platform.uname()
    lines = [
        f"operating_system={platform.platform()}",
        f"system={uname.system}",
        f"release={uname.release}",
        f"version={uname.version}",
        f"machine_architecture={uname.machine}",
        f"processor={uname.processor}",
        f"python_executable={sys.executable}",
        f"python_version={sys.version.replace(os.linesep, ' ')}",
        f"numpy_version={np.__version__}",
        f"h5py_version={h5py.__version__}",
        f"hdf5_version={h5py.version.hdf5_version}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_sha256s(result_dir: Path) -> None:
    checksum_path = result_dir / "SHA256SUMS.txt"
    members = sorted(
        path
        for path in result_dir.rglob("*")
        if path.is_file() and path != checksum_path
    )
    lines = [
        f"{sha256_file(path)}  {path.relative_to(result_dir).as_posix()}"
        for path in members
    ]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def make_deterministic_zip(result_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    root_name = result_dir.name
    with zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(p for p in result_dir.rglob("*") if p.is_file()):
            relative = path.relative_to(result_dir).as_posix()
            archive_name = f"{root_name}/{relative}"
            info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, path.read_bytes())


def run(package_root: Path, output_parent: Path, source_path: Path) -> Path:
    result_dir = output_parent / RESULT_BASENAME
    result_zip = output_parent / f"{RESULT_BASENAME}.zip"
    if result_dir.exists():
        shutil.rmtree(result_dir)
    result_dir.mkdir(parents=True)
    source_dir = result_dir / "SOURCE_CODE"
    source_dir.mkdir()

    shutil.copy2(source_path, source_dir / source_path.name)
    command_parts = [sys.executable]
    if sys.flags.no_site:
        command_parts.append("-S")
    command_parts.extend(sys.argv)
    command = shlex.join(command_parts)
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        command = f"PYTHONPATH={shlex.quote(pythonpath)} {command}"
    (result_dir / "RUN_COMMAND.txt").write_text(
        command + "\n", encoding="utf-8", newline="\n"
    )
    write_environment(result_dir / "ENVIRONMENT.txt")
    write_method_note(result_dir / "METHOD_NOTE.md")

    stdout_path = result_dir / "RUN_LOG_STDOUT.txt"
    stderr_path = result_dir / "RUN_LOG_STDERR.txt"

    try:
        with stdout_path.open("w", encoding="utf-8", newline="\n") as stdout_stream, \
             stderr_path.open("w", encoding="utf-8", newline="\n") as stderr_stream, \
             contextlib.redirect_stdout(stdout_stream), \
             contextlib.redirect_stderr(stderr_stream):

            manifest_path = package_root / "SOURCE_MANIFEST.tsv"
            inputs_dir = package_root / "INPUTS"
            manifest = read_source_manifest(manifest_path)

            hash_records: list[tuple[dict[str, str], Path, str, bool]] = []
            for row in manifest:
                input_path = inputs_dir / row["filename"]
                actual = sha256_file(input_path)
                match = actual == row["sha256"]
                hash_records.append((row, input_path, actual, match))
                print(
                    f"HASH {row['filename']} "
                    f"{'PASS' if match else 'FAIL'} {actual}"
                )

            audit_rows: list[dict[str, object]] = []
            parameter_rows: list[dict[str, object]] = []
            quantile_rows: list[dict[str, object]] = []

            if not all(record[3] for record in hash_records):
                print("SOURCE_HASH_GATE=FAIL")
                for row, _input_path, actual, match in hash_records:
                    audit_rows.append(
                        empty_audit_row(
                            row["filename"], actual, "PASS" if match else "FAIL"
                        )
                    )
            else:
                print("SOURCE_HASH_GATE=PASS")
                for row, input_path, actual, _match in hash_records:
                    audit_row, file_parameters, quantile_row = audit_file(
                        input_path, row["filename"], actual
                    )
                    audit_rows.append(audit_row)
                    parameter_rows.extend(file_parameters)
                    if quantile_row is not None:
                        quantile_rows.append(quantile_row)
                    print(
                        f"AUDIT {row['filename']} "
                        f"{audit_row['structural_status']}"
                    )

            write_tsv(result_dir / "FILE_AUDIT.tsv", AUDIT_COLUMNS, audit_rows)
            write_tsv(
                result_dir / "PARAMETERS.tsv",
                ["filename", "column_index", "parameter_name"],
                parameter_rows,
            )
            write_tsv(
                result_dir / "H0_QUANTILES.tsv",
                QUANTILE_COLUMNS,
                quantile_rows,
            )
    except Exception:
        with stderr_path.open("a", encoding="utf-8", newline="\n") as stream:
            traceback.print_exc(file=stream)
        raise

    write_sha256s(result_dir)
    make_deterministic_zip(result_dir, result_zip)
    return result_zip


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output-parent", type=Path, required=True)
    args = parser.parse_args()

    package_root = args.package_root.resolve()
    output_parent = args.output_parent.resolve()
    output_parent.mkdir(parents=True, exist_ok=True)
    run(package_root, output_parent, Path(__file__).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
