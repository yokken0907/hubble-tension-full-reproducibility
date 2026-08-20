# Hubble Tension Map — Full Reproducibility Repository

**Repository version:** 1.1  
**Associated manuscript:** *From Numerical Reproduction to the Limits of Causal Attribution: A Layered Audit of Public Hubble-Constant Inference Products*  
**Author:** Keiji Yoshimura, Independent Researcher

## Purpose

This repository is a compact environment for reproducing, verifying, and tracing the scientific results and evidence boundaries reported in the associated manuscript and its two technical supplements. It was assembled from the complete project archive by retaining claim-relevant code, numerical records, source identities, and validation artifacts rather than the full working directory.

The repository does **not** distribute the manuscript or supplement PDFs. Reproducibility is defined at the level of scientific quantities, table and figure source data, mathematical checks, source/version identity, and explicitly bounded provenance claims.

Four reproducibility categories are recorded in `docs/PAPER_REPRODUCTION_MATRIX.tsv`; their machine-readable identifiers are shown in parentheses:

1. **Numerical re-execution with public inputs** (`EXACT_REEXECUTION_WITH_PUBLIC_INPUTS`) — a numerical result can be recomputed from pinned public inputs and code developed within this study.
2. **Deterministic verification from recorded evidence** (`DETERMINISTIC_EVIDENCE_REPLAY`) — a structural, dependency, scope, consistency, or nonclaim statement can be regenerated from version-locked machine-readable records.
3. **Exact data-free mathematical test case** (`EXACT_DATA_FREE_FIXTURE`) — a mathematical mechanism is reproduced with exact synthetic or rational examples.
4. **Bounded public-provenance verification** (`BOUNDED_TRACEABILITY_REPLAY`) — the scientific result is itself that the available public record supports only a bounded level of provenance or source completeness. The repository confirms that evidential boundary without inventing unavailable upstream information.

These categories describe what the repository can establish. They do not imply that unavailable third-party likelihoods, samplers, covariance-generation pipelines, or executed production histories have been reconstructed.

## Quick start

Use an isolated environment. The recorded H0DN/SN numerical reference environment used Python 3.12.13; the retained TDCOSMO output replay was recorded under Python 3.13.5.

```bash
python -m venv .venv
# Linux/macOS:
.venv/bin/python -m pip install -r environment/requirements.txt
.venv/bin/python tools/verify_repository.py
.venv/bin/python tools/run_repository_tests.py
.venv/bin/python tools/run_offline_reproduction.py
.venv/bin/python tools/reproduce_manuscript_assets.py
```

On Windows, use `.venv\Scripts\python` in place of `.venv/bin/python`.

The default offline suite verifies repository integrity, the publication-evidence package, exact fixtures, claim coverage, isolated tests for historical analysis modules that do not require third-party inputs, the retained 1,000-draw fixed-seed CMB reproduction output, and deterministic regeneration of publication table/figure source data.

To rerun the CMB bootstrap itself from the fixed Gaussian moments and seed:

```bash
python tools/run_offline_reproduction.py --full-cmb
```

For public-input re-execution:

```bash
python tools/fetch_public_inputs.py --root external
python tools/run_external_reproduction.py --external-root external
```

Network retrieval is separated from the repository tree. Downloaded inputs must satisfy the commit/hash contracts in `docs/EXTERNAL_SOURCE_REGISTRY.tsv` before use.

## Reading order

- `docs/PAPER_REPRODUCTION_MATRIX.tsv` — claim-by-claim scientific reproduction map.
- `REPRODUCIBILITY.md` — commands, reproducibility categories, and scope.
- `docs/VALIDATION_REPORT.md` — repository-level validation record.
- `publication_evidence/` — current publication-evidence interface with fixed historical evidence records preserved beneath it.
- `evidence/canonical_ledgers/` — selected machine-readable records from four version-locked archival source packages; the directory name is retained for traceability.
- `reproduction/first_season/` — retained broad-survey reproducibility modules; the historical directory name is retained for traceability.
- `reproduction/second_season/` — focused GWTC, H0DN, and supernova analysis code/contracts, excluding third-party payloads.
- `reproduction/final_validation/` — final numerical and logical validation code and recorded results.
- `expected/manuscript_assets/` — expected machine-readable source data for the publication's principal tables and figures.

## Deliberate exclusions

The repository does **not** contain:

- manuscript or supplement PDFs;
- the complete project working archive;
- caches, temporary working directories, or duplicated transport packages;
- large third-party posterior archives, HDF5 chains, Pantheon+ covariance files, H0DN upstream files, or papers;
- a guessed replacement for any unavailable official source product.

Historical records retained for evidence tracing may preserve their original internal status vocabulary, filenames, or execution-path strings. Those historical strings are not requirements for running the current repository; see `docs/HISTORICAL_RECORDS_NOTE.md`.

## Scientific boundary

This repository does not create a new H0 estimate, revised Hubble-tension significance, preferred correction, unique systematic cause, pipeline-failure claim, or new-physics claim. It reproduces the numerical and evidential conclusions within the scope stated in `SCOPE_AND_NONCLAIMS.md`.
