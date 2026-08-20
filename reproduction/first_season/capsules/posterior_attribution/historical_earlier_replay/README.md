# Earlier fresh-replay comparison

This directory preserves the comparison table with SHA-256
`29f2c9f5443557692b1283e9bf04f9013c7fca293326451ce384060a1dd54738`
without changing its bytes.

Its corrected role is `HISTORICAL_EARLIER_FRESH_REPLAY`.

```text
NOT_PHASE2C_GENERATED = YES
CURRENT_E002_ACCEPTANCE_EVIDENCE = NO
RUN_ID = UNKNOWN
EXECUTION_ENVIRONMENT = UNRESOLVED
```

The canonical current E002 acceptance lineage is the Phase2C official
empty-cache run recorded in `PROVENANCE/PHASE3B_RUN_LINEAGE_REGISTER.tsv`.
The eight designated substantive tables from that run are compared directly
against the preserved historical substantive reference by
`generate_hts67_phase2c_comparison.py`.
