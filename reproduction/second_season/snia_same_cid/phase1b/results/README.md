# Generated results

`scripts/run_audit.py` generates this directory from two separately acquired,
source-locked repositories. Upstream data bytes are not redistributed.

The final 277/277 mapping is a joint catalog-and-covariance lineage result:
275 rows are uniquely identified by catalog fields alone; the 2 catalog-only
ambiguous rows require the official STAT+SYS diagonal as a numerical
fingerprint. The subsequent covariance comparison is not presented as fully
independent of every input used in those two disambiguations.

Principal artifacts:

- `row_mapping.tsv`: final 277-row one-to-one mapping.
- `candidate_evidence.tsv`: all 279 stage-one catalog candidates, with
  covariance-assist evidence only where that stage was used.
- `row_mapping_dependency.tsv`: all 277 rows with catalog and final
  dependency classifications and deterministic candidate details.
- `row_mapping_dependency_summary.json`: computed dependency counts, final
  coverage, and joint-lineage label.
- `covariance_diagonal_required_rows.tsv`: the two rows for which the
  official diagonal is required.
- `error_field_discrepancy_rows.tsv`: 277-row comparison of
  `m_b_corr_err_DIAG`, the printed STAT+SYS diagonal square root, and H0DN
  `err_m_b`.
- `error_field_discrepancy_summary.json`: recomputed counts and maximum
  differences, with cause
  `UNRESOLVED_DOCUMENTATION_DATA_DISCREPANCY`.
- `multirow_group_summary.tsv`: all 30 exact-name multi-row groups and survey
  multiplicity classes.
- `multirow_row_evidence.tsv`: all 69 rows in those groups.
- `covariance_lineage.json`: 76,729-element exact comparison and its
  evidentiary limit.
- `audit_summary.json`: formal status, top-level counts, amendment disclosure,
  and scientific non-claims.
- `EXECUTION_STATUS.json`: formal gate status and boundary.

The frozen README describes `m_b_corr_err_DIAG` as a covariance-diagonal
uncertainty, but the printed catalog values do not numerically equal the
square roots of the printed STAT+SYS covariance diagonal. The cause is not
determined here. The diagnostic records the discrepancy without changing any
input value or making a causal claim.
