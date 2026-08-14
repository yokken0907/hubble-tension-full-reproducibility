# Package validation

## Scientific state

- Contract: `H0DN-SNIA-RESIDUAL-PHASE1A-20260730-01`
- Status:
  `AUDIT_COMPLETE_LOW_CHI2_LOCALIZED_TO_DUPLICATE_NAME_CONTRASTS`
- Source: 69/69 frozen H0DN paths PASS
- Known Phase 0 baseline: PASS
- Primary/reference numerical comparison: PASS
- Partition closure and degrees of freedom: PASS
- Exact-name structure: 277 rows, 238 groups, 30 multi-row groups containing
  69 rows, and 39 duplicate-name contrast degrees of freedom
- Fixed-seed permutations: 32/32 PASS
- Analytic-null implementation checks: 3/3 PASS
- Unit tests: 13/13 PASS
- Isolated clean reproduction: semantic equality PASS; serialized-byte
  equality and both SHA-256 values are recorded separately in
  `results/clean_reproduction_summary.json`

## Boundary state

- No upstream H0DN data bytes are redistributed.
- No duplicate row is removed or reweighted.
- No covariance is rescaled, tuned, or replaced.
- No individual name is ranked as anomalous.
- No corrected \(H_0\) or Hubble-tension significance is reported.

## Packaging state

`scripts/finalize_package.py`:

1. enumerates every delivered file except the two generated manifest files;
2. rejects symbolic links and transient build directories;
3. writes `MANIFEST.tsv` and `SHA256SUMS.txt`;
4. verifies both records against the delivered tree;
5. writes a deterministic ZIP with sorted paths and fixed timestamps;
6. writes a sidecar whose filename field exactly matches the ZIP basename.

`python scripts/verify_results.py` is read-only and fails rather than repairing
a manifest mismatch. `--record-results` is restricted to the two closure-time
records and is followed by manifest regeneration.

`results/final_verification_summary.json` is the saved pre-manifest closure
record. The complete package-level check, including `MANIFEST.tsv` and
`SHA256SUMS.txt`, is a read-only live verification printed to stdout or written
outside the package with `--output-dir`.
