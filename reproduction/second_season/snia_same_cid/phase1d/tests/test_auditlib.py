#!/usr/bin/env python3
"""Unit and locked-result regression tests for Phase 1D."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import sys
import tempfile
import unittest


PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

import auditlib  # noqa: E402


def candidate(
    path: str,
    cid: str,
    survey: str,
    digest: str,
    observations: list[bytes] | None = None,
    status: str = "PASS",
) -> dict[str, object]:
    obs = observations or [b"OBS: 1"]
    return {
        "source_directory": path.split("/")[0],
        "path": path,
        "git_blob_sha1": "a" * 40,
        "bytes": 100,
        "sha256": digest,
        "SNID": cid,
        "SURVEY": survey,
        "NOBS": len(obs),
        "observation_lines": obs,
        "observation_line_count": len(obs),
        "observation_lines_sha256": hashlib.sha256(
            b"\n".join(obs) + b"\n"
        ).hexdigest(),
        "active_list_occurrences": 1,
        "ignore_list_occurrences": 0,
        "status": status,
    }


def synthetic_inputs(
    second_hash: str = "2" * 64,
    second_observations: list[bytes] | None = None,
) -> tuple[
    list[dict[str, object]],
    dict[str, object],
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
]:
    population = [
        {
            "h0dn_row_1based": 1,
            "official_row_1based": 11,
            "CID": "SNX",
            "IDSURVEY": 1,
        },
        {
            "h0dn_row_1based": 2,
            "official_row_1based": 12,
            "CID": "SNX",
            "IDSURVEY": 2,
        },
    ]
    config = {
        "source_vocabulary": {
            "1": {
                "label": "ONE",
                "survey_headers": ["S1"],
                "directories": [{"directory": "d1"}],
            },
            "2": {
                "label": "TWO",
                "survey_headers": ["S2"],
                "directories": [{"directory": "d2"}],
            },
        }
    }
    parsed = {
        "d1/a.dat": candidate(
            "d1/a.dat", "SNX", "S1", "1" * 64, [b"OBS: A"]
        ),
        "d2/b.dat": candidate(
            "d2/b.dat",
            "SNX",
            "S2",
            second_hash,
            second_observations or [b"OBS: B"],
        ),
    }
    directories = {
        "d1": {
            "active_paths": ["d1/a.dat"],
            "unparseable_paths": [],
        },
        "d2": {
            "active_paths": ["d2/b.dat"],
            "unparseable_paths": [],
        },
    }
    return population, config, directories, parsed


class PrimitiveTests(unittest.TestCase):
    def test_sha256_bytes(self) -> None:
        self.assertEqual(
            auditlib.sha256_bytes(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_normalize_repository(self) -> None:
        self.assertEqual(
            auditlib.normalize_repository(" https://example.test/a.git/ "),
            "https://example.test/a",
        )

    def test_normalize_survey(self) -> None:
        self.assertEqual(
            auditlib.normalize_survey("  PS1_LOWZ   (X)\t"), "PS1_LOWZ (X)"
        )

    def test_active_list_entries(self) -> None:
        rows, counts = auditlib.active_list_entries(
            b"# comment\n a.dat \n\nb.dat\na.dat\n"
        )
        self.assertEqual(rows, ["a.dat", "b.dat", "a.dat"])
        self.assertEqual(counts["a.dat"], 2)
        self.assertEqual(counts["b.dat"], 1)

    def test_json_writer_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "x.json"
            auditlib.write_json(path, {"z": 1, "a": 2})
            self.assertEqual(path.read_text(), '{\n  "a": 2,\n  "z": 1\n}\n')

    def test_tsv_round_trip_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "x.tsv"
            auditlib.write_tsv(path, [{"a": "1", "b": "2"}], ("a", "b"))
            self.assertEqual(
                auditlib.read_tsv(path, ("a", "b")),
                [{"a": "1", "b": "2"}],
            )
            with self.assertRaises(auditlib.AuditFailure):
                auditlib.read_tsv(path, ("b", "a"))


class PhotometryParserTests(unittest.TestCase):
    def test_valid_blob(self) -> None:
        result = auditlib.parse_photometry_blob(
            b"SNID: 2005M\nSURVEY:  CSP  \nNOBS: 2\nOBS: A\nOBS: B\n"
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["SNID"], "2005M")
        self.assertEqual(result["SURVEY"], "CSP")
        self.assertEqual(result["NOBS"], 2)
        self.assertEqual(result["observation_line_count"], 2)

    def test_nobs_is_optional(self) -> None:
        result = auditlib.parse_photometry_blob(
            b"SNID: X\nSURVEY: S\nOBS: A\n"
        )
        self.assertEqual(result["status"], "PASS")
        self.assertIsNone(result["NOBS"])

    def test_duplicate_snid_fails(self) -> None:
        result = auditlib.parse_photometry_blob(
            b"SNID: X\nSNID: Y\nSURVEY: S\n"
        )
        self.assertIn("SNID_HEADER_COUNT_2", result["parse_errors"])

    def test_missing_survey_fails(self) -> None:
        result = auditlib.parse_photometry_blob(b"SNID: X\nNOBS: 0\n")
        self.assertIn("SURVEY_HEADER_COUNT_0", result["parse_errors"])

    def test_duplicate_nobs_fails(self) -> None:
        result = auditlib.parse_photometry_blob(
            b"SNID: X\nSURVEY: S\nNOBS: 0\nNOBS: 0\n"
        )
        self.assertIn("NOBS_HEADER_COUNT_2", result["parse_errors"])

    def test_nobs_count_mismatch_fails(self) -> None:
        result = auditlib.parse_photometry_blob(
            b"SNID: X\nSURVEY: S\nNOBS: 2\nOBS: A\n"
        )
        self.assertIn(
            "NOBS_OBSERVATION_LINE_COUNT_MISMATCH",
            result["parse_errors"],
        )

    def test_negative_nobs_fails(self) -> None:
        result = auditlib.parse_photometry_blob(
            b"SNID: X\nSURVEY: S\nNOBS: -1\n"
        )
        self.assertIn("NEGATIVE_NOBS", result["parse_errors"])

    def test_invalid_header_utf8_fails(self) -> None:
        result = auditlib.parse_photometry_blob(
            b"SNID: \xff\nSURVEY: S\nNOBS: 0\n"
        )
        self.assertIn("HEADER_UTF8_DECODE_FAILURE", result["parse_errors"])

    def test_observation_digest_normalizes_line_terminators(self) -> None:
        left = auditlib.parse_photometry_blob(
            b"SNID: X\r\nSURVEY: S\r\nNOBS: 1\r\nOBS: A\r\n"
        )
        right = auditlib.parse_photometry_blob(
            b"SNID: X\nSURVEY: S\nNOBS: 1\nOBS: A\n"
        )
        self.assertEqual(
            left["observation_lines_sha256"],
            right["observation_lines_sha256"],
        )


class LineageRuleTests(unittest.TestCase):
    def test_distinct_unique_group(self) -> None:
        args = synthetic_inputs()
        rows, files, groups, pairs = auditlib.row_and_group_lineage(*args)
        self.assertEqual(
            [row["lineage_status"] for row in rows],
            ["UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE"] * 2,
        )
        self.assertEqual(len(files), 2)
        self.assertEqual(
            groups[0]["group_lineage_classification"],
            "ALL_ROWS_UNIQUE_DISTINCT_PUBLIC_PHOTOMETRY_FILES",
        )
        self.assertEqual(
            pairs[0]["observation_line_overlap_classification"],
            "NO_BYTE_IDENTICAL_OBSERVATION_LINES",
        )

    def test_reused_file_hash_classification(self) -> None:
        args = synthetic_inputs(second_hash="1" * 64)
        _rows, _files, groups, _pairs = auditlib.row_and_group_lineage(*args)
        self.assertEqual(
            groups[0]["group_lineage_classification"],
            "PUBLIC_PHOTOMETRY_FILE_REUSE_PRESENT",
        )

    def test_exact_observation_overlap(self) -> None:
        args = synthetic_inputs(second_observations=[b"OBS: A", b"OBS: C"])
        _rows, _files, groups, pairs = auditlib.row_and_group_lineage(*args)
        self.assertEqual(pairs[0]["shared_exact_observation_line_count"], 1)
        self.assertEqual(
            pairs[0]["observation_line_overlap_classification"],
            "BYTE_IDENTICAL_OBSERVATION_LINES_PRESENT",
        )
        self.assertEqual(
            groups[0]["pairs_with_byte_identical_observation_lines"], 1
        )

    def test_zero_candidate_is_unresolved(self) -> None:
        population, config, directories, parsed = synthetic_inputs()
        directories["d2"]["active_paths"] = []
        rows, _files, groups, pairs = auditlib.row_and_group_lineage(
            population, config, directories, parsed
        )
        self.assertEqual(
            rows[1]["lineage_status"], "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE"
        )
        self.assertEqual(
            groups[0]["group_lineage_classification"],
            "PUBLIC_PHOTOMETRY_LINEAGE_UNRESOLVED",
        )
        self.assertEqual(
            pairs[0]["observation_line_overlap_classification"],
            "UNRESOLVED_FILE_PAIR",
        )

    def test_multiple_candidates_are_ambiguous(self) -> None:
        population, config, directories, parsed = synthetic_inputs()
        parsed["d2/c.dat"] = candidate(
            "d2/c.dat", "SNX", "S2", "3" * 64
        )
        directories["d2"]["active_paths"].append("d2/c.dat")
        rows, files, _groups, _pairs = auditlib.row_and_group_lineage(
            population, config, directories, parsed
        )
        self.assertEqual(
            rows[1]["lineage_status"],
            "AMBIGUOUS_ACTIVE_PUBLIC_PHOTOMETRY_FILES",
        )
        self.assertEqual(rows[1]["active_candidate_count"], 2)
        self.assertEqual(len(files), 3)

    def test_parse_failure_has_precedence(self) -> None:
        population, config, directories, parsed = synthetic_inputs()
        directories["d2"]["unparseable_paths"] = ["d2/broken.dat"]
        rows, _files, _groups, _pairs = auditlib.row_and_group_lineage(
            population, config, directories, parsed
        )
        self.assertEqual(rows[1]["lineage_status"], "PHOTOMETRY_PARSE_FAILURE")


class LockedResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.results = PROJECT / "results"

    def load(self, name: str) -> dict[str, object]:
        return json.loads((self.results / name).read_text())

    def test_contract_freeze(self) -> None:
        result = auditlib.verify_contract_freeze(PROJECT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["contract_freeze_sha256"],
            auditlib.CONTRACT_FREEZE_SHA256,
        )

    def test_amendment_register_contains_exact_amend_001(self) -> None:
        with (PROJECT / "provenance" / "CONTRACT_AMENDMENTS.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["amendment_id"], "AMEND-001")
        self.assertEqual(rows[0]["new_results_observed"], "YES")
        self.assertEqual(rows[0]["interpretation_affected"], "YES")

    def test_main_summary_counts(self) -> None:
        summary = self.load("audit_summary.json")
        self.assertEqual(summary["status"], auditlib.SUCCESS_STATUS)
        self.assertEqual(
            summary["release_sufficiency_classification"],
            "PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE",
        )
        self.assertEqual(summary["row_lineage"]["row_count"], 69)
        self.assertEqual(
            summary["row_lineage"]["classification_counts"],
            {
                "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE": 31,
                "UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE": 38,
            },
        )
        self.assertEqual(summary["group_lineage"]["group_count"], 30)
        self.assertEqual(summary["group_lineage"]["pair_count"], 48)

    def test_main_independent_verification(self) -> None:
        result = self.load("independent_verification.json")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["check_count"], result["pass_count"])
        self.assertEqual(result["check_count"], 15)
        self.assertEqual(
            result["verification_type"], "SECOND_IMPLEMENTATION_CROSS_CHECK"
        )
        self.assertEqual(result["independent_external_replication"], "NO")
        self.assertEqual(result["peer_review_or_expert_endorsement"], "NO")

    def test_posthoc_is_nonpromoting_and_protected(self) -> None:
        summary = self.load("posthoc_cid_only_crosswalk_summary.json")
        self.assertEqual(summary["unresolved_main_row_count"], 31)
        self.assertEqual(summary["cid_only_candidate_ledger_row_count"], 73)
        self.assertEqual(
            summary["classification_counts"],
            {
                "MULTIPLE_CID_ONLY_PUBLIC_FILES_OUTSIDE_FROZEN_CROSSWALK": 31
            },
        )
        self.assertEqual(
            summary["promotion_status"],
            "POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE",
        )
        self.assertTrue(summary["all_protected_main_results_byte_unchanged"])

    def test_posthoc_independent_verification(self) -> None:
        result = self.load(
            "posthoc_cid_only_crosswalk_independent_verification.json"
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["check_count"], result["pass_count"])
        self.assertEqual(
            result["verification_type"], "SECOND_IMPLEMENTATION_CROSS_CHECK"
        )
        self.assertEqual(result["independent_external_replication"], "NO")
        self.assertEqual(result["peer_review_or_expert_endorsement"], "NO")

    def test_row_legacy_statuses_have_explicit_interpretations(self) -> None:
        with (self.results / "row_lineage.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 69)
        for row in rows:
            self.assertEqual(row["lineage_status_legacy"], row["lineage_status"])
            self.assertEqual(
                row["lineage_status_interpretation"],
                auditlib.ROW_STATUS_INTERPRETATIONS[row["lineage_status"]],
            )
            self.assertEqual(
                row["evidence_level"],
                auditlib.INPUT_CANDIDATE_EVIDENCE_LEVEL,
            )
            self.assertEqual(
                row["direct_final_measurement_ancestry"], "NOT_ESTABLISHED"
            )

    def test_candidate_ledger_does_not_claim_direct_ancestry(self) -> None:
        with (self.results / "candidate_file_evidence.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 38)
        self.assertTrue(
            all(
                row["evidence_level"]
                == "FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE"
                and row["direct_final_measurement_ancestry"]
                == "NOT_ESTABLISHED"
                for row in rows
            )
        )

    def test_group_legacy_statuses_have_explicit_interpretations(self) -> None:
        with (self.results / "group_lineage.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 30)
        for row in rows:
            self.assertEqual(
                row["group_lineage_classification_legacy"],
                row["group_lineage_classification"],
            )
            self.assertEqual(
                row["group_lineage_interpretation"],
                auditlib.GROUP_STATUS_INTERPRETATIONS[
                    row["group_lineage_classification"]
                ],
            )
            self.assertEqual(
                row["unique_compatible_candidate_row_count"],
                row["unique_resolved_row_count"],
            )
            self.assertEqual(
                row["direct_final_measurement_ancestry"], "NOT_ESTABLISHED"
            )

    def test_pair_ledger_has_candidate_evidence_boundary(self) -> None:
        with (self.results / "pair_observation_overlap.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 48)
        self.assertTrue(
            all(
                row["evidence_level"]
                == "FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE"
                and row["direct_final_measurement_ancestry"]
                == "NOT_ESTABLISHED"
                for row in rows
            )
        )

    def test_pipeline_anchors_are_configuration_level_only(self) -> None:
        with (self.results / "pipeline_anchor_evidence.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 12)
        self.assertTrue(
            all(
                row["status"] == "PASS"
                and row["evidence_level"] == "CONFIGURATION_LEVEL"
                and row["executed_run_to_final_catalog_lineage"]
                == "NOT_ESTABLISHED"
                for row in rows
            )
        )

    def test_referenced_assets_use_frozen_release_boundary(self) -> None:
        with (self.results / "referenced_asset_availability.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 3)
        self.assertTrue(
            all(
                row["availability_status"]
                == "REFERENCED_NOT_TRACKED_IN_FROZEN_RELEASE"
                and row["original_analysis_asset_existence"]
                == "NOT_DETERMINED"
                for row in rows
            )
        )

    def test_survey_crosswalk_evidence_register(self) -> None:
        correction = json.loads(
            (PROJECT / "provenance" / "CORRECTION_CONFIG.json").read_text()
        )
        with (
            PROJECT / "provenance" / "SURVEY_CROSSWALK_EVIDENCE.tsv"
        ).open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        expected = correction[
            "crosswalk_evidence_classification_by_IDSURVEY"
        ]
        self.assertEqual(len(rows), 8)
        self.assertEqual({row["IDSURVEY"] for row in rows}, set(expected))
        for row in rows:
            self.assertEqual(
                row["evidence_classification"], expected[row["IDSURVEY"]]
            )
            self.assertEqual(row["posthoc_candidate_promoted"], "NO")
            self.assertRegex(row["evidence_excerpt_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            {
                row["IDSURVEY"]
                for row in rows
                if row["evidence_classification"] == "UNRESOLVED_BRIDGE"
            },
            {"51", "57", "65"},
        )

    def test_execution_status_records_both_boundaries(self) -> None:
        result = self.load("EXECUTION_STATUS.json")
        self.assertEqual(
            result["evidence_level"],
            "FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE",
        )
        self.assertEqual(result["direct_final_measurement_ancestry"], "NOT_ESTABLISHED")
        self.assertEqual(
            result["configuration_level_boundary"],
            "CONFIGURATION_LEVEL_SHARED_DEPENDENCY_EVIDENCE_ONLY",
        )
        self.assertEqual(
            result["executed_run_boundary"],
            "NO_EXECUTED_RUN_TO_FINAL_CATALOG_LINEAGE_PROOF",
        )

    def test_summary_preserves_scientific_counts_and_adds_boundaries(self) -> None:
        result = self.load("audit_summary.json")
        self.assertEqual(result["photometry_scan"]["active_file_count"], 847)
        self.assertEqual(result["shared_pipeline"]["anchor_pass_count"], 12)
        self.assertEqual(result["group_lineage"]["resolved_pair_count"], 10)
        self.assertEqual(
            result["group_lineage"][
                "pairs_with_byte_identical_observation_lines"
            ],
            0,
        )
        self.assertEqual(
            result["interpretation"]["direct_final_measurement_ancestry"],
            "NOT_ESTABLISHED",
        )
        self.assertEqual(
            result["survey_crosswalk_evidence"][
                "posthoc_candidate_promoted_count"
            ],
            0,
        )

    def test_all_machine_formats_are_strict_and_rectangular(self) -> None:
        def reject_nonfinite(token: str) -> object:
            raise ValueError(token)

        for path in PROJECT.rglob("*.json"):
            json.loads(
                path.read_text(encoding="utf-8"),
                parse_constant=reject_nonfinite,
            )
        for path in PROJECT.rglob("*.tsv"):
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle, delimiter="\t"))
            self.assertTrue(rows)
            self.assertEqual(len(rows[0]), len(set(rows[0])))
            self.assertTrue(all(len(row) == len(rows[0]) for row in rows))

    def test_reader_documents_contain_required_boundaries(self) -> None:
        for name in ("README.md", "REPORT.md", "REPORT_JA.md"):
            text = (PROJECT / name).read_text(encoding="utf-8")
            self.assertIn(
                "CONFIGURATION_LEVEL_SHARED_DEPENDENCY_EVIDENCE_ONLY", text
            )
            self.assertIn(
                "NO_EXECUTED_RUN_TO_FINAL_CATALOG_LINEAGE_PROOF", text
            )
            self.assertTrue(
                "FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE" in text
                or "凍結クロスウォーク適合入力候補" in text
            )
            self.assertTrue("NOT_ESTABLISHED" in text or "確立していない" in text)

    def test_reader_documents_avoid_prohibited_overclaims(self) -> None:
        names = (
            "README.md",
            "REPORT.md",
            "REPORT_JA.md",
            "REPRODUCIBILITY.md",
            "PACKAGE_VALIDATION.md",
            "DELIVERY_ID.md",
            "CHANGELOG.md",
            "results/README.md",
        )
        text = "\n".join((PROJECT / name).read_text() for name in names)
        for phrase in (
            "preregistered",
            "事前登録済み",
            "REFERENCED_NOT_TRACKED_IN_RELEASE",
            "independent verifier passes",
            "独立検証：",
            "外部独立検証",
        ):
            self.assertNotIn(phrase, text)

    def test_citation_and_ai_disclosure_metadata(self) -> None:
        citation = (PROJECT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertNotIn("date-released:", citation)
        disclosure = (PROJECT / "AI_ASSISTANCE_DISCLOSURE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("ChatGPT", disclosure)
        self.assertIn("Work environment", disclosure)
        self.assertIn("Keiji Yoshimura", disclosure)
        self.assertIn("retains responsibility", disclosure)
        self.assertIn("not an independent external replication", disclosure)

    def test_default_closure_verifier_has_no_write_operation(self) -> None:
        source = (PROJECT / "scripts" / "verify_results.py").read_text()
        self.assertNotRegex(
            source,
            re.compile(r"\.(?:write_text|write_bytes|open)\([^\n]*['\"]w"),
        )
        self.assertNotIn("auditlib.write_json", source)
        recorder = (PROJECT / "scripts" / "record_verification.py").read_text()
        self.assertIn("auditlib.write_json", recorder)


if __name__ == "__main__":
    unittest.main()
