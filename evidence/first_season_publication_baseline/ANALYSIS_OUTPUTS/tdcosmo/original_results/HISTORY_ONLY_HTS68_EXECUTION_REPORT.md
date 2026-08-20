# HTS68 execution report

`PASS_TDCOSMO2025_PUBLIC_CHAIN_DEPENDENCY_RECONSTRUCTION_WITH_SCOPE`

## Outcome

The HTV136 TDCOSMO re-entry trigger is now met: the official public
repository supplies 28 HDF5 posterior exports and likelihood-preparation
materials. All 28 HDF5 files open successfully, contain 500,000 finite
rows, have internally consistent parameter dimensions, and match their
embedded model identifiers.

The released chains reproduce 12/12 flat-LambdaCDM H0 rows in the paper's Table 6 at the published precision.

## Key posterior layers

| Release model | Dataset layer | H0 median (16th, 84th) | lambda_mst median |
|---|---|---:|---:|
| ULambdaCDM1 | TDCOSMO | 73.7 (-4.4/+4.7) | 0.996 |
| ULambdaCDM4 | TDCOSMO + SLACS + SL2S | 77.8 (-4.7/+3.7) | 1.064 |
| LambdaCDM1d | TDCOSMO + Pantheon+ + SLACS + SL2S | 74.3 (-3.7/+3.1) | 1.025 |
| LambdaCDM2d | TDCOSMO + DES-SN5YR + SLACS + SL2S | 73.9 (-3.0/+3.4) | 1.026 |
| LambdaCDM3b | TDCOSMO + DESI BAO + SLACS + SL2S | 74.8 (-3.4/+3.5) | 1.035 |

Across all four flat-LambdaCDM auxiliary-cosmology contexts, adding
SLACS+SL2S moves both the H0 median and the internal mass-sheet
population mean upward. Where SLACS and SL2S are separately released,
the SLACS shift is larger in every comparable context. This localizes
the dominant released-posterior dependency to the external-lens
population layer, primarily SLACS. It does not establish a causal
systematic or an independent shift significance.

## Contract warning

The paper identifier `ΛCDM2b` denotes the DES-SN5YR posterior with
SLACS+SL2S. In the expanded chain release, `LambdaCDM2b.h5` is SLACS
only; the paper row is reproduced by `LambdaCDM2d.h5`. Dataset
attributes, not filenames alone, are therefore authoritative.

## Remaining hold

Exact MCMC convergence and exact likelihood reexecution are not
independently closed. The exports omit walker/time, burn-in, thinning,
seed, weights and log-probability metadata. The supplied sampling code
also contains site-specific absolute paths, the README references an
absent example config, and no pinned dependency environment is present.

## Boundary

This is a posterior-contract and dependency audit. It is not an
independent tension significance, a corrected H0, a causal mass-sheet
attribution, or evidence that the Hubble tension is resolved.
