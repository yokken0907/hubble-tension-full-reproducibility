# Final internal validation and closure audit

## Formal disposition

```text
FINAL_INTERNAL_VALIDATION = PASS
PROJECT_INTERNAL_VALIDATION_PROGRAM = CLOSED_WITH_SCOPE
ACTIVE_INTERNAL_SCIENTIFIC_BRANCH = NONE
STOP_CURRENT_FROZEN_EVIDENCE = YES
EXTERNAL_REPLICATION_AND_OFFICIAL_PRODUCT_GATES = OPEN
PUBLICATION_DRAFTING = NOT_PERFORMED
```

The three input archives matched their declared SHA-256 values and passed ZIP
CRC checks. Their bundled verifiers passed: first-season manifest 36 plus
embedded ZIP CRC, second season 32/32, cross-season package 56/56, and 18/18
direct checks against both masters.

## H0DN singular-covariance result

The frozen 255-by-255 covariance has rank 183. Four project-internal solver
paths—SciPy Moore-Penrose, explicit `gesvd`, symmetric `evd`, and retained-
support whitening plus `gelsy`—all reproduced the diagonal-standardization
shift. Their standardized-minus-original H0 shifts ranged only from
`-0.05244542261242` to `-0.05244542261043` km/s/Mpc.

An 80-decimal-digit solve of the constructed normal systems gave
`-0.05244542261171722333...` km/s/Mpc. Four dense orthogonal transformations
changed H0 by at most `1.51e-10` km/s/Mpc, while the non-orthogonal mapped-
precision defect was `3.80468e-4` in relative Frobenius norm. The nullspace
projection norms were `1.04e-13` for the design matrix and `0.1887491` for the
data vector.

An exact rational rank-one fixture yielded estimates `1/2` before and `1/5`
after `diag(1,2)` scaling, while an orthogonal rotation retained `1/2`. This
confirms the mechanism without floating point.

The observed H0DN result is therefore strongly consistent with the algebraic
non-covariance of a Moore-Penrose inverse under general non-orthogonal
congruence for a singular problem with an unresolved support inconsistency.
This is internal evidence, not external replication, a corrected H0, or a
choice of a physically preferred representation.

## SN compression

For the frozen 277-row, one-intercept, fixed-covariance Gaussian block, the
complete-square identity was independently verified with maximum residual
`3.41e-13`. The recovered values were

- intercept `0.7163834210954622`,
- standard error `0.0018926416391806472`,
- parameter-independent residual chi-square `206.7606364373241`.

An exact synthetic pair retained the same compressed mean and variance while
having residual chi-squares 2 and 8. Parameter-dependent likelihood
sufficiency and residual-diagnostic sufficiency are therefore distinct within
the stated model. No automatic extension is made to nonlinear, multi-direction,
parameter-dependent-covariance, selection, or generative models.

## Same-CID contrasts and stop rule

No new contrast statistic was introduced. The canonical Phase 1C verifier
passed 24/24 gates and its separate independent verifier passed. Existing
alternative-basis, eigendecomposition, 32 orthogonal-trial, rank/df, and
source-lineage checks already establish robustness to contrast coordinates
within the fixed subspace and covariance transformations.

All other unresolved high-value questions require external replication or new
official products. Further decomposition of the same masters would not close
BBC truth lineage, SN executed-run lineage, the GWTC old comparator, DESI raw
variants, TDCOSMO generation, or the other recorded re-entry gates.

The earlier six-axis working framework is refined—not universally replaced—by
separating algebraic representation equivalence from target-inference
invariance/sufficiency. The resulting seven-coordinate working map is recorded
in `FRAMEWORK_REFINEMENT_JA.md`.

The internal program is closed with scope. Re-entry requires materially new
external evidence, official products, a changed source/model, or a concrete
external review finding.
