# Frozen post-hoc CID-only crosswalk diagnostic

Diagnostic identifier:
`H0DN-SNIA-PHASE1D-POSTHOC-CID-ONLY-CROSSWALK-20260730-01`

Freeze timestamp: 2026-07-30T07:43:00Z

## Trigger and chronology

The main Phase 1D contract had already been executed. The following main
results were known:

- 38 of 69 rows were `UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE`;
- 31 of 69 rows were `NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE` under the frozen
  `(CID, IDSURVEY)` source vocabulary;
- 3 of 30 groups had all rows resolved to distinct public file blobs;
- all 12 pipeline anchors verified;
- all 3 predeclared external assets were referenced but not tracked;
- the main classification was
  `PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE`.

Illustrative same-CID files outside the frozen row crosswalk had also been
manually observed for `2007qe`, `2005M`, and `2007kk`. No complete
31-row CID-only candidate ledger or aggregate classification had been run.

## Question

For each of the 31 unresolved main-audit rows, does the frozen DataRelease
contain active, parseable photometry files with the exact same `SNID` when
the row's `IDSURVEY` directory/header restriction is deliberately removed?

This diagnostic distinguishes:

- no same-CID active file in the seven already configured public source
  directories;
- exactly one same-CID file outside the frozen crosswalk;
- multiple same-CID files outside the frozen crosswalk.

It does not decide which alternate file, if any, generated the final row.

## Frozen inputs

- the same H0DN and Pantheon+SH0ES commits as the main Phase 1D audit;
- `results/row_lineage.tsv` from the completed main audit;
- the same seven unique photometry directories, active `.LIST` membership,
  `.IGNORE` exclusions, and parser used by the main audit;
- the main protected files:
  `audit_summary.json`, `row_lineage.tsv`, `group_lineage.tsv`,
  `candidate_file_evidence.tsv`, and
  `referenced_asset_availability.tsv`.

## Frozen rule

1. Select only main-audit rows whose `lineage_status` is not
   `UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE`.
2. Search every active parseable file in all seven configured directories.
3. A CID-only candidate requires only byte-for-byte equality between the row
   `CID` and file `SNID` after stripping leading/trailing ASCII whitespace.
4. Do not use or reinterpret `IDSURVEY`, directory name, `SURVEY`,
   magnitude, redshift, residual, covariance, or fit parameters to promote a
   candidate.
5. Classify each row:
   - zero candidates: `NO_CID_ONLY_PUBLIC_FILE`;
   - one: `ONE_CID_ONLY_PUBLIC_FILE_OUTSIDE_FROZEN_CROSSWALK`;
   - more than one:
     `MULTIPLE_CID_ONLY_PUBLIC_FILES_OUTSIDE_FROZEN_CROSSWALK`.
6. Search the complete Git tree for a tracked basename exactly equal to
   `SURVEY.DEF`; record presence or absence without expanding the source
   universe.

## Protected-main-result rule

The five main protected files must have identical SHA-256 values before and
after the diagnostic. The diagnostic may not edit the main audit summary,
row/group ledgers, formal status, or release-sufficiency classification.

The diagnostic status is `POSTHOC_DIAGNOSTIC_COMPLETE`. Its promotion status
must remain `POSTHOC_ONLY_NO_MAIN_RESULT_CHANGE`.

## Non-claims

- A CID-only candidate is not a demonstrated row ancestor.
- An alternate directory or header is not an inferred `IDSURVEY` crosswalk.
- Absence of `SURVEY.DEF` from this release is not evidence that SNANA or the
  original analysis lacked a survey definition.
- No survey is ranked and no object is called anomalous.
- No covariance, `H0`, or tension significance is changed.
