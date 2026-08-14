from __future__ import annotations

import csv
import hashlib
import json
import os
import pathlib
import sys
import unittest
from collections import Counter
from decimal import Decimal


PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from auditlib import (  # noqa: E402
    CONTRACT_FREEZE_SHA256,
    Observation,
    build_candidate_map,
    compare_pairs,
    intervals_overlap,
    load_config,
    map_filters,
    mutual_unique_edges,
    parse_photometry_blob,
    parse_printed_decimal,
    payload_near,
    payload_rounding_compatible,
    profile_candidates,
    relative_difference,
    sha256_bytes,
    verify_contract,
    verify_sources,
)


def rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class Phase1FAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(os.environ["PANTHEONPLUS_REPO"]).resolve()
        cls.config = load_config(PROJECT)
        cls.candidates, cls.inventory = build_candidate_map(PROJECT, cls.config)
        cls.profiles, cls.parsed = profile_candidates(cls.repo, cls.candidates, cls.config)
        cls.filter_rows, cls.filter_lookup = map_filters(cls.repo, cls.profiles, cls.parsed, cls.config)
        cls.pairs, cls.matches = compare_pairs(cls.candidates, cls.parsed, cls.filter_lookup, cls.config)
        cls.summary = json.loads((PROJECT / "results/audit_summary.json").read_text())
        cls.posthoc = json.loads((PROJECT / "results/posthoc_cross_cid_negative_control_summary.json").read_text())

    def test_01_sha256_bytes(self):
        self.assertEqual(sha256_bytes(b"abc"), hashlib.sha256(b"abc").hexdigest())

    def test_02_decimal_plain_value(self):
        self.assertEqual(parse_printed_decimal("17.028").value, Decimal("17.028"))

    def test_03_decimal_plain_half_ulp(self):
        self.assertEqual(parse_printed_decimal("17.028").half_ulp, Decimal("0.0005"))

    def test_04_decimal_trailing_zero_precision(self):
        self.assertEqual(parse_printed_decimal("1.2300").half_ulp, Decimal("0.00005"))

    def test_05_decimal_scientific_precision(self):
        self.assertEqual(parse_printed_decimal("1.20e3").half_ulp, Decimal("5"))

    def test_06_interval_overlap_true(self):
        self.assertTrue(intervals_overlap(parse_printed_decimal("1.2"), parse_printed_decimal("1.20")))

    def test_07_interval_overlap_false(self):
        self.assertFalse(intervals_overlap(parse_printed_decimal("1.2"), parse_printed_decimal("1.4")))

    def test_08_relative_difference_zero(self):
        self.assertEqual(relative_difference(Decimal("2"), Decimal("2")), Decimal(0))

    def test_09_relative_difference_floor(self):
        self.assertEqual(relative_difference(Decimal("0.1"), Decimal("0.2")), Decimal("0.1"))

    def test_10_mutual_unique_simple(self):
        self.assertEqual(mutual_unique_edges([(0, 0), (1, 1)]), [(0, 0), (1, 1)])

    def test_11_mutual_unique_ambiguous(self):
        self.assertEqual(mutual_unique_edges([(0, 0), (0, 1)]), [])

    def test_12_config_contract_identifier(self):
        self.assertEqual(self.config["contract_id"], "H0DN-SNIA-CROSS-SERIES-INPUT-DEPENDENCY-PHASE1F-20260809-01")

    def test_13_contract_freeze_hash_constant(self):
        self.assertEqual(CONTRACT_FREEZE_SHA256, "3b1e1508d366151a0204f52d1d94e1e81e90454b1fb75fa085df3a17b44acd91")

    def test_14_contract_verification(self):
        self.assertEqual(verify_contract(PROJECT)["status"], "PASS")

    def test_15_source_verification(self):
        self.assertEqual(verify_sources(PROJECT, self.repo)["status"], "PASS")

    def test_16_source_lock_count(self):
        self.assertEqual(verify_sources(PROJECT, self.repo)["source_lock_row_count"], 45)

    def test_17_tree_lock_count(self):
        self.assertEqual(verify_sources(PROJECT, self.repo)["tree_lock_row_count"], 20)

    def test_18_candidate_count(self):
        self.assertEqual(len(self.candidates), 69)

    def test_19_group_count(self):
        counts = Counter(row["CID"] for row in self.candidates)
        self.assertEqual(sum(value > 1 for value in counts.values()), 30)

    def test_20_pair_count(self):
        self.assertEqual(len(self.pairs), 48)

    def test_21_phase1d_candidate_count(self):
        self.assertEqual(self.inventory["phase1d_candidate_count"], 38)

    def test_22_phase1e_candidate_count(self):
        self.assertEqual(self.inventory["phase1e_candidate_count"], 31)

    def test_23_distinct_candidate_paths(self):
        self.assertEqual(self.inventory["distinct_candidate_path_count"], 69)

    def test_24_profile_count(self):
        self.assertEqual(len(self.profiles), 69)

    def test_25_total_observation_count(self):
        self.assertEqual(sum(row["observation_count"] for row in self.profiles), 6744)

    def test_26_distinct_profile_blobs(self):
        self.assertEqual(len({row["git_blob_sha1"] for row in self.profiles}), 69)

    def test_27_candidate_series_count(self):
        self.assertEqual(len({row["source_directory"] for row in self.profiles}), 6)

    def test_28_configured_series_count(self):
        self.assertEqual(len(self.config["series"]), 7)

    def test_29_filter_record_count(self):
        self.assertEqual(len(self.filter_rows), 434)

    def test_30_filter_all_mapped(self):
        self.assertEqual({row["mapping_classification"] for row in self.filter_rows}, {"PUBLIC_KCOR_TEXT_AND_TRANSMISSION_ASSET_MAPPED"})

    def test_31_filter_mapped_observation_count(self):
        self.assertEqual(sum(int(row["observation_count_for_token"]) for row in self.filter_rows), 6744)

    def test_32_kcor_input_count(self):
        self.assertEqual(len({row["kcor_input_path"] for row in self.filter_rows}), 5)

    def test_33_transmission_blob_count(self):
        self.assertEqual(len({row["public_transmission_git_blob_sha1"] for row in self.filter_rows}), 50)

    def test_34_no_byte_exact_positive_pair(self):
        self.assertEqual(sum(int(row["byte_exact_observation_row_match_count"]) > 0 for row in self.pairs), 0)

    def test_35_single_payload_pair_count(self):
        self.assertEqual(sum(row["primary_pair_classification"] == "SINGLE_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD" for row in self.pairs), 4)

    def test_36_repeated_payload_pair_count(self):
        self.assertEqual(sum(row["primary_pair_classification"] == "REPEATED_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD" for row in self.pairs), 0)

    def test_37_match_evidence_count(self):
        self.assertEqual(len(self.matches), 4)

    def test_38_only_one_main_match_within_point11_day(self):
        self.assertEqual(sum(row["absolute_mjd_delta_le_0p11_day"] == "YES" for row in self.matches), 1)

    def test_39_no_main_match_same_transmission_blob(self):
        self.assertEqual(sum(row["same_public_transmission_blob"] == "YES" for row in self.matches), 0)

    def test_40_summary_status(self):
        self.assertEqual(self.summary["status"], "AUDIT_COMPLETE_PUBLIC_INPUT_DEPENDENCY_CLASSIFIED")

    def test_41_summary_no_exposure_identity(self):
        self.assertFalse(self.summary["pair_comparison"]["physical_exposure_identity_proven"])

    def test_42_summary_no_execution_lineage(self):
        self.assertFalse(self.summary["configuration_lineage"]["executed_run_to_final_catalog_lineage_proven"])

    def test_43_posthoc_pair_count(self):
        self.assertEqual(self.posthoc["cross_CID_candidate_file_pair_count"], 1523)

    def test_44_posthoc_positive_pair_count(self):
        self.assertEqual(self.posthoc["cross_CID_positive_candidate_file_pair_count"], 24)

    def test_45_posthoc_opportunity_count(self):
        self.assertEqual(self.posthoc["cross_CID_observation_pair_opportunity_count"], 14670999)

    def test_46_posthoc_main_unchanged(self):
        self.assertTrue(self.posthoc["protected_main_results_unchanged_after_diagnostic"])

    def test_47_second_implementation(self):
        value = json.loads((PROJECT / "results/independent_verification.json").read_text())
        self.assertEqual((value["pass_count"], value["check_count"], value["status"]), (31, 31, "PASS"))

    def test_48_candidate_map_has_no_residual_field(self):
        fieldnames = rows(PROJECT / "results/input_candidate_map.tsv")[0].keys()
        self.assertFalse(any("resid" in name.lower() for name in fieldnames))

    def test_49_pair_map_has_no_h0_value_field(self):
        fieldnames = rows(PROJECT / "results/pair_dependency_classification.tsv")[0].keys()
        self.assertFalse(any(name.lower() in {"h0", "m_b_corr", "mu_sh0es"} for name in fieldnames))

    def test_50_parse_minimal_lightcurve(self):
        blob = b"SNID: X\nSURVEY: S\nNOBS: 1\nVARLIST: MJD FLT FLUXCAL FLUXCALERR MAG MAGERR\nOBS: 1.0 g 2.0 0.1 3.0 0.2\n"
        parsed = parse_photometry_blob(blob, ("MJD", "FLT", "FLUXCAL", "FLUXCALERR", "MAG", "MAGERR"))
        self.assertEqual((parsed["SNID"], parsed["NOBS"]), ("X", 1))


if __name__ == "__main__":
    unittest.main()
