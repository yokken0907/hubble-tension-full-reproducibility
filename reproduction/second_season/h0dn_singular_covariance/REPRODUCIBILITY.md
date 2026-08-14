# Reproducibility guide

## Scope

This package audits the public H0 Distance Network Python pipeline at the exact
Git commit
`cc0a4b9f36e65470d514f254a3c5cffa463fbd94`. It does not redistribute the
upstream repository or data. `provenance/SOURCE_LOCK.tsv` records all 69 tracked
paths, Git blob identifiers, byte counts, and SHA-256 digests.

The delivered analysis has three deliberately separated stages:

1. `AUDIT_CONTRACT.md`: primary reproduction, covariance decomposition,
   stability checks, ablations, and leave-one-block-out runs, pre-specified
   under a project-internal frozen contract.
2. `POSTHOC_DIAGNOSTIC_CONTRACT.md` and
   `POSTHOC_INTERACTION_DECOMPOSITION_CONTRACT.md`: diagnosis and exact
   localization of the unexpected row-standardization failure.
3. `EXPLORATORY_VARIANCE_COMPONENT_CONTRACT.md`: one explicit generative
   variance-component extension motivated by that diagnosis.

## Frozen environment

The result was generated with:

- Python 3.12.13
- NumPy 2.4.2
- SciPy 1.17.0
- pandas 3.0.0
- PyYAML 6.0.3
- Linux x86-64

The four Python dependencies are exact-pinned in `requirements-lock.txt`.
Floating-point values can differ in their final displayed digits across BLAS,
LAPACK, operating-system, or processor builds; the verifier uses tolerances
that are much tighter than the reported scientific precision.

## Clean execution

From the project root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt

.venv/bin/python scripts/acquire_upstream.py --destination ../H0DN_CLEAN

.venv/bin/python scripts/run_audit.py --upstream ../H0DN_CLEAN
.venv/bin/python scripts/run_posthoc_diagnostics.py --upstream ../H0DN_CLEAN
.venv/bin/python scripts/run_exploratory_variance_component.py \
  --upstream ../H0DN_CLEAN

.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/verify_results.py --upstream ../H0DN_CLEAN \
  --skip-package-integrity
.venv/bin/python scripts/finalize_package.py --write-manifests --check
.venv/bin/python scripts/verify_results.py --upstream ../H0DN_CLEAN
```

The acquisition command checks out the frozen commit in detached-HEAD state
and verifies every tracked file. Each analysis runner repeats that verification
before importing or executing upstream code.

For a recorded end-to-end run that starts from a nonexistent workspace,
creates a new audit worktree and virtual environment, obtains a fresh upstream
checkout, empties `results/`, executes every runner and test, and verifies both
the scientific values and package closure:

```bash
python3 scripts/run_clean_reproduction.py \
  --workspace ../h0dn-full-clean-reproduction
```

The delivered `results/full_clean_reproduction.log` and
`results/clean_reproduction_summary.json` record the corresponding run. The
wrapper stops with `HOLD_NUMERICAL_DRIFT` rather than exporting outputs if a
fixed scientific value exceeds its tolerance.

To verify an already generated package without an upstream checkout:

```bash
.venv/bin/python scripts/verify_results.py
```

This verifies internal structure, statuses, counts, closures, frozen numerical
signatures, and the source-lock manifest. Adding `--upstream` also recomputes
all 69 upstream file checks.

## Expected terminal statuses

- Primary: `PASS_WITH_FLAGGED_NUMERICAL_SENSITIVITY`, because the frozen
  row-standardization invariance check fails.
- Post-hoc diagnosis: `PASS`, with diagnosis
  `HOLD_INCONSISTENT_SUPPORT`.
- Exploratory variance component:
  `PASS_WITH_FLAGGED_PROFILE_NUMERICS`, because the intentionally strict full
  profile-grid invariance threshold fails only at the lower bound
  `tau = 1e-5 mag`, more than \(3.56\times10^8\) deviance units above the
  optimum. The fitted optima, intervals, and inference-bearing profile region
  pass their representation checks.
- Unit tests: seven passing tests.
- Delivered-result verifier: all 16 gates `PASS`, including the corrected
  delivery ID, TSV schema,
  authorship/CFF, ablation classification, SN-Ia constraint drop,
  leave-one-out match, report generation, no-upstream-bytes, and root closure.

These flagged statuses are retained evidence, not execution failures.

## Principal output map

| Output | Purpose |
| --- | --- |
| `results/baseline_reproduction.json` | Untouched upstream and independent-solver match |
| `results/covariance_component_inventory.tsv` | Exact additive covariance inventory |
| `results/covariance_component_ablation.tsv` | All component results with separate solver, interpretation, rank/drop, LOO-match, and covariance-model fields |
| `results/audit_summary.json` | PSD-only public ranking plus separately retained constraint-discarding/indefinite diagnostics |
| `results/leave_one_block_out.tsv` | Frozen equation-block removals |
| `results/representation_invariance.tsv` | Standardization and 32 permutation checks |
| `results/solver_cutoff_sensitivity.tsv` | Moore–Penrose cutoff sweep |
| `results/hubble_flow_covariance_audit.json` | Independent Pantheon+ intercept reconstruction |
| `results/posthoc_row_scaling_diagnostic.json` | Nullspace support and congruence diagnosis |
| `results/posthoc_cepheid_interaction_cells.tsv` | All 111 host–anchor interactions |
| `results/exploratory_variance_component_summary.json` | REML, ML, moment, intervals, and checks |
| `results/exploratory_variance_component_profile.tsv` | Full frozen profile grid |
| `results/report_generation.json` | Generator identity and exact REPORT.md hash |
| `results/full_clean_reproduction.log` | Complete isolated rerun command/output log |
| `results/clean_reproduction_summary.json` | Fixed-value comparison from the isolated rerun |
| `results/final_verification_summary.json` | Final named-gate PASS summary |

All JSON is serialized with strict RFC-compatible finite numbers or `null`; no
nonstandard `NaN` or `Infinity` tokens are emitted.

`MANIFEST.tsv` and `SHA256SUMS.txt` cover every delivered tracked file except
the two checksum files themselves. They can be verified with:

```bash
.venv/bin/python scripts/finalize_package.py --check
```

Building the deterministic archive also writes an external checksum:

```bash
.venv/bin/python scripts/finalize_package.py \
  --archive ../h0dn-covariance-influence-audit_v0.1.0.zip
```
