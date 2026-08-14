# Final internal validation and closure contract

Contract ID: `HT-FINAL-INTERNAL-CLOSURE-20260809-01`

Frozen at: `2026-08-09T15:34:39Z`

Status at freeze: `FROZEN_BEFORE_NEW_INTERNAL_VALIDATION_OUTPUTS`

## Purpose

This contract governs the final project-internal validation before publication
design. It does not authorize a new H0 estimate, a correction, a causal
attribution, a Hubble-tension resolution, or a paper draft.

The decision rule is information gain, not the availability of another
calculation. A new check is admitted only if either outcome could materially
change confidence in a bounded claim or the decision to stop.

## Scientific source identities

1. `HUBBLE_TENSION_FIRST_SEASON_MASTER_REFERENCE_PACKAGE_v1.0.0.zip`
   - SHA-256: `3e6df9f557485de1bb21c54bb129af78943e8e5d08da036e648d251dd952663c`
2. `HUBBLE_TENSION_SECOND_SEASON_MASTER_REFERENCE_PACKAGE_v1.0.0.zip`
   - SHA-256: `cc15c96a45865f22fcd13c2ef03c8cccc39af8fa6dcace4a25f229d07e964940`
3. `HUBBLE_TENSION_CROSS_SEASON_AUDIT_PACKAGE_v0.1.0.zip`
   - SHA-256: `9719fae4cbfefeca5ec9e8f04f7949f1a1bdb21d784523752a587ecd166e60cf`
   - Role: review record only; it does not override either season master.
4. H0DN source commit:
   `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`.
5. PantheonPlusSH0ES/DataRelease source commit:
   `c447f0fea703fcd0fff57de5000947b5ca81286b`.

## Admitted new validations

### IV-H0DN-01: actual-matrix decomposition and support check

The untouched H0DN source workflow supplies the frozen `A`, `y`, and `C` test
vector. Matrix construction is therefore not independently reimplemented;
the linear-algebra solution and diagnostics are project-internal independent
reimplementations.

The following paths are fixed:

- SciPy Moore-Penrose reference with absolute cutoff `1e-10`, relative cutoff
  zero;
- an explicit SVD reconstruction using LAPACK `gesvd`;
- a symmetric eigendecomposition reconstruction using LAPACK `evd`;
- a retained-support whitening plus least-squares formulation;
- an 80-decimal-digit solution of the already constructed 64-by-64 normal
  systems, used only to test whether the final normal solve explains the
  observed difference;
- four dense orthogonal equation-coordinate transformations from fixed seed
  `20260809`;
- the exact diagonal row standardization already used by the canonical audit.

Pre-fixed gates:

- covariance rank is `183` in both original and standardized coordinates;
- baseline H0 differs from `73.49875364360662` by at most `5e-9` km/s/Mpc;
- every admitted implementation reproduces a standardized-minus-original H0
  shift within `5e-8` km/s/Mpc of `-0.052445422611000936`;
- the spread of that shift across implementations is at most `5e-8`
  km/s/Mpc;
- the 80-digit normal solve differs from its double-precision input-system
  solve by at most `5e-9` km/s/Mpc in each coordinate system;
- the largest dense-orthogonal H0 change is at most `5e-8` km/s/Mpc;
- the mapped Moore-Penrose precision defect under non-orthogonal scaling is
  greater than `1e-6` in relative Frobenius norm;
- original-coordinate null projection of `A` is at most `1e-10` in Frobenius
  norm, while that of `y` is greater than `1e-4` in L2 norm.

Passing these gates supports a numerical/mathematical mechanism claim for this
fixed formulation. It is not external replication and does not validate an
unrounded or latent generative model.

### IV-H0DN-02: exact rational mechanism fixture

Use

- `C = [[1,1],[1,1]]`,
- `A = [[1],[1]]`,
- `y = [1,0]`,
- non-orthogonal `S = diag(1,2)`.

The exact expected Moore-Penrose GLS estimates are `1/2` before scaling and
`1/5` after scaling. An exact orthogonal 90-degree rotation must retain `1/2`.
The covariance rank remains one and the degenerate-Gaussian support equations
remain infeasible because a covariance-null vector annihilates `A` but not
`y`.

This fixture establishes mechanism possibility exactly; it does not establish
that the H0DN scientific model is physically wrong.

### IV-SN-01: one-intercept sufficiency identity and diagnostic loss

Independently parse the frozen 277-row H0DN SN Ia input and covariance, rebuild
the fixed cosmographic one-intercept block, and verify by Cholesky and symmetric
eigendecomposition that

`(d-1*a)^T C^-1 (d-1*a) = chi2_min + (a-a_hat)^2 / V`

on the fixed offset grid `[-8,-4,-1,0,1,4,8]` in units of `sqrt(V)`.

Pre-fixed gates:

- row count is `277` and covariance shape is `277 x 277`;
- `a_hat` differs from `0.7163834210954622` by at most `5e-13`;
- `sqrt(V)` differs from `0.0018926416391806472` by at most `5e-13`;
- `chi2_min` differs from `206.76063643732414` by at most `5e-10`;
- Cholesky/eigendecomposition discrepancies are at most `5e-10`;
- maximum complete-square residual is at most `5e-9`.

An exact synthetic pair with common covariance must also have identical
`(a_hat,V)` but different residual chi-square. This distinguishes target-
parameter sufficiency from diagnostic sufficiency without claiming universal
minimal sufficiency for arbitrary models.

## Existing-result revalidation without a new scientific branch

### EV-SAMECID-01

Phase 1C is not redefined. Its existing canonical checks already contain a
separate parser/null-space/eigendecomposition verifier, an alternative
contrast basis, 32 orthogonal-coordinate trials, rank/df bookkeeping, and
five covariance baselines. The final audit only reruns the canonical verifier
and independent verifier against the two frozen source commits and records
the result. No new contrast statistic, threshold, row selection, covariance
model, or classification is authorized.

An input-placement failure may be corrected by supplying the byte-identical
locked source file. It must be logged and is not a scientific failure.

## Rejected additions

The following are rejected before new outputs:

- further pseudoinverse cutoff sweeps or row permutations;
- more same-CID bases after the canonical alternative-basis and orthogonal
  tests pass;
- row deletion, averaging, reweighting, covariance shrinkage, or a corrected
  covariance;
- another BBC downstream slope decomposition without a matched truth-level
  bundle;
- substitution for the GWTC old-side comparator;
- inferred SN run ancestry from public candidate files;
- more TDCOSMO endpoint plots or quantile runs;
- automatic expansion of any HOLD because it is open;
- drafting a title, abstract, introduction, or submission manuscript.

## Closure rule

The project-internal validation program may be declared `STOP` only if:

1. all admitted new validations pass or are boundedly reclassified without
   erasing earlier results;
2. canonical package/source verifiers pass after any documented
   input-placement correction;
3. no remaining open item can be closed by current internal evidence without
   inventing an unsupported model, source, or provenance link;
4. external replication, new official products, and publication are kept as
   separate future routes.

A STOP declaration closes repeated internal analysis of the current frozen
evidence. It does not close the scientific questions to external evidence.
