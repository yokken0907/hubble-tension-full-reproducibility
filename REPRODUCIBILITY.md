# Reproducibility Guide

## 1. Reproduction target

The target is the scientific content of the associated manuscript and Technical Supplements A and B, not byte-for-byte regeneration of PDF typography or distribution of the publication files themselves.

The repository treats the following as reproducible objects:

- numerical values, tolerances, and fixed-version source identities;
- table rows and figure-source data;
- dependency and evidence-scope classifications;
- algebraic relations between representations;
- preservation or loss of the declared target inference;
- residual and covariance-support diagnostics;
- exact synthetic/rational mathematical fixtures;
- computational provenance to the level supported by public records; and
- explicit limits on generative or causal interpretation.

These objects correspond to the seven evidence dimensions discussed in the manuscript: data-product identity, numerical output traceability, relation between representations, preservation of target inference, diagnostic information retention, computational provenance, and support for generative or causal interpretation.

## 2. Offline suite

Run:

```bash
python tools/verify_repository.py
python tools/run_repository_tests.py
python tools/run_offline_reproduction.py
python tools/reproduce_manuscript_assets.py
```

The default offline suite performs:

- repository SHA-256/manifest verification;
- JSON/TSV parsing and Python syntax checks;
- verification of the fixed publication-evidence archive;
- exact H0DN rational and SN equal-compression fixtures;
- isolated test suites for historical analysis modules that do not require third-party inputs;
- verification of the retained broad-survey 1,000-draw fixed-seed CMB reproduction output;
- claim-evidence hash verification; and
- deterministic regeneration of publication table and figure-source data.

To rerun the CMB bootstrap itself from the fixed Gaussian moments and seed:

```bash
python tools/run_offline_reproduction.py --full-cmb
```

The offline suite checks package self-consistency and the stated fixed-input/data-free contracts. Stored expected values are not treated as independent scientific evidence.

## 3. Public-input suite

High-information numerical cases require official upstream products. Source URLs, commits or records, expected file sizes, and SHA-256 values are listed in `docs/EXTERNAL_SOURCE_REGISTRY.tsv`.

After retrieval:

```bash
python tools/run_external_reproduction.py --external-root external
```

The wrapper uses a temporary working copy so that source-derived vectors or downloaded inputs do not mutate the repository tree.

### H0DN / Pantheon+ SN Ia

The fixed H0DN and Pantheon+ source versions are used to rebuild the source-derived vectors required by the H0DN and same-name residual analyses. Historical implementations are retained under:

- `reproduction/second_season/h0dn_singular_covariance/`
- `reproduction/second_season/snia_same_cid/`

The historical exploratory H0DN variance-component contract is preserved unchanged. Its stronger historical wording about the 72-dimensional covariance null space is explicitly qualified for publication in `reproduction/second_season/h0dn_singular_covariance/PUBLIC_INTERPRETATION_NOTE.md`: the observed released-data null-space projection is localized in the examined host-by-anchor interaction coordinates, but equality of the full subspaces is not claimed without a direct subspace comparison.

The Phase 1F test suite additionally requires the `PANTHEONPLUS_REPO` source tree. It can be included in the isolated test runner with:

```bash
python tools/run_repository_tests.py --pantheonplus-repo /path/to/PantheonPlusSH0ES-DataRelease
```

### GWTC-4 / GWTC-5 v1

`tools/fetch_public_inputs.py` retrieves the two verified Zenodo JSON posterior files. The six fixed percentiles and displayed headline intervals must reproduce. GWTC-5 v1 defines its improvement metric as the relative decrease in average uncertainty computed from the 68% credible interval and describes the comparison with GWTC-4. Applying that definition to the two examined public headline posterior files gives 28.547849...%, not 25.7%. The exact public legacy product or numerical realization that yields the published 25.7% was not identified in the provenance examined here.

### TDCOSMO

Retrieve the 13 HDF5 chains at the registered source version and verify them against `publication_evidence/evidence/tdcosmo/SOURCE_MANIFEST_13_CHAINS.tsv`. The admitted result is output-level traceability: 13/13 structures, 39/39 quantiles within tolerance, and 12/12 Table 6 rows at published precision. Original likelihood, sampler, and generative reconstruction are not claimed.

### Broad-survey reproducibility modules

`reproduction/first_season/capsules/` retains reproducibility modules for DESI DR2 BAO Gaussian fitting, the fixed-seed CMB amplitude bootstrap, and the HTS59-67 posterior-attribution workflow. Their own READMEs define the input contracts and scientific scope.

## 4. Claim-by-claim status

Use `docs/PAPER_REPRODUCTION_MATRIX.tsv`.

A row classified as `BOUNDED_TRACEABILITY_REPLAY` is not a failed reproduction. It means the scientific conclusion is that the public record does not uniquely determine a higher-level provenance or generative reconstruction. Reproduction consists of confirming the source identities, recorded outputs, missing/ambiguous inputs, and the resulting evidence boundary.

## 5. Publication table and figure-source data

`tools/reproduce_manuscript_assets.py` generates machine-readable source data for:

- Main Table 1 and Table 2;
- Main Figure 1 analysis progression and Figure 2 seven-dimension evidence matrix;
- Supplement A Table A1 and Figure A1 source values;
- Supplement B Table B1, Table B2, Figure B1 source values, and Figure B2 provenance-frontier data.

`tools/verify_manuscript_assets.py` compares the regenerated files byte-for-byte against `expected/manuscript_assets/`. Fonts, pagination, and graphic layout are publication formatting rather than scientific results.

## 6. Historical records

Historical source and reproducibility records are intentionally not rewritten to replace old internal terminology or machine-specific paths, because doing so would alter fixed provenance records. The current public interface translates those records into standard scientific language where appropriate. See `docs/HISTORICAL_RECORDS_NOTE.md` and `docs/COMPACT_REPOSITORY_OMISSIONS.tsv`.

## 7. Scope of reruns

Running these scripts reproduces fixed analyses. It does not by itself constitute a new scientific analysis of unchanged evidence, change the fixed source records, or justify stronger causal claims than those stated in the manuscript.
