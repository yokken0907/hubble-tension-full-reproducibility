# Post-hoc contract: cross-CID payload-collision negative control

This diagnostic was designed after the frozen Phase 1F main result was known.
The protected main result contained 48 same-CID file pairs: zero pairs with a
byte-exact observation row, four pairs with exactly one mutual-unique
rounding-compatible four-quantity payload match, and zero pairs with two or
more such matches. Only one of the four accepted matches had an absolute MJD
difference at most 0.11 day.

The diagnostic asks how often the identical frozen payload-matching rule
produces a mutual-unique match between files belonging to different CIDs. It is
a collision/background screen, not a new main test.

## Frozen universe

1. Rebuild the same 69-candidate map and parse the same candidate files.
2. Form every unordered candidate-file pair with different CID.
3. Retain a pair only when its unordered source-directory combination occurs
   among the 48 frozen same-CID main pairs.
4. Do not use residuals, fitted values, covariance values, redshift, or H0.

## Frozen comparison

Apply the main contract's displayed-precision rounding-compatibility rule to
`FLUXCAL`, `FLUXCALERR`, `MAG`, and `MAGERR`, including its mutual-uniqueness
requirement. Record candidate-pair count, observation-pair opportunity count,
positive pair count, mutual-unique match count, and results stratified by
unordered source-directory combination.

The diagnostic does not use the secondary near-match or 0.11-day rules to
select matches. It reports them only for the four already protected main
matches.

## Interpretation boundary

Cross-CID files are not exchangeable controls for same-CID files: they differ
in brightness, sampling, and observation count. Therefore no p-value,
significance, causal attribution, or correction is computed. A nonzero control
collision rate weakens the specificity of isolated main matches; a zero rate
would still not prove shared physical exposures. The diagnostic cannot modify
the main Phase 1F pair ledger, main counts, formal status, or scientific
classification.

