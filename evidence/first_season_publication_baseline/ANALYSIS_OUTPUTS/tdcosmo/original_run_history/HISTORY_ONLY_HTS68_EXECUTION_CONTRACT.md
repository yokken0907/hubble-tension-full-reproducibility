# HTS68 execution contract

## Stage

`TDCOSMO2025_PUBLIC_CHAIN_CONTRACT_AND_DEPENDENCY_AUDIT`

## Frozen question

The HTV136 re-entry condition for the TDCOSMO branch required public HDF5
posterior chains to be locally available and contract-audited. Once that source
condition is met:

1. do the public exports reproduce the published flat-LambdaCDM H0 results; and
2. which released posterior layer controls the movement of H0 and the internal
   mass-sheet population mean?

## Frozen sources

- official repository:
  `https://github.com/TDCOSMO/TDCOSMO2025_public.git`
- exact commit:
  `d7f38db341f68be1df0d9ac1fc528c45113f94cf`
- paper:
  `https://arxiv.org/pdf/2506.03023`

## Operations

- validate the exact set of 28 HDF5 posterior exports;
- hash every export and validate datasets, attributes, dimensions and finiteness;
- reproduce the 12 flat-LambdaCDM H0 rows in paper Table 6;
- build an explicit paper/release identifier crosswalk;
- compare nested external-lens layers within four fixed auxiliary-cosmology
  contexts;
- audit whether the public code and metadata are sufficient for exact
  convergence and likelihood reexecution.

## Gates

- exact 28-file chain set;
- every file opens as HDF5;
- every export has `parameters` and `samples`;
- 500,000 finite rows per export;
- parameter dimensions and embedded model identifiers agree;
- 12/12 published flat-LambdaCDM H0 rows reproduce at reported precision.

## Boundaries

Nested posterior shifts share data and hierarchical assumptions. They are not
independent significances, likelihood-ratio tests, causal component
attributions, corrected H0 values, or evidence that the Hubble tension is
resolved.
