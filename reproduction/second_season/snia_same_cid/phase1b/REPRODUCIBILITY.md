# Reproducibility

## Environment

The delivered run used Python 3.12.13, NumPy 2.3.5, and Git. Only NumPy is
required at runtime; tests use the standard library.

## Fixed sources

From the project root:

```bash
python scripts/source_tools.py \
  --manifest provenance/SOURCE_LOCK.tsv \
  --acquire-root ../frozen-sources
```

This creates clean fixed checkouts:

- `../frozen-sources/H0DN` at
  `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`;
- `../frozen-sources/PantheonPlusSH0ES_DataRelease` at
  `c447f0fea703fcd0fff57de5000947b5ca81286b`.

The command verifies all nine registered files by commit, Git blob, byte
count, and SHA-256, including the disclosed `SRC-001` correction overlay.
Existing checkouts can be verified without network access:

```bash
python scripts/source_tools.py \
  --manifest provenance/SOURCE_LOCK.tsv \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease
```

## Primary audit

```bash
python scripts/run_audit.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease
```

The runner reads the fields and tolerances once from
`provenance/ACTIVE_MATCHING_CONFIG.json`. It first constructs catalog-only
candidate sets, then applies the official STAT+SYS diagonal only to
catalog-only ambiguities. It also regenerates the 277-row dependency and
error-field diagnostics. It writes neither source checkout.

## Eighteen unit and adversarial tests

```bash
PYTHONDONTWRITEBYTECODE=1 \
python -m unittest discover -s tests -v
```

The 18 tests cover frozen-contract integrity; both parsers; covariance shape
and symmetry behavior; `AMEND-004`; catalog-only unique, ambiguous, and
unmatched cases; covariance-required, still-ambiguous, and unmatched final
cases; exclusion of `m_b_corr_err_DIAG` from matching; permutation
invariance; covariance-diagonal perturbation; dependency-ledger generation;
error-diagnostic recomputation; all survey classes; and exact covariance
pass/fail and mapping-HOLD behavior.

## Independent read-only verifier

```bash
python scripts/verify_results.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease
```

The verifier uses its own table parsing and NumPy `loadtxt` covariance path.
It independently repeats both mapping stages, all group classifications, the
error-field diagnostic, and the exact covariance comparison. Its named gates
are `GATE-P1B-01` through `GATE-P1B-18`; package gates 17 and 18 activate once
the manifests exist. By default it snapshots the project before and after and
fails if any delivered file changes. The replica gate creates two temporary
archives outside the project and compares their bytes.

## Isolated clean reproduction

Choose a path that does not yet exist:

```bash
python scripts/run_clean_reproduction.py \
  --workdir /absolute/path/to/new-cleanroom \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease
```

The script copies only the audit project, regenerates results in isolation,
runs all tests, and records semantic equality separately from byte equality
for these 13 deterministic artifacts:

- `EXECUTION_STATUS.json`
- `audit_summary.json`
- `candidate_evidence.tsv`
- `covariance_diagonal_required_rows.tsv`
- `covariance_lineage.json`
- `error_field_discrepancy_rows.tsv`
- `error_field_discrepancy_summary.json`
- `input_inventory.json`
- `multirow_group_summary.tsv`
- `multirow_row_evidence.tsv`
- `row_mapping.tsv`
- `row_mapping_dependency.tsv`
- `row_mapping_dependency_summary.json`

## Closure and deterministic archives

First record the pre-manifest closure, then write manifests:

```bash
python scripts/verify_results.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease \
  --record-results

python scripts/finalize_package.py --write-manifests
python scripts/finalize_package.py --check
```

Run the final 18-gate read-only verification to an external directory:

```bash
python scripts/verify_results.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease \
  --output-dir ../live-verification

python scripts/finalize_package.py --check
```

Create the primary and replica archives from the same manifested tree:

```bash
python scripts/finalize_package.py \
  --archive ../h0dn-snia-multirow-provenance-audit_v0.1.0.zip

python scripts/finalize_package.py \
  --archive ../h0dn-snia-multirow-provenance-audit_v0.1.0.replica.zip

unzip -t ../h0dn-snia-multirow-provenance-audit_v0.1.0.zip
sha256sum -c \
  ../h0dn-snia-multirow-provenance-audit_v0.1.0.zip.sha256
cmp \
  ../h0dn-snia-multirow-provenance-audit_v0.1.0.zip \
  ../h0dn-snia-multirow-provenance-audit_v0.1.0.replica.zip
```

Sorted paths, fixed timestamps and permissions, and DEFLATE level 9 make the
ZIP deterministic. Its SHA-256 sidecar remains external to avoid
self-reference.

## Expected bounded result

The expected formal status is
`AUDIT_COMPLETE_PROVENANCE_AND_COVARIANCE_LINEAGE_TRACED`, with 275
catalog-only unique rows, 2 covariance-diagonal-required rows, 277 final
one-to-one mappings, and 76,729 exact covariance elements.

The final mapping is a joint catalog-and-covariance lineage result; the
76,729-element comparison is not fully independent of every input used to
disambiguate the two catalog-only ambiguous rows. The package contains no
Phase 1C result.
