# Package validation

The package closes only when scientific results, interpretation boundaries,
second-implementation cross-checks, and archive integrity all pass.

## Scientific and interpretation gates

- The original contract, freeze record, source locks, decision configuration,
  and Phase 1B map retain their frozen bytes. The amendment register is
  append-only and contains exactly `AMEND-001`, with both
  `new_results_observed = YES` and `interpretation_affected = YES`.
- The formal status, release classification, and main counts remain unchanged:
  30 groups, 69 rows, 38 unique legacy candidates, 31 unresolved legacy rows,
  3 fully candidate-covered groups, 10/48 evaluable pairs, 0/10 pairs with a
  byte-identical observation line, 847 files, 12/12 configuration anchors,
  and three referenced assets.
- Every row, candidate, group, and pair record states the compatible-input
  evidence level and `direct_final_measurement_ancestry = NOT_ESTABLISHED`.
- Shared-pipeline evidence is limited by
  `CONFIGURATION_LEVEL_SHARED_DEPENDENCY_EVIDENCE_ONLY` and
  `NO_EXECUTED_RUN_TO_FINAL_CATALOG_LINEAGE_PROOF`.
- All eight survey codes have a crosswalk-evidence record. Codes 51, 57, and
  65 remain `UNRESOLVED_BRIDGE`; no post-hoc candidate is promoted.
- The three asset results use
  `REFERENCED_NOT_TRACKED_IN_FROZEN_RELEASE` and do not claim that the assets
  were absent from the original analysis.

## Cross-check and containment gates

- The main second-implementation cross-check passes 15/15 checks.
- The post-hoc second-implementation cross-check passes 9/9 checks.
- Both records explicitly state that they are not an independent external
  replication, peer review, or expert endorsement.
- All 31 unresolved main rows and 73 CID-only candidate records recompute.
- Five protected main files are byte-identical before and after the diagnostic,
  and promotion remains `POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE`.

## Repository and reproduction gates

- All unit and locked-result regression tests in `results/unit_tests.log` pass.
- An isolated copy regenerates 19 result files byte-for-byte.
- JSON is strict and finite; TSV is UTF-8, rectangular, and has unique headers.
- Reader documents contain the corrected evidence boundaries and avoid the
  superseded overclaims.
- Every Python source parses successfully.
- No symlink, scratch-workspace absolute path, upstream source tree,
  covariance file, or FITRES file is redistributed.

`scripts/verify_results.py` performs these checks read-only and proves that its
default invocation leaves the package tree byte-identical. The intentional
writer `scripts/record_verification.py` records the passing result in
`results/final_verification_summary.json` before manifests are frozen. Passing
closure is `ACCEPT_COMPLETE_WITH_SCOPE`; any failed gate produces
`HOLD_VERIFICATION_FAILURE`.

## Manifest and archive gates

`scripts/finalize_package.py` requires passing recorded closure before it can
write or verify manifests or build an archive.

`MANIFEST.tsv` and `SHA256SUMS.txt` cover every delivered file except the two
manifest files themselves. `scripts/verify_delivery.py` then checks manifest
equality, ZIP CRC, checksum sidecar, byte identity to a separately generated
replica, one expected archive root, and absence of upstream source data.

The delivery-verification record is stored beside, not inside, the immutable
archive. The final ZIP is also unpacked into a new directory and checked using
only the archive contents.
