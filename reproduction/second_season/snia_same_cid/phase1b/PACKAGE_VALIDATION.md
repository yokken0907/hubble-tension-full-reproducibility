# Package validation

Boundary marker:
`PROVENANCE_ONLY_NO_ROW_MODIFICATION_NO_COVARIANCE_CORRECTION_NO_CORRECTED_H0_NO_TENSION_RESOLUTION`

Formal status:
`AUDIT_COMPLETE_PROVENANCE_AND_COVARIANCE_LINEAGE_TRACED`

The corrected package is accepted only if all named
`GATE-P1B-01`–`GATE-P1B-18` checks pass in the final live verifier:

1. two fixed commits and nine source-lock files;
2. the ordered, schema-valid `AMEND-001`–`AMEND-004` ledger;
3. removal of the prohibited uncertainty-type assertion;
4. fixed README description, observed numerical discrepancy, and
   `UNRESOLVED_DOCUMENTATION_DATA_DISCREPANCY`;
5. a summary mutually consistent with all 277 error-diagnostic rows;
6. catalog-only classes summing to 277;
7. zero final ambiguity and zero final unmatched rows;
8. 277 one-to-one matches, zero official-row reuse, and complete coverage;
9. 30 multi-row groups and 69 rows, split 21 two-row and 9 three-row groups;
10. 30 cross-survey groups and zero same-survey repeat groups;
11. 76,729/76,729 exact `float64` covariance matches and maximum difference
    zero;
12. no unsupported covariance-construction-process assertion;
13. joint catalog-and-covariance lineage disclosure;
14. unchanged status, version, boundary, and absence of Phase 1C results;
15. 18/18 tests plus clean reproduction;
16. a read-only default verifier;
17. valid `MANIFEST.tsv` and `SHA256SUMS.txt`;
18. byte-identical deterministic ZIP replicas.

## Recorded closure targets

- Source locks: PASS, 9/9 across two repositories.
- Catalog-only classification: unique 275, ambiguous 2, unmatched 0.
- Covariance-assisted final classification: required 2, ambiguous 0,
  unmatched 0.
- Final mapping: 277/277 one-to-one, official-row reuse 0, full eligible-pool
  coverage.
- Error diagnostic: 277/277 H0DN values within H0DN print tolerance of the
  printed STAT+SYS diagonal square root; discrepancy cause unresolved.
- Groups: 30 groups, 69 rows, 21 two-row, 9 three-row, all 30 cross-survey.
- Covariance: 76,729/76,729 exact, maximum absolute difference zero.
- Unit/adversarial tests: PASS, 18/18.
- Clean reproduction: PASS, 13/13 core artifacts semantically and
  byte-identical.
- Pre-manifest closure record: PASS, 16/16 gates.
- Final post-manifest live verification: PASS, 18/18 gates.

The frozen README describes `m_b_corr_err_DIAG` as a covariance-diagonal
uncertainty, while its printed values do not numerically equal the square
roots of the printed STAT+SYS covariance diagonal. The cause is not
determined here. `AMEND-004` records this with
`results_observed=YES`, `interpretation_affected=NO`.

The final result is joint catalog-and-covariance lineage: 275 rows are
catalog-only unique and 2 require the matrix diagonal. The covariance
comparison is therefore not claimed to be fully independent of every
disambiguation input.

ZIP CRC, final archive SHA-256, and the external primary-versus-replica
comparison are recorded beside the two canonical delivery files because
embedding an archive hash inside that archive would be self-referential.
