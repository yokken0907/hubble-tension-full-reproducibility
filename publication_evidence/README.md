# Publication Reproducibility / Evidence Supplement

Version 1.1, 20 August 2026

This archive is a compact public evidence and reproducibility supplement for the four-stage Hubble-constant audit: broad survey, focused analyses, cross-analysis consistency review, and final validation. The directory names retain the project’s historical stage labels for provenance.

It is not the full project archive. It is a compact, publication-focused, public-safe evidence archive extracted for readers of *From Numerical Reproduction to the Limits of Causal Attribution: A Layered Audit of Public Hubble-Constant Inference Products*. The four version-locked project records are the archival provenance sources from which this public supplement was assembled; their exact identities are in `provenance/MASTER_IDENTITIES.tsv`. This archive selects claim-level machine-readable evidence, provenance, bounded recorded results, and verification code. Its modest size reflects removal of duplicates and non-redistribution of large third-party products, not absence of evidence.

No new scientific analysis, H0 estimate, statistical test, causal hypothesis, or claim boundary is introduced by version 1.1. This release normalizes public terminology and clarifies the interpretation of pre-specified numerical tolerances; version-locked historical evidence records and their original status vocabulary are preserved unchanged.

## Evidence path

The intended trace is:

`manuscript claim -> project stage -> analysis module -> version-locked result -> source/version -> artifact -> SHA-256 -> limitation/nonclaim`

The expanded `evidence/CLAIM_EVIDENCE_CROSSWALK.tsv` is the main entry point.

## Directory map

- `evidence/first_season/`: ten claim-level records from the broad-survey stage (historical directory label retained).
- `evidence/gwtc/`, `evidence/bbc/`, `results/`: retained focused-analysis and final records.
- `evidence/tdcosmo/`: retained broad-survey TDCOSMO output-level evidence.
- `evidence/second_season/`: formal focused-analysis ledgers and byte-identity audit records (historical directory label retained).
- `evidence/cross_season/`: cross-analysis proposition alignment, contradiction ledger, and seven-dimension evidence matrix (historical directory label retained).
- `evidence/final_validation/`: 24 final-validation checks, exact fixtures, mechanism controls, and documented conditions that would justify renewed analysis.
- `provenance/`: Master identities, external source registry, and identifier crosswalk.
- `scripts/`: package verification, synthetic fixtures, and existing source-reproduction helpers.

## Start here

1. Read `SCOPE_AND_NONCLAIMS.md` and `THIRD_PARTY_NOTICES.md`.
2. Run `python scripts/verify_package.py`.
3. Run `python scripts/verify_synthetic_fixtures.py`.
4. Use `evidence/CLAIM_EVIDENCE_CROSSWALK.tsv` to locate each manuscript claim.
5. Follow `REPRODUCTION.md` only when reader-retrieved official source products are available.

Third-party posterior archives, HDF5 chains, source tables, covariance matrices, papers, and derived numerical arrays are not redistributed. Alternate implementations developed within this study are not external independent replication.
