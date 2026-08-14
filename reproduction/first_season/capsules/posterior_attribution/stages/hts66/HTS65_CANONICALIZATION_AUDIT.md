# HTS65 canonicalization audit

`PASS_EXHAUSTIVE_COALITION_PARTITION_SENSITIVITY_AUDIT`

Integrity:
- outer ZIP SHA256: `0cd4714c250806eb2153900a5e42510655c715eb150b713e76338bc08cb326ab`
- ZIP CRC: PASS
- internal SHA256 manifest: 30/30 PASS
- independent raw-chain and all-LOO reconstruction: PASS
- maximum saved-summary reconstruction error: `8.88e-16`

Primary results:
- partition-stable directed edges: 11/14
- partition-sensitive directed edges: 3/14
- top-variable turnover: BASE_TO_ACT forward and BASE_TO_PR4 forward
- BASE_TO_ACT reverse is sensitive through effective-variable-count range
- maximum variable Owen-share range across all partitions: `0.0982351`
- maximum partition effective-count range: `0.516971`

Partition stability does not override HTS64 basis sensitivity.


## Portable exact-archive gate note

The current public replay uses a path-sanitized portable replica whose substantive scientific members are byte-identical to the historical archive. The historical outer SHA-256 and the portable gate SHA-256 are cross-recorded in `../../PORTABLE_EXACT_ARCHIVE_MAPPING.tsv`. This checksum update is a non-scientific portability edit.
