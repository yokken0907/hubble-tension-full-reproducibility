#!/usr/bin/env python3
"""Regression tests for the bounded Phase 1C provenance correction."""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile

import numpy as np


PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from auditlib import (  # noqa: E402
    covariance_representations,
    git_blob_sha1_file,
    probability_reference_questions,
    read_source_lock,
    selected_submatrix_asymmetry,
    sha256_file,
    verify_locked_file,
    verify_upstream_audit_dependencies,
)
from verify_results import manifest_target_hashes  # noqa: E402


ADDED_H0DN_PATHS = (
    "h0_constrainer/configs/config.ini",
    "h0_constrainer/h0_constrainer/intercept.py",
    "h0_constrainer/h0_constrainer/main.py",
    "h0_constrainer/h0_constrainer/data_loader.py",
)


class Phase1CCorrectionTests(unittest.TestCase):
    def _assert_lock_mismatch_detected(self, locked_path: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = pathlib.Path(directory) / "fixture.bin"
            candidate.write_bytes(("fixture:" + locked_path).encode("utf-8"))
            row = {
                "path": locked_path,
                "bytes": str(candidate.stat().st_size),
                "sha256": sha256_file(candidate),
                "git_blob_sha1": git_blob_sha1_file(candidate),
            }
            self.assertEqual(
                verify_locked_file(candidate, row)["status"], "PASS"
            )
            candidate.write_bytes(candidate.read_bytes() + b":mutated")
            self.assertEqual(
                verify_locked_file(candidate, row)["status"], "FAIL"
            )

    def test_config_lock_mismatch_detection(self) -> None:
        self._assert_lock_mismatch_detected(ADDED_H0DN_PATHS[0])

    def test_intercept_lock_mismatch_detection(self) -> None:
        self._assert_lock_mismatch_detected(ADDED_H0DN_PATHS[1])

    def test_main_lock_mismatch_detection(self) -> None:
        self._assert_lock_mismatch_detected(ADDED_H0DN_PATHS[2])

    def test_data_loader_lock_mismatch_detection(self) -> None:
        self._assert_lock_mismatch_detected(ADDED_H0DN_PATHS[3])

    def test_added_source_locks_have_expected_git_blobs(self) -> None:
        rows = read_source_lock(PROJECT / "provenance" / "SOURCE_LOCK.tsv")
        selected = {row["path"]: row for row in rows if row["path"] in ADDED_H0DN_PATHS}
        self.assertEqual(set(selected), set(ADDED_H0DN_PATHS))
        self.assertEqual(
            selected[ADDED_H0DN_PATHS[0]]["git_blob_sha1"],
            "d697aa8797e1bdf95ab1c5b587cc71b2f6b95069",
        )
        self.assertEqual(
            selected[ADDED_H0DN_PATHS[1]]["git_blob_sha1"],
            "01d1c08c4a38a7222305a8df3051cdcca807d50f",
        )
        self.assertEqual(
            selected[ADDED_H0DN_PATHS[2]]["git_blob_sha1"],
            "722f58fa5750ac89687dbf35105dabc655abd712",
        )
        self.assertEqual(
            selected[ADDED_H0DN_PATHS[3]]["git_blob_sha1"],
            "31a4314333c75e36ea4909fd118f50d99128e9a6",
        )

    def test_phase1a_archive_sha_mismatch_detection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            provenance = root / "provenance"
            provenance.mkdir()
            archive_names = {
                "phase1a": "phase1a.zip",
                "phase1b": "phase1b.zip",
            }
            archives: dict[str, pathlib.Path] = {}
            actual_hashes: dict[str, str] = {}
            for identifier, name in archive_names.items():
                path = root / name
                with zipfile.ZipFile(path, "w") as handle:
                    handle.writestr("fixture.txt", identifier)
                archives[identifier] = path
                actual_hashes[identifier] = sha256_file(path)
            dependency = {
                "phase1a": {
                    "archive_name": archive_names["phase1a"],
                    "archive_sha256": "0" * 64,
                },
                "phase1b": {
                    "archive_name": archive_names["phase1b"],
                    "archive_sha256": actual_hashes["phase1b"],
                },
            }
            (provenance / "UPSTREAM_AUDIT_DEPENDENCIES.json").write_text(
                json.dumps(dependency), encoding="utf-8"
            )
            for identifier, archive in archives.items():
                expected_hash = dependency[identifier]["archive_sha256"]
                archive.with_name(archive.name + ".sha256").write_text(
                    f"{expected_hash}  {archive.name}\n",
                    encoding="utf-8",
                )
            result = verify_upstream_audit_dependencies(root, archives)
        self.assertEqual(
            result["dependencies"]["phase1a"]["status"], "FAIL"
        )
        self.assertEqual(
            result["dependencies"]["phase1b"]["status"], "PASS"
        )

    def test_selected_submatrix_asymmetry_fixture(self) -> None:
        matrix = np.array(
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
        )
        mapping = [
            {
                "h0dn_row_1based": index + 1,
                "official_row_1based": index + 10,
                "CID": f"SN{index}",
                "IDSURVEY": index + 20,
            }
            for index in range(3)
        ]
        result = selected_submatrix_asymmetry(matrix, mapping)
        self.assertEqual(result["asymmetric_offdiagonal_pair_count"], 3)
        self.assertEqual(result["asymmetric_offdiagonal_element_count"], 6)
        self.assertEqual(
            result["maximum_absolute_offdiagonal_transpose_difference"],
            4.0,
        )
        self.assertEqual(result["maximum_location_status"], "RECORDED")
        self.assertEqual(
            result["maximum_location"]["row_endpoint"][
                "selected_index_0based"
            ],
            0,
        )
        self.assertEqual(
            result["maximum_location"]["column_endpoint"][
                "selected_index_0based"
            ],
            2,
        )

    def test_upper_lower_and_symmetric_representations(self) -> None:
        matrix = np.array(
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
        )
        representations = covariance_representations(matrix)
        np.testing.assert_array_equal(
            representations["SYMMETRIC_AVERAGE"],
            np.array(
                [[1.0, 3.0, 5.0], [3.0, 5.0, 7.0], [5.0, 7.0, 9.0]]
            ),
        )
        np.testing.assert_array_equal(
            representations["UPPER_TRIANGLE_MIRRORED"],
            np.array(
                [[1.0, 2.0, 3.0], [2.0, 5.0, 6.0], [3.0, 6.0, 9.0]]
            ),
        )
        np.testing.assert_array_equal(
            representations["LOWER_TRIANGLE_MIRRORED"],
            np.array(
                [[1.0, 4.0, 7.0], [4.0, 5.0, 8.0], [7.0, 8.0, 9.0]]
            ),
        )

    def test_probability_reference_questions_are_separate(self) -> None:
        result = probability_reference_questions(3.6795245876638087e-06)
        self.assertEqual(
            result["phase1a_conditional_beta_probability"]["value"],
            9.368362232281232e-05,
        )
        self.assertEqual(
            result["phase1a_conditional_beta_probability"]["display_value"],
            9.3683622e-05,
        )
        self.assertEqual(
            result[
                "phase1c_marginal_chi2_39_lower_tail_probability"
            ]["value"],
            3.6795245876638087e-06,
        )
        self.assertNotEqual(
            result["phase1a_conditional_beta_probability"][
                "reference_distribution"
            ],
            result[
                "phase1c_marginal_chi2_39_lower_tail_probability"
            ]["reference_distribution"],
        )

    def test_posthoc_same_mapping_and_basis_recorded(self) -> None:
        result = json.loads(
            (
                PROJECT
                / "results"
                / "printed_vs_high_precision_contrast_diagnostic.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(result["same_mapping_and_basis"])
        self.assertEqual(result["mapping_row_count"], 277)
        self.assertEqual(result["contrast_basis_shape"], [39, 277])

    def test_posthoc_does_not_replace_main_results(self) -> None:
        posthoc = json.loads(
            (
                PROJECT
                / "results"
                / "printed_vs_high_precision_contrast_diagnostic.json"
            ).read_text(encoding="utf-8")
        )
        main = json.loads(
            (
                PROJECT / "results" / "covariance_baselines.json"
            ).read_text(encoding="utf-8")
        )
        for baseline, row in posthoc[
            "ordered_baseline_comparisons"
        ].items():
            self.assertEqual(
                row["printed_h0dn_m_b"]["chi2"], main[baseline]["chi2"]
            )
        self.assertTrue(
            posthoc["main_result_invariance"][
                "protected_artifacts_byte_unchanged"
            ]
        )
        self.assertEqual(
            posthoc["promotion_status"],
            "POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE",
        )

    def test_actual_selected_submatrices_are_symmetric(self) -> None:
        result = json.loads(
            (
                PROJECT
                / "results"
                / "mapped_submatrix_asymmetry_diagnostic.json"
            ).read_text(encoding="utf-8")
        )
        for row in result["sources"].values():
            self.assertEqual(
                row["raw_selected_submatrix"][
                    "asymmetric_offdiagonal_pair_count"
                ],
                0,
            )
            self.assertEqual(
                row["interpretive_statement"],
                "FULL_1701_ASYMMETRY_LIES_OUTSIDE_SELECTED_MAPPING",
            )
            self.assertEqual(
                row["raw_selected_submatrix"]["maximum_location_status"],
                "NOT_APPLICABLE_EXACTLY_SYMMETRIC",
            )

    def test_manifest_target_hash_snapshot_detects_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = pathlib.Path(directory)
            target = project / "target.txt"
            target.write_text("before\n", encoding="utf-8")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            (project / "MANIFEST.tsv").write_text(
                "path\tbytes\tsha256\n"
                f"target.txt\t{target.stat().st_size}\t{digest}\n",
                encoding="utf-8",
            )
            before = manifest_target_hashes(project)
            unchanged = manifest_target_hashes(project)
            target.write_text("after\n", encoding="utf-8")
            after = manifest_target_hashes(project)
        self.assertEqual(before, unchanged)
        self.assertNotEqual(before, after)

    def test_verify_results_module_has_no_write_primitives(self) -> None:
        source = (PROJECT / "scripts" / "verify_results.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(".write_text(", source)
        self.assertNotIn("write_json(", source)
        self.assertNotIn("record-results", source)

    def test_posthoc_json_rejects_nonstandard_constants(self) -> None:
        def reject(value: str) -> None:
            raise ValueError(value)

        for name in (
            "printed_vs_high_precision_contrast_diagnostic.json",
            "mapped_submatrix_asymmetry_diagnostic.json",
        ):
            json.loads(
                (PROJECT / "results" / name).read_text(encoding="utf-8"),
                parse_constant=reject,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
