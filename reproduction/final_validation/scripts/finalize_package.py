#!/usr/bin/env python3
"""Generate deterministic manifest and checksum files for the package tree."""

from __future__ import annotations

import csv
import hashlib
import pathlib


EXCLUDED = {"MANIFEST.tsv", "SHA256SUMS.txt"}


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def package_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.name not in EXCLUDED
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    rows = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        }
        for path in package_files(root)
    ]
    with (root / "MANIFEST.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "bytes", "sha256"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    (root / "SHA256SUMS.txt").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in rows),
        encoding="utf-8",
    )
    print(f"manifest_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
