# PHASE2C_OFFICIAL_EMPTY_CACHE_FETCH_REPORT

## 1. CHECKPOINT VERIFICATION

- Checkpoint ID: `PHASE1-HTS67-HISTORY-SELF-CONTAINMENT-20260728T101042Z`
- Detached checkpoint manifest SHA-256: `2de76aa6d7b0a147a7314848b076f1fb664400efbf26ccf268774ce2e1c580c0`
- Bundle/checkpoint verification exit code: `0`
- Repository tree before: `fa3ce398f881f1f50e0520dca0fb5af0d866edb4e3f9f7491782677f7b78beca`
- Repository tree after: `fa3ce398f881f1f50e0520dca0fb5af0d866edb4e3f9f7491782677f7b78beca`
- Repository modification: `NONE`

## 2. EXECUTION ENVIRONMENT

- Started UTC: `2026-07-28T12:29:33Z`
- Finished UTC: `2026-07-28T13:39:29Z`
- Execution root: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z`
- Free disk before execution: `927042940928` bytes
- Environment record: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/PHASE2C_ENVIRONMENT.json`
- Network preflight: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/PHASE2C_NETWORK_PREFLIGHT.tsv`

## 3. EMPTY-CACHE PROOF

- external_cache starting file count: `0`
- work starting file count: `0`
- outputs starting file count: `0`
- No previous archive, selected member, work directory, or output was imported.

## 4. OFFICIAL ACQUISITION

- Original archive contract: `NOT_RUN`
- Fixed archive contract: `PASS`
- HTTP headers and final URLs: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/OFFICIAL_HTTP_HEADERS/`
- Acquisition table: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/OFFICIAL_ARCHIVE_ACQUISITION.tsv`

## 5. SELECTED MEMBER VERIFICATION

- Verified members: `51/51`
- Detail: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/OFFICIAL_SELECTED_MEMBER_VERIFICATION.tsv`

## 6. REPLAY RESULTS

- E002 from official empty cache: `PASS`
- Stage status/classification records: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/E002_STAGE_STATUS.tsv`, `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/E002_STAGE_CLASSIFICATION_VERIFICATION.tsv`
- Fresh result comparison: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/E002_FRESH_OUTPUT_COMPARISON.tsv`
- Fresh stage comparison: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/E002_FRESH_STAGE_COMPARISON.tsv`
- HTS67 historical reference comparison: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/HTS67_HISTORICAL_VS_FRESH_COMPARISON.tsv`
- Phase 1 local verifier log: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/logs/PHASE2C_PHASE1_LOCAL_VERIFIER.txt`

## 7. COMMANDS AND EXIT CODES

- Runner: `python3 repository/REPRODUCTION/posterior_attribution/run_all.py --fetch-inputs --cache <empty-cache> --work <empty-work> --output <empty-output> --verify`
- Runner exit code: `0`
- stdout: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/logs/PHASE2C_RUN_STDOUT.txt` (`13629` bytes; SHA-256 `62b1a0b62ecc02a0bf9225457f6b389a9b051fa6243b49651ec51685061c5bfa`)
- stderr: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/logs/PHASE2C_RUN_STDERR.txt` (`0` bytes; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`)

## 8. GENERATED EVIDENCE

- Evidence manifest detached SHA-256: `5bf0d7ee009d8eb128a569e82de19562def1e1f2606137e9a6e27b4624959609`
- Evidence manifest: `PHASE2C_EVIDENCE_MANIFEST.tsv`
- Evidence checksum register: `/home/kei/h0_phase2c_official_fetch_20260728T122933Z/evidence/PHASE2C_EVIDENCE_SHA256SUMS.txt`

## 9. REPOSITORY MODIFICATION CHECK

- Repository modification: `NONE`
- Phase 1 checkpoint was referenced read-only and no repository file was intentionally changed.

## 10. FAILURE CLASSIFICATION

- Classification: `PASS`
- Summary: `NONE`

## 11. CHECKPOINT

- Phase 2C evidence checkpoint ID: `PHASE2C-NETWORK-EXECUTION-20260728T122933Z`
- Evidence manifest detached SHA-256: `5bf0d7ee009d8eb128a569e82de19562def1e1f2606137e9a6e27b4624959609`

## 12. CLAIMED RESULT

```text
OFFICIAL_FETCH_EMPTY_CACHE = PASS
E002_FROM_OFFICIAL_EMPTY_CACHE = PASS
FAILURE_CLASSIFICATION = NONE
```
