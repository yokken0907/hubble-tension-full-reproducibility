# Repository Validation Report

**Repository candidate:** `hubble-tension-full-reproducibility-repository-v1.0.0`  
**Validation date:** 2026-08-14  
**Target:** final Main Manuscript + Technical Supplements A and B

## 1. Source archive intake

The two uploaded split members were concatenated byte-for-byte and the resulting ZIP passed archive CRC testing.

- combined source bytes: `860,552,381`
- combined source SHA-256: `5a667c16dc5847aad83d77b4865d40227bf6fc71c7c0e69405ef11f62451f2a5`
- source files enumerated: `3,117`
- directly readable text/code/ledger files inspected: `2,143`
- unique direct byte identities: `909`
- recursive nested-ZIP text/code/ledger instances inspected: `10,142`
- unique nested text/code byte identities: `6,006`
- unique nested ZIP identities scanned: `418`

Selection was authority- and claim-driven. The full source archive, caches, duplicate transport packages, and large retrievable third-party products were deliberately not copied into this repository.

## 2. Exact manuscript targets

All three final scientific PDFs are retained byte-exactly. Their expected sizes and SHA-256 values are frozen in `MANUSCRIPT_TARGETS.tsv` and independently checked by `tools/verify_repository.py`.

- Main: `c7b54062f9f2d2a27e1555d289b5fc6a558cd56e740c4d7147324c94e1d3c392`
- Supplement A: `c96336d7e599fc14e60c276850449bd7b9bae0e4dc2d762a73aefb91dc9795ec`
- Supplement B: `9f14d43ac393ee80388022ae511aa2468fd1fd58d7d5b986dc739cd431705348`

## 3. Frozen authorities retained by reference and claim-relevant extraction

- First Season Master v1.0.0: `3e6df9f557485de1bb21c54bb129af78943e8e5d08da036e648d251dd952663c`
- Second Season Master v1.0.0: `cc15c96a45865f22fcd13c2ef03c8cccc39af8fa6dcace4a25f229d07e964940`
- Cross-Season Audit v0.1.0: `9719fae4cbfefeca5ec9e8f04f7949f1a1bdb21d784523752a587ecd166e60cf`
- Final Internal Validation / Closure v0.1.0: `db70c27daa85eb1daf907aeedd644c2d0f0cb3a262c121b28431d15c7b95fb2f`

The large/nested master binaries are not duplicated. Claim-relevant ledgers, code, contracts, results, and replay capsules are selected directly into the repository tree.

## 4. Claim coverage

`docs/PAPER_REPRODUCTION_MATRIX.tsv` contains one row for every claim in the publication evidence crosswalk.

- manuscript/supplement claims covered: `33/33`
- claim-evidence SHA-256 replay: `33/33 PASS`
- reproduction classes are explicit: exact re-execution, deterministic evidence replay, exact data-free fixture, or bounded traceability/source-readiness replay.

A bounded replay is intentional when the manuscript itself concludes that a higher evidential layer is not publicly closed. No unavailable collaboration likelihood, sampler, joint covariance, executed manifest, or generative chain is fabricated.

## 5. Offline validation executed during packaging

The following checks passed on the assembled repository candidate:

- root repository integrity verifier: `PASS`
- JSON parse: `201 PASS`
- TSV parse: `409 PASS`
- Python syntax compilation: `173 PASS`
- publication-evidence package verifier: `PASS`
- publication exact/synthetic fixture verification: `26/26 PASS`
- claim-evidence hash replay: `33/33 PASS`
- retained clean First-Season CMB 1,000-draw replay output verification: `PASS`
- manuscript/supplement machine-readable asset regeneration: `10/10 byte-exact PASS`
- exact manuscript target identity: `3/3 PASS`
- embedded HDF5 payload scan: `0` included
- unexpected file above 2 MB: `0`

The canonical 1,000-draw CMB fixed-seed replay code and frozen Gaussian moments are included and can be rerun with `tools/run_offline_reproduction.py --full-cmb`. Packaging validation used the project's retained clean full-replay outputs for the fast verifier rather than repeating the slow bootstrap itself.

## 6. Public-input re-execution contract

Large or third-party upstream inputs are intentionally external. `tools/fetch_public_inputs.py` pins and verifies the official H0DN, Pantheon+, GWTC, and TDCOSMO sources. `tools/run_external_reproduction.py` executes the public-input cases in a disposable copy so that no reproduction run mutates the frozen repository tree.

This external suite was not network-executed during packaging. Its scripts, commit/record identifiers, file sizes, SHA-256 contracts, expected results, and acceptance criteria are all included and syntax-checked.

## 7. Scientific closure

Repository construction is a publication/reproduction operation only. It does not reopen the frozen Hubble-tension program, change an accepted branch result, create a new H0 estimate, revise a tension significance, infer a unique cause, or authorize same-data exploratory extension.

**Packaging verdict: PASS / RELEASE-CANDIDATE REPRODUCIBILITY TREE.**
