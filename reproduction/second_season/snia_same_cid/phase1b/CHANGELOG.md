# Changelog

## 0.1.0 — 2026-07-30

This remains the initial, unpublished release version.

- Added a source-locked 277-row H0DN-to-Pantheon+SH0ES provenance audit.
- Preserved the initial contract and `AMEND-001`–`AMEND-003` chronology.
- Added `AMEND-004` with `results_observed=YES` and
  `interpretation_affected=NO`.
- Corrected the reader explanation: the frozen README describes
  `m_b_corr_err_DIAG` as covariance-diagonal-derived, while the printed
  catalog values do not numerically equal the printed STAT+SYS diagonal
  square roots; the cause remains unresolved.
- Split matching into a catalog-only stage and a covariance-assisted stage
  used only for catalog-only ambiguity.
- Recorded 275 catalog-only unique rows and 2
  covariance-diagonal-required rows, with zero final ambiguous or unmatched
  rows.
- Added full dependency ledgers and 277-row error-field discrepancy
  diagnostics.
- Limited covariance interpretation to the observed numerical result: no
  evidence of element loss, transcription change, additional rounding, or
  row-order mismatch.
- Added explicit joint catalog-and-covariance lineage disclosure.
- Expanded tests from 10 to 18 and the independent verifier to named final
  gates `GATE-P1B-01`–`GATE-P1B-18`.
- Preserved the main scientific results: 277/277 final mappings, 30
  cross-survey multi-row groups containing 69 rows, and 76,729/76,729 exact
  covariance elements.
