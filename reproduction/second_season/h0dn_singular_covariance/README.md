# Independent H0DN covariance-block influence audit

This is not an official H0DN product and is not affiliated with or endorsed by
the H0DN authors.

This is a separate, reproducible audit of the public H0 Distance Network
(H0DN) Python baseline. Keiji Yoshimura is the human author and accountable
maintainer. It does not modify or supersede the completed
`hubble-constant-inference-traceability` project. See the
[AI Assistance Disclosure](AI_ASSISTANCE_DISCLOSURE.md) for the role and
limits of AI assistance.

The audit reproduces the public baseline, reconstructs every encoded covariance
component, tests pseudoinverse and representation stability, performs
covariance-component ablations pre-specified under a project-internal frozen
contract and leave-one-block-out runs, and audits the Pantheon+ Hubble-flow
covariance before its compression to one network equation.

The upstream H0DN repository is intentionally not bundled because no
repository-level license was present at the frozen commit. The runner accepts a
separate checkout and verifies its commit and file hashes.

## Delivered result

The untouched public result is reproduced at
`H0 = 73.49875364 +/- 0.80880003 km/s/Mpc`. The primary audit then finds that
the singular-covariance Moore–Penrose solution is stable to the frozen cutoff
sweep and to 32 row/column permutations, but not to exact non-orthogonal row
standardization.

The post-hoc diagnosis localizes the entire 72-dimensional covariance-nullspace
support inconsistency to the interaction subspace of the complete 37 host × 3
anchor R22 HST-Cepheid table. A separately contracted exploratory
variance-component model removes the zero modes and is representation-invariant
at its fitted optimum, while changing the conditional H0 by only
`-0.00442767 km/s/Mpc`. None of these diagnostics is a corrected H0 or a causal
identification of a physical systematic.

## Quick start

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

The primary scientific boundary and all pre-specified blocks are in
[`AUDIT_CONTRACT.md`](AUDIT_CONTRACT.md). Every later analysis has its own
contract documenting that it is post-hoc. Generated machine-readable outputs
are written under `results/`.

## Reports

- `REPORT.md`: primary report generated under the project-internal frozen
  contract.
- `POSTHOC_REPORT.md`: diagnosis and exact localization of the failed
  row-scaling check.
- `EXPLORATORY_REPORT.md`: explicit Cepheid interaction-variance model.
- `REPORT_JA.md`: integrated Japanese-language interpretation.
- `REPRODUCIBILITY.md`: source, environment, execution, and verification
  details.
- `MANIFEST.tsv` and `SHA256SUMS.txt`: byte-level integrity of delivered files.

## Interpretation boundary

Block removal measures dependence of this encoded computational network on a
chosen block. It does not identify a physical systematic, assign causality, or
supply a corrected estimate of the Hubble constant. Many blocks overlap through
shared hosts and parameters, so their shifts are not additive.
