# Historical sequence

This file preserves the chronology without overwriting earlier status records.

## 1. Original public-chain posterior-summary analysis

The original HTS68 analysis inspected released public HDF5 posterior exports and produced descriptive released-sample summaries. It was later classified as post hoc and exploratory. It did not reconstruct the original likelihood, sampler, convergence diagnostics, or posterior-generation process.

## 2. Post hoc status and source-contract defects identified

On **2026-07-24 (UTC)**, `ANALYSIS_OUTPUTS/tdcosmo/corr1/HTS68_CORR1_CANONICAL_CLASSIFICATION.md` recorded:

```text
HTS68 independent alternate-implementation recomputation = NOT_DONE
```

The corresponding method report required source and paper identity to be resolved before any future rerun.

## 3. Method/contract-only corrections created

On **2026-07-24 (UTC)**, CORR1 documented method and contract corrections without opening chains or performing a new scientific calculation.

On **2026-07-25**, CORR2 validated a governance and source-gate patch for a possible future rerun. Its execution state remained:

```text
HOLD_G0_AND_PAPER_VERSION_INCOMPLETE
```

The patch validation did not itself rerun the scientific analysis.

## 4. Historical alternate-implementation state = NOT_DONE

At the C026/C027 stage, no separately coded alternate implementation had yet been performed. These records remain unchanged in `PROVENANCE/STATEMENT_TO_EVIDENCE_REGISTER.tsv`.

## 5. Later three-file pilot

A later project-internal implementation was written from the packaged execution specification and run on three fixed HDF5 files. The contract prohibited access to prior HTS68 numerical results, prior code, the paper, the repository, expected values, and the identifier crosswalk.

The post-pilot audit recorded:

- 3/3 structural comparisons passed;
- 9/9 quantile comparisons were exact.

No calendar date is asserted here because the retained pilot records do not state one in their document text.

## 6. Method, code, tolerance, and stopping rule frozen

Before the 13-file extension:

- implementation SHA-256 was fixed as `6360c803c584cc29e939445001fa6508cd875d16b4cdba5caba8be8b031368f7`;
- the equal-weight Type-7 quantile definition was fixed;
- the absolute/relative comparison tolerance was fixed;
- the 13-file source manifest and source commit were fixed;
- code modification during extension was prohibited;
- hard-stop conditions were specified.

## 7. Unchanged-code extension to 13 files

The frozen implementation was applied to 13 released files: the twelve flat-LambdaCDM Table 6 chains plus one release-identifier collision control. The extension execution record states that code modification was prohibited.

## 8. Later final state = COMPLETE_WITH_SCOPE

The later closeout classification records:

```text
TDCOSMO_ALTERNATE_IMPLEMENTATION_BRANCH = COMPLETE_WITH_SCOPE
```

with:

- 13/13 structural comparisons passed;
- 39/39 q16/q50/q84 comparisons passed within the frozen tolerance;
- 12/12 Table 6 rows matched at published precision.

## Chronology rule

```text
NOT_DONE and COMPLETE_WITH_SCOPE are not contradictory.
They refer to different historical dates and stages.
```

The later V001 record supplements the historical C026/C027 records. It does not rewrite them or retroactively convert the original post hoc analysis into a prefrozen confirmatory analysis.
