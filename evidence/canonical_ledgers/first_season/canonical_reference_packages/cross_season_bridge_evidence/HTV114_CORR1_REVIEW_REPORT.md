# HTV114 CORR1 Review Report

## Review classification

```text
HTV114_CORR1 = ACCEPTED_WITH_SCOPE
PUBLIC_CONTRACT_REPRODUCTION = PASS
RUNTIME_DEFECT_CORRECTED = PASS
COVARIANCE_BLOCK_RECONSTRUCTION = PASS
NUMERICAL_STABILITY = PASS
SCIENTIFIC_RESULT_CHANGED_FROM_HTV113 = NO
```

This is an in-thread review. A separate-thread independent acceptance is not present.

## Package integrity

```text
OUTER_ZIP_SHA256
= ab3f0b632a65318855497847742a96685cec94f783ffc4ac31f52574890a0eb1

SIDECAR_MATCH = PASS
ZIP_CRC       = PASS
members       = 52
internal SHA  = 51/51 PASS
shell exit    = 0
source tree   = clean
```

## Frozen public-contract reproduction

```text
V00 = 73.4987536436 +0.8088000253
      chi2/ndof = 117.5596816821 / 119

V27 = 73.4112302244 +0.7996178526
O1  = 73.1100125471 +0.9200884404
O2  = 73.4338567980 +1.7948171465
```

All expected checks passed.

The O2 result differs slightly from the rounded paper target
`73.451 ±1.777`, but it remains inside the predeclared reproduction tolerance
and is the exact result of the frozen public Python contract.

## Matrix and numerical audit

```text
observation covariance dimension = 255
observation covariance rank      = 183
normal matrix dimension           = 64
normal matrix rank                = 64

minimum covariance eigenvalue
= -2.9344e-17

minimum positive eigenvalue
= 3.5821e-06

nonzero covariance condition
= 5.3274e04

normal-matrix condition
= 1.0114e04
```

The tiny negative eigenvalue is numerical roundoff at the singular boundary,
not evidence of a physically negative covariance mode.

The Moore-Penrose solution is invariant for all tested absolute tolerances from
`1e-14` through `1e-7`:

```text
H0 spread    = 0
sigma spread = 0
rank         = 183 throughout
```

Therefore the very large raw NumPy condition number is caused by the covariance
matrix being intentionally rank deficient; it is not producing solver
instability under the public pseudoinverse contract.

## Host covariance reconstruction

The corrected dimensions are:

```text
host-distance equation rows = 166
unique latent host parameters = 59

len(anchor_index) = 166
len(mas_index)    = 166
len(hms_index)    = 166
```

The exact anchor + MAS + HMS reconstruction gives:

```text
maximum absolute residual
= 2.7105e-20

Frobenius residual
= 1.3299e-18
```

The HTV114 attempt-1 indexing defect is therefore fully corrected.

## Diagnostic covariance ablations

```text
baseline
H0 = 73.49875
sigma = 0.80880

remove anchor off-diagonal:
delta H0 = -0.18107
sigma = 0.66672

remove MAS off-diagonal:
delta H0 = +0.35873
sigma = 0.73210

remove HMS off-diagonal:
delta H0 = -0.20611
sigma = 0.77362

remove all host shared off-diagonal:
delta H0 = -0.16839
sigma = 0.55484
```

The maximum center movement is the MAS diagnostic:

```text
|delta H0| = 0.35873 km/s/Mpc
           = 0.444 baseline-sigma
```

The central high-H0 direction is therefore not produced by one implemented
host-covariance block.

However, removing all host shared correlations reduces the reported uncertainty
by about 31.4 percent. The covariance blocks materially prevent repeated
anchor/host/reference information from being treated as independent.

```text
IMPLEMENTED_SHARED_COVARIANCE_DRIVES_HIGH_CENTER = NO
IMPLEMENTED_SHARED_COVARIANCE_PREVENTS_FALSE_PRECISION = YES
```

## Rank interpretation of the ablations

Each off-diagonal ablation increases the observation-covariance rank from 183
to 255 and changes the nominal degrees of freedom from 119 to 191.

This occurs because the diagnostic destroys the exact covariance links that
identify repeated equations as measurements of shared information. The
ablation values must therefore not be interpreted as plausible alternative
scientific likelihoods.

```text
ABLATION_AS_CORRECTED_H0 = PROHIBITED
ABLATION_SIGMA_AS_REAL_PRECISION = PROHIBITED
ABLATION_AS_INFLUENCE_DIAGNOSTIC = ACCEPTED
```

The equality

```text
REMOVE_ALL_HOST_SHARED_OFFDIAG
=
DIAGONALIZE_ENTIRE_OBSERVATION_COVARIANCE
```

is structurally consistent with the public equation system: Pantheon+ Hubble
flow covariance is first condensed into the scalar SN intercept constraint.
Its exact upstream effect is separately tested by V27.

## Pantheon+ and orthogonal paths

The exact V27 change is small:

```text
delta H0    = -0.08752
delta sigma = -0.00918
```

The data-orthogonal paths reproduce:

```text
O1 = 73.11001 ±0.92009
O2 = 73.43386 ±1.79482

display difference = 0.16056
weighted mean      = 73.17741 ±0.81877
```

O1 supplies about 79.2 percent of the inverse-variance weight, so this remains
an orthogonal data-graph confirmation rather than two equally precise votes.

## Final scientific classification

```text
H0DN_PUBLIC_CODE_NUMERICAL_FAILURE
= NO

H0DN_IMPLEMENTED_COVARIANCE_ARCHITECTURE
= EXACTLY_REPRODUCED

LOCAL_HIGH_H0_CENTER_SENSITIVITY_TO_IMPLEMENTED_COVARIANCE
= SMALL_TO_MODERATE_AND_NON_DECISIVE

LOCAL_HIGH_H0_CONDITIONAL_PRECISION_DEPENDS_MATERIALLY_ON_SHARED_COVARIANCE
= YES

FULL_CROSS_METHOD_COVARIANCE_CLOSURE
= NO

FULL_SYSTEMATICS_MARGINALIZATION
= NO

HUBBLE_TENSION_RESOLVED
= NO
```

HTV113's central conclusion is strengthened:

```text
LOCAL_HIGH_H0_DATA_GRAPH_ROBUSTNESS = STRONG
LOCAL_HIGH_H0_FULL_SYSTEMATICS_CLOSURE = INCOMPLETE
```

## Branch status

```text
HTV114_PUBLIC_CODE_AND_NUMERICAL_STABILITY_BRANCH
= CLOSED_WITH_SCOPE

IDL_CROSS_IMPLEMENTATION_CHECK
= NOT_EXECUTED_NONFATAL

UNIMPLEMENTED_CROSS_METHOD_SYSTEMATICS
= REMAIN_OPEN
```
