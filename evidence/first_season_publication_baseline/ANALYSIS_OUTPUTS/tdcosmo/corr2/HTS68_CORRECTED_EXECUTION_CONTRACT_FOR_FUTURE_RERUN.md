# HTS68 corrected execution contract for a future rerun

Contract ID: `HTS68_CORRECTED_EXECUTION_CONTRACT_FOR_FUTURE_RERUN`  
Contract version: `CORR2`  
Prepared: 2026-07-25 (Asia/Tokyo)  
Current authorization: `HOLD_G0_AND_PAPER_VERSION_INCOMPLETE`

## 1. Status and historical boundary

This contract applies only to a possible future rerun. It was created after the original HTS68 result and cannot retroactively convert the original run into a prefrozen confirmatory analysis.

Original HTS68 analysis mode remains:

`POSTHOC_FORMALIZED_EXPLORATORY_PUBLIC_CHAIN_RECONSTRUCTION`

A future execution may be classified as a prospectively contracted replication only after Gate G0 is completely frozen and approved before execution begins.

## 2. Authorized scientific scope

After G0 and source identity pass, the script may only:

- validate the frozen 28 public HDF5 exports;
- calculate the existing equal-weight marginal quantiles;
- compare them with the separately stored and independently hashed Table 6 reference TSV;
- generate the existing descriptive nested-posterior shift map;
- preserve the existing limitation and reproducibility audits.

It may not retrieve or substitute sources, add models or datasets, run MCMC or likelihood code, calculate independent significance, infer causal attribution, localize a systematic, identify a precision-controlling layer, or call the same implementation an independent recomputation.

## 3. Required governance artifacts

The future run requires all of the following as separate files:

1. corrected execution script;
2. this execution contract, updated with a resolved paper version;
3. `HTS68_PAPER_TABLE6_REFERENCE.tsv`, updated to the same paper version;
4. an approved `HTS68_G0_APPROVAL_RECORD.json`;
5. `HTS68_G0_FREEZE_MANIFEST.json` binding the exact hashes of items 1–4.

The supplied templates are intentionally unresolved and are not authorization to execute.

## 4. Gate G0 — contract completeness before scientific source read

G0 must run before reading repository metadata, the paper PDF, or any HDF5 chain.

PASS requires:

- a resolved literal paper version;
- exact normalized script hash frozen in the script and G0 manifest;
- exact G0 manifest hash frozen in the script;
- exact execution-contract hash in the G0 manifest;
- exact approval-record hash in the G0 manifest;
- exact reference-TSV hash in both code contract and G0 manifest;
- approval record status `APPROVED`;
- approval record contract ID/version equal to this contract;
- approval timestamp strictly earlier than execution start;
- approval paper identifier/version equal to the frozen code and manifest values.

Any unresolved sentinel, missing artifact, mismatch, invalid timestamp, or approval created at or after execution start produces:

`HOLD_CONTRACT_INCOMPLETE`

with nonzero exit before any scientific source read.

### Normalized script hash

To avoid a self-reference loop, the script hash is calculated after replacing only the values of:

- `EXPECTED_SCRIPT_NORMALIZED_SHA256`
- `EXPECTED_G0_FREEZE_MANIFEST_SHA256`

with fixed normalization markers. All other script bytes remain hash-relevant.

The historical correction package included `tools/prepare_hts68_g0_freeze.py`, which performed this governance-only preparation and did not open scientific sources; the utility is not redistributed in the present selective public repository.

## 5. Gate G1 — source identity before HDF5 open

After G0 PASS, G1 requires exact agreement for:

- Git remote URL: `https://github.com/TDCOSMO/TDCOSMO2025_public.git`;
- Git commit: `d7f38db341f68be1df0d9ac1fc528c45113f94cf`;
- exact 28-file chain set and all 28 frozen SHA256 values embedded in the patch;
- paper identifier: `arXiv:2506.03023`;
- resolved paper version;
- paper PDF SHA256: `e94a728864f3afe9cc7672b97918ff366863a55df183ba116c3ceff526a7f5c7`;
- repository `README.md` SHA256: `20ba4944985c1435b1b111f713a58968e8468c430022fec11ab526797b6e89f5`;
- repository `likelihood_sampling.py` SHA256: `45825cbe3104a8bbd73f1001c6ede7fa08105e4c26e09486115639a3855b5a42`;
- Table 6 TSV SHA256 frozen in the code and G0 manifest.

Missing, extra, renamed, or hash-mismatched chains cause `HOLD_SOURCE_IDENTITY_MISMATCH` before HDF5 open.

## 6. Gate G2 — chain structural contract

After G0 and G1 PASS only, all 28 HDF5 exports must satisfy the pre-existing structural checks. Failure produces:

`HOLD_CHAIN_CONTRACT_FAILURE`

## 7. Gate G3 — reference comparison

After G0–G2 PASS only, equal-weight 16/50/84-percentile summaries are compared at recorded precision with `HTS68_PAPER_TABLE6_REFERENCE.tsv`.

The TSV is a separately stored and independently hashed transcription table. It is not evidence of automated PDF extraction.

Failure produces:

`HOLD_PAPER_REFERENCE_MATCH_FAILURE`

## 8. Gate G4 — descriptive mapping outside the PASS gate

The nested-posterior shift map may be generated after G0–G3. The observation that SLACS-associated shifts exceed SL2S-associated shifts is:

`DESCRIPTIVE_OBSERVATION_OUTSIDE_THE_FORMAL_PASS_GATE`

It does not establish causality, independent significance, a systematic, a dominant cause, or a precision-controlling layer. Joint SLACS+SL2S additions may be non-additive.

## 9. Formal outcome logic

Formal PASS requires:

`G0 && G1 && G2 && G3`

Future-rerun PASS classification:

`PASS_TDCOSMO2025_FROZEN_PUBLIC_CHAIN_CONTRACT_AND_DESCRIPTIVE_NESTED_POSTERIOR_SHIFT_MAPPING_WITH_SCOPE`

Short management classification:

`PASS_WITH_SCOPE`

Any failed required gate produces a corresponding `HOLD_*` classification and:

`management_classification = HOLD`

The original HTS68 correction classification remains separately governed by `HTS68_CORR1_CANONICAL_CLASSIFICATION.md`; a successful future rerun does not rewrite that historical record.

## 10. Independent-audit status

`HTS68 independent alternate-implementation recomputation = NOT_DONE`

Applying this patch, rerunning the corrected script, copying it, or superficially refactoring it does not create an independent alternate implementation.

## 11. Change control

Any future amendment must record the old value, new value, reason, timestamp, whether scientific results already existed, and whether post-hoc reclassification is required. No mismatch may be waived inside a successful run.
