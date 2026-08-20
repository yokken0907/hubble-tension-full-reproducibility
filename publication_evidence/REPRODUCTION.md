# Reproduction instructions

Version 1.1 preserves every version-1.0 scientific reproduction path and adds schema-level verification of broad-survey coverage, focused-analysis record identity, cross-analysis contradiction alignment, the seven-dimension evidence matrix, claim-evidence paths, and final-validation records. From the extracted package root run:

```sh
python scripts/verify_package.py
python scripts/verify_synthetic_fixtures.py
```

The first command verifies the manifest, SHA-256 records, authoritative-record identities, all required coverage files, TSV schemas, evidence locators, the version-locked cross-analysis contradiction summary, 24/24 final-validation checks, and the no-third-party-payload boundary. The second re-runs only the already registered data-free exact fixtures and recorded-result consistency checks.

## Existing external-source reproduction paths

Run commands from the extracted package root. Paths below are examples and may be changed, provided the fixed identities are preserved.

## 1. Environment and package integrity

Reference numerical environment for the H0DN/SN validation: Python 3.12.13, NumPy 2.3.5, SciPy 1.17.0, and pandas 3.0.0. The recorded TDCOSMO run used Python 3.13.5, NumPy 2.3.5, h5py 3.15.1, and HDF5 1.14.6.

Create an isolated environment and install the declared Python packages:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r environment/requirements.txt
.venv/bin/python scripts/verify_package.py
.venv/bin/python scripts/verify_synthetic_fixtures.py
```

Expected: both verifiers print `status=PASS` and exit with status 0.

## 2. H0DN network and fixed-model supernova calculations

Retrieve the official repository and fix the audited commit:

```sh
git clone https://github.com/StefCas789/H0DN.git external/H0DN
git -C external/H0DN checkout cc0a4b9f36e65470d514f254a3c5cffa463fbd94
```

Confirm the files against `provenance/SOURCE_REGISTRY.tsv`, then build local test vectors. The generated NPZ files remain local and are not part of this archive.

```sh
.venv/bin/python scripts/rebuild_test_vectors_from_h0dn.py \
  --upstream external/H0DN \
  --output-root test_vectors

.venv/bin/python scripts/run_internal_validations.py \
  --root . \
  --verify-recorded
```

Expected: 24 checks pass. Principal toleranced comparisons include H0 = 73.49875364360662, the off-support projected-loss transformation delta = -0.052445422611000936, supernova intercept = 0.7163834210954622, standard error = 0.0018926416391806472, and omitted residual chi-square = 206.7606364373241.

The network-matrix capture imports the unchanged version-locked H0DN workflow. The validation solvers and SN parser are alternate implementations developed within this study, not external replication.

## 3. Same-name contrast and Pantheon+ covariance variants

Retrieve Pantheon+ and fix the audited commit:

```sh
git clone https://github.com/PantheonPlusSH0ES/DataRelease.git external/PantheonPlus
git -C external/PantheonPlus checkout c447f0fea703fcd0fff57de5000947b5ca81286b

.venv/bin/python scripts/independent_verify_same_cid.py \
  --h0dn external/H0DN \
  --pantheonplus external/PantheonPlus
```

The script checks 277 identifier mappings, the selected 277 × 277 STAT+SYS covariance block, a 39-dimensional same-name contrast, the full/no-row-velocity/STATONLY variants, and the recorded sensitivity classification. Expected overall status: PASS. The row crosswalk contains identifiers and indices only; no source photometry or covariance values are bundled.

## 4. GWTC-4 and GWTC-5 v1 posterior summaries

Obtain the following files from the official Zenodo records and place them exactly as shown:

| Record | File | Local placement | SHA-256 |
|---|---|---|---|
| 10.5281/zenodo.16919645 | `H0_dark_combined.json` | `INPUTS/GWTC4/H0_dark_combined.json` | `b4b5e271d94f0ac828c840a46d72bd5e9433d706a47f352abfcdd3fbc2014fc8` |
| 10.5281/zenodo.20378418 | `H0_dark_combined_gw170817.json` | `INPUTS/GWTC5/H0_dark_combined_gw170817.json` | `00aaee9573ae940ac156c1b4af441e075a462a4c54152ac20d03511b877ce0d5` |

Run:

```sh
.venv/bin/python scripts/reproduce_gwtc_quantiles.py
```

The script writes current results at package root. Expected result: all six Hyndman–Fan type 7 percentiles match the secondary implementation and both one-decimal headline summaries are recovered. GWTC-5 v1 defines its improvement as the relative decrease in average uncertainty computed from the 68% credible interval and describes the comparison with GWTC-4. Applying that definition to the two examined public headline posterior files gives 28.5478491605%; the exact public legacy product or numerical realization yielding the published 25.7% was not identified in the provenance examined here.

## 5. TDCOSMO output-level audit

Retrieve the 13 HDF5 chains from `https://github.com/TDCOSMO/TDCOSMO2025_public` at commit `d7f38db341f68be1df0d9ac1fc528c45113f94cf`. Verify each filename, byte size, and SHA-256 against `evidence/tdcosmo/SOURCE_MANIFEST_13_CHAINS.tsv`.

Prepare a work directory:

```sh
mkdir -p tdcosmo_work/INPUTS tdcosmo_output
cp evidence/tdcosmo/SOURCE_MANIFEST_13_CHAINS.tsv tdcosmo_work/SOURCE_MANIFEST.tsv
# Copy the 13 verified HDF5 files into tdcosmo_work/INPUTS/.
.venv/bin/python scripts/reproduce_tdcosmo_outputs.py \
  --package-root tdcosmo_work \
  --output-parent tdcosmo_output
```

Compare the generated structure and quantile tables with `evidence/tdcosmo/`. The bounded recorded result is 13/13 structures and 39/39 quantiles within the pre-specified numerical tolerance recorded before the 13-file extension, with 12/12 Table 6 rows at published precision. This wording does not imply registration with an external preregistration service. This is output-level traceability, not reproduction of the original likelihood, sampler, convergence assessment, blinding process, or astrophysical generative model.

## 6. Clean-extraction check

After downloading the ZIP, test its CRC, extract into a new empty directory, run `scripts/verify_package.py`, and then run the exact fixtures. No command requires network access after the reader has retrieved the external products described above.
