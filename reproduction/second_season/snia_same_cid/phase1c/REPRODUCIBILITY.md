# Reproducibility

## Environment

The delivered run used:

- Python 3.12.13
- NumPy 2.3.5
- SciPy 1.17.0
- Git

Install the pinned Python dependencies:

```bash
python -m pip install -r requirements-lock.txt
```

## Acquire and verify fixed sources

```bash
python scripts/source_tools.py --acquire-root ../frozen-sources
```

This checks out and verifies:

- `../frozen-sources/H0DN`
- `../frozen-sources/PantheonPlusSH0ES_DataRelease`

Existing checkouts can be verified without downloading:

```bash
python scripts/source_tools.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease
```

Verification covers repository URL, commit, Git blob, byte count, and SHA-256
for all 13 consumed files. The added H0DN lock entries cover the configuration
and implementation paths that define the selected magnitude and velocity
fields.

## Verify upstream audit archives

Keep the canonical archives and their `.zip.sha256` sidecars together:

- `h0dn-snia-residual-deficit-localization-audit_v0.1.0.zip`
  (Phase 1A, SHA-256
  `38bb6e55c66ec3442e465cfe4367c1b75e5ecb369933df6de71b75c6182e8333`);
- `h0dn-snia-multirow-provenance-audit_v0.1.0.zip`
  (Phase 1B, SHA-256
  `1b099109ac7dca7fd34d5e28b51c299acd87c0626e9c3976a37dd35c5df42959`).

The primary runner checks each exact filename, archive SHA-256, sidecar
contents, and ZIP CRC. The archives are dependencies and are not redistributed
inside this package.

## Primary audit

```bash
python scripts/run_audit.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease \
  --phase1a-archive /absolute/path/to/h0dn-snia-residual-deficit-localization-audit_v0.1.0.zip \
  --phase1b-archive /absolute/path/to/h0dn-snia-multirow-provenance-audit_v0.1.0.zip
```

The primary implementation uses:

- the compact Phase 1B mapping after rechecking it against both source tables;
- a deterministic groupwise Helmert basis;
- explicitly averaged official covariance matrices after recording their
  raw transpose differences;
- Cholesky triangular solves for quadratic forms;
- an eigendecomposition reference calculation;
- a second null-space basis and 32 fixed-seed orthogonal transformations.

No upstream source file is modified.

## Frozen post-hoc diagnostics

The post-hoc contract and sidecar must verify before execution:

```bash
sha256sum -c \
  POSTHOC_PRECISION_AND_ASYMMETRY_DIAGNOSTIC_CONTRACT.sha256

python scripts/run_posthoc_precision_asymmetry.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease
```

This separate runner reuses the frozen 277-row mapping and one in-memory
Helmert basis for the printed `m_b` and official `m_b_corr` vectors. It also
measures raw selected-submatrix asymmetry before applying any representation
rule. It writes only the four named post-hoc artifacts and verifies that the
protected main result files are byte unchanged.

## Independent recalculation

```bash
python scripts/independent_verify.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease
```

This script does not import `auditlib`. It uses a separate ASCII covariance
reader, constructs the null space of the exact-name incidence matrix, and
computes all five quadratic forms by symmetric eigendecomposition. It then
checks the classification against the primary report.

## Thirty-three unit and adversarial tests

```bash
PYTHONDONTWRITEBYTECODE=1 \
python -m unittest discover -s tests -v
```

The tests cover contract integrity, Helmert identities, cross-survey gating,
covariance schema and failure paths, both quadratic solvers, all
classification branches, probability labels, scale intervals, matrix and
component diagnostics, generalized eigenvalue identity, alternative-basis
and orthogonal invariance, finite JSON enforcement, deterministic JSON, and
source-lock schema. Added adversarial cases cover each of the four H0DN
implementation locks, Phase 1A archive SHA mismatch, same mapping/basis use,
post-hoc main-result immutability, selected-submatrix asymmetry, all three
upper/lower/symmetric representations, probability-field separation, and
read-only verification.

## Clean-copy reproduction

After producing the primary results:

```bash
python scripts/run_clean_reproduction.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease \
  --phase1a-archive /absolute/path/to/h0dn-snia-residual-deficit-localization-audit_v0.1.0.zip \
  --phase1b-archive /absolute/path/to/h0dn-snia-multirow-provenance-audit_v0.1.0.zip
```

The script creates a temporary package copy, removes its results, runs the
main and post-hoc calculations there, and compares 22 artifacts byte for byte.
The delivered summary is `results/clean_reproduction_summary.json`.

## Read-only live verification and explicit recording

`verify_results.py` never writes a result or manifest target:

```bash
python scripts/verify_results.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease \
  --phase1a-archive /absolute/path/to/h0dn-snia-residual-deficit-localization-audit_v0.1.0.zip \
  --phase1b-archive /absolute/path/to/h0dn-snia-multirow-provenance-audit_v0.1.0.zip
```

Only the explicitly mutating wrapper records its output:

```bash
python scripts/record_verification.py \
  --h0dn /absolute/path/to/H0DN \
  --pantheonplus /absolute/path/to/PantheonPlusSH0ES_DataRelease \
  --phase1a-archive /absolute/path/to/h0dn-snia-residual-deficit-localization-audit_v0.1.0.zip \
  --phase1b-archive /absolute/path/to/h0dn-snia-multirow-provenance-audit_v0.1.0.zip
```

## Manifests and deterministic archive

After all reports and verification outputs exist:

```bash
python scripts/finalize_package.py --write-manifests
python scripts/finalize_package.py --check

python scripts/finalize_package.py \
  --archive ../h0dn-snia-contrast-covariance-calibration-audit_v0.1.0.zip
```

The archive builder sorts paths and fixes timestamps, permissions, compression
method, and compression level. Verify the external sidecar and ZIP CRC:

```bash
sha256sum -c \
  ../h0dn-snia-contrast-covariance-calibration-audit_v0.1.0.zip.sha256

unzip -t \
  ../h0dn-snia-contrast-covariance-calibration-audit_v0.1.0.zip
```

To verify deterministic packaging, create a second archive from the unchanged
manifested tree and compare it byte for byte.

## Expected bounded result

The expected status is
`AUDIT_COMPLETE_CONTRAST_COVARIANCE_CALIBRATION_DIAGNOSTIC`, with
classification `LOW_FLAG_PERSISTS_THROUGH_STATONLY`.

This expected result is stated for reproduction, not as an unfrozen decision
rule. The decision rule and chronology are fixed in `AUDIT_CONTRACT.md` and
`provenance/CONTRACT_FREEZE.json`.
