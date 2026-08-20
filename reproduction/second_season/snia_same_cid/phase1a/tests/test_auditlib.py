#!/usr/bin/env python3
"""Unit tests for the frozen Phase 1A audit routines."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest

import numpy as np


PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from auditlib import (  # noqa: E402
    build_group_design,
    load_config,
    load_contract_amendments,
    primary_partition,
    reference_partition,
    statistical_interpretation,
    verify_contract_freeze,
)
from package_tools import verify_manifests, write_manifests  # noqa: E402
from run_clean_reproduction import compare_audit_summaries  # noqa: E402
from verify_results import (  # noqa: E402
    tracked_tree_snapshot,
    verify,
    write_record_results,
)


class GroupDesignTests(unittest.TestCase):
    def test_exact_string_grouping(self) -> None:
        names = ("SN-A", "SN-A", "sn-a", "SN-B", "SN-B", "SN-C")
        groups = build_group_design(names)
        self.assertEqual(groups["object_count"], 6)
        self.assertEqual(groups["unique_exact_name_count"], 4)
        self.assertEqual(groups["multi_row_exact_name_group_count"], 2)
        self.assertEqual(groups["rows_in_multi_row_exact_name_groups"], 4)
        self.assertEqual(groups["duplicate_name_excess_row_count"], 2)
        self.assertEqual(groups["duplicate_name_contrast_df"], 2)
        self.assertEqual(groups["legacy_duplicate_name_row_count"], 2)
        self.assertIn("not all rows", groups["legacy_field_note"])
        self.assertEqual(groups["multiplicity_histogram"], {"1": 2, "2": 2})
        np.testing.assert_allclose(np.sum(groups["design"], axis=1), 1.0)
        self.assertNotEqual(
            np.argmax(groups["design"][0]), np.argmax(groups["design"][2])
        )


class NestedGlSTests(unittest.TestCase):
    def setUp(self) -> None:
        rng = np.random.default_rng(91231)
        n = 6
        raw = rng.normal(size=(n, n))
        self.covariance = raw @ raw.T + np.eye(n) * 0.7
        self.data = rng.normal(size=n)
        self.names = ("A", "A", "B", "C", "C", "D")
        self.design = build_group_design(self.names)["design"]

    def test_partition_closure_and_degrees_of_freedom(self) -> None:
        result = primary_partition(
            self.data, self.covariance, self.design
        )
        self.assertEqual(result["df_total"], 5)
        self.assertEqual(result["df_duplicate_name_contrasts"], 2)
        self.assertEqual(result["df_between_name_modes"], 3)
        self.assertLess(abs(result["partition_closure_residual"]), 1e-11)

    def test_reference_solver_agreement(self) -> None:
        primary = primary_partition(
            self.data, self.covariance, self.design
        )
        reference = reference_partition(
            self.data, self.covariance, self.design
        )
        for quantity in (
            "chi2_total",
            "chi2_duplicate_name_contrasts",
            "chi2_between_name_modes",
        ):
            self.assertAlmostEqual(primary[quantity], reference[quantity], places=11)

    def test_simultaneous_permutation_invariance(self) -> None:
        primary = primary_partition(
            self.data, self.covariance, self.design
        )
        permutation = np.asarray([5, 3, 1, 4, 0, 2])
        names = tuple(np.asarray(self.names, dtype=object)[permutation].tolist())
        permuted = primary_partition(
            self.data[permutation],
            self.covariance[np.ix_(permutation, permutation)],
            build_group_design(names)["design"],
        )
        for quantity in (
            "chi2_total",
            "chi2_duplicate_name_contrasts",
            "chi2_between_name_modes",
        ):
            self.assertAlmostEqual(primary[quantity], permuted[quantity], places=11)


class DecisionRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT)

    def result(self, total: float, duplicate: float) -> dict[str, float]:
        return {
            "chi2_total": total,
            "chi2_duplicate_name_contrasts": duplicate,
            "chi2_between_name_modes": total - duplicate,
        }

    def test_duplicate_localized_label(self) -> None:
        result = statistical_interpretation(
            self.result(100.0, 0.1), self.config
        )
        self.assertEqual(
            result["status"],
            self.config["status_labels"]["duplicate_localized"],
        )

    def test_between_localized_label(self) -> None:
        result = statistical_interpretation(
            self.result(100.0, 30.0), self.config
        )
        self.assertEqual(
            result["status"],
            self.config["status_labels"]["between_localized"],
        )

    def test_proportional_label(self) -> None:
        total = 206.0
        duplicate = total * 39.0 / 276.0
        result = statistical_interpretation(
            self.result(total, duplicate), self.config
        )
        self.assertEqual(
            result["status"],
            self.config["status_labels"]["proportional"],
        )


class ContractTests(unittest.TestCase):
    def test_contract_freeze_hashes(self) -> None:
        result = verify_contract_freeze(PROJECT)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["partition_results_observed_before_freeze"])
        amendment_check = next(
            row
            for row in result["checks"]
            if row["path"] == "provenance/CONTRACT_AMENDMENTS.tsv"
        )
        self.assertEqual(
            amendment_check["verification_scope"],
            "frozen_header_plus_append_only_ledger",
        )

    def test_contract_amendment_schema_and_disclosure(self) -> None:
        rows = load_contract_amendments(PROJECT)
        amendment = next(
            row for row in rows if row["amendment_id"] == "AMEND-001"
        )
        self.assertEqual(amendment["results_observed"], "YES")
        self.assertEqual(amendment["interpretation_affected"], "NO")


class ReproducibilityInterfaceTests(unittest.TestCase):
    def test_default_verifier_is_read_only(self) -> None:
        before = tracked_tree_snapshot(PROJECT)
        synthetic_tests = subprocess.CompletedProcess(
            args=["unittest"], returncode=0, stdout="", stderr=""
        )
        synthetic_log = (
            "test_record_result_writer_changes_only_authorized_files\n"
            "Ran 13 tests\n\nOK\n"
        )
        verify(
            PROJECT,
            tests=synthetic_tests,
            test_log=synthetic_log,
            include_manifest=False,
            validate_saved_records=False,
        )
        after = tracked_tree_snapshot(PROJECT)
        self.assertEqual(before, after)

    def test_record_result_writer_changes_only_authorized_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = pathlib.Path(temporary)
            results = project / "results"
            results.mkdir()
            unrelated = results / "unrelated.json"
            unrelated.write_text('{"fixed": true}\n', encoding="utf-8")
            before = {
                path.relative_to(project).as_posix(): path.read_bytes()
                for path in project.rglob("*")
                if path.is_file()
            }
            write_record_results(
                project,
                "closure test log\n",
                {"status": "PASS", "verification_scope": "test"},
            )
            after = {
                path.relative_to(project).as_posix(): path.read_bytes()
                for path in project.rglob("*")
                if path.is_file()
            }
            changed = {
                name
                for name in set(before) | set(after)
                if before.get(name) != after.get(name)
            }
            self.assertEqual(
                changed,
                {
                    "results/unit_tests.log",
                    "results/final_verification_summary.json",
                },
            )
            self.assertEqual(
                unrelated.read_text(encoding="utf-8"),
                '{"fixed": true}\n',
            )

    def test_manifest_mismatch_is_detected_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = pathlib.Path(temporary)
            payload = project / "payload.txt"
            payload.write_text("frozen\n", encoding="utf-8")
            write_manifests(project)
            manifest_before = (project / "MANIFEST.tsv").read_bytes()
            sums_before = (project / "SHA256SUMS.txt").read_bytes()
            payload.write_text("tampered\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                verify_manifests(project)
            self.assertEqual(
                (project / "MANIFEST.tsv").read_bytes(), manifest_before
            )
            self.assertEqual(
                (project / "SHA256SUMS.txt").read_bytes(), sums_before
            )

    def test_clean_reproduction_separates_semantic_and_byte_equality(
        self,
    ) -> None:
        original = b'{"a": 1, "status": "PASS"}\n'
        reproduced = b'{\n  "status": "PASS",\n  "a": 1\n}\n'
        comparison = compare_audit_summaries(original, reproduced)
        self.assertTrue(
            comparison["audit_summary_semantically_identical"]
        )
        self.assertFalse(comparison["audit_summary_bytes_identical"])
        self.assertEqual(comparison["status"], "PASS")
        self.assertNotEqual(
            comparison["original_audit_summary_sha256"],
            comparison["reproduced_audit_summary_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
