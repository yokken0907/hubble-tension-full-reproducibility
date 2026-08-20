# Changelog

## 0.1.0 — pre-publication provenance correction and reassembly

Scientific values unchanged; classification, wording, metadata, verification,
and package closure corrected.

The failed row-standardization check, all flagged numerical statuses, and the
post-hoc/exploratory interpretation boundaries remain intact. No threshold was
relaxed, no failed row was removed, and no result was promoted to a corrected
\(H_0\).

### Changed files

- Authorship and disclosure:
  `CITATION.cff`, `LICENSE`, `README.md`,
  `AI_ASSISTANCE_DISCLOSURE.md`.
- Contract/provenance language:
  `POSTHOC_DIAGNOSTIC_CONTRACT.md`,
  `EXPLORATORY_VARIANCE_COMPONENT_CONTRACT.md`,
  `provenance/CONTRACT_AMENDMENTS.tsv`.
- Scientific reports and reproduction documentation:
  `REPORT.md`, `REPORT_JA.md`, `POSTHOC_REPORT.md`,
  `REPRODUCIBILITY.md`.
- Analysis and package code:
  `scripts/auditlib.py`, `scripts/run_audit.py`,
  `scripts/run_posthoc_diagnostics.py`, `scripts/verify_results.py`,
  `scripts/finalize_package.py`, `scripts/run_clean_reproduction.py`.
- Environment and tests:
  `requirements-lock.txt`, `tests/test_auditlib.py`.
- Regenerated machine-readable results:
  `results/covariance_component_ablation.tsv`,
  `results/audit_summary.json`, `results/run_environment.json`,
  `results/report_generation.json`.
- Clean-run and final verification evidence:
  `results/full_clean_reproduction.log`,
  `results/clean_reproduction_summary.json`,
  `results/final_verification_summary.json`.
- Final package closure:
  `MANIFEST.tsv`, `SHA256SUMS.txt`, the corrected ZIP, and its external
  `.sha256` file.

### Classification correction

The existing component-ablation `status` is retained, while
`solver_status`, `interpretation_status`, covariance rank/drop diagnostics,
zero-variance and zero-precision-row counts, discarded equation indices,
leave-one-block-out matching, and `covariance_model_status` are added.

The public ranking now contains only `PSD_ALGEBRAIC_SENSITIVITY`. Constraint-
discarding and indefinite cases remain machine-readable but are reported
separately. In particular, `sn1a_hubble_flow_link_variance` is classified
`PSEUDOINVERSE_DISCARDED_CONSTRAINT`: its removal lowers covariance rank from
183 to 182, discards equation 248 in the pseudoinverse precision, and matches
the corresponding equation-removal result within the fixed tolerance.

### Distribution verification correction

Package-path discovery now supports both the source Git worktree and a plain
ZIP extraction without `.git`. Runtime-only `.venv` and cache files are
excluded from the extracted-package scan, while every delivered file remains
closed by `MANIFEST.tsv` and `SHA256SUMS.txt`.

### Delivery disambiguation

`CORRECTED_BUILD_MARKER.md` adds the unique delivery ID
`H0DN-AUDIT-0.1.0-CORRECTED-FINAL-20260730-01`. It is absent from the
pre-correction archive and allows a recipient to reject stale same-name copies
without relying on a filename alone. No scientific output was changed.
