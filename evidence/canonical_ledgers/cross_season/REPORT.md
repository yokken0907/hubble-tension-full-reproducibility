# Cross-season audit of the Hubble-tension 1st and 2nd seasons

## Disposition

```text
CROSS_SEASON_AUDIT = COMPLETE_WITH_SCOPE
FIRST_SEASON_MAP = RETAINED_WITH_MATERIAL_LATER_QUALIFICATIONS
TRUE_CROSS_SEASON_SCIENTIFIC_CONTRADICTIONS = 0
CORRECTED_H0 = NOT ESTABLISHED
HUBBLE_TENSION_CAUSE_OR_RESOLUTION = NOT ESTABLISHED
NEW_PHYSICS = NOT ESTABLISHED
```

This audit used only the two season master packages and their embedded canonical packages. No external source, likelihood, MCMC, posterior generation, corrected-H0 calculation, or new large analysis was added.

## Main finding

The first-season scientific map remains valid as a broad dependency and traceability map. The second season did not independently retest the BAO, DESI, CMB, ACT, MCP/CF4, or lensed-supernova branches. It revisited a narrower set of questions: GWTC posterior traceability, Pantheon+ BBC truth-closure readiness, H0DN singular covariance, and H0DN SN Ia residual and lineage diagnostics.

No later result requires silently rewriting a first-season formal judgment. Several results do require important later qualifications.

### H0DN numerical stability

HTV114 and B03A reproduce the same public baseline:

- HTV114 H0: `73.49875364360406`
- B03A H0: `73.49875364360662`
- difference: `+2.56e-12 km/s/Mpc`
- covariance rank: 183 in both records

The original result—stability under the frozen representation, solver policy, and tested pseudoinverse cutoffs—is retained. B03A later showed that an exactly equivalent non-orthogonal row scaling changes H0 by `-0.052445422611000936 km/s/Mpc`. Thus fixed-representation stability does not establish general representation invariance. B03A also records `HOLD_INCONSISTENT_SUPPORT` for the literal degenerate-Gaussian interpretation because `P0 A` is numerically zero while `||P0 y||2 = 0.1887490826897376 mag`.

These are numerical and statistical-model qualifications, not a corrected H0 or a finding that the public value is wrong.

### SN Ia compression and residual diagnostics

Within the frozen one-intercept, fixed-covariance model, the 277-row Hubble-flow block compresses exactly to the scalar intercept and its variance for network-parameter and H0 inference. The same compression discards a parameter-independent residual term of `206.76063643732414`.

The residual deficit localizes disproportionately to 39 same-name contrast degrees of freedom (`11.209315/39`) and persists through the public STATONLY covariance (`16.233448/39`). The 277 rows map one-to-one to the official 277 Hubble-flow rows, and the mapped 277×277 STAT+SYS covariance is exactly equal in all 76,729 float64 elements.

Public input candidates and configuration dependencies were traced with scope, but the executed-run-to-final-`m_b_corr` lineage remains unestablished. No covariance overestimation, duplicate-row error, survey cause, row deletion, or corrected H0 follows.

### Pantheon+ BBC

HTV29’s algebraic localization is retained: the recorded fixed-effect slope in the released corrected vector closes as a near-zero bias-removed proxy plus the explicit BBC term. The second-season source-readiness audit did not refute that algebra.

It instead established that the fixed public record does not uniquely close:

`BiasCor truth -> matched fit -> BBC pre/post vector -> corresponding covariance`.

The truth-level execution therefore remains `HOLD_SOURCE_INCOMPLETE`. This is not evidence for BBC overcorrection or pipeline error.

### GWTC

The first-season GWTC `FROZEN_OPEN` state was only partially resolved. B01 reproduced the frozen GWTC-4 and GWTC-5 one-decimal headline quantiles, but the exact old-side posterior bytes behind the published 25.7% comparator remain non-unique in the official public record. The 28.547849% headline-pair diagnostic is not the 25.7% reproduction.

### TDCOSMO and output traceability

The first-season project-internal alternate implementation recovered the fixed Table 6 output quantities within preregistered tolerance. Together with GWTC, this provides two distinct examples in which successful output recovery does not reproduce the originating likelihood, sampler, convergence diagnostics, or posterior-generation pipeline.

## Revised evidence model

The proposed three-layer model is directionally supported but too compressed. The combined records support a six-axis evidence vector:

1. artifact identity and authority;
2. numerical/output traceability;
3. mathematical equivalence and representation invariance;
4. diagnostic sufficiency and adequacy;
5. executed lineage and provenance;
6. generative and causal closure.

These axes are not a strict ladder. Output reproduction can pass while representation invariance fails; parameter sufficiency can pass while residual diagnostics are lost; source bytes can be fixed while executed lineage remains open.

## Contradictions

No genuine scientific contradiction was found after matching proposition, source/product, contract, quantity, and time. Apparent conflicts were resolved as scope or chronology differences, including:

- fixed H0DN stability versus general non-orthogonal non-invariance;
- parameter-sufficient SN compression versus residual-information loss;
- GWTC files missing in the earlier record versus later headline products becoming available;
- BBC downstream algebraic localization versus missing truth-level execution lineage;
- the dated pre-closeout TDCOSMO record versus the later first-season closeout.

## Current Hubble-tension boundary

The combined evidence supports a stronger map of what is reproducible and what remains dependent on representation, compression, covariance, and provenance. It does not support a corrected or preferred H0, a revised tension significance, a unique systematic cause, BBC overcorrection, a defective named pipeline, tension resolution, or new physics.

## Highest-value re-entry conditions

The most valuable unresolved areas require new evidence rather than more decomposition of the same masters:

1. external numerical/statistical replication of the H0DN representation and support findings, plus unrounded inputs or the covariance-generation/latent-variable model;
2. an official versioned BBC truth/fit/pre-post/covariance/run bundle;
3. exact SN photometry-to-FITRES-to-bias-correction-to-final-row lineage and dependence construction;
4. aligned DESI raw robustness products and cross-fit covariance;
5. MCP/CF4 joint flow covariance, samples, and likelihood;
6. the exact old-side GWTC posterior registry for the 25.7% metric.

No automatic same-data branch expansion is justified by this audit.

## Publication architecture

The most natural structure is one synthesis/methods paper plus two technical papers:

1. multi-axis reproducibility and executed-lineage gaps across public H0 inference;
2. H0DN singular covariance, Moore–Penrose non-invariance, and degenerate-Gaussian support;
3. SN Ia parameter-sufficient compression, localized residual deficit, covariance provenance, and public-lineage frontier.

GWTC, TDCOSMO, and BBC source-readiness are best used as bounded case studies or technical supplements unless developed as short provenance notes. A single giant paper would mix heterogeneous claims and make it easier to overcount stages or shared sources as independent evidence.
