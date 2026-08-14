# Reproducibility guide

## Frozen input

The audit targets H0DN commit
`cc0a4b9f36e65470d514f254a3c5cffa463fbd94`. All 69 tracked files are recorded
in `provenance/SOURCE_LOCK.tsv`. Upstream source and data are deliberately not
redistributed.

## Environment

- Python 3.12.13
- NumPy 2.4.2
- SciPy 1.17.0
- pandas 3.0.0
- Linux x86-64

Exact Python dependency versions are in `requirements-lock.txt`.
The two pandas support dependencies resolved during the first clean execution
are also exact-pinned. Amendment `A001` records this post-result reproducibility
hardening; it changed no scientific code, input, grid, tolerance, status rule,
or result.

## Clean execution

The standard commands are shown in `README.md`. A stronger end-to-end wrapper
starts from an empty workspace, copies only the audit source state, creates a
new virtual environment, obtains and verifies a fresh detached upstream
checkout, empties generated results, runs Phase 0 and all tests, and verifies
both scientific values and package closure:

```bash
python3 scripts/run_clean_reproduction.py \
  --workspace ../h0dn-snia-phase0-clean-reproduction
```

The delivered clean-run log and summary are stored under `results/`.

## Output map

| Output | Purpose |
| --- | --- |
| `results/EXECUTION_STATUS.json` | authoritative Phase 0 status and gate summary |
| `results/source_verification.json` | frozen-source check |
| `results/upstream_baseline_reproduction.json` | untouched public baseline and fidelity gate |
| `results/input_inventory.json` | independent input/schema/covariance diagnostics |
| `results/intercept_reconstruction.json` | upstream, Cholesky, and inverse intercept fits |
| `results/compression_identity_grid.tsv` | fixed full/scalar chi-square profile comparison |
| `results/network_embedding_equivalence.json` | scalar, expanded, blockwise, and closure checks |
| `results/permutation_invariance.tsv` | 16 seeded expanded-block permutations |
| `results/phase0_summary.json` | compact scientific result and non-claim |
| `results/run_environment.json` | runtime versions and platform |
| `results/full_clean_reproduction.log` | isolated rerun transcript |
| `results/clean_reproduction_summary.json` | isolated rerun value comparison |
| `results/final_verification_summary.json` | named final-verifier gates |

All JSON output is strict JSON: non-finite values are rejected. `MANIFEST.tsv`
and `SHA256SUMS.txt` cover every delivered file except the checksum files
themselves.

Floating-point implementations can differ in final digits across BLAS/LAPACK
builds. The frozen tolerances are much tighter than any reported scientific
precision and are never changed after observing results.
