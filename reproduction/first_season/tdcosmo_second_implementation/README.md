# TDCOSMO released-sample second-implementation evidence

## Status

```text
VALIDATION_ID = V001
BASE_PUBLIC_VERSION = 1.5.5
INTEGRATED_RELEASE_CANDIDATE = 1.6.0
METHOD_STATUS = PRE_SPECIFIED_AND_FROZEN_BEFORE_13_FILE_EXTENSION
FINAL_RESULT = COMPLETE_WITH_SCOPE
```

This validation was performed after the original 30-statement and 46-number manuscript audit.

It does not change any of the original 46 principal numerical results (`N001`–`N046`) or any of the original 30 publication statements (`C001`–`C030`).

It provides a bounded, project-internal second-implementation check of released TDCOSMO HDF5 sample summaries. The three-file pilot was governed by a contract that prohibited access to prior HTS68 numerical results, the paper, the source repository, prior code, expected values, and the identifier crosswalk. The package audit supports compliance with that contract, but it cannot establish the absence of unrecorded exposure outside the packaged workflow. The public description is therefore limited to a **three-file pilot followed by an unchanged-code 13-file extension**.

The implementation, quantile definition, comparison tolerance, source manifest, and stopping rule were fixed before the 13-file extension results were examined.

## Result within scope

- 13/13 structural comparisons passed.
- 39/39 q16/q50/q84 comparisons passed within the frozen tolerance.
- 12/12 Table 6 rows matched at published precision.
- The implementation SHA-256 is `6360c803c584cc29e939445001fa6508cd875d16b4cdba5caba8be8b031368f7`.
- The 13 public inputs are identified by filename, byte size, source commit, and SHA-256 in `SOURCE_MANIFEST_13_CHAINS.tsv`.
- Third-party HDF5 files are not redistributed.

## What this does not reproduce

This validation does not reproduce:

- the original likelihood;
- the original sampler;
- burn-in or thinning;
- convergence diagnostics;
- posterior weights or log probabilities;
- the posterior-generation pipeline;
- an external independent replication.

It does not establish a corrected value of H0, a causal systematic, a preferred lens-population interpretation, new physics, or a resolution of the Hubble tension.

## Historical relationship

The earlier records `C026` and `C027` remain valid descriptions of the historical stage at which an alternate implementation had not yet been performed and the corrected future-rerun contract remained on HOLD. The later `V001` record documents a separate subsequent workflow.

`NOT_DONE` and `COMPLETE_WITH_SCOPE` are not contradictory: they refer to different dates and stages. See `HISTORICAL_SEQUENCE.md`.

## Evidence map

| Purpose | File |
|---|---|
| Claim and interpretation boundary | `CLAIM_AND_SCOPE_BOUNDARY.md` |
| Historical sequence | `HISTORICAL_SEQUENCE.md` |
| Pilot execution contract | `BLIND_EXECUTION_CONTRACT.md` |
| Frozen extension contract | `EXTENSION_EXECUTION_CONTRACT.md` |
| Method and tolerance freeze | `METHOD_FREEZE_RECORD.json` |
| 13-input identity manifest | `SOURCE_MANIFEST_13_CHAINS.tsv` |
| Separately written implementation | `run_audit.py` |
| Pilot comparison record | `PILOT_COMPARISON_AUDIT_REPORT.md` |
| 13-file structure comparison | `STRUCTURAL_COMPARISON_13_CHAINS.tsv` |
| 39 quantile comparisons | `NUMERICAL_COMPARISON_13_CHAINS.tsv` |
| 12 Table 6 published-precision comparisons | `TABLE6_PUBLISHED_PRECISION_COMPARISON.tsv` |
| Final bounded classification | `FINAL_CLASSIFICATION.json` |
| Package-integrity summary | `VALIDATION_REPORT.md` |
| Selection and exclusion rationale | `SELECTION_AND_EXCLUSION_RECORD.md` |

The repository-level stable record is `PROVENANCE/POST_SYNTHESIS_VALIDATION_REGISTER.tsv`, entry `V001`.

## Historical execution-path record

`EXTENSION_RUN_COMMAND.txt` preserves the historical command structure while replacing ephemeral absolute runtime locations with explicit placeholders (`<HISTORICAL_PYTHON>`, `<HISTORICAL_BUILD_RUNTIME>`, and `<HISTORICAL_TEMP_ROOT>`). This redaction changes no scientific input, method, code, or result.

## License

Documentation, tables, and audit records in this directory are CC BY 4.0 under the repository license. The author-generated `run_audit.py` is separately licensed under the MIT License; see `LICENSE_CODE_MIT`.
