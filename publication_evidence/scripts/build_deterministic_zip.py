#!/usr/bin/env python3
"""Create MANIFEST.tsv, SHA256SUMS.txt, and a deterministic v1.1 ZIP."""

from __future__ import annotations

import argparse
import csv
import hashlib
import pathlib
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCLUDED = {"MANIFEST.tsv", "SHA256SUMS.txt"}
FIXED_TIME = (2026, 8, 20, 0, 0, 0)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def role(relative: pathlib.PurePosixPath) -> str:
    if relative.parts[0] == "scripts":
        return "project_created_reproduction_code"
    if relative.parts[0] == "provenance":
        return "source_identity_or_crosswalk"
    if relative.parts[0] in {"evidence", "results"}:
        return "project_created_recorded_evidence"
    if relative.parts[0] == "environment":
        return "environment_declaration"
    return "documentation_or_license"


def build(output: pathlib.Path) -> pathlib.Path:
    members = sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and path.name not in EXCLUDED
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    rows: list[list[str]] = []
    checksums: list[str] = []
    for path in members:
        relative = pathlib.PurePosixPath(path.relative_to(ROOT).as_posix())
        digest = sha256(path)
        rows.append([relative.as_posix(), str(path.stat().st_size), digest, role(relative)])
        checksums.append(f"{digest}  {relative.as_posix()}")

    with (ROOT / "MANIFEST.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["path", "bytes", "sha256", "role"])
        writer.writerows(rows)
    (ROOT / "SHA256SUMS.txt").write_text(
        "\n".join(checksums) + "\n", encoding="utf-8"
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    archive_members = sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in archive_members:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{ROOT.name}/{relative}", FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if path.suffix == ".py" else 0o644
            info.external_attr = mode << 16
            archive.writestr(info, path.read_bytes())
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=ROOT.parent / "PUBLICATION_REPRODUCIBILITY_EVIDENCE_SUPPLEMENT_v1.1.zip",
    )
    args = parser.parse_args()
    result = build(args.output.resolve())
    print(f"zip={result} sha256={sha256(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
