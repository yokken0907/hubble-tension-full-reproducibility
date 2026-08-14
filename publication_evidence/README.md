# Publication Reproducibility / Evidence Supplement

Version 1.1.0, 10 August 2026

This archive is a compact public evidence and reproducibility supplement for the integrated First-Season / Second-Season / Cross-Season / Final-Validation Hubble-constant audit.

It is not the full project archive. It is a minimum-sufficient, public-safe evidence archive extracted for readers of *From Numerical Reproduction to Causal-Closure Boundaries: A Layered Audit of Public Hubble-Constant Inference Products*. The four frozen authoritative project records remain the governing internal scientific records; their exact identities are in `provenance/MASTER_IDENTITIES.tsv`. This archive selects claim-level machine-readable evidence, provenance, bounded recorded results, and verification code. Its modest size reflects removal of duplicates and non-redistribution of large third-party products, not absence of evidence.

No new scientific analysis, H0 estimate, statistical test, causal hypothesis, or claim boundary was added in version 1.1.0. HOLD and STOP states remain in force.

## Evidence path

The intended trace is:

`manuscript claim -> season -> branch/phase -> frozen result -> source/version -> artifact -> SHA-256 -> limitation/nonclaim`

The expanded `evidence/CLAIM_EVIDENCE_CROSSWALK.tsv` is the main entry point.

## Directory map

- `evidence/first_season/`: ten claim-level First-Season branch clusters.
- `evidence/gwtc/`, `evidence/bbc/`, `results/`: retained canonical Second-Season and final records.
- `evidence/tdcosmo/`: retained First-Season TDCOSMO output-level evidence.
- `evidence/second_season/`: formal branch ledgers and byte-identity audit of retained canonical evidence.
- `evidence/cross_season/`: proposition alignment, contradiction ledger, and F0-F6 matrix.
- `evidence/final_validation/`: 24 gates, exact fixtures, mechanism controls, STOP, and re-entry conditions.
- `provenance/`: Master identities, external source registry, and identifier crosswalk.
- `scripts/`: package verification, synthetic fixtures, and existing source-reproduction helpers.

## Start here

1. Read `SCOPE_AND_NONCLAIMS.md` and `THIRD_PARTY_NOTICES.md`.
2. Run `python scripts/verify_package.py`.
3. Run `python scripts/verify_synthetic_fixtures.py`.
4. Use `evidence/CLAIM_EVIDENCE_CROSSWALK.tsv` to locate each manuscript claim.
5. Follow `REPRODUCTION.md` only when reader-retrieved official source products are available.

Third-party posterior archives, HDF5 chains, source tables, covariance matrices, papers, and derived numerical arrays are not redistributed. Project-internal alternate implementations are not external independent replication.
