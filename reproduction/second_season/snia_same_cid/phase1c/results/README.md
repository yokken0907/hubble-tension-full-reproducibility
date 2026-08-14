# Result artifacts

The machine-readable result set contains:

- `audit_summary.json` — bounded status, classification, and three ordered
  baseline results;
- `quadratic_forms.tsv` — all three ordered and two diagonal-only diagnostics;
- `covariance_baselines.json` — probabilities, scale diagnostics, matrix
  diagnostics, and reference-solver comparisons;
- `component_diagnostics.json` — projected component and generalized
  eigenvalue summaries;
- `covariance_lineage.json` — 76,729-element STAT+SYS/H0DN equality check;
- `contrast_definition.tsv` — deterministic non-outcome Helmert basis ledger;
- `dependency_mapping_verification.json` — compact Phase 1B mapping checks;
- `upstream_audit_dependency_verification.json` — canonical Phase 1A and
  Phase 1B ZIP filename, SHA-256, sidecar, and CRC checks;
- `input_inventory.json` — dimensions, group counts, and raw symmetry
  diagnostics;
- `known_phase1a_reproduction.json` — known-value gate;
- `alternative_basis_checks.json` — null-space basis recalculation;
- `orthogonal_invariance.tsv` and summary — 32 coordinate trials across five
  baselines;
- `numerical_crosschecks.json` — 27 frozen numerical gates;
- `independent_verification.json` — separately implemented five-baseline
  recalculation;
- `printed_vs_high_precision_contrast_diagnostic.json` and `.tsv` — frozen
  post-hoc comparison of H0DN `m_b` and mapped official `m_b_corr` using the
  same mapping, basis, and three main covariance baselines;
- `mapped_submatrix_asymmetry_diagnostic.json` — raw mapped STAT+SYS and
  STATONLY off-diagonal asymmetry counts and locations;
- `mapped_submatrix_asymmetry_sensitivity.tsv` — frozen symmetric-average,
  upper-mirrored, and lower-mirrored results when selected asymmetry triggers
  that branch; the delivered file is header-only because both selected
  277-by-277 submatrices are exactly symmetric;
- `unit_tests.log` — 33 unit and adversarial tests;
- `clean_reproduction.log` and summary — clean-copy byte comparison;
- `contract_verification.json`, `source_verification.json`,
  `run_environment.json`, and `EXECUTION_STATUS.json` — execution trace;
- `final_verification_summary.json` — package closure gates.

No per-object chi-square, residual ranking, survey ranking, corrected
covariance, corrected Hubble constant, or Hubble-tension result is present.
The four supplemental files are explicitly post-hoc and do not replace any
main status, probability, vector, or classification.
