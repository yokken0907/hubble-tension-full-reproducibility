# Package validation

Boundary marker:
`CALIBRATION_DIAGNOSTIC_ONLY_NO_COVARIANCE_RESCALE_NO_CORRECTED_H0_NO_TENSION_RESOLUTION`

Formal status:
`AUDIT_COMPLETE_CONTRAST_COVARIANCE_CALIBRATION_DIAGNOSTIC`

Correction closure:
`ACCEPT_COMPLETE_WITH_SCOPE`

The package is accepted only if all 24 closure gates pass:

1. active Contract 02 freeze, preserved Contract 01 schema HOLD, amendment
   ledger, and separate post-hoc contract hash;
2. two fixed commits and all 13 source-lock files;
3. canonical Phase 1A and Phase 1B ZIP filename, SHA-256, sidecar, and CRC;
4. 277 ordered one-to-one Phase 1B mapping rows verified against both tables;
5. 30 groups, 69 rows, 39 modes, and every multi-row group cross-survey;
6. raw covariance dimensions, finiteness, and `5e-8` transpose bound;
7. 76,729/76,729 exact H0DN versus mapped STAT+SYS values;
8. Cholesky success and positive eigenvalue gate for all five projected
   covariance matrices;
9. known Phase 1A 39-mode value reproduced within `2e-8`;
10. Cholesky and eigendecomposition agreement for every baseline;
11. alternative null-space basis agreement for every baseline;
12. 32 fixed-seed orthogonal-coordinate trials;
13. chi-square CDF/gamma agreement, distinct `0.001` and `0.01` thresholds,
    and the ordered classification;
14. Phase 1A conditional Beta and Phase 1C marginal chi-square probabilities
    in separate fields;
15. independent parser/null-space/eigendecomposition verifier;
16. 33/33 unit and adversarial tests, including verifier read-only
    regression;
17. clean-copy byte identity for 22/22 main and post-hoc artifacts;
18. formal success status and 27/27 internal numerical checks;
19. required English/Japanese documentation and explicit boundary marker;
20. high-precision diagnostic under the same 277 mapping and 39-row basis;
21. finite post-hoc values and no promotion into the main result;
22. selected-submatrix asymmetry counts, locations, and fixed-tolerance
    behavior;
23. upper/lower/symmetric representation coverage and output-row consistency.
24. before/after SHA-256 identity for every existing manifest target during
    the live verifier.

After the manifested tree is fixed, two external delivery checks are also
required:

- valid `MANIFEST.tsv`, `SHA256SUMS.txt`, ZIP CRC, and checksum sidecar;
- byte-identical deterministic ZIP replicas with no redistributed upstream
  covariance bytes.

## Recorded scientific closure

- Phase 1A full: `q=11.209315063602716`, lower tail
  `3.6795245876638087e-06`.
- STAT+SYS without rowwise velocity: `q=14.734235950587198`, lower tail
  `0.00014711328968576817`.
- STATONLY: `q=16.233447508593247`, lower tail
  `0.0004856832550848106`.
- Classification: `LOW_FLAG_PERSISTS_THROUGH_STATONLY`.
- High-precision `m_b_corr` q values:
  `11.181959816277521`, `14.694714732492480`,
  `16.192911494208520` (post-hoc only).
- Both selected 277-by-277 covariance submatrices: zero asymmetric
  off-diagonal pairs; full 1701-by-1701 asymmetry lies outside the mapping.
- Primary numerical checks: 27/27 PASS.
- Independent five-baseline comparisons: 5/5 PASS.
- Tests: 33/33 PASS.
- Clean reproduction: 22/22 byte-identical.

The archive hash and primary-versus-replica comparison remain outside the
archive because embedding an archive's own hash would be self-referential.
