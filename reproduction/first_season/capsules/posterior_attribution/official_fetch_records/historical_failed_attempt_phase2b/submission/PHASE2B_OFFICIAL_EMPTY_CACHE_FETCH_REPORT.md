# PHASE2B_OFFICIAL_EMPTY_CACHE_FETCH_REPORT

## 1. CHECKPOINT VERIFICATION

- Checkpoint ID: `PHASE1-HTS67-HISTORY-SELF-CONTAINMENT-20260728T101042Z`
- Detached checkpoint manifest SHA-256: `2de76aa6d7b0a147a7314848b076f1fb664400efbf26ccf268774ce2e1c580c0`
- Bundle/checkpoint verification exit code: `0`
- Repository tree before: `f54a149551f9a89dfda7619f3f9a46d2b8057bcb28cb71cf41639c66a378744c`
- Repository tree after: `f54a149551f9a89dfda7619f3f9a46d2b8057bcb28cb71cf41639c66a378744c`
- Repository modification: `NONE`

## 2. EXECUTION ENVIRONMENT

- Started UTC: `2026-07-28T10:57:22Z`
- Finished UTC: `2026-07-28T11:58:02Z`
- Execution root: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z`
- Free disk before execution: `928877608960` bytes
- Environment record: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/PHASE2B_ENVIRONMENT.json`
- Network preflight: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/PHASE2B_NETWORK_PREFLIGHT.tsv`

## 3. EMPTY-CACHE PROOF

- external_cache starting file count: `0`
- work starting file count: `0`
- outputs starting file count: `0`
- No previous archive, selected member, work directory, or output was imported.

## 4. OFFICIAL ACQUISITION

- Original archive contract: `NOT_RUN`
- Fixed archive contract: `PASS`
- HTTP headers and final URLs: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/OFFICIAL_HTTP_HEADERS/`
- Acquisition table: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/OFFICIAL_ARCHIVE_ACQUISITION.tsv`

## 5. SELECTED MEMBER VERIFICATION

- Verified members: `51/51`
- Detail: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/OFFICIAL_SELECTED_MEMBER_VERIFICATION.tsv`

## 6. REPLAY RESULTS

- E002 from official empty cache: `NOT_RUN`
- Stage status/classification records: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/E002_STAGE_STATUS.tsv`, `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/E002_STAGE_CLASSIFICATION_VERIFICATION.tsv`
- Fresh result comparison: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/E002_FRESH_OUTPUT_COMPARISON.tsv`
- Fresh stage comparison: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/E002_FRESH_STAGE_COMPARISON.tsv`
- HTS67 historical reference comparison: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/HTS67_HISTORICAL_VS_FRESH_COMPARISON.tsv`
- Phase 1 local verifier log: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/logs/PHASE2B_PHASE1_LOCAL_VERIFIER.txt`

## 7. COMMANDS AND EXIT CODES

- Runner: `python3 repository/REPRODUCTION/posterior_attribution/run_all.py --fetch-inputs --cache <empty-cache> --work <empty-work> --output <empty-output> --verify`
- Runner exit code: `1`
- stdout: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/logs/PHASE2B_RUN_STDOUT.txt` (`13121` bytes; SHA-256 `8d7ea923d10860102e6fb4eb707ccb18573aa714a2d123a7288aa43435298865`)
- stderr: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/logs/PHASE2B_RUN_STDERR.txt` (`1511` bytes; SHA-256 `ace217eec8767de0c3c0d203ef991bbefa66d7852e05fd1e271ca5e9b2e1d178`)

## 8. GENERATED EVIDENCE

- Evidence manifest detached SHA-256: `9398647dc421fe65d3de4361f5c80f154f0a93a82cb83151ed09f5ce7a31fd80`
- Evidence manifest: `PHASE2B_EVIDENCE_MANIFEST.tsv`
- Evidence checksum register: `/home/kei/h0_phase2b_official_fetch_20260728T105722Z/evidence/PHASE2B_EVIDENCE_SHA256SUMS.txt`

## 9. REPOSITORY MODIFICATION CHECK

- Repository modification: `NONE`
- Phase 1 checkpoint was referenced read-only and no repository file was intentionally changed.

## 10. FAILURE CLASSIFICATION

- Classification: `FAIL_STAGE_REPLAY`
- Summary: `run_all.py returned non-zero. See the recorded stdout/stderr hashes and principal error lines.`

## 11. CHECKPOINT

- Phase 2B evidence checkpoint ID: `PHASE2B-NETWORK-EXECUTION-20260728T105722Z`
- Evidence manifest detached SHA-256: `9398647dc421fe65d3de4361f5c80f154f0a93a82cb83151ed09f5ce7a31fd80`

## 12. CLAIMED RESULT

```text
OFFICIAL_FETCH_EMPTY_CACHE = BLOCKED
E002_FROM_OFFICIAL_EMPTY_CACHE = NOT_RUN
FAILURE_CLASSIFICATION = FAIL_STAGE_REPLAY
```
