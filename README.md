# Hubble Tension Map — Full Reproducibility Repository

**Repository version:** 1.0.0  
**Manuscript:** *From Numerical Reproduction to Causal-Closure Boundaries: A Layered Audit of Public Hubble-Constant Inference Products*  
**Author:** Keiji Yoshimura, Independent Researcher

## Purpose

This repository is a compact reproduction environment for the scientific content of the manuscript and its two technical supplements. It was assembled from the complete non-cache project archive after closure. It is **not** a dump of the project working directory.

“Complete reproduction” here means that every manuscript/supplement claim is connected to one of four explicit replay classes:

1. **EXACT_REEXECUTION** — a numerical result can be recomputed from pinned public inputs and project-created code.
2. **DETERMINISTIC_EVIDENCE_REPLAY** — a structural, dependency, contradiction, HOLD, or STOP claim can be regenerated from frozen machine-readable ledgers.
3. **EXACT_DATA_FREE_FIXTURE** — a mathematical mechanism is reproduced with exact synthetic/rational fixtures.
4. **BOUNDED_TRACEABILITY_REPLAY** — the manuscript itself claims only output-level or public-frontier traceability because the collaboration's original likelihood, sampler, executed manifest, joint covariance, or generative chain is not publicly closed. The repository reproduces that bounded state; it does not fabricate unavailable upstream lineage.

This definition reproduces the **claims actually made by the paper**. It does not claim to reproduce third-party collaboration pipelines that the paper explicitly says are unavailable or outside scope.

## Quick start

```bash
python tools/verify_repository.py
python tools/run_offline_reproduction.py
python tools/reproduce_manuscript_assets.py
```

The default offline suite checks the repository itself, the Publication Reproducibility / Evidence Supplement, exact fixtures, claim coverage, the stored output of the already-retained clean 1,000-draw fixed-seed CMB replay, and manuscript-asset generation. To rerun that CMB bootstrap itself from the frozen moments, use `python tools/run_offline_reproduction.py --full-cmb`; it is intentionally much slower.

For public-input re-execution:

```bash
python tools/fetch_public_inputs.py --root external
python tools/run_external_reproduction.py --external-root external
```

Network retrieval is deliberately separated from the frozen repository. All downloaded files must satisfy the registered commit/hash contracts before they are used.

## Reading order

- `docs/PAPER_REPRODUCTION_MATRIX.tsv` — one row per manuscript claim.
- `REPRODUCIBILITY.md` — what each replay class means and exact commands.
- `publication_evidence/` — publication-facing claim/evidence archive (v1.1.0), preserved unchanged.
- `evidence/canonical_ledgers/` — compact top-level records from the four frozen authorities; nested master ZIPs are not duplicated.
- `evidence/first_season_publication_baseline/` — machine-readable First-Season traceability products from the prior public repository.
- `reproduction/first_season/` — existing First-Season replay capsules.
- `reproduction/second_season/` — canonical code/contracts for GWTC and H0DN/SN audits, excluding third-party payloads.
- `reproduction/final_validation/` — final validation code and recorded results; large source-derived vectors are rebuilt from pinned H0DN inputs.
- `manuscript/` — exact submitted scientific PDFs used as the reproduction target.

## Deliberate exclusions

The repository does **not** contain:
- the full 860 MB project archive;
- caches, temporary work directories, duplicated historical transport ZIPs, or conversational/work-log material;
- large third-party posterior archives, HDF5 chains, Pantheon+ covariance files, H0DN upstream files, or papers;
- a guessed replacement for any missing official source product.

Those items are either redundant, retrievable from the authoritative public source, or explicitly outside the paper's evidence boundary.

## Scientific boundary

This repository does not create a new H0 estimate, revised tension significance, preferred correction, unique cause, or new-physics claim. HOLD and STOP states remain scientifically active exactly as recorded in the manuscript and frozen masters.

See `SCOPE_AND_NONCLAIMS.md`.
