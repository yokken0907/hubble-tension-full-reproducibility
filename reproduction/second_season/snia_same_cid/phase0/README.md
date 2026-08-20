# H0DN SN Ia compression-sufficiency audit

This independent repository tests one bounded question in the frozen public H0
Distance Network baseline: whether its 277-object Pantheon+ Hubble-flow block
can be replaced by one fitted intercept \(a_B\) and one variance without
changing any parameter-dependent information delivered to the network.

The audit reconstructs the full Hubble-flow design and covariance independently,
checks the complete chi-square profile identity, expands the H0DN scalar link
back into 277 correlated equations, and compares all fitted parameters and
their covariance matrices. It also uses a separate blockwise solver and seeded
row/column permutations.

The upstream repository and data are not included. They are acquired separately
and verified against `provenance/SOURCE_LOCK.tsv`.

## Run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/acquire_upstream.py --destination ../H0DN_PHASE0
.venv/bin/python scripts/run_phase0.py --upstream ../H0DN_PHASE0
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/verify_results.py --upstream ../H0DN_PHASE0 \
  --skip-package-integrity
.venv/bin/python scripts/finalize_package.py --write-manifests --check
.venv/bin/python scripts/verify_results.py --upstream ../H0DN_PHASE0
```

See `PHASE0_CONTRACT.md` for the frozen question, equations, tolerances, stop
rules, and non-claims. See `REPRODUCIBILITY.md` for clean-room execution and
output details.

This is not an official H0DN repository. A passing result establishes exact
sufficiency only within the frozen one-intercept, fixed-covariance linear model;
it does not validate that model, produce a corrected \(H_0\), or resolve the
Hubble tension.

## Phase 0 result

Status: `PASS_EXACT_SUFFICIENCY_FOR_FROZEN_LINEAR_MODEL`.

The independent reconstruction found
\(a_B=0.7163834210954622\pm0.0018926416391806\). Across the frozen profile
grid, the maximum full-versus-scalar \(\Delta\chi^2\) residual was
\(3.55\times10^{-13}\). Restoring all 277 correlated Hubble-flow equations
changed no fitted network parameter by more than \(7.82\times10^{-14}\);
the largest tested difference across 16 seeded permutations was
\(3.91\times10^{-12}\).

The scalar link omits a parameter-independent Hubble-flow minimum
\(\chi^2=206.7606364373\) and the individual residual pattern. It is therefore
sufficient for parameter inference in the frozen model, but not for
goodness-of-fit diagnostics or richer physical models.
