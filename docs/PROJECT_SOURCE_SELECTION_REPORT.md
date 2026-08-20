# Source Review and Selection Report

## Source archive reviewed

The two original split archive members were concatenated without modification and passed ZIP CRC testing.

- part 001 bytes: 524,288,000
- part 002 bytes: 336,264,381
- combined bytes: 860,552,381
- combined SHA-256: `5a667c16dc5847aad83d77b4865d40227bf6fc71c7c0e69405ef11f62451f2a5`
- top-level archive files: 3,117
- directly readable text/code/ledger files inspected: 2,143 (13.27 MB), representing 909 unique byte identities
- nested ZIP text/code/ledger instances inspected recursively: 10,142, representing 6,006 unique byte identities across 418 unique nested ZIP identities

The archive contains extensive deliberate duplication: review ZIPs, sidecars, historical snapshots, repository-reassembly records, and nested reference packages. Scientific selection was therefore made by source status and claim relevance rather than by copying every file.

## Version-locked archival source records

| Record | SHA-256 |
|---|---|
| First Season Master v1.0.0 | `3e6df9f557485de1bb21c54bb129af78943e8e5d08da036e648d251dd952663c` |
| Second Season Master v1.0.0 | `cc15c96a45865f22fcd13c2ef03c8cccc39af8fa6dcace4a25f229d07e964940` |
| Cross-Season Audit v0.1.0 | `9719fae4cbfefeca5ec9e8f04f7949f1a1bdb21d784523752a587ecd166e60cf` |
| Final Internal Validation / Closure v0.1.0 | `db70c27daa85eb1daf907aeedd644c2d0f0cb3a262c121b28431d15c7b95fb2f` |

Claim-relevant records selected from these archival sources are retained under `evidence/canonical_ledgers/`; the directory name is retained as a traceability path. Nested source-package ZIP binaries are not duplicated inside the GitHub tree because the required code, records, numerical specifications, and compact results are selected directly into the reproducibility layer.

## Publication alignment

The repository is aligned to the scientific claims and evidence boundaries of the associated manuscript and Technical Supplements A and B. Publication PDFs are not repository members and are not required by the integrity verifier.

## Selection rule

A source file was retained when at least one of the following is true:

1. it is needed to execute a publication-level numerical validation;
2. it defines a fixed numerical contract, source identity, or evidence boundary used by the publication;
3. it is the machine-readable result behind a manuscript or supplement claim;
4. it is required to verify historical provenance of a retained reproducibility record; or
5. it is needed to regenerate publication table/figure source data.

Files were excluded when they are cache/runtime material, duplicate transport archives, superseded nonessential work-log copies, publication PDFs, or retrievable third-party payloads.

## Important interpretation

The repository is compact because several publication conclusions are explicitly evidence-bounded. When the public record does not uniquely specify an executed analysis path, reproduction consists of confirming the source identities, available products, missing or ambiguous links, and the resulting limit of inference. Inventing an unavailable upstream pipeline would weaken rather than improve reproducibility.
