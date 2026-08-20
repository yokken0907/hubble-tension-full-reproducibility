# Pre-correction log audit note

`RUN_LOG_PRE_CORRECTION_HOLD.txt` preserves only stdout from the initial
preflight and does not itself contain the checksum-mismatch error or explicit
HOLD line, likely because the failure detail was emitted to stderr.

The historical HOLD remains independently supported by:

- the V1 truncated GWTC-4 SHA256 entry;
- the unchanged source byte;
- the complete SHA256 recorded elsewhere in V1;
- the CORR1 documentation;
- the successful post-CORR1 identity preflight.

Classification:

```text
PRE_CORRECTION_LOG = INCOMPLETE_STDOUT_ONLY
SCIENTIFIC_IMPACT = NONE
```
