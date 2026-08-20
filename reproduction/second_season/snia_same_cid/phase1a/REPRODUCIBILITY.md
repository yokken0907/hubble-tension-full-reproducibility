# Reproducibility

## Frozen source

The required upstream source is:

- repository: `https://github.com/StefCas789/H0DN.git`
- commit: `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`
- tracked paths: 69

`provenance/SOURCE_LOCK.tsv` records every path, Git blob identifier, byte
count, and SHA-256. Upstream bytes are not redistributed.

## Environment

The recorded execution used:

- Python 3.12.13
- NumPy 2.3.5
- SciPy 1.17.0

See `results/run_environment.json` and `requirements-lock.txt`.

## Contract provenance

The statistical contract was hash-frozen inside the project before the
partition output was examined. This is a project-internal freeze, not an
external registry or third-party timestamp. The frozen contract, decision
configuration, freeze record, and source lock remain unchanged.
`provenance/CONTRACT_AMENDMENTS.tsv` records the post-result reader-facing
terminology and output-schema clarification as `AMEND-001`, with
`results_observed=YES` and `interpretation_affected=NO`.

## Clean procedure

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt

python scripts/source_tools.py \
  --destination ../H0DN_FROZEN \
  --manifest provenance/SOURCE_LOCK.tsv

python -m unittest discover -s tests -v
python scripts/run_audit.py --upstream ../H0DN_FROZEN

python scripts/run_clean_reproduction.py \
  --workdir ../H0DN_SNIA_PHASE1A_CLEAN \
  --upstream ../H0DN_FROZEN

python scripts/verify_results.py --record-results
python scripts/finalize_package.py --write-manifests
python scripts/verify_results.py
```

The acquisition step requires network access and Git. All later scientific
calculation is local.

The final command is fully read-only. It captures the unit-test stream in
memory, checks the saved closure records and manifests, prints the live
summary, and does not modify the package. During package assembly only,
`--record-results` updates exactly `results/unit_tests.log` and
`results/final_verification_summary.json`; manifests are generated afterward.
For a persistent live log without touching the package, use
`python scripts/verify_results.py --output-dir /path/outside/the/project`.

## Calculation separation

The primary implementation uses:

- Cholesky whitening;
- SVD rank checks;
- QR orthonormal bases;
- nested Euclidean projections.

The independent reference implementation uses:

- Cholesky precision solves;
- two separate GLS normal systems;
- direct residual quadratic forms.

The implementations share only the parsed frozen inputs and model
transformation. The reference calculation does not reuse the primary QR
projectors.

## Result files

| File | Purpose |
| --- | --- |
| `results/contract_verification.json` | verifies result-before/after boundary hashes |
| `results/source_verification.json` | exact upstream source verification |
| `results/input_inventory.json` | schema; 277/238/30/69/39 canonical identifier counts; covariance diagnostics |
| `results/primary_partition.json` | QR-projection calculation |
| `results/reference_partition.json` | direct-GLS cross-check |
| `results/baseline_reproduction.*` | known Phase 0 baseline gate |
| `results/numerical_crosschecks.*` | solver, closure, and degree checks |
| `results/permutation_invariance.*` | 32 fixed-seed permutations |
| `results/monte_carlo_null_check.*` | analytic-null implementation check |
| `results/statistical_interpretation.json` | frozen decision rule applied to results |
| `results/audit_summary.json` | compact machine-readable conclusion |
| `results/clean_reproduction_summary.json` | semantic equality, byte equality, and both audit-summary hashes |
| `results/final_verification_summary.json` | saved pre-manifest closure record; complete live verification is printed read-only |

## Determinism

The scientific calculation is deterministic. Randomized implementation checks
use seed `20260730`:

- 32 simultaneous row/column permutations;
- 20,000 standard-normal analytic-null draws.

The delivery archive uses a fixed ZIP timestamp and sorted paths.

## Non-reproduction caveat

Reproducing the numbers verifies the frozen calculation. It does not establish
that the public covariance is complete, known without uncertainty, or
physically correct.
