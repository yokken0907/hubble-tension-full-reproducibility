#!/usr/bin/env python3
"""Derive the compact frozen Phase 1B mapping dependency."""

from __future__ import annotations

import argparse
import csv
import pathlib


FIELDS = [
    "h0dn_row_1based",
    "official_row_1based",
    "CID",
    "IDSURVEY",
    "final_dependency_classification",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase1b-row-mapping", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    with args.phase1b_row_mapping.open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        source = list(csv.DictReader(handle, delimiter="\t"))
    if len(source) != 277:
        raise RuntimeError(f"expected 277 Phase 1B rows, found {len(source)}")

    compact: list[dict[str, str]] = []
    for expected_row, row in enumerate(source, start=1):
        if (
            int(row["h0dn_row_1based"]) != expected_row
            or row["match_status"] != "UNIQUE_MATCH"
            or row["name"] != row["official_CID"]
        ):
            raise RuntimeError(f"invalid Phase 1B mapping row {expected_row}")
        compact.append(
            {
                "h0dn_row_1based": row["h0dn_row_1based"],
                "official_row_1based": row["official_row_1based"],
                "CID": row["official_CID"],
                "IDSURVEY": row["IDSURVEY"],
                "final_dependency_classification": row[
                    "final_dependency_classification"
                ],
            }
        )
    if len({row["official_row_1based"] for row in compact}) != 277:
        raise RuntimeError("Phase 1B target rows are not one-to-one")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(compact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

