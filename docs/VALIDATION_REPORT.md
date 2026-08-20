# Repository Validation Report

**Repository:** `hubble-tension-full-reproducibility-repository-v1.1`  
**Validation date:** 2026-08-20  
**Target:** scientific results, evidence boundaries, and publication table/figure source data associated with the main manuscript and Technical Supplements A and B

## 1. Release purpose

Repository v1.1 refines the public reproducibility layer while leaving the underlying scientific results and version-locked archival source records unchanged. The repository is complete without manuscript or supplement PDFs; publication files are not part of the repository integrity contract.

The release also aligns current public-facing language with the manuscript's seven evidence dimensions and preserves historical evidence records without rewriting their original provenance vocabulary.

## 2. Source archive and archival records

The original source archive identity remains:

- combined source bytes: `860,552,381`
- combined source SHA-256: `5a667c16dc5847aad83d77b4865d40227bf6fc71c7c0e69405ef11f62451f2a5`

The four version-locked archival source identities remain unchanged:

- First Season Master v1.0.0: `3e6df9f557485de1bb21c54bb129af78943e8e5d08da036e648d251dd952663c`
- Second Season Master v1.0.0: `cc15c96a45865f22fcd13c2ef03c8cccc39af8fa6dcace4a25f229d07e964940`
- Cross-Season Audit v0.1.0: `9719fae4cbfefeca5ec9e8f04f7949f1a1bdb21d784523752a587ecd166e60cf`
- Final Internal Validation / Closure v0.1.0: `db70c27daa85eb1daf907aeedd644c2d0f0cb3a262c121b28431d15c7b95fb2f`

Repository construction does not modify those historical archival packages.

## 3. Current repository integrity

The v1.1 root verifier passed after the repository was exercised by pytest, demonstrating that runtime-generated caches do not invalidate the integrity contract.

- repository verifier: `PASS`
- repository version contract: `1.1`
- publication PDFs in repository: `0`
- JSON parse: `201 PASS`
- TSV parse: `409 PASS`
- Python syntax compilation: `175 PASS`
- claim matrix coverage: `33/33`
- allowed reproduction-class vocabulary: `PASS`
- root manifest/checksum verification: `PASS`
- redistributed HDF5 payloads: `0`
- unexpected files above 2 MB: `0`

The root `MANIFEST.tsv` and `SHA256SUMS.txt` are the integrity records for the current compact tree. Runtime products such as `.pytest_cache`, `__pycache__`, `.pyc`, and `.pyo` are explicitly excluded from the repository member set.

## 4. Publication-evidence archive

The v1.1 publication-evidence verifier passed after public-facing metadata and terminology were updated while version-locked historical evidence records remained intact:

- checksums: `115 PASS`
- manifest rows: `115 PASS`
- first-analysis cases: `10`
- second-analysis fixed records: `24`
- true contradictions after claim/source/version alignment: `0`
- evidence-matrix cases: `13`
- claim/evidence rows: `33`
- final numerical checks: `24`
- verifier failures: `0`

Claim-evidence hash verification independently returned:

- `33/33 PASS`

## 5. Exact mathematical and numerical fixtures

The synthetic fixture verifier returned `26/26 PASS`.

Among the exact results recovered:

- off-support rational fixture: `1/2 -> 1/5` under the specified non-orthogonal scaling;
- on-support quadratic fixture: `9 -> 9` under the corresponding support-preserving statement;
- equal-compression supernova fixture residual χ² values: `2` and `8`.

These fixtures demonstrate the stated mathematical mechanisms and do not enlarge their scientific interpretation.

## 6. Isolated software tests for historical analysis modules

Historical analysis modules contain repeated local module names such as `auditlib.py`; collecting all historical test files in a single Python import namespace causes avoidable import collisions. v1.1 provides `tools/run_repository_tests.py`, which executes each historical-module suite in an isolated process without altering historical code.

The offline suites not requiring third-party source trees passed:

- H0DN singular-covariance tests: `7/7 PASS`
- SN Phase 0 tests: `8/8 PASS`
- same-name Phase 1A tests: `13/13 PASS`
- Phase 1B tests: `18/18 PASS`
- Phase 1C tests: `33/33 PASS`
- Phase 1D tests: `41/41 PASS`
- Phase 1E tests: `36/36 PASS`
- total isolated tests without external inputs: `156/156 PASS`

The root `pytest` configuration now tests only the current public interface and passed `3/3`; historical phase suites are intentionally delegated to the isolated runner.

The documented isolated-environment installation now includes `pytest==9.0.2` in both root and publication-evidence requirements, so the advertised test commands are installable from the declared package list.

Phase 1F requires an external Pantheon+ DataRelease checkout through `PANTHEONPLUS_REPO` and is therefore not part of the no-external-input test total. The isolated runner can include it when that source tree is supplied.

## 7. CMB fixed-input reproduction

The retained fixed-seed CMB calculation was rerun from the stored Gaussian moments rather than only checking the previously retained output.

- bootstrap draws: `1000`
- fixed seed: `10199`
- model rows: `5`
- amplitude rows: `10`
- test rows: `3`
- output verification: `E001_VERIFY=PASS`

This is a fixed-input reproduction contract beginning from stored Gaussian moments; it is not a reconstruction of an upstream collaboration likelihood.

## 8. Publication table and figure-source regeneration

`tools/reproduce_manuscript_assets.py` was updated to use the current public scientific terminology and seven-dimension evidence labels. Regeneration and byte-exact comparison against `expected/manuscript_assets/` passed:

- generated source files: `10/10 PASS`
- Main Table 1 source: `PASS`
- Main Table 2 source: `PASS`
- Main Figure 1 source: `PASS`
- Main Figure 2 seven-dimension matrix: `PASS`
- Supplement A table/figure sources: `2/2 PASS`
- Supplement B table/figure sources: `4/4 PASS`

The regenerated Supplement B residual-localization source records the between-name component as `195.55132137372135`, exactly equal (to the displayed source precision) to `206.7606364373241 - 11.209315063602752`; this is the value used by manuscript v1.0.4.

The generated Figure 2 translates historical status codes into the publication-facing terms `SUPPORTED`, `PARTIAL`, `UNRESOLVED`, `NOT_PRESERVED`, and `NOT_EVALUATED` without modifying the historical source matrix.

The repository-level claim map also records the statistical limitation that the same-name residual tail probabilities are diagnostic calibrations for the specified statistic rather than multiplicity-adjusted confirmatory discovery probabilities, because a complete prospective search history over all candidate diagnostic subspaces is not established by the retained evidence.

The current publication-source schema uses `diagnostic_information_retention`; the obsolete public label `diagnostic_sufficiency` is retained only in version-locked historical machine-readable records. The H0DN exploratory variance-component contract is likewise preserved as a historical pre-execution record, while `PUBLIC_INTERPRETATION_NOTE.md` explicitly limits the publication-level conclusion to the demonstrated localization of the observed null-space projection and does not claim equality of the full 72-dimensional subspaces.

## 9. Historical checksum references and compact-tree omissions

Retained historical records can name files that belonged to larger source packages or transport archives but were deliberately not selected into the compact GitHub tree. Rather than editing those historical checksum files, v1.1 records such unresolved-in-current-tree references in:

`docs/COMPACT_REPOSITORY_OMISSIONS.tsv`

- documented historical checksum/sidecar references not included in the compact tree: `631`

This table is explanatory only. Current-tree integrity is determined by the root `MANIFEST.tsv` and `SHA256SUMS.txt`.

## 10. Public-input re-execution boundary

Large or third-party upstream inputs remain external. The repository pins H0DN, Pantheon+, GWTC, and TDCOSMO source identities and provides retrieval/re-execution tools.

The complete network-dependent external-input suite was not rerun during this packaging validation because the execution environment used here does not provide unrestricted external network retrieval. This limitation does not affect the offline integrity, exact fixtures, claim-evidence hashes, isolated no-external-input tests, or fixed-input CMB replay reported above.

## 11. Scientific boundary

Repository v1.1 does not alter an H0 value, posterior summary, residual statistic, covariance result, mathematical fixture, or scientific nonclaim. It does not establish a corrected H0, revised tension significance, unique systematic cause, invalid BBC correction, defective named pipeline, or new physics.

**Validation verdict: PASS — release-ready compact reproducibility tree within the stated offline and public-input boundaries.**
