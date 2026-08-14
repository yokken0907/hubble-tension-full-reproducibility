# Extension Execution Contract

## Fixed classification

- `TASK_TYPE = UNCHANGED_CODE_13_CHAIN_EXTENSION`
- `FROZEN_IMPLEMENTATION_SHA256 = 6360c803c584cc29e939445001fa6508cd875d16b4cdba5caba8be8b031368f7`
- `INPUT_FILE_COUNT = 13`
- `SOURCE_COMMIT = d7f38db341f68be1df0d9ac1fc528c45113f94cf`
- `NEW_PHYSICAL_CLAIM = NO`
- `PAPER_COMPARISON = NO`
- `CODE_MODIFICATION = PROHIBITED`

## Required procedure

1. Calculate SHA256 for `FROZEN_CODE/run_audit.py`.
2. Require exact equality with `FROZEN_IMPLEMENTATION_SHA256`.
3. Calculate SHA256 for all inputs and require exact equality with
   `SOURCE_MANIFEST.tsv`.
4. Execute `RUN_EXTENSION.py` from the package root.
5. Do not change the frozen implementation, quantile method, HDF5 parsing,
   tolerance, parameter-selection rule, or source manifest.
6. Do not consult a paper, website, prior numerical result, previous HTS68
   output, comparison audit, or expected value.
7. Do not compare or interpret the generated values.
8. Return only the renamed final result ZIP and a brief execution-status line.

## Output-name handling

The frozen implementation internally uses its original sentinel result
basename. `RUN_EXTENSION.py` executes it unchanged and then changes only the
external ZIP filename, without changing the ZIP bytes:

`TDCOSMO_BLIND_TABLE6_EXTENSION_RESULTS_FOR_REVIEW.zip`

The internal archive root may retain the original sentinel basename. This is
expected and does not indicate reuse of the three-file result.

## Hard stops

Stop without numerical interpretation if:

- the frozen source-code hash differs;
- an input hash differs;
- the implementation raises an exception;
- the generated result ZIP fails CRC;
- the copied source code inside the generated result differs from the frozen
  source-code hash.

## Prohibited output language

Do not use `REPRODUCED`, `CONFIRMED`, `AGREES_WITH_PAPER`, or a Hubble-tension
claim. The separate post-blind audit will perform all comparisons.
