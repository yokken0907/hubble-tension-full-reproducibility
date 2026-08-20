#!/usr/bin/env python3
"""Unit and regression tests for Phase 1E."""

from __future__ import annotations

import copy
import csv
import json
import pathlib
import sys
import tempfile
import unittest


PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

import auditlib  # noqa: E402


class AuditLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = auditlib.load_config(PROJECT)

    def test_01_sha256_known(self) -> None:
        self.assertEqual(
            auditlib.sha256_bytes(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_02_normalize_repository(self) -> None:
        self.assertEqual(
            auditlib.normalize_repository("HTTPS://GITHUB.COM/X/Y.git/"),
            "https://github.com/x/y",
        )

    def test_03_normalize_survey(self) -> None:
        self.assertEqual(auditlib.normalize_survey("  A   B\tC "), "A B C")

    def test_04_active_list_comments(self) -> None:
        names, counts = auditlib.active_list_entries(b"# x\n a.dat \n\n## b.dat\nc.dat\n")
        self.assertEqual(names, ["a.dat", "c.dat"])
        self.assertEqual(counts["a.dat"], 1)

    def test_05_active_list_duplicate_count(self) -> None:
        _names, counts = auditlib.active_list_entries(b"a\na\n")
        self.assertEqual(counts["a"], 2)

    def test_06_parse_valid_without_nobs(self) -> None:
        row = auditlib.parse_photometry_blob(b"SNID: X\nSURVEY: TEST\nOBS: 1\n")
        self.assertEqual(row["status"], "PASS")
        self.assertIsNone(row["NOBS"])

    def test_07_parse_valid_with_nobs(self) -> None:
        row = auditlib.parse_photometry_blob(b"SNID: X\nSURVEY: TEST\nNOBS: 2\nOBS: 1\nOBS: 2\n")
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["observation_line_count"], 2)

    def test_08_parse_nobs_mismatch(self) -> None:
        row = auditlib.parse_photometry_blob(b"SNID: X\nSURVEY: TEST\nNOBS: 2\nOBS: 1\n")
        self.assertEqual(row["status"], "FAIL")

    def test_09_parse_duplicate_snid(self) -> None:
        row = auditlib.parse_photometry_blob(b"SNID: X\nSNID: X\nSURVEY: TEST\nOBS: 1\n")
        self.assertEqual(row["status"], "FAIL")

    def test_10_parse_duplicate_survey(self) -> None:
        row = auditlib.parse_photometry_blob(b"SNID: X\nSURVEY: A\nSURVEY: B\nOBS: 1\n")
        self.assertEqual(row["status"], "FAIL")

    def test_11_write_read_tsv_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "x.tsv"
            auditlib.write_tsv(path, [{"a": "1", "b": "2"}], ("a", "b"))
            self.assertEqual(auditlib.read_tsv(path, ("a", "b")), [{"a": "1", "b": "2"}])

    def test_12_official_labels_smart_quotes(self) -> None:
        labels, summary = auditlib.parse_official_labels(
            "51:’LOSS1’, 57:'LOSS2', 65:’CFA4p2’".encode(),
            {"51": "LOSS1", "57": "LOSS2", "65": "CFA4p2"},
        )
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(labels["65"], "CFA4p2")

    def test_13_label_header_mismatch(self) -> None:
        rows = auditlib.label_header_diagnostic(
            [{"IDSURVEY": "65", "official_label": "CFA4p2", "inferred_SURVEY_headers": "X(CFA4p1)"}],
            self.config,
        )
        self.assertEqual(rows[0]["diagnostic_classification"], "PUBLIC_LABEL_RAW_HEADER_CFA_TOKEN_MISMATCH")

    def test_14_label_header_consistent(self) -> None:
        rows = auditlib.label_header_diagnostic(
            [{"IDSURVEY": "65", "official_label": "CFA4p2", "inferred_SURVEY_headers": "X(CFA4p2)"}],
            self.config,
        )
        self.assertEqual(rows[0]["diagnostic_classification"], "PUBLIC_LABEL_RAW_HEADER_CFA_TOKEN_CONSISTENT")

    @staticmethod
    def synthetic_files(directory: str, survey: str, count: int = 5) -> list[dict[str, object]]:
        return [
            {
                "status": "PASS",
                "SNID": f"X{i}",
                "SURVEY": survey,
                "source_directory": directory,
                "path": f"p/{i}",
                "git_blob_sha1": f"oid{i}",
                "bytes": i + 1,
                "sha256": f"sha{i}",
                "NOBS": 1,
                "observation_line_count": 1,
            }
            for i in range(count)
        ]

    @staticmethod
    def synthetic_catalog(count: int = 5) -> list[dict[str, str]]:
        return [
            {
                "catalog_row_1based": str(i + 1),
                "CID": f"X{i}",
                "IDSURVEY": "51",
                "USED_IN_SH0ES_HF": "1" if i < 3 else "0",
            }
            for i in range(count)
        ]

    def test_15_inference_supported(self) -> None:
        _holdout, anchors, crosswalks = auditlib.infer_crosswalks(
            self.synthetic_catalog(), set(), self.synthetic_files("D", "S"), {"51": "LOSS1", "57": "LOSS2", "65": "CFA4p2"}, self._one_code_config()
        )
        self.assertEqual(len(anchors), 5)
        self.assertEqual(crosswalks[0]["support_status"], self.config["classification"]["supported"])

    def test_16_inference_insufficient(self) -> None:
        _holdout, _anchors, crosswalks = auditlib.infer_crosswalks(
            self.synthetic_catalog(4), set(), self.synthetic_files("D", "S", 4), {"51": "LOSS1", "57": "LOSS2", "65": "CFA4p2"}, self._one_code_config()
        )
        self.assertEqual(crosswalks[0]["support_status"], self.config["classification"]["insufficient"])

    def test_17_inference_conflicting(self) -> None:
        files = self.synthetic_files("D1", "S", 5)
        files[-1]["source_directory"] = "D2"
        _holdout, _anchors, crosswalks = auditlib.infer_crosswalks(
            self.synthetic_catalog(), set(), files, {"51": "LOSS1", "57": "LOSS2", "65": "CFA4p2"}, self._one_code_config()
        )
        self.assertEqual(crosswalks[0]["support_status"], self.config["classification"]["conflicting"])

    def test_18_excluded_CID_never_anchor(self) -> None:
        _holdout, anchors, _crosswalks = auditlib.infer_crosswalks(
            self.synthetic_catalog(), {"X0"}, self.synthetic_files("D", "S"), {"51": "LOSS1", "57": "LOSS2", "65": "CFA4p2"}, self._one_code_config()
        )
        self.assertNotIn("X0", {row["CID"] for row in anchors})

    def test_19_apply_unique(self) -> None:
        target = [{"h0dn_row_1based": "1", "official_row_1based": "2", "CID": "X0", "IDSURVEY": "51", "lineage_status": "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE"}]
        crosswalk = [{"IDSURVEY": "51", "inferred_source_directory": "D", "inferred_SURVEY_headers": "S", "support_status": self.config["classification"]["supported"]}]
        rows, evidence = auditlib.apply_crosswalks(target, self.synthetic_files("D", "S"), crosswalk, self.config)
        self.assertEqual(rows[0]["candidate_count"], 1)
        self.assertEqual(len(evidence), 1)

    def test_20_apply_wrong_directory_unresolved(self) -> None:
        target = [{"h0dn_row_1based": "1", "official_row_1based": "2", "CID": "X0", "IDSURVEY": "51", "lineage_status": "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE"}]
        crosswalk = [{"IDSURVEY": "51", "inferred_source_directory": "OTHER", "inferred_SURVEY_headers": "S", "support_status": self.config["classification"]["supported"]}]
        rows, evidence = auditlib.apply_crosswalks(target, self.synthetic_files("D", "S"), crosswalk, self.config)
        self.assertEqual(rows[0]["candidate_count"], 0)
        self.assertEqual(evidence, [])

    def test_21_contract_freeze_passes(self) -> None:
        self.assertEqual(auditlib.verify_contract(PROJECT)["status"], "PASS")

    def test_22_phase_population_passes(self) -> None:
        excluded, targets, summary = auditlib.phase_populations(PROJECT, self.config)
        self.assertEqual(len(excluded), 30)
        self.assertEqual(len(targets), 31)
        self.assertEqual(summary["status"], "PASS")

    def test_23_frozen_directory_universe_exact(self) -> None:
        configured = tuple(item["directory"] for item in self.config["directory_inventory"])
        self.assertEqual(configured, auditlib.FROZEN_CROSSWALK_DIRECTORIES)

    def test_24_audit_summary_universe_exact(self) -> None:
        summary = json.loads((PROJECT / "results/audit_summary.json").read_text(encoding="utf-8"))
        universe = summary["crosswalk_universe"]
        self.assertEqual(universe["configured_directory_count"], 7)
        self.assertEqual(tuple(universe["directories"]), auditlib.FROZEN_CROSSWALK_DIRECTORIES)
        self.assertEqual(universe["uniqueness_scope"], "WITHIN_FROZEN_SEVEN_DIRECTORY_UNIVERSE_ONLY")

    def test_25_broader_uniqueness_claims_false(self) -> None:
        summary = json.loads((PROJECT / "results/audit_summary.json").read_text(encoding="utf-8"))
        universe = summary["crosswalk_universe"]
        self.assertIs(universe["full_public_photometry_tree_uniqueness_claim"], False)
        self.assertIs(universe["external_archive_uniqueness_claim"], False)

    def test_26_status_semantics_preferred_candidate_label(self) -> None:
        semantics = json.loads((PROJECT / "results/status_semantics.json").read_text(encoding="utf-8"))
        self.assertEqual(
            semantics["UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK"]["preferred_label"],
            "UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_PUBLIC_INPUT_CANDIDATE",
        )

    def test_27_status_semantics_disclaims_ancestry(self) -> None:
        semantics = json.loads((PROJECT / "results/status_semantics.json").read_text(encoding="utf-8"))
        boundaries = semantics["UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK"]["does_not_establish"]
        self.assertIn("direct ancestry to the final m_b_corr row", boundaries)
        self.assertIn("executed-run-to-final-catalog lineage", boundaries)
        self.assertIn("statistical independence", boundaries)

    def test_28_interpretive_scope_false_boundaries(self) -> None:
        summary = json.loads((PROJECT / "results/audit_summary.json").read_text(encoding="utf-8"))
        scope = summary["interpretive_scope"]
        for field in (
            "direct_final_measurement_ancestry_proven",
            "fit_output_lineage_proven",
            "bias_correction_run_lineage_proven",
            "executed_run_to_final_catalog_lineage_proven",
            "statistical_independence_proven",
        ):
            self.assertIs(scope[field], False)

    def test_29_original_frozen_record_hashes_unchanged(self) -> None:
        record = json.loads(
            (PROJECT / "provenance/UPSTREAM_DEPENDENCY_SUPERSESSION.json").read_text(encoding="utf-8")
        )
        for relative, expected in record["phase1e_original_frozen_records_sha256"].items():
            self.assertEqual(auditlib.sha256_file(PROJECT / relative), expected)

    @staticmethod
    def _read_tsv(path: pathlib.Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            return tuple(reader.fieldnames or ()), list(reader)

    def test_30_corrected_phase1d_preserves_original_columns(self) -> None:
        old_fields, old_rows = self._read_tsv(PROJECT / "provenance/PHASE1D_ROW_LINEAGE.tsv")
        _new_fields, new_rows = self._read_tsv(
            PROJECT / "provenance/PHASE1D_ACCEPTED_CORRECTED_ROW_LINEAGE.tsv"
        )
        self.assertEqual(len(old_rows), 69)
        self.assertEqual(len(new_rows), 69)
        self.assertEqual(
            [[row[field] for field in old_fields] for row in old_rows],
            [[row[field] for field in old_fields] for row in new_rows],
        )

    def test_31_target_driving_31_rows_identical(self) -> None:
        _old_fields, old_rows = self._read_tsv(PROJECT / "provenance/PHASE1D_ROW_LINEAGE.tsv")
        _new_fields, new_rows = self._read_tsv(
            PROJECT / "provenance/PHASE1D_ACCEPTED_CORRECTED_ROW_LINEAGE.tsv"
        )
        selected = ("h0dn_row_1based", "official_row_1based", "CID", "IDSURVEY", "lineage_status")
        old_targets = [tuple(row[field] for field in selected) for row in old_rows if row["lineage_status"] == "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE"]
        new_targets = [tuple(row[field] for field in selected) for row in new_rows if row["lineage_status"] == "NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE"]
        self.assertEqual(len(old_targets), 31)
        self.assertEqual(old_targets, new_targets)

    def test_32_supersession_is_nonretroactive_and_pass(self) -> None:
        record = json.loads(
            (PROJECT / "provenance/UPSTREAM_DEPENDENCY_SUPERSESSION.json").read_text(encoding="utf-8")
        )
        self.assertEqual(record["record_type"], "POSTRESULT_ACCEPTED_UPSTREAM_SUPERSESSION")
        self.assertIs(record["created_after_phase1e_results"], True)
        self.assertIs(record["prospective_freeze_claim"], False)
        self.assertIs(record["phase1e_scientific_results_changed"], False)
        self.assertEqual(record["status"], "PASS")

    def test_33_protected_primary_result_hashes_unchanged(self) -> None:
        record = json.loads(
            (PROJECT / "provenance/UPSTREAM_DEPENDENCY_SUPERSESSION.json").read_text(encoding="utf-8")
        )
        for relative, expected in record["phase1e_protected_primary_results_sha256"].items():
            self.assertEqual(auditlib.sha256_file(PROJECT / relative), expected)

    def test_34_scientific_counts_unchanged(self) -> None:
        summary = json.loads((PROJECT / "results/audit_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["target_excluded_inference"]["eligible_row_count"], 74)
        self.assertEqual(summary["target_excluded_inference"]["anchor_row_count"], 62)
        self.assertEqual(summary["target_excluded_inference"]["crosswalk_count"], 3)
        self.assertEqual(summary["target_application"]["target_row_count"], 31)
        self.assertEqual(summary["target_application"]["unique_target_row_count"], 31)
        self.assertEqual(summary["photometry_scan"]["active_file_count"], 847)
        self.assertEqual(summary["photometry_scan"]["parse_failure_count"], 0)

    def test_35_code65_remains_descriptive_metadata_tension(self) -> None:
        _fields, rows = self._read_tsv(PROJECT / "results/label_header_diagnostic.tsv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["diagnostic_classification"], "PUBLIC_LABEL_RAW_HEADER_CFA_TOKEN_MISMATCH")
        self.assertEqual(rows[0]["interpretive_boundary"], "DESCRIPTIVE_METADATA_TENSION_ONLY_NO_SOURCE_RELABELING")

    def test_36_reader_documents_state_bounded_candidate_scope(self) -> None:
        english = [
            (PROJECT / "README.md").read_text(encoding="utf-8"),
            (PROJECT / "REPORT.md").read_text(encoding="utf-8"),
            (PROJECT / "results/README.md").read_text(encoding="utf-8"),
        ]
        required = (
            "The uniqueness and crosswalk classifications hold within the prospectively "
            "frozen seven-directory public-photometry audit universe."
        )
        self.assertTrue(all(required in text for text in english))
        japanese = (PROJECT / "REPORT_JA.md").read_text(encoding="utf-8")
        self.assertIn("結果閲覧前に固定した7つの公開測光ディレクトリ", japanese)
        self.assertIn("最終m_b_corr行への直接祖先は未証明", japanese)

    def _one_code_config(self) -> dict[str, object]:
        config = copy.deepcopy(self.config)
        config["target"]["IDSURVEY_codes"] = [51]
        return config


if __name__ == "__main__":
    unittest.main()
