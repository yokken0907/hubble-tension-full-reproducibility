# Reproducibility Guide

## 1. Reproduction target

The target is the scientific content of the final manuscript and Technical Supplements A and B, not byte-for-byte regeneration of PDF typography.

The repository therefore treats these as reproducible objects:
- numerical values and tolerances;
- table rows and figure-source data;
- dependency/status classifications;
- artifact/version identities;
- explicit HOLD/STOP/re-entry decisions;
- mathematical invariance/sufficiency statements and exact fixtures;
- the public evidence frontier itself when upstream execution/generative provenance is not public.

## 2. Offline suite

Run:

```bash
python tools/verify_repository.py
python tools/run_offline_reproduction.py
python tools/reproduce_manuscript_assets.py
```

The default offline suite performs:
- repository SHA/manifest verification;
- JSON/TSV parse and Python syntax checks;
- the unchanged publication-evidence verifier;
- exact H0DN rational and SN equal-compression fixtures;
- verification of the stored output from the retained clean First-Season 1,000-draw fixed-seed CMB replay;
- deterministic regeneration of manuscript/supplement table and figure-source data.

To rerun the CMB bootstrap itself from the frozen Gaussian moments and fixed seed, use:
```bash
python tools/run_offline_reproduction.py --full-cmb
```
This is scientifically the same retained replay contract but is substantially slower than the default quick verification.

This suite does **not** pretend that stored expected values are independent evidence. Its role is to prove package self-consistency and to reproduce the data-free/fixed-input contracts.

## 3. Public-input suite

The high-information numerical cases require official upstream products.

### H0DN / Pantheon+ SN Ia
Pinned commits and file hashes are in:
`publication_evidence/provenance/SOURCE_REGISTRY.tsv`.

After fetching, use the isolated wrapper:
```bash
python tools/run_external_reproduction.py --external-root external
```

The wrapper copies `publication_evidence/` into a temporary working directory before generating source-derived test vectors or placing GWTC inputs. This is deliberate: **the frozen repository tree is never modified by a reproduction run**. Use `--keep-work` only when you want to inspect the temporary files.

For manual H0DN-only inspection, first copy `publication_evidence/` to a scratch directory and run the embedded scripts there; do not write rebuilt vectors into the frozen repository itself.

Canonical branch implementations are additionally retained under:
- `reproduction/second_season/h0dn_singular_covariance/`
- `reproduction/second_season/snia_same_cid/`

They preserve the historical contracts and alternate code paths used by the project.

### GWTC-4 / GWTC-5 v1
`tools/fetch_public_inputs.py` downloads the two verified Zenodo JSON files under `external/`. The isolated external wrapper then places them into the exact relative paths expected by the frozen GWTC script **inside a temporary copy** and runs `reproduce_gwtc_quantiles.py`.

The six frozen percentiles and printed headline summaries must pass. The 28.547849...% width-reduction value is a diagnostic of that pair and **must not** be relabeled as reproduction of the historical 25.7% metric.

### TDCOSMO
Retrieve the 13 HDF5 chains at the pinned source commit and verify all hashes in:
`publication_evidence/evidence/tdcosmo/SOURCE_MANIFEST_13_CHAINS.tsv`.

Then use:
```bash
python publication_evidence/scripts/reproduce_tdcosmo_outputs.py ...
```

The admitted claim is output-level traceability: 13/13 structures, 39/39 quantiles within tolerance, and 12/12 Table 6 rows at published precision. Original likelihood/sampler/generative reproduction is not claimed.

### First-Season capsules
`reproduction/first_season/capsules/` preserves the public replay capsules for:
- DESI DR2 BAO Gaussian fit;
- fixed-seed CMB amplitude bootstrap;
- HTS59-67 posterior-attribution workflow.

Their own READMEs state input contracts and boundaries. The broad First-Season map also contains branches whose paper-level result is deliberately structural/traceability-only; these are reproduced from frozen ledgers rather than promoted to unclaimed raw-pipeline reruns.

## 4. Claim-by-claim status

Use:
`docs/PAPER_REPRODUCTION_MATRIX.tsv`.

A claim marked `BOUNDED_TRACEABILITY_REPLAY` is not a repository defect. It means the manuscript's scientific conclusion is itself that public evidence does not close a higher layer. Reproduction consists of verifying the source identities, recorded output, missing-object register, and the bounded classification.

## 5. Manuscript assets

`tools/reproduce_manuscript_assets.py` writes machine-readable versions of:
- Main Table 1 and Table 2;
- Figure 1 audit progression and Figure 2 evidence matrix;
- Supplement A Table A1 and Figure A1 source values;
- Supplement B Table B1, Table B2, Figure B1 source values, and Figure B2 lineage-frontier data.

Exact fonts, pagination, and graphic layout are publication formatting, not scientific results.

## 6. No scientific reopening

Running these scripts is a reproduction operation only. It does not reopen the frozen scientific program, change any master, or authorize same-data exploratory extension.
