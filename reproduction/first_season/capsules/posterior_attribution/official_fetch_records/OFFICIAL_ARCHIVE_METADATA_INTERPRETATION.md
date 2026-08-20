# Official original-archive metadata interpretation

The Phase2C clean execution accessed the official `chains_ttteee_winter1920.zip` endpoint by HTTP Range and verified the 40 selected ORIGINAL members individually by byte size and SHA-256. The 6.19 GB outer archive was not fully materialized and no full-archive SHA-256 is claimed.

The recorded expected ETag and the ETag observed on 2026-07-28 differ. This mismatch is preserved as HTTP metadata and is **not** silently normalized. ETag is not used as the scientific identity gate for the replay. The input identity gate is the 40/40 selected ORIGINAL-member size/SHA-256 verification, together with the 11/11 selected FIXED-member verification and the full FIXED archive SHA-256 check.

Accordingly:

- official Range acquisition of the ORIGINAL selected members: PASS;
- full ORIGINAL archive materialization/hash: not performed and not claimed;
- ORIGINAL ETag equality: no;
- selected scientific input identity: 51/51 PASS;
- E002 from a newly empty external cache: PASS;
- original likelihoods, samplers, and posterior-generation processes: not reproduced.

The raw launcher acquisition table is retained unchanged under `phase2c_network_execution/OFFICIAL_ARCHIVE_ACQUISITION_RAW.tsv`. Its `STATUS=NOT_RUN` entry for ORIGINAL denotes that the full outer archive contract was not materialized; it does not denote failure of the Range-based selected-member acquisition.
