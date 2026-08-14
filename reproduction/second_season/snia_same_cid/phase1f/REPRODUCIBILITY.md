# Reproducibility

## Requirements

- Python 3.11 or newer (reference run: CPython 3.12.13)
- Git
- A local Pantheon+SH0ES DataRelease clone containing commit
  `c447f0fea703fcd0fff57de5000947b5ca81286b`

The audit and verification code use only the Python standard library. Raw
upstream files are read through `git show`; they are not copied into this
package.

## Prepare the external source

```bash
git clone https://github.com/PantheonPlusSH0ES/DataRelease.git PantheonPlusSH0ES-DataRelease
git -C PantheonPlusSH0ES-DataRelease checkout --detach c447f0fea703fcd0fff57de5000947b5ca81286b
PPLUS_REPO=/absolute/path/to/PantheonPlusSH0ES-DataRelease
```

The source verifier checks the commit, origin, three principal tree OIDs, 20
tree locks, and 45 exact file/blob/byte/SHA-256 locks. A working tree with the
required Git objects is sufficient; the scripts do not depend on its current
checked-out file contents.

## Re-run the scientific pipeline

From the extracted package root:

```bash
python3 scripts/run_audit.py --pantheonplus "$PPLUS_REPO"
python3 scripts/run_posthoc_negative_control.py --pantheonplus "$PPLUS_REPO"
python3 scripts/independent_verify.py --pantheonplus "$PPLUS_REPO"
python3 scripts/run_tests.py --pantheonplus "$PPLUS_REPO"
python3 scripts/clean_reproduce.py --pantheonplus "$PPLUS_REPO"
python3 scripts/verify_results.py --pantheonplus "$PPLUS_REPO"
python3 scripts/finalize_package.py --check
```

Do not re-freeze either contract when reproducing the delivered analysis. The
included freeze documents are the fixed chronology records. The post-hoc
script verifies that the protected main outputs still match their pre-
diagnostic hashes before it runs.

Expected closure:

- formal audit status:
  `AUDIT_COMPLETE_PUBLIC_INPUT_DEPENDENCY_CLASSIFIED`;
- second implementation: 31/31 checks PASS;
- tests: 50/50 PASS;
- clean reproduction: 20/20 generated outputs byte-identical;
- strict final verifier: all gates PASS;
- manifest verification: PASS.

## Output roles

The primary scientific tables are `input_candidate_map.tsv`,
`row_input_profile.tsv`, `pair_dependency_classification.tsv`,
`observation_match_evidence.tsv`, `filter_calibration_mapping.tsv`,
`series_configuration_lineage.tsv`, `public_asset_availability.tsv`, and
`shared_dependency_ledger.tsv` under `results/`.

The cross-CID files are explicitly post-hoc descriptive diagnostics. They do
not modify `audit_summary.json` or the formal main classification.

`independent_verification.json` records a second code path within this project;
it is not external replication. `clean_reproduction_summary.json` proves byte
identity after deleting and regenerating 20 outputs in a temporary clean copy.

## Delivery integrity

`MANIFEST.tsv` records path, byte count, and SHA-256 for every packaged file
other than the two self-referential checksum files. `SHA256SUMS.txt` expresses
the same records in conventional form. The external `.zip.sha256` sidecar
authenticates the archive itself.

Running `scripts/finalize_package.py --write-manifests` intentionally rewrites
the two tree-integrity files. Ordinary users should run `--check`, which is
read-only.
